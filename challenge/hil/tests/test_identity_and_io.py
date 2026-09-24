from __future__ import annotations

import json
from pathlib import Path

import pytest

from ..identity import (
    UNRESOLVED,
    CandidateIdentity,
    identity_from_artifact,
    identity_from_weight_manifest,
    sha256_file,
)
from ..run_io import RunDir, read_jsonl, write_csv, write_jsonl
from ..samplers import cpu_calibration_ms, machine_load_percent, power_source, sample_process_memory


def test_cpu_calibration_returns_a_positive_duration():
    value = cpu_calibration_ms(repeats=2, size=128)
    assert value is None or value > 0


def test_power_source_is_one_of_the_known_states():
    assert power_source() in {"AC", "BATTERY", "UNKNOWN"}


def test_machine_load_is_a_percentage_or_none():
    value = machine_load_percent(interval_s=0.1)
    assert value is None or 0.0 <= value <= 100.0 * 64


def test_process_memory_backends_agree_and_return_plausible_values():
    """The psutil-free fallback must work: it is the path a bare board env hits."""
    import sys

    psutil_result = None
    try:
        import psutil  # noqa: F401

        psutil_result = sample_process_memory("psutil")
    except ImportError:
        pass

    if sys.platform == "win32":
        fallback = sample_process_memory("win32_psapi")
    else:
        fallback = sample_process_memory("proc_status")
    assert fallback["rss_kib"] and fallback["rss_kib"] > 0
    assert fallback["peak_rss_kib"] >= fallback["rss_kib"]
    assert fallback["source"] in {"win32_psapi", "proc_status"}

    if psutil_result is not None:
        # Two independent readers of the same process must agree to within 20%.
        ratio = fallback["rss_kib"] / psutil_result["rss_kib"]
        assert 0.8 < ratio < 1.2, (fallback, psutil_result)


def test_unknown_memory_backend_is_rejected():
    import pytest

    with pytest.raises(ValueError):
        sample_process_memory("psychic")


def test_identity_defaults_are_never_complete():
    identity = CandidateIdentity()
    assert identity.complete is False
    assert set(identity.missing()) == {
        "git_sha",
        "model_id",
        "model_sha256",
        "dataset_version",
        "config_id",
    }
    assert identity.to_dict()["complete"] is False


def test_identity_rejects_malformed_sha():
    with pytest.raises(ValueError):
        CandidateIdentity(git_sha="abc")


def test_weight_manifest_hash_is_recomputed(tmp_path: Path):
    weights = tmp_path / "student.pt"
    weights.write_bytes(b"not-really-weights")
    digest = sha256_file(weights)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "git_sha": "a" * 40,
                "model_id": "student-v0-r3-fp32",
                "weights_sha256": digest,
                "dataset_version": "teacher_distill_v1",
                "config_id": "cfg",
                "gate_status": "A3_FP32_GATE_PASSED",
            }
        ),
        encoding="utf-8",
    )
    identity = identity_from_weight_manifest(weights, manifest)
    assert identity.complete
    assert identity.model_sha256 == digest

    tampered = json.loads(manifest.read_text(encoding="utf-8"))
    tampered["weights_sha256"] = "0" * 64
    manifest.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(ValueError, match="SHA256 mismatch"):
        identity_from_weight_manifest(weights, manifest)


def test_identity_from_artifact_uses_the_real_file(tmp_path: Path):
    artifact = tmp_path / "model.onnx"
    artifact.write_bytes(b"onnx")
    identity = identity_from_artifact(artifact, model_id="m", config_id="c")
    assert identity.model_sha256 == sha256_file(artifact)
    assert identity.git_sha == UNRESOLVED


def test_identity_reads_a3_nested_candidate_identity_layout(tmp_path: Path):
    """A3's handoff_manifest.json nests the identifiers under `candidate_identity`."""
    weights = tmp_path / "student_v0_fp32_candidate.pt"
    weights.write_bytes(b"pure-state-dict")
    digest = sha256_file(weights)
    manifest = tmp_path / "handoff_manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "package_status": "PENDING_B2_INDEPENDENT_VALIDATION",
                "gate_status": "PENDING_A3_FP32_GATE",
                "candidate_identity": {
                    "git_sha": "1" * 40,
                    "model_id": "student-v0-r3-fp32",
                    "config_id": "student-v0-r3-structure-20260911",
                    "weights_sha256": digest,
                    "dataset_version": "b1_d2_v1_1_plus_d3_wave1_a3_strict_positive_v1",
                },
                "files": {"student_v0_fp32_candidate.pt": {"sha256": digest}},
            }
        ),
        encoding="utf-8",
    )
    identity = identity_from_weight_manifest(weights, manifest)
    assert identity.complete, identity.missing()
    assert identity.model_id == "student-v0-r3-fp32"
    assert identity.git_sha == "1" * 40
    assert identity.gate_status == "PENDING_A3_FP32_GATE"
    assert identity.verification["layout"] == "nested_candidate_identity"
    assert identity.verification["reported_weights_sha256"] == digest

    # A candidate that is still pending must not be promoted by the gate checks.
    from ..gate import gate_verified

    assert gate_verified(identity) is False

    # Tampering with the nested digest is still rejected.
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["candidate_identity"]["weights_sha256"] = "0" * 64
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="SHA256 mismatch"):
        identity_from_weight_manifest(weights, manifest)


def test_csv_writer_rejects_columns_outside_the_schema(tmp_path: Path):
    with pytest.raises(ValueError):
        write_csv(tmp_path / "x.csv", ("a", "b"), [{"a": 1, "b": 2, "c": 3}])


def test_jsonl_round_trip_and_manifest(tmp_path: Path):
    path = write_jsonl(tmp_path / "rows.jsonl", [{"a": 1}, {"a": 2}])
    assert read_jsonl(path) == [{"a": 1}, {"a": 2}]

    run = RunDir(tmp_path / "runs", "run-1")
    write_jsonl(run.path("hil_replay.jsonl"), [{"a": 1}])
    run.write_hardware_env({"device_class": "X86_WORKSTATION"})
    manifest = run.build_manifest(
        identity=CandidateIdentity(),
        claim_scope="X86_PRE_VALIDATED",
    )
    assert manifest["claim_scope"] == "X86_PRE_VALIDATED"
    assert "hil_replay.jsonl" in manifest["files"]
    assert "measurement_manifest.json" not in manifest["files"]
    assert manifest["files"]["hil_replay.jsonl"]["sha256"]


def test_run_dir_refuses_to_reuse_an_id(tmp_path: Path):
    RunDir(tmp_path, "same-id")
    with pytest.raises(FileExistsError):
        RunDir(tmp_path, "same-id")
