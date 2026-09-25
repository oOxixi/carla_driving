"""Fully manifest-bound Teacher evaluation package for B2."""

from __future__ import annotations

import json
import shutil
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from .benchmark_manifest import (
    BenchmarkManifestError,
    benchmark_manifest_sha256,
    build_benchmark_manifest,
    write_benchmark_manifest,
)
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

from .case_manifest import (
    CaseManifestError,
    compute_case_set_digest,
    extract_case_identities,
)

def write_formal_teacher_bundle(
    destination: str | Path,
    cases: Iterable[Mapping[str, Any]],
    records: Iterable[Mapping[str, Any]],
    *,
    evaluation_id: str,
    benchmark_config: Mapping[str, Any],
    case_manifest: Mapping[str, Any],
    evaluator_git_sha: str,
    evidence_bindings: Mapping[str, str] | None = None,
    template_ids: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """
    Publish a Teacher package bound to actual benchmark and policy manifests.

    Current repository WAITING states intentionally fail closed.
    """
    target = Path(destination)
    staging = target.with_name(
        target.name + ".formal.tmp"
    )

    if target.exists():
        raise EvaluationPackageError(
            "evaluation package destination already exists"
        )

    if staging.exists():
        raise EvaluationPackageError(
            "formal package staging directory already exists"
        )

    case_rows = list(cases)
    record_rows = list(records)

    try:
        benchmark_manifest = build_benchmark_manifest(
            benchmark_config,
            case_manifest,
        )
        policy_manifest = build_policy_manifest(
            benchmark_config,
        )
        try:
            actual_case_identities = extract_case_identities(
                [
                    dict(case)
                    for case in case_rows
                ],
                template_ids=template_ids,
            )
        except CaseManifestError as error:
            raise EvaluationPackageError(
                f"cannot bind actual case set: {error}"
            ) from error

        actual_sample_count = len(
            actual_case_identities
        )
        actual_case_set_digest = (
            compute_case_set_digest(
                actual_case_identities
            )
        )

        if (
            actual_sample_count
            != benchmark_manifest["sample_count"]
        ):
            raise EvaluationPackageError(
                "benchmark manifest sample_count "
                "does not match actual cases"
            )

        if (
            actual_case_set_digest
            != benchmark_manifest["case_set_digest"]
        ):
            raise EvaluationPackageError(
                "benchmark manifest case_set_digest "
                "does not match actual cases"
            )

        benchmark_sha256 = benchmark_manifest_sha256(
            benchmark_manifest
        )
        policy_sha256 = policy_manifest_sha256(
            policy_manifest
        )

    except (
        BenchmarkManifestError,
        PolicyManifestError,
    ) as error:
        raise EvaluationPackageError(
            f"cannot build formal manifests: {error}"
        ) from error

    try:
        result = write_teacher_evidence_package(
            staging,
            case_rows,
            record_rows,
            evaluation_id=evaluation_id,
            dataset_version=benchmark_manifest[
                "dataset_version"
            ],
            benchmark_manifest_sha256=benchmark_sha256,
            policy_manifest_sha256=policy_sha256,
            case_set_digest=benchmark_manifest[
                "case_set_digest"
            ],
            evaluator_git_sha=evaluator_git_sha,
            evidence_bindings=evidence_bindings,
        )

        written_benchmark_sha256 = (
            write_benchmark_manifest(
                staging / "benchmark_manifest.json",
                benchmark_manifest,
            )
        )

        written_policy_sha256 = (
            write_policy_manifest(
                staging / "policy_manifest.json",
                policy_manifest,
            )
        )

        if written_benchmark_sha256 != benchmark_sha256:
            raise EvaluationPackageError(
                "written benchmark manifest SHA256 mismatch"
            )

        if written_policy_sha256 != policy_sha256:
            raise EvaluationPackageError(
                "written policy manifest SHA256 mismatch"
            )

        evaluation = json.loads(
            (
                staging / "teacher_evaluation.json"
            ).read_text(encoding="utf-8")
        )

        if (
            evaluation.get("benchmark_manifest_sha256")
            != benchmark_sha256
        ):
            raise EvaluationPackageError(
                "Teacher evaluation benchmark binding mismatch"
            )

        if (
            evaluation.get("policy_manifest_sha256")
            != policy_sha256
        ):
            raise EvaluationPackageError(
                "Teacher evaluation policy binding mismatch"
            )

        if (
            evaluation.get("case_set_digest")
            != benchmark_manifest["case_set_digest"]
        ):
            raise EvaluationPackageError(
                "Teacher evaluation case-set binding mismatch"
            )

        if (
            evaluation.get("sample_count")
            != benchmark_manifest["sample_count"]
        ):
            raise EvaluationPackageError(
                "Teacher evaluation sample_count does not match "
                "benchmark manifest"
            )

        staging.replace(target)

    except (
        EvaluationPackageError,
        OSError,
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
            f"cannot publish formal Teacher bundle: {error}"
        ) from error

    return {
        "evaluation_id": evaluation_id,
        "directory": str(target),
        "benchmark_manifest": str(
            target / "benchmark_manifest.json"
        ),
        "policy_manifest": str(
            target / "policy_manifest.json"
        ),
        "teacher_predictions": str(
            target / "teacher_predictions.jsonl"
        ),
        "teacher_evaluation": str(
            target / "teacher_evaluation.json"
        ),
        "predictions_checksum": str(
            target / "predictions.sha256"
        ),
        "benchmark_manifest_sha256": benchmark_sha256,
        "policy_manifest_sha256": policy_sha256,
        "case_set_digest": benchmark_manifest[
            "case_set_digest"
        ],
        "predictions_sha256": result[
            "predictions_sha256"
        ],
        "teacher_evaluation_sha256": result[
            "teacher_evaluation_sha256"
        ],
    }


__all__ = [
    "write_formal_teacher_bundle",
]