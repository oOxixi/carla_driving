"""Policy-bound Teacher evidence package assembly for B2."""

from __future__ import annotations

import json
import shutil
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from .evaluation_package import (
    EvaluationPackageError,
    write_teacher_evidence_package,
)
from .policy_manifest import (
    PolicyManifestError,
    build_policy_manifest,
    policy_manifest_sha256,
    write_policy_manifest,
)


def write_policy_bound_teacher_package(
    destination: str | Path,
    cases: Iterable[Mapping[str, Any]],
    records: Iterable[Mapping[str, Any]],
    *,
    evaluation_id: str,
    dataset_version: str,
    benchmark_manifest_sha256: str,
    case_set_digest: str,
    evaluator_git_sha: str,
    policy_config: Mapping[str, Any],
    evidence_bindings: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """
    Publish a Teacher evidence package bound to an actual policy manifest.

    Formal publication fails closed unless build_policy_manifest() accepts the
    supplied policy configuration.
    """
    target = Path(destination)
    staging = target.with_name(
        target.name + ".policy.tmp"
    )

    if target.exists():
        raise EvaluationPackageError(
            "evaluation package destination already exists"
        )

    if staging.exists():
        raise EvaluationPackageError(
            "policy-bound package staging directory already exists"
        )

    try:
        policy_manifest = build_policy_manifest(
            policy_config
        )
        policy_sha256 = policy_manifest_sha256(
            policy_manifest
        )
    except PolicyManifestError as error:
        raise EvaluationPackageError(
            f"cannot build formal policy manifest: {error}"
        ) from error

    try:
        result = write_teacher_evidence_package(
            staging,
            cases,
            records,
            evaluation_id=evaluation_id,
            dataset_version=dataset_version,
            benchmark_manifest_sha256=benchmark_manifest_sha256,
            policy_manifest_sha256=policy_sha256,
            case_set_digest=case_set_digest,
            evaluator_git_sha=evaluator_git_sha,
            evidence_bindings=evidence_bindings,
        )

        written_policy_sha256 = write_policy_manifest(
            staging / "policy_manifest.json",
            policy_manifest,
        )

        if written_policy_sha256 != policy_sha256:
            raise EvaluationPackageError(
                "written policy manifest SHA256 does not match "
                "computed policy identity"
            )

        evaluation = json.loads(
            (
                staging / "teacher_evaluation.json"
            ).read_text(encoding="utf-8")
        )

        if (
            evaluation.get("policy_manifest_sha256")
            != policy_sha256
        ):
            raise EvaluationPackageError(
                "Teacher evaluation is not bound to "
                "the written policy manifest"
            )

        staging.replace(target)

    except (
        EvaluationPackageError,
        OSError,
        PolicyManifestError,
        ValueError,
    ) as error:
        if staging.exists():
            shutil.rmtree(
                staging,
                ignore_errors=True,
            )

        if isinstance(
            error,
            EvaluationPackageError,
        ):
            raise

        raise EvaluationPackageError(
            f"cannot publish policy-bound package: {error}"
        ) from error

    return {
        "evaluation_id": evaluation_id,
        "directory": str(target),
        "policy_manifest": str(
            target / "policy_manifest.json"
        ),
        "policy_manifest_sha256": policy_sha256,
        "teacher_predictions": str(
            target / "teacher_predictions.jsonl"
        ),
        "teacher_evaluation": str(
            target / "teacher_evaluation.json"
        ),
        "predictions_checksum": str(
            target / "predictions.sha256"
        ),
        "predictions_sha256": result[
            "predictions_sha256"
        ],
        "teacher_evaluation_sha256": result[
            "teacher_evaluation_sha256"
        ],
    }


__all__ = [
    "write_policy_bound_teacher_package",
]