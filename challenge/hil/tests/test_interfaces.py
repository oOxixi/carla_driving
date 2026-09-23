from __future__ import annotations

import os
from pathlib import Path

import pytest

from ..contract import NOT_RUN, check_runtime_contract
from ..identity import CandidateIdentity, sha256_file
from ..runtime_adapter import RuntimeCapabilities, split_command
from ..tensors import dump_tensors_for_request, load_tensor_dump, output_checksums
from .fakes import FakeRuntime


class _InterfaceRuntime(FakeRuntime):
    """FakeRuntime plus the three entries the interface checks drive."""

    def __init__(self, *, describe_payload=None, batch_error=None, model_only_result=None):
        super().__init__()
        self.identity = CandidateIdentity(
            git_sha="0" * 40,
            model_id="fake-model",
            model_sha256="1" * 64,
            dataset_version="fake-dataset-v1",
            config_id="fake-config",
        )
        self.capabilities = RuntimeCapabilities(
            full_chain=True, model_only=True, plan_validator=True, stage_source="INSTRUMENTED"
        )
        self._describe = describe_payload
        self._batch_error = batch_error
        self._model_only = model_only_result

    def describe(self):
        if self._describe is None:
            raise RuntimeError("no describe in this fake")
        return self._describe

    def run_batch(self, requests):
        if self._batch_error is not None:
            raise RuntimeError(self._batch_error)
        return [
            {
                "request_id": request["request_id"],
                "command_id": request["command_id"],
                "steps": [{"behavior": "FOLLOW"}],
            }
            for request in requests
        ]

    def run_model_only(self, tensor_dir, *, iterations=1):
        if self._model_only is None:
            raise RuntimeError("no model-only in this fake")
        return dict(self._model_only)


def _request(index: int = 0) -> dict:
    return {
        "request_id": f"req-{index}",
        "command_id": f"cmd-{index}",
        "source_text": "keep lane",
        "targets": [],
        "created_at_ns": 1_000,
        "scene_summary": {"traffic_light": "GREEN", "risk_level": "LOW"},
        "constraints": {"must_stop": False, "allowed_behaviors": ["FOLLOW", "KEEP_LANE"]},
        "command_hint": {"intent": "KEEP_LANE"},
    }


def _full_describe(digest: str) -> dict:
    return {
        "git_sha": "0" * 40,
        "model_id": "fake-model",
        "model_sha256": digest,
        "dataset_version": "fake-dataset-v1",
        "config_id": "fake-config",
        "precision": "int8",
        "batch": 1,
        "input_shapes": {"rgb": [1, 3, 224, 224]},
    }


def test_interface_checks_pass_for_a_complete_runtime():
    runtime = _InterfaceRuntime(
        describe_payload=_full_describe("1" * 64),
        model_only_result={"status": "OK", "mode": "board", "outputs": {"head": "ab"}},
    )
    report = check_runtime_contract(
        runtime,
        [_request()],
        expected_model_sha256="1" * 64,
        model_only_tensor_dir="dump",
    )
    by_name = {item["check"]: item for item in report["checks"]}
    assert by_name["describe_endpoint"]["status"] == "PASS"
    assert by_name["describe_matches_artifact"]["status"] == "PASS"
    assert by_name["batch_mode"]["status"] == "PASS"
    assert by_name["model_only_mode"]["status"] == "PASS"
    assert report["passed"] is True


def test_describe_mismatch_and_missing_fields_fail():
    runtime = _InterfaceRuntime(describe_payload={"model_id": "fake-model"})
    report = check_runtime_contract(
        runtime, [_request()], expected_model_sha256="2" * 64
    )
    by_name = {item["check"]: item for item in report["checks"]}
    assert by_name["describe_endpoint"]["status"] == "FAIL"
    assert "git_sha" in by_name["describe_endpoint"]["detail"]
    assert report["passed"] is False


def test_batch_failure_is_reported_with_the_reason():
    runtime = _InterfaceRuntime(
        describe_payload=_full_describe("1" * 64),
        batch_error="returned 1 plans for 2 requests",
    )
    report = check_runtime_contract(runtime, [_request(0), _request(1)])
    by_name = {item["check"]: item for item in report["checks"]}
    assert by_name["batch_mode"]["status"] == "FAIL"
    assert "1 plans for 2 requests" in by_name["batch_mode"]["detail"]


def test_model_only_without_a_dump_is_not_run_and_not_a_failure():
    runtime = _InterfaceRuntime(describe_payload=_full_describe("1" * 64))
    report = check_runtime_contract(runtime, [_request()])
    by_name = {item["check"]: item for item in report["checks"]}
    assert by_name["model_only_mode"]["status"] == NOT_RUN
    assert by_name["model_only_mode"]["status"] != "FAIL"
    assert report["passed"] is True


def test_model_only_without_output_digest_fails():
    runtime = _InterfaceRuntime(
        describe_payload=_full_describe("1" * 64),
        model_only_result={"status": "NO_OUTPUT_DIGEST", "mode": "board", "outputs": None},
    )
    report = check_runtime_contract(runtime, [_request()], model_only_tensor_dir="dump")
    by_name = {item["check"]: item for item in report["checks"]}
    assert by_name["model_only_mode"]["status"] == "FAIL"


def test_tensor_dump_round_trip_and_tamper_detection(tmp_path: Path):
    repo = Path(__file__).resolve().parents[3]
    out = tmp_path / "dump"
    manifest = dump_tensors_for_request(
        repo, _request(), out, case_id="case#0001", frame_label="SCENE_A"
    )
    assert manifest["case_id"] == "case#0001"
    assert set(manifest["files"]) == {
        "rgb.npy",
        "text_tokens.npy",
        "targets.npy",
        "state.npy",
    }
    arrays, loaded = load_tensor_dump(out)
    assert loaded["request_sha256"] == manifest["request_sha256"]
    assert arrays["rgb"].shape == (1, 3, 224, 224)
    assert arrays["text_tokens"].shape == (1, 32)
    digests = output_checksums({"head": arrays["rgb"]})
    assert len(digests["head"]) == 64

    (out / "state.npy").write_bytes(b"not the dumped tensor")
    with pytest.raises(ValueError, match="changed since it was dumped"):
        load_tensor_dump(out)


@pytest.mark.skipif(os.name != "nt", reason="Windows path splitting only")
def test_split_command_keeps_windows_backslashes():
    argv = split_command(r'"C:\tools\python.exe" "C:\work dir\run.py" --trace')
    assert argv == [r"C:\tools\python.exe", r"C:\work dir\run.py", "--trace"]


def test_dump_records_the_artifact_digest_it_used(tmp_path: Path):
    repo = Path(__file__).resolve().parents[3]
    out = tmp_path / "dump2"
    manifest = dump_tensors_for_request(repo, _request(3), out)
    for entry in manifest["files"].values():
        assert len(entry["sha256"]) == 64
        assert entry["size_bytes"] > 0
    assert manifest["request_id"] == "req-3"
    assert sha256_file(out / "rgb.npy") == manifest["files"]["rgb.npy"]["sha256"]
