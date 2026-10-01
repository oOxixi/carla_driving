"""Fail-closed B1 closeout and A3 candidate intake checks for A2.

The quantizer must not infer that an artifact is current merely because its
weights hash is internally consistent.  Formal A2 work is also bound to B1's
latest governed dataset closeout and to the exact A3 handoff trained from it.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from challenge.hil.identity import identity_from_weight_manifest, sha256_file


B1_CLOSEOUT_RELATIVE = Path("challenge/dataset/governance/b1_closeout_v1")
B1_GOVERNED_DATASET_VERSION = "b1_governed_dataset_closeout_v1"
B1_CALIBRATION_VERSION = "b1_calibration_v1"
B1_INDEPENDENT_VALIDATION_VERSION = "b1_independent_validation_v1"

_REQUIRED_LEDGER_FILES = (
    "B1_CLOSEOUT_REPORT.json",
    "B1_HANDOFF.md",
    "attestations/gap300_provenance_binding.json",
    "attestations/ms34_teacher_provenance_addendum.json",
    "calibration_identity.json",
    "governed_release_manifest.json",
    "independent_validation_v1/case_manifest.json",
    "independent_validation_v1/case_set_digest.json",
    "independent_validation_v1/cases.jsonl",
    "independent_validation_v1/dataset_identity.json",
    "independent_validation_v1/source_release_binding.json",
    "leakage_audit.json",
    "teacher_provenance_registry.json",
)


def _json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _git_canonical_digest_and_size(path: Path, expected_sha256: str) -> tuple[str, int]:
    """Verify raw bytes, allowing only Git's Windows CRLF checkout transform."""
    raw = path.read_bytes()
    raw_digest = hashlib.sha256(raw).hexdigest()
    if raw_digest.lower() == expected_sha256.lower():
        return raw_digest, len(raw)
    if b"\r\n" in raw:
        canonical = raw.replace(b"\r\n", b"\n")
        canonical_digest = hashlib.sha256(canonical).hexdigest()
        if canonical_digest.lower() == expected_sha256.lower():
            return canonical_digest, len(canonical)
    raise ValueError(
        f"content SHA256 mismatch for {path}: expected={expected_sha256} actual={raw_digest}"
    )


def _canonical_text_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _repo_label(path: Path, repo: Path) -> str:
    try:
        return path.relative_to(repo).as_posix()
    except ValueError:
        return str(path)


def _verified_ledger(root: Path) -> dict[str, str]:
    ledger_path = root / "SHA256SUMS"
    declared: dict[str, str] = {}
    for number, raw in enumerate(ledger_path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        parts = raw.strip().split(None, 1)
        if len(parts) != 2 or len(parts[0]) != 64:
            raise ValueError(f"invalid B1 SHA256SUMS line {number}")
        digest, name = parts
        relative = Path(name.strip())
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"unsafe B1 SHA256SUMS path: {name}")
        target = (root / relative).resolve()
        try:
            target.relative_to(root.resolve())
        except ValueError as error:
            raise ValueError(f"B1 SHA256SUMS path escapes closeout: {name}") from error
        if not target.is_file():
            raise ValueError(f"B1 closeout ledger target is missing: {name}")
        try:
            actual, _ = _git_canonical_digest_and_size(target, digest)
        except ValueError as error:
            raise ValueError(f"B1 closeout SHA256 mismatch for {name}: {error}") from error
        declared[relative.as_posix()] = actual
    missing = sorted(set(_REQUIRED_LEDGER_FILES) - set(declared))
    if missing:
        raise ValueError(f"B1 closeout SHA256SUMS misses required files: {missing}")
    return declared


def _expect(value: Any, expected: Any, message: str) -> None:
    if value != expected:
        raise ValueError(f"{message}: {value!r} != {expected!r}")


def _verify_file_binding(repo: Path, binding: Mapping[str, Any], expected_path: str) -> None:
    _expect(binding.get("available"), True, f"B1 binding {expected_path} is unavailable")
    _expect(binding.get("path"), expected_path, f"B1 binding path mismatch for {expected_path}")
    target = (repo / expected_path).resolve()
    if not target.is_file():
        raise ValueError(f"B1 bound file is missing: {expected_path}")
    expected_sha = str(binding.get("sha256") or "")
    actual_sha, canonical_size = _git_canonical_digest_and_size(target, expected_sha)
    _expect(binding.get("sha256"), actual_sha, f"B1 binding SHA256 mismatch for {expected_path}")
    _expect(binding.get("size_bytes"), canonical_size, f"B1 binding size mismatch for {expected_path}")


@dataclass(frozen=True, slots=True)
class B1Closeout:
    """Verified canonical B1 data closeout consumed by A2."""

    root: Path
    report: dict[str, Any]
    governed_release: dict[str, Any]
    calibration: dict[str, Any]
    independent_validation: dict[str, Any]
    identity: dict[str, Any]


def load_b1_closeout(
    repo_root: str | Path,
    *,
    closeout_directory: str | Path = B1_CLOSEOUT_RELATIVE,
) -> B1Closeout:
    """Verify the canonical B1 closeout, its ledger, and role separation."""
    repo = Path(repo_root).resolve()
    canonical = (repo / B1_CLOSEOUT_RELATIVE).resolve()
    requested = (
        (repo / closeout_directory).resolve()
        if not Path(closeout_directory).is_absolute()
        else Path(closeout_directory).resolve()
    )
    if requested != canonical:
        raise ValueError(
            "formal A2 intake must use challenge/dataset/governance/b1_closeout_v1"
        )

    ledger = _verified_ledger(canonical)
    report = _json_object(canonical / "B1_CLOSEOUT_REPORT.json")
    governed = _json_object(canonical / "governed_release_manifest.json")
    calibration = _json_object(canonical / "calibration_identity.json")
    independent = _json_object(canonical / "independent_validation_v1/dataset_identity.json")
    source_binding = _json_object(
        canonical / "independent_validation_v1/source_release_binding.json"
    )

    _expect(report.get("status"), "PASS", "B1 closeout is not PASS")
    state = report.get("b1_state")
    if not isinstance(state, Mapping):
        raise ValueError("B1 closeout has no b1_state object")
    for key, expected in {
        "B1_DATA_CLOSEOUT": "PASS",
        "CALIBRATION_V1": "FROZEN",
        "GOVERNED_DATASET": "FROZEN",
        "INDEPENDENT_VALIDATION": "FROZEN",
    }.items():
        _expect(state.get(key), expected, f"B1 state {key} mismatch")
    required = report.get("required_b1_artifacts")
    if not isinstance(required, Mapping) or not required or not all(required.values()):
        raise ValueError("B1 closeout required artifact checklist is incomplete")

    _expect(
        governed.get("dataset_version"), B1_GOVERNED_DATASET_VERSION,
        "B1 governed dataset version mismatch",
    )
    _expect(governed.get("status"), "B1_GOVERNED_RELEASE_SET", "B1 governed release status mismatch")
    counts = governed.get("aggregate_counts")
    if not isinstance(counts, Mapping):
        raise ValueError("B1 governed release has no aggregate_counts object")
    for key in ("train", "dev", "calibration", "independent_validation"):
        value = counts.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise ValueError(f"B1 governed count {key} is invalid: {value!r}")
    _expect(counts.get("calibration"), 300, "B1 calibration count mismatch")
    _expect(counts.get("independent_validation"), 240, "B1 independent validation count mismatch")
    for key, value in counts.items():
        _expect(
            report.get("governed_counts", {}).get(key), value,
            f"B1 report/governed count mismatch for {key}",
        )

    _expect(calibration.get("status"), "FROZEN_CALIBRATION", "B1 calibration status mismatch")
    _expect(calibration.get("dataset_version"), B1_CALIBRATION_VERSION, "B1 calibration version mismatch")
    _expect(calibration.get("purpose"), "PTQ_CALIBRATION_ONLY", "B1 calibration purpose mismatch")
    _expect(calibration.get("counts"), {"groups": 300, "samples": 300}, "B1 calibration counts mismatch")
    calibration_governance = calibration.get("governance")
    if not isinstance(calibration_governance, Mapping):
        raise ValueError("B1 calibration governance is missing")
    for key, expected in {
        "calibration": True,
        "development": False,
        "frozen_test": False,
        "independent_validation": False,
        "training": False,
        "independent_validation_group_overlap": 0,
        "independent_validation_sample_overlap": 0,
    }.items():
        _expect(
            calibration_governance.get(key), expected,
            f"B1 calibration governance mismatch for {key}",
        )
    bindings = calibration.get("bindings")
    if not isinstance(bindings, Mapping):
        raise ValueError("B1 calibration bindings are missing")
    expected_bindings = {
        "calibration_manifest": "challenge/dataset/releases/calibration_v1/calibration_manifest.json",
        "calibration_rows": "challenge/dataset/releases/calibration_v1/calibration.jsonl",
        "coverage_report": "challenge/dataset/releases/calibration_v1/calibration_coverage_report.json",
        "rgb_manifest": "challenge/dataset/releases/calibration_v1/rgb_manifest.json",
        "selection_assignments": "challenge/dataset/releases/calibration_v1/selection_assignments.jsonl",
    }
    for key, expected_path in expected_bindings.items():
        binding = bindings.get(key)
        if not isinstance(binding, Mapping):
            raise ValueError(f"B1 calibration binding is missing: {key}")
        _verify_file_binding(repo, binding, expected_path)

    _expect(independent.get("status"), "FROZEN", "B1 independent validation status mismatch")
    _expect(
        independent.get("dataset_version"), B1_INDEPENDENT_VALIDATION_VERSION,
        "B1 independent validation version mismatch",
    )
    _expect(independent.get("role"), "INDEPENDENT_VALIDATION", "B1 independent role mismatch")
    _expect(independent.get("counts"), {"groups": 240, "samples": 240}, "B1 independent counts mismatch")
    independent_governance = independent.get("governance")
    if not isinstance(independent_governance, Mapping):
        raise ValueError("B1 independent validation governance is missing")
    for key, expected in {
        "calibration": False,
        "development": False,
        "independent_validation": True,
        "labels_must_not_be_used_for_A3_training_or_tuning": True,
        "training": False,
    }.items():
        _expect(
            independent_governance.get(key), expected,
            f"B1 independent governance mismatch for {key}",
        )
    leakage = independent.get("leakage_checks")
    if not isinstance(leakage, Mapping) or not leakage or not all(leakage.values()):
        raise ValueError("B1 independent validation leakage checks are incomplete")
    _expect(
        source_binding.get("calibration_manifest", {}).get("sha256"),
        bindings["calibration_manifest"]["sha256"],
        "B1 independent/calibration source binding mismatch",
    )

    identity = {
        "schema_version": "1.0",
        "status": "VERIFIED_B1_DATA_CLOSEOUT",
        "closeout_id": report.get("closeout_id"),
        "dataset_version": governed["dataset_version"],
        "governed_counts": dict(counts),
        "closeout_path": B1_CLOSEOUT_RELATIVE.as_posix(),
        "closeout_report_sha256": ledger["B1_CLOSEOUT_REPORT.json"],
        "governed_release_manifest_sha256": ledger["governed_release_manifest.json"],
        "calibration_identity_sha256": ledger["calibration_identity.json"],
        "independent_validation_identity_sha256": ledger[
            "independent_validation_v1/dataset_identity.json"
        ],
        "independent_validation_case_manifest_sha256": ledger[
            "independent_validation_v1/case_manifest.json"
        ],
        "hash_ledger_sha256": _canonical_text_sha256(canonical / "SHA256SUMS"),
        "calibration": {
            "dataset_version": calibration["dataset_version"],
            "sample_count": calibration["counts"]["samples"],
            "group_count": calibration["counts"]["groups"],
            "jsonl_sha256": bindings["calibration_rows"]["sha256"],
            "manifest_sha256": bindings["calibration_manifest"]["sha256"],
        },
        "independent_validation": {
            "dataset_version": independent["dataset_version"],
            "sample_count": independent["counts"]["samples"],
            "group_count": independent["counts"]["groups"],
            "case_set_digest_sha256": independent["case_set_digest_sha256"],
            "a2_usage": "FORBIDDEN_FOR_CALIBRATION_TUNING_OR_ERROR_DRIVEN_ITERATION",
        },
    }
    return B1Closeout(
        root=canonical,
        report=report,
        governed_release=governed,
        calibration=calibration,
        independent_validation=independent,
        identity=identity,
    )


def audit_a3_candidate(
    repo_root: str | Path,
    *,
    weights_manifest: str | Path,
    weights: str | Path | None = None,
    closeout_directory: str | Path = B1_CLOSEOUT_RELATIVE,
) -> dict[str, Any]:
    """Compare an A3 handoff with the exact latest B1 governed closeout."""
    repo = Path(repo_root).resolve()
    manifest_path = Path(weights_manifest)
    if not manifest_path.is_absolute():
        manifest_path = (repo / manifest_path).resolve()
    manifest = _json_object(manifest_path)
    candidate = manifest.get("candidate_identity")
    candidate = candidate if isinstance(candidate, Mapping) else manifest
    evidence = manifest.get("training_evidence")
    evidence = evidence if isinstance(evidence, Mapping) else {}
    governed_source_counts = manifest.get("governed_source_counts")
    if not isinstance(governed_source_counts, Mapping):
        governed_source_counts = evidence.get("governed_source_counts")
    governed_source_counts = (
        governed_source_counts if isinstance(governed_source_counts, Mapping) else {}
    )
    closeout = load_b1_closeout(repo, closeout_directory=closeout_directory)

    expected_counts = closeout.identity["governed_counts"]
    optimizer_train = evidence.get("train_samples")
    optimizer_dev = evidence.get("validation_samples")
    governed_train = governed_source_counts.get(
        "train", evidence.get("raw_governed_train")
    )
    governed_dev = governed_source_counts.get(
        "dev", evidence.get("raw_governed_dev", evidence.get("raw_governed_val"))
    )
    blockers: list[str] = []
    if governed_train != expected_counts["train"]:
        blockers.append(
            "A3_GOVERNED_TRAIN_COUNT_MISMATCH:"
            f"{governed_train!r}!={expected_counts['train']}"
        )
    if governed_dev != expected_counts["dev"]:
        blockers.append(
            "A3_GOVERNED_DEV_COUNT_MISMATCH:"
            f"{governed_dev!r}!={expected_counts['dev']}"
        )

    expected_governed_sha = closeout.identity["governed_release_manifest_sha256"]
    reported_governed_sha = candidate.get("b1_governed_release_manifest_sha256")
    if reported_governed_sha is None:
        blockers.append("A3_MISSING_B1_GOVERNED_RELEASE_BINDING")
    elif reported_governed_sha != expected_governed_sha:
        blockers.append(
            "A3_B1_GOVERNED_RELEASE_BINDING_MISMATCH:"
            f"{reported_governed_sha}!={expected_governed_sha}"
        )

    gate_status = str(manifest.get("gate_status") or candidate.get("gate_status") or "NOT_PROVIDED")
    if gate_status != "A3_FP32_GATE_PASSED":
        blockers.append(f"A3_FP32_GATE_NOT_PASSED:{gate_status}")

    verified_weights: dict[str, Any] | None = None
    if weights is not None:
        weights_path = Path(weights)
        if not weights_path.is_absolute():
            weights_path = (repo / weights_path).resolve()
        identity = identity_from_weight_manifest(weights_path, manifest_path)
        verification = dict(identity.verification or {})
        verification["manifest_path"] = _repo_label(manifest_path, repo)
        verification["artifact_path"] = _repo_label(weights_path, repo)
        verified_weights = {
            "path": _repo_label(weights_path, repo),
            "sha256": identity.model_sha256,
            "model_id": identity.model_id,
            "config_id": identity.config_id,
            "dataset_version": identity.dataset_version,
            "gate_status": identity.gate_status,
            "verification": verification,
        }

    formal_eligible = not blockers
    return {
        "schema_version": "1.0",
        "status": "READY_FOR_A2_FORMAL" if formal_eligible else "BLOCKED",
        "formal_eligible": formal_eligible,
        "candidate_use": "FORMAL_A2_INPUT" if formal_eligible else "DIAGNOSTIC_ONLY",
        "weights_manifest": {
            "path": _repo_label(manifest_path, repo),
            "sha256": sha256_file(manifest_path),
        },
        "candidate": {
            "model_id": candidate.get("model_id"),
            "config_id": candidate.get("config_id"),
            "dataset_version": candidate.get("dataset_version"),
            "weights_sha256": candidate.get("weights_sha256"),
            "gate_status": gate_status,
            "package_status": manifest.get("package_status"),
            "optimizer_train_samples": optimizer_train,
            "optimizer_dev_samples": optimizer_dev,
            "governed_source_train_samples": governed_train,
            "governed_source_dev_samples": governed_dev,
            "b1_governed_release_manifest_sha256": reported_governed_sha,
        },
        "verified_weights": verified_weights,
        "b1_closeout": closeout.identity,
        "requirements": {
            "expected_train_samples": expected_counts["train"],
            "expected_dev_samples": expected_counts["dev"],
            "expected_b1_governed_release_manifest_sha256": expected_governed_sha,
            "required_gate_status": "A3_FP32_GATE_PASSED",
        },
        "blockers": blockers,
        "independent_validation_policy": (
            "b1_independent_validation_v1 is B2-owned and must not be used by A2 "
            "for calibration, tuning, sensitivity selection, or error-driven iteration."
        ),
    }


__all__ = [
    "B1_CALIBRATION_VERSION",
    "B1_CLOSEOUT_RELATIVE",
    "B1_GOVERNED_DATASET_VERSION",
    "B1_INDEPENDENT_VALIDATION_VERSION",
    "B1Closeout",
    "audit_a3_candidate",
    "load_b1_closeout",
]
