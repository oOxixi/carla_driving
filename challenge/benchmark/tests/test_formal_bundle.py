from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest
import yaml

pytest.importorskip("torch")

from challenge.benchmark.case_manifest import (
    compute_case_set_digest,
    extract_case_identities,
)

from challenge.benchmark.evaluation_package import (
    EvaluationPackageError,
)
from challenge.benchmark.formal_bundle import (
    write_formal_teacher_bundle,
)
from challenge.distillation.dataset import (
    build_mock_records,
)


ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = (
    ROOT
    / "challenge"
    / "benchmark"
    / "benchmark_config.yaml"
)


def _repository_config() -> dict:
    return yaml.safe_load(
        CONFIG_PATH.read_text(
            encoding="utf-8"
        )
    )


def _complete_config() -> dict:
    config = copy.deepcopy(
        _repository_config()
    )

    config["status"] = "FROZEN"
    config["dataset"]["case_manifest_path"] = (
        "frozen/independent_validation_v1.json"
    )

    config["formal_policy"] = {
        "status": "FROZEN",
        "policy_version": "b2-policy-test-v1",
        "slice_minimum_denominators": {
            "seen": 1,
            "variant": 1,
            "unseen": 1,
        },
        "multi_run_merge_rule": (
            "pool_numerators_and_denominators"
        ),
    }

    return config

def _b1_cases(
    count: int = 5,
) -> list[dict]:
    mock_records = copy.deepcopy(
        build_mock_records(count)
    )

    cases: list[dict] = []

    for index, record in enumerate(
        mock_records
    ):
        request = copy.deepcopy(
            record["input"]
        )
        teacher_plan = copy.deepcopy(
            record["teacher"]["maneuver_plan"]
        )

        run_id = f"formal-run-{index:05d}"
        command_id = request["command_id"]
        request_id = request["request_id"]
        frame_id = request[
            "scene_summary"
        ]["frame_id"]

        event_identity = {
            "run_id": run_id,
            "command_id": command_id,
            "request_id": request_id,
            "frame_id": frame_id,
        }

        canonical_identity = json.dumps(
            event_identity,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

        supervision_event_key = (
            hashlib.sha256(
                canonical_identity
            ).hexdigest()
        )

        sample_id = (
            "td_"
            + supervision_event_key[:24]
        )

        metadata = copy.deepcopy(
            record["metadata"]
        )
        metadata.update(
            {
                "scenario_id": (
                    f"formal-scenario-{index:05d}"
                ),
                "template_id": (
                    f"formal-template-{index:05d}"
                ),
                "group_key": (
                    f"formal-group-{index:05d}"
                ),
                "run_id": run_id,
                "command_id": command_id,
                "request_id": request_id,
                "frame_id": frame_id,
            }
        )

        rgb_sha256 = hashlib.sha256(
            f"formal-rgb-{index:05d}".encode(
                "utf-8"
            )
        ).hexdigest()

        cases.append(
            {
                "sample_id": sample_id,
                "metadata": metadata,
                "model_request": request,
                "teacher_plan": teacher_plan,
                "visual_input": {
                    "rgb_sha256": rgb_sha256,
                },
            }
        )

    return cases

def _case_manifest(
    cases: list[dict],
    *,
    sample_count: int | None = None,
) -> dict:
    config = _repository_config()

    identities = extract_case_identities(
        cases
    )

    actual_count = len(cases)
    declared_count = (
        actual_count
        if sample_count is None
        else sample_count
    )

    risk_counts = {
        "normal": 0,
        "complex": 0,
        "safety_critical": 0,
    }

    for case in cases:
        sample_class = case[
            "metadata"
        ]["sample_class"]
        risk_counts[sample_class] += 1

    # Keep the deliberately mismatched sample-count
    # fixture structurally valid so the formal bundle,
    # rather than the manifest parser, catches it.
    risk_counts["normal"] += (
        declared_count - actual_count
    )

    return {
        "benchmark_id": config[
            "benchmark_id"
        ],
        "benchmark_version": "1.0",
        "benchmark_kind": (
            "independent_validation"
        ),
        "dataset_version": config[
            "dataset"
        ]["dataset_version"],
        "sample_count": declared_count,
        "case_set_digest": (
            compute_case_set_digest(
                identities
            )
        ),
        "rgb_set_sha256": "b" * 64,
        "split_rule": (
            "template_scenario_group_disjoint"
        ),
        "group_rule": (
            "no_group_key_cross_split_overlap"
        ),
        "cohort_counts": {
            "seen": declared_count,
            "variant": 0,
            "unseen": 0,
        },
        "risk_category_denominators": (
            risk_counts
        ),
        "frozen_at_utc": (
            "2026-09-24T00:00:00Z"
        ),
    }


def _records(
    cases: list[dict],
) -> list[dict]:
    return [
        {
            "sample_id": case["sample_id"],
            "status": "SUCCESS",
            "prediction": copy.deepcopy(
                case["teacher_plan"]
            ),
            "error": None,
        }
        for case in cases
    ]


def test_formal_bundle_binds_real_manifest_hashes(
    tmp_path,
) -> None:
    cases = _b1_cases(5)

    destination = (
        tmp_path
        / "b2_evaluation"
        / "formal-test"
    )

    result = write_formal_teacher_bundle(
        destination,
        cases,
        _records(cases),
        evaluation_id="formal-test",
        benchmark_config=_complete_config(),
        case_manifest=_case_manifest(cases),
        evaluator_git_sha="d" * 40,
    )

    assert sorted(
        path.name
        for path in destination.iterdir()
    ) == [
        "benchmark_manifest.json",
        "policy_manifest.json",
        "predictions.sha256",
        "teacher_evaluation.json",
        "teacher_predictions.jsonl",
    ]

    benchmark_bytes = (
        destination / "benchmark_manifest.json"
    ).read_bytes()

    policy_bytes = (
        destination / "policy_manifest.json"
    ).read_bytes()

    benchmark_sha256 = hashlib.sha256(
        benchmark_bytes
    ).hexdigest()

    policy_sha256 = hashlib.sha256(
        policy_bytes
    ).hexdigest()

    evaluation = json.loads(
        (
            destination / "teacher_evaluation.json"
        ).read_text(encoding="utf-8")
    )

    assert result[
        "benchmark_manifest_sha256"
    ] == benchmark_sha256

    assert result[
        "policy_manifest_sha256"
    ] == policy_sha256

    assert evaluation[
        "benchmark_manifest_sha256"
    ] == benchmark_sha256

    assert evaluation[
        "policy_manifest_sha256"
    ] == policy_sha256

    actual_case_set_digest = (
    compute_case_set_digest(
        extract_case_identities(cases)
    )
)

    assert evaluation[
        "case_set_digest"
    ] == actual_case_set_digest

    assert result[
        "case_set_digest"
    ] == actual_case_set_digest


def test_current_repository_state_cannot_publish_formal_bundle(
    tmp_path,
) -> None:
    cases = _b1_cases(5)

    destination = (
        tmp_path
        / "b2_evaluation"
        / "blocked"
    )

    with pytest.raises(
        EvaluationPackageError,
        match="formal manifests",
    ):
        write_formal_teacher_bundle(
            destination,
            cases,
            _records(cases),
            evaluation_id="blocked",
            benchmark_config=_repository_config(),
            case_manifest=_case_manifest(cases),
            evaluator_git_sha="d" * 40,
        )

    assert not destination.exists()


def test_manifest_sample_count_must_match_actual_evaluation(
    tmp_path,
) -> None:
    cases = _b1_cases(5)

    destination = (
        tmp_path
        / "b2_evaluation"
        / "count-mismatch"
    )

    with pytest.raises(
        EvaluationPackageError,
        match="sample_count does not match",
    ):
        write_formal_teacher_bundle(
            destination,
            cases,
            _records(cases),
            evaluation_id="count-mismatch",
            benchmark_config=_complete_config(),
            case_manifest=_case_manifest(
                cases,
                sample_count=6
            ),
            evaluator_git_sha="d" * 40,
        )

    assert not destination.exists()
    assert not destination.with_name(
        destination.name + ".formal.tmp"
    ).exists()

def test_actual_case_identity_tamper_fails_closed(
    tmp_path,
) -> None:
    original_cases = _b1_cases(5)

    case_manifest = _case_manifest(
        original_cases
    )

    tampered_cases = copy.deepcopy(
        original_cases
    )
    tampered_cases[0]["metadata"][
        "scenario_id"
    ] = "tampered-scenario"

    destination = (
        tmp_path
        / "b2_evaluation"
        / "tampered"
    )

    with pytest.raises(
        EvaluationPackageError,
        match="case_set_digest.*actual cases",
    ):
        write_formal_teacher_bundle(
            destination,
            tampered_cases,
            _records(tampered_cases),
            evaluation_id="tampered",
            benchmark_config=_complete_config(),
            case_manifest=case_manifest,
            evaluator_git_sha="d" * 40,
        )

    assert not destination.exists()

    assert not destination.with_name(
        destination.name + ".formal.tmp"
    ).exists()