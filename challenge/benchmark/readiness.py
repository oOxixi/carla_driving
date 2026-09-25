"""Fail-closed readiness check for the final B2 evaluation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .policy_manifest import (
    PolicyManifestError,
    load_benchmark_policy_config,
)
from .student_candidate import (
    StudentCandidateError,
    verify_student_candidate,
)


class ReadinessError(ValueError):
    """Raised when the B2 readiness input cannot be inspected."""


def check_b2_readiness(
    benchmark_config_path: str | Path,
    *,
    student_candidate_directory: str | Path | None = None,
) -> dict[str, Any]:
    """Return a fail-closed readiness report for final B2 execution."""

    config_path = Path(benchmark_config_path)

    try:
        config = load_benchmark_policy_config(config_path)
    except (OSError, PolicyManifestError, ValueError) as error:
        raise ReadinessError(
            f"cannot load B2 benchmark config: {error}"
        ) from error

    independent = _check_independent_validation(config)
    policy = _check_formal_policy(config)
    student = _check_student_candidate(
        student_candidate_directory,
        expected_dataset_version=independent.get(
            "dataset_version"
        ),
    )

    blockers = [
        *independent["blockers"],
        *policy["blockers"],
        *student["blockers"],
    ]

    ready = not blockers

    return {
        "schema_version": "1.0",
        "ready": ready,
        "status": "READY" if ready else "BLOCKED",
        "independent_validation": independent,
        "formal_policy": policy,
        "student_candidate": student,
        "blockers": blockers,
    }


def _check_independent_validation(
    config: Mapping[str, Any],
) -> dict[str, Any]:
    status = config.get("status")

    dataset = config.get("dataset")

    if not isinstance(dataset, Mapping):
        return {
            "ready": False,
            "status": status,
            "case_manifest_path": None,
            "blockers": [
                "benchmark configuration is missing dataset"
            ],
        }

    case_manifest_path = dataset.get(
        "case_manifest_path"
    )
    dataset_version = dataset.get("dataset_version")

    blockers: list[str] = []

    if status != "FROZEN":
        blockers.append(
            "Independent Validation benchmark is not FROZEN"
        )

    if (
        not isinstance(case_manifest_path, str)
        or not case_manifest_path.strip()
    ):
        blockers.append(
            "Independent Validation case manifest is missing"
        )

    if (
        not isinstance(dataset_version, str)
        or not dataset_version.strip()
    ):
        blockers.append(
            "Independent Validation dataset_version is missing"
        )

    return {
        "ready": not blockers,
        "status": status,
        "case_manifest_path": case_manifest_path,
        "dataset_version": dataset_version,
        "blockers": blockers,
    }


def _check_formal_policy(
    config: Mapping[str, Any],
) -> dict[str, Any]:
    policy = config.get("formal_policy")

    if not isinstance(policy, Mapping):
        return {
            "ready": False,
            "status": None,
            "policy_version": None,
            "blockers": [
                "benchmark configuration is missing formal_policy"
            ],
        }

    status = policy.get("status")
    policy_version = policy.get("policy_version")
    slice_minimum_denominators = policy.get(
        "slice_minimum_denominators"
    )
    multi_run_merge_rule = policy.get(
        "multi_run_merge_rule"
    )

    blockers: list[str] = []

    if status != "FROZEN":
        blockers.append(
            "Formal B2 policy is not FROZEN"
        )

    if (
        not isinstance(policy_version, str)
        or not policy_version.strip()
    ):
        blockers.append(
            "Formal B2 policy_version is missing"
        )

    if (
        not isinstance(
            slice_minimum_denominators,
            Mapping,
        )
        or not slice_minimum_denominators
    ):
        blockers.append(
            "Formal B2 slice minimum denominators are missing"
        )

    if (
        not isinstance(multi_run_merge_rule, str)
        or not multi_run_merge_rule.strip()
    ):
        blockers.append(
            "Formal B2 multi-run merge rule is missing"
        )

    return {
        "ready": not blockers,
        "status": status,
        "policy_version": policy_version,
        "blockers": blockers,
    }


def _check_student_candidate(
    package_directory: str | Path | None,
    *,
    expected_dataset_version: Any = None,
) -> dict[str, Any]:
    if package_directory is None:
        return {
            "ready": False,
            "package_directory": None,
            "identity": None,
            "blockers": [
                "Verified A3 Student candidate package was not provided"
            ],
        }

    package = Path(package_directory)

    try:
        identity = verify_student_candidate(package)
    except (
        OSError,
        StudentCandidateError,
        ValueError,
    ) as error:
        return {
            "ready": False,
            "package_directory": str(package),
            "identity": None,
            "blockers": [
                f"A3 Student candidate verification failed: {error}"
            ],
        }

    blockers: list[str] = []
    if (
        not isinstance(expected_dataset_version, str)
        or not expected_dataset_version.strip()
    ):
        blockers.append(
            "B2 benchmark dataset_version is unavailable for candidate binding"
        )
    elif identity.get("dataset_version") != expected_dataset_version:
        blockers.append(
            "A3 Student candidate dataset_version does not match "
            "the B2 benchmark configuration"
        )

    return {
        "ready": not blockers,
        "package_directory": str(package),
        "identity": identity,
        "expected_dataset_version": expected_dataset_version,
        "blockers": blockers,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__
    )

    parser.add_argument(
        "--config",
        default=(
            "challenge/benchmark/"
            "benchmark_config.yaml"
        ),
    )

    parser.add_argument(
        "--student-candidate",
        help=(
            "verified A3 FP32 candidate handoff directory"
        ),
    )

    args = parser.parse_args(argv)

    report = check_b2_readiness(
        args.config,
        student_candidate_directory=(
            args.student_candidate
        ),
    )

    print(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
