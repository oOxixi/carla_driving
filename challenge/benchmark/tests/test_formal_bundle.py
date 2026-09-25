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
    write_formal_student_bundle,
    write_formal_teacher_bundle,
)

from challenge.distillation.candidate_handoff import (
    build_candidate_handoff,
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

def _write_json(
    path: Path,
    value: dict,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_text(
        json.dumps(value),
        encoding="utf-8",
    )


def _candidate_handoff(
    tmp_path: Path,
    *,
    dataset_version: str,
) -> Path:
    source = tmp_path / "a3-run"
    source.mkdir()

    weights = b"formal-candidate-weights"
    checkpoint = b"formal-best-checkpoint"

    (
        source / "student_v0_fp32_candidate.pt"
    ).write_bytes(weights)

    (
        source / "student_fp32_best.pt"
    ).write_bytes(checkpoint)

    candidate = {
        "git_sha": "a" * 40,
        "source_worktree_dirty": False,
        "teacher_git_sha": "MULTI_PINNED_B1_D2_V1_1",
        "teacher_model_id": "Qwen/Qwen3.5-2B",
        "teacher_model_revision": "b" * 40,
        "teacher_artifact_fingerprint_sha256": "c" * 64,
        "teacher_identity_policy": "signed_d2_release_formal",
        "model_id": "student-v0-r3-fp32",
        "config_id": "student-v0-r3-structure-test",
        "weights_sha256": hashlib.sha256(
            weights
        ).hexdigest(),
        "source_checkpoint_sha256": hashlib.sha256(
            checkpoint
        ).hexdigest(),
        "dataset_version": dataset_version,
        "release_manifest_sha256": "d" * 64,
        "a3_view_manifest_sha256": "e" * 64,
        "gate_status": "PENDING_A3_FP32_GATE",
    }

    _write_json(
        source / "student_v0_fp32_candidate.json",
        candidate,
    )

    _write_json(
        source / "training_summary.json",
        {
            "git_sha": candidate["git_sha"],
            "teacher_git_sha": candidate["teacher_git_sha"],
            "teacher_model_id": candidate["teacher_model_id"],
            "teacher_model_revision": candidate[
                "teacher_model_revision"
            ],
            "teacher_artifact_fingerprint_sha256": candidate[
                "teacher_artifact_fingerprint_sha256"
            ],
            "teacher_identity_policy": candidate[
                "teacher_identity_policy"
            ],
            "model_id": candidate["model_id"],
            "model_config_id": candidate["config_id"],
            "dataset_version": candidate["dataset_version"],
            "release_manifest_sha256": candidate[
                "release_manifest_sha256"
            ],
            "a3_view_manifest_sha256": candidate[
                "a3_view_manifest_sha256"
            ],
            "candidate_weights_sha256": candidate[
                "weights_sha256"
            ],
            "best_checkpoint_sha256": candidate[
                "source_checkpoint_sha256"
            ],
            "candidate_gate_status": candidate["gate_status"],
            "smoke_only": False,
            "integration_smoke_only": False,
            "train_samples": 10,
            "validation_samples": 3,
            "hard_case_count": 2,
        },
    )

    _write_json(
        source / "dataset_preflight.json",
        {
            "valid": True,
            "error_count": 0,
            "expected_dataset_version": dataset_version,
        },
    )

    _write_json(
        source / "hard_cases" / "summary.json",
        {"hard_case_count": 2},
    )

    (
        source / "training_report.md"
    ).write_text(
        "report",
        encoding="utf-8",
    )

    (
        source / "training.jsonl"
    ).write_text(
        "{}\n",
        encoding="utf-8",
    )

    output = tmp_path / "a3-handoff"

    build_candidate_handoff(
        source,
        output,
        config_snapshot=b"config_id: formal\n",
        config_source={
            "git_sha": "a" * 40,
            "path": "config.yaml",
        },
    )

    return output

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

def test_formal_student_bundle_binds_verified_candidate(
    tmp_path,
) -> None:
    cases = _b1_cases(5)
    config = _complete_config()

    handoff = _candidate_handoff(
        tmp_path,
        dataset_version=config["dataset"]["dataset_version"],
    )

    destination = (
        tmp_path
        / "b2_evaluation"
        / "formal-student-test"
    )

    result = write_formal_student_bundle(
        destination,
        cases,
        _records(cases),
        evaluation_id="formal-student-test",
        benchmark_config=config,
        case_manifest=_case_manifest(cases),
        evaluator_git_sha="f" * 40,
        candidate_handoff=handoff,
    )

    assert sorted(
        path.name
        for path in destination.iterdir()
    ) == [
        "benchmark_manifest.json",
        "policy_manifest.json",
        "predictions.sha256",
        "student_evaluation.json",
        "student_predictions.jsonl",
    ]

    evaluation = json.loads(
        (
            destination / "student_evaluation.json"
        ).read_text(encoding="utf-8")
    )

    assert evaluation["evaluation_role"] == "student"
    assert evaluation["model_id"] == (
        "student-v0-r3-fp32"
    )
    assert evaluation["config_id"] == (
        "student-v0-r3-structure-test"
    )

    actual_weights_sha256 = hashlib.sha256(
        (
            handoff / "student_v0_fp32_candidate.pt"
        ).read_bytes()
    ).hexdigest()

    assert evaluation["weights_sha256"] == (
        actual_weights_sha256
    )

    assert result[
        "candidate_handoff_manifest_sha256"
    ] == hashlib.sha256(
        (
            handoff / "handoff_manifest.json"
        ).read_bytes()
    ).hexdigest()

    benchmark_sha256 = hashlib.sha256(
        (
            destination / "benchmark_manifest.json"
        ).read_bytes()
    ).hexdigest()

    policy_sha256 = hashlib.sha256(
        (
            destination / "policy_manifest.json"
        ).read_bytes()
    ).hexdigest()

    assert evaluation[
        "benchmark_manifest_sha256"
    ] == benchmark_sha256

    assert evaluation[
        "policy_manifest_sha256"
    ] == policy_sha256

    assert evaluation["case_set_digest"] == (
        compute_case_set_digest(
            extract_case_identities(cases)
        )
    )

    assert evaluation["sample_count"] == len(cases)

def test_formal_student_bundle_rejects_tampered_candidate_weights(
    tmp_path,
) -> None:
    cases = _b1_cases(5)
    config = _complete_config()

    handoff = _candidate_handoff(
        tmp_path,
        dataset_version=config["dataset"]["dataset_version"],
    )

    # Tamper with the actual candidate after A3 created the signed handoff.
    (
        handoff / "student_v0_fp32_candidate.pt"
    ).write_bytes(
        b"tampered-formal-candidate-weights"
    )

    destination = (
        tmp_path
        / "b2_evaluation"
        / "tampered-student"
    )

    with pytest.raises(
        EvaluationPackageError,
        match="cannot verify Student candidate",
    ):
        write_formal_student_bundle(
            destination,
            cases,
            _records(cases),
            evaluation_id="tampered-student",
            benchmark_config=config,
            case_manifest=_case_manifest(cases),
            evaluator_git_sha="f" * 40,
            candidate_handoff=handoff,
        )

    assert not destination.exists()

    assert not destination.with_name(
        destination.name + ".formal.tmp"
    ).exists()

def test_formal_student_bundle_rejects_tampered_actual_cases(
    tmp_path,
) -> None:
    cases = _b1_cases(5)
    config = _complete_config()

    # Freeze the manifest against the original case set.
    frozen_case_manifest = _case_manifest(cases)

    handoff = _candidate_handoff(
        tmp_path,
        dataset_version=config["dataset"]["dataset_version"],
    )

    # Mutate one identity-bearing field only after the manifest is frozen.
    tampered_cases = copy.deepcopy(cases)

    tampered_cases[0]["model_request"]["text"] = (
        "tampered independent-validation request"
    )

    destination = (
        tmp_path
        / "b2_evaluation"
        / "tampered-case-set"
    )

    with pytest.raises(
        EvaluationPackageError,
        match="case_set_digest",
    ):
        write_formal_student_bundle(
            destination,
            tampered_cases,
            _records(tampered_cases),
            evaluation_id="tampered-case-set",
            benchmark_config=config,
            case_manifest=frozen_case_manifest,
            evaluator_git_sha="f" * 40,
            candidate_handoff=handoff,
        )

    assert not destination.exists()

    assert not destination.with_name(
        destination.name + ".formal.tmp"
    ).exists()