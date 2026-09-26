from pathlib import Path

import yaml

from challenge.benchmark.readiness import (
    check_b2_readiness,
)


ROOT = Path(__file__).parents[3]

CONFIG = (
    ROOT
    / "challenge"
    / "benchmark"
    / "benchmark_config.yaml"
)


def test_current_repository_is_not_ready_for_final_b2() -> None:
    report = check_b2_readiness(CONFIG)

    assert report["ready"] is False
    assert report["status"] == "BLOCKED"

    independent = report["independent_validation"]

    assert independent["ready"] is False
    assert independent["status"] == (
        "WAITING_FOR_INDEPENDENT_VALIDATION"
    )

    policy = report["formal_policy"]

    assert policy["ready"] is False
    assert policy["status"] == (
        "WAITING_FOR_POLICY_COMPLETION"
    )

    student = report["student_candidate"]

    assert student["ready"] is False

    assert (
        "Verified A3 Student candidate package "
        "was not provided"
        in student["blockers"]
    )


def test_readiness_reports_all_current_blockers() -> None:
    report = check_b2_readiness(CONFIG)

    blockers = report["blockers"]

    assert (
        "Independent Validation benchmark is not FROZEN"
        in blockers
    )

    assert (
        "Independent Validation case manifest is missing"
        in blockers
    )

    assert (
        "Formal B2 policy is not FROZEN"
        in blockers
    )

    assert (
        "Verified A3 Student candidate package "
        "was not provided"
        in blockers
    )

def test_complete_inputs_are_ready(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config = yaml.safe_load(
        CONFIG.read_text(encoding="utf-8")
    )

    config["status"] = "FROZEN"
    config["dataset"]["case_manifest_path"] = (
        "artifacts/b2/"
        "independent_validation/"
        "case_manifest.json"
    )

    config["formal_policy"] = {
        "status": "FROZEN",
        "policy_version": "b2-policy-v1",
        "slice_minimum_denominators": {
            "seen": 1,
            "variant": 1,
            "unseen": 1,
            "safety_critical": 1,
        },
        "multi_run_merge_rule": "single_run_only",
    }

    config_path = tmp_path / "benchmark_config.yaml"
    config_path.write_text(
        yaml.safe_dump(
            config,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    candidate_directory = tmp_path / "candidate"
    candidate_directory.mkdir()

    expected_identity = {
        "model_id": "student-v0-r3-fp32",
        "config_id": (
            "student-v0-r3-structure-20260911"
        ),
        "weights_sha256": "a" * 64,
        "dataset_version": config["dataset"][
            "dataset_version"
        ],
        "candidate_git_sha": "b" * 40,
        "handoff_manifest_sha256": "c" * 64,
        "release_manifest_sha256": "d" * 64,
        "a3_view_manifest_sha256": "e" * 64,
    }

    def fake_verify_student_candidate(path):
        assert Path(path) == candidate_directory
        return expected_identity

    monkeypatch.setattr(
        "challenge.benchmark.readiness."
        "verify_student_candidate",
        fake_verify_student_candidate,
    )

    report = check_b2_readiness(
        config_path,
        student_candidate_directory=candidate_directory,
    )

    assert report["ready"] is True
    assert report["status"] == "READY"
    assert report["blockers"] == []

    assert report["independent_validation"][
        "ready"
    ] is True

    assert report["formal_policy"]["ready"] is True

    assert report["student_candidate"]["ready"] is True
    assert report["student_candidate"][
        "identity"
    ] == expected_identity


def test_candidate_dataset_version_must_match_benchmark(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config = yaml.safe_load(
        CONFIG.read_text(encoding="utf-8")
    )
    config["status"] = "FROZEN"
    config["dataset"]["case_manifest_path"] = (
        "artifacts/b2/independent_validation/case_manifest.json"
    )
    config["formal_policy"] = {
        "status": "FROZEN",
        "policy_version": "b2-policy-v1",
        "slice_minimum_denominators": {
            "seen": 1,
            "variant": 1,
            "unseen": 1,
            "safety_critical": 1,
        },
        "multi_run_merge_rule": "single_run_only",
    }
    config_path = tmp_path / "benchmark_config.yaml"
    config_path.write_text(
        yaml.safe_dump(config, sort_keys=False),
        encoding="utf-8",
    )
    candidate_directory = tmp_path / "candidate"
    candidate_directory.mkdir()

    monkeypatch.setattr(
        "challenge.benchmark.readiness.verify_student_candidate",
        lambda _: {
            "model_id": "student-v0-r3-fp32",
            "config_id": "student-v0-r3-structure-20260911",
            "weights_sha256": "a" * 64,
            "dataset_version": "different-training-release",
        },
    )

    report = check_b2_readiness(
        config_path,
        student_candidate_directory=candidate_directory,
    )

    assert report["ready"] is False
    assert report["student_candidate"]["ready"] is False
    assert report["student_candidate"]["identity"][
        "dataset_version"
    ] == "different-training-release"
    assert (
        "A3 Student candidate dataset_version does not match "
        "the B2 benchmark configuration"
        in report["blockers"]
    )
