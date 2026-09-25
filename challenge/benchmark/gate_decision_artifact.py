"""Deterministic persistence for B2 gate decision artifacts."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .gate_decision import build_gate_decision


class GateDecisionArtifactError(ValueError):
    """Raised when a gate decision artifact cannot be written safely."""


def write_gate_decision_artifact(
    destination: str | Path,
    *,
    teacher_evaluation: Mapping[str, Any],
    student_evaluation: Mapping[str, Any],
    policy_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    path = Path(destination)

    if path.exists():
        raise GateDecisionArtifactError(
            f"destination already exists: {path}"
        )

    if not path.parent.exists():
        raise GateDecisionArtifactError(
            f"destination parent does not exist: {path.parent}"
        )

    decision = build_gate_decision(
        teacher_evaluation,
        student_evaluation,
        policy_manifest,
    )

    payload = _canonical_json_bytes(decision)
    digest = hashlib.sha256(payload).hexdigest()

    temporary = path.with_name(
        f".{path.name}.tmp"
    )

    if temporary.exists():
        raise GateDecisionArtifactError(
            f"temporary path already exists: {temporary}"
        )

    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())

        temporary.replace(path)
    except Exception:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise

    return {
        "path": path,
        "sha256": digest,
        "gate_status": decision["gate_status"],
    }


def gate_decision_artifact_sha256(
    path: str | Path,
) -> str:
    return hashlib.sha256(
        Path(path).read_bytes()
    ).hexdigest()


def _canonical_json_bytes(
    value: Mapping[str, Any],
) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


__all__ = [
    "GateDecisionArtifactError",
    "gate_decision_artifact_sha256",
    "write_gate_decision_artifact",
]