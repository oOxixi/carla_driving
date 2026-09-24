"""Atomic Teacher evidence package assembly for B2."""

from __future__ import annotations

import hashlib
import shutil
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from .evaluation_artifact import (
    EvaluationArtifactError,
    build_teacher_evaluation,
    write_evaluation_artifact,
)
from .raw_predictions import (
    RawPredictionError,
    write_prediction_records,
)


class EvaluationPackageError(ValueError):
    """Raised when a B2 evaluation evidence package cannot be published."""


def write_teacher_evidence_package(
    destination: str | Path,
    cases: Iterable[Mapping[str, Any]],
    records: Iterable[Mapping[str, Any]],
    *,
    evaluation_id: str,
    dataset_version: str,
    benchmark_manifest_sha256: str,
    policy_manifest_sha256: str,
    case_set_digest: str,
    evaluator_git_sha: str,
    evidence_bindings: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """
    Publish one immutable Teacher evidence sub-package.

    The destination is created only after all files have been written and
    cross-checked in a temporary sibling directory.
    """
    target = Path(destination)
    temporary = target.with_name(
        target.name + ".tmp"
    )

    if target.exists():
        raise EvaluationPackageError(
            "evaluation package destination already exists"
        )

    if temporary.exists():
        raise EvaluationPackageError(
            "evaluation package temporary directory already exists"
        )

    case_rows = list(cases)
    record_rows = list(records)

    try:
        artifact = build_teacher_evaluation(
            case_rows,
            record_rows,
            evaluation_id=evaluation_id,
            dataset_version=dataset_version,
            benchmark_manifest_sha256=benchmark_manifest_sha256,
            policy_manifest_sha256=policy_manifest_sha256,
            case_set_digest=case_set_digest,
            evaluator_git_sha=evaluator_git_sha,
            evidence_bindings=evidence_bindings,
        )
    except (
        EvaluationArtifactError,
        RawPredictionError,
    ) as error:
        raise EvaluationPackageError(
            f"cannot build Teacher evaluation package: {error}"
        ) from error

    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary.mkdir()

    try:
        predictions_path = (
            temporary / "teacher_predictions.jsonl"
        )
        evaluation_path = (
            temporary / "teacher_evaluation.json"
        )
        checksum_path = (
            temporary / "predictions.sha256"
        )

        predictions_sha256 = write_prediction_records(
            predictions_path,
            record_rows,
        )

        if (
            predictions_sha256
            != artifact["predictions_sha256"]
        ):
            raise EvaluationPackageError(
                "written prediction SHA256 does not match "
                "Teacher evaluation artifact"
            )

        evaluation_sha256 = write_evaluation_artifact(
            evaluation_path,
            artifact,
        )

        actual_predictions_sha256 = hashlib.sha256(
            predictions_path.read_bytes()
        ).hexdigest()

        if actual_predictions_sha256 != predictions_sha256:
            raise EvaluationPackageError(
                "written prediction file failed SHA256 verification"
            )

        checksum_path.write_bytes(
            (
                f"{predictions_sha256}"
                "  teacher_predictions.jsonl\n"
            ).encode("ascii")
        )

        temporary.replace(target)

    except (
        EvaluationArtifactError,
        EvaluationPackageError,
        OSError,
        RawPredictionError,
    ) as error:
        if temporary.exists():
            shutil.rmtree(
                temporary,
                ignore_errors=True,
            )

        if isinstance(
            error,
            EvaluationPackageError,
        ):
            raise

        raise EvaluationPackageError(
            f"cannot publish Teacher evaluation package: {error}"
        ) from error

    return {
        "evaluation_id": artifact["evaluation_id"],
        "directory": str(target),
        "teacher_predictions": str(
            target / "teacher_predictions.jsonl"
        ),
        "teacher_evaluation": str(
            target / "teacher_evaluation.json"
        ),
        "predictions_checksum": str(
            target / "predictions.sha256"
        ),
        "predictions_sha256": predictions_sha256,
        "teacher_evaluation_sha256": evaluation_sha256,
    }


__all__ = [
    "EvaluationPackageError",
    "write_teacher_evidence_package",
]