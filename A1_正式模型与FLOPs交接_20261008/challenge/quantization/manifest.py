"""Fail-closed INT8 manifest validation and B2 result binding."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
from typing import Any, Mapping

from .calibration import sha256_file


REQUIRED_INT8_FIELDS = (
    "quantization_id",
    "git_sha",
    "source_fp32_weights_sha256",
    "source_fp32_onnx_sha256",
    "calibration_manifest_sha256",
    "quant_config_sha256",
    "int8_artifact_sha256",
    "model_id",
    "config_id",
    "dataset_version",
    "B2_result",
)


def validate_int8_manifest(value: Mapping[str, Any]) -> None:
    missing = [name for name in REQUIRED_INT8_FIELDS if name not in value]
    if missing:
        raise ValueError(f"INT8 manifest missing required fields: {missing}")
    for name in REQUIRED_INT8_FIELDS[:-1]:
        item = value[name]
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"INT8 manifest field {name} must be a non-empty string")
    if not isinstance(value["B2_result"], Mapping):
        raise ValueError("INT8 manifest B2_result must be an object")


def bind_b2_gate_result(
    *,
    int8_manifest: str | Path,
    int8_artifact: str | Path,
    b2_decision: str | Path,
) -> dict[str, Any]:
    """Bind a B2-issued PASS without allowing A2 to self-sign the Gate."""
    manifest_path = Path(int8_manifest)
    artifact_path = Path(int8_artifact)
    decision_path = Path(b2_decision)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or not isinstance(decision, dict):
        raise ValueError("INT8 manifest and B2 decision must be JSON objects")
    validate_int8_manifest(manifest)
    actual_sha = sha256_file(artifact_path)
    if manifest["int8_artifact_sha256"].lower() != actual_sha.lower():
        raise ValueError("INT8 artifact SHA256 does not match its manifest")
    if decision.get("gate_status") != "A2_INT8_GATE_PASSED":
        raise ValueError("B2 decision must explicitly state A2_INT8_GATE_PASSED")
    if decision.get("quantization_id") != manifest["quantization_id"]:
        raise ValueError("B2 decision quantization_id mismatch")
    if str(decision.get("int8_artifact_sha256", "")).lower() != actual_sha.lower():
        raise ValueError("B2 decision INT8 artifact SHA256 mismatch")
    if not decision.get("benchmark_manifest_sha256") or not decision.get("policy_manifest_sha256"):
        raise ValueError("B2 decision must bind benchmark and policy manifests")

    copied = manifest_path.parent / "b2_gate_decision.json"
    if copied.resolve() != decision_path.resolve():
        shutil.copyfile(decision_path, copied)
    manifest["gate_status"] = "A2_INT8_GATE_PASSED"
    manifest["B2_result"] = {
        "status": "A2_INT8_GATE_PASSED",
        "decision_manifest": copied.name,
        "decision_manifest_sha256": sha256_file(copied),
        "benchmark_manifest_sha256": decision["benchmark_manifest_sha256"],
        "policy_manifest_sha256": decision["policy_manifest_sha256"],
        "bound_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    validate_int8_manifest(manifest)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return manifest


__all__ = ["REQUIRED_INT8_FIELDS", "bind_b2_gate_result", "validate_int8_manifest"]
