from __future__ import annotations

from pathlib import Path

import pytest

from challenge.dataset import collect_d2_wave2 as c


def _runs(n: int = 5):
    return [
        {
            "extension_id": f"D2W2_TEST_{i}",
            "scenario_id": f"S{i}",
            "scenario_path": f"scenarios/test/S{i}.json",
            "extension_seed": 2_100_000 + i,
            "quota_bucket": "BALANCED_SEEN",
        }
        for i in range(n)
    ]


def _state():
    return {
        "runs": {},
    }


def test_wave2_constants_are_frozen() -> None:
    assert (
        c.DATASET_VERSION
        == "teacher_distill_v0.4_d2_expansion_wave2_v4"
    )

    assert (
        c.EXPECTED_PLAN_VERSION
        == "b1_d2_expansion_wave2_v1"
    )

    assert (
        c.EXPECTED_PLAN_REPO_SHA
        == "a5b0258eb3d2d184f053e62b5c382741217259d3"
    )

    assert (
        c.EXPECTED_PLAN_CANONICAL_SHA256
        == "c20e997494c67f9238a200e359b81abcd5b7b51aaf365a8d16e7f60ebfddaea8"
    )

    assert (
        c.EXPECTED_PLAN_FILE_SHA256
        == "28bccc35cc76483b4d7bcfe4c989238eaabc147b99de399cfbdd439e9467a819"
    )

    assert c.EXPECTED_RUNS == 2000
    assert c.EXPECTED_SEED_START == 2_100_000
    assert c.EXPECTED_SEED_END == 2_101_999


def test_teacher_v4_constants_are_frozen() -> None:
    assert (
        c.EXPECTED_TEACHER_PROFILE
        == "b1-pinned-teacher-v4"
    )

    assert (
        c.EXPECTED_TEACHER_GIT_SHA
        == "95e97b00def8ec36f12937da34ce8bb9082c4a04"
    )

    assert (
        c.EXPECTED_MODEL_ID
        == "Qwen/Qwen3.5-2B"
    )

    assert (
        c.EXPECTED_QWEN_MODE
        == "planner_v2"
    )


def test_default_output_is_wave2_isolated() -> None:
    assert (
        c.DEFAULT_OUTPUT_ROOT
        == "artifacts/b1_d2_wave2_2000_teacher_v4"
    )

    assert "wave1" not in c.DEFAULT_OUTPUT_ROOT.lower()


def test_default_service_is_v4_verification_service() -> None:
    assert (
        c.DEFAULT_SERVICE_URL
        == "http://127.0.0.1:18007"
    )


def test_select_runs_without_resume() -> None:
    selected, skipped = c.select_runs(
        _runs(),
        _state(),
        start_index=0,
        max_runs=2,
        resume=False,
    )

    assert skipped == 0
    assert [
        x["extension_id"]
        for x in selected
    ] == [
        "D2W2_TEST_0",
        "D2W2_TEST_1",
    ]


def test_select_runs_respects_start_index() -> None:
    selected, skipped = c.select_runs(
        _runs(),
        _state(),
        start_index=2,
        max_runs=2,
        resume=False,
    )

    assert skipped == 0

    assert [
        x["extension_id"]
        for x in selected
    ] == [
        "D2W2_TEST_2",
        "D2W2_TEST_3",
    ]


def test_resume_skips_only_succeeded() -> None:
    state = _state()

    state["runs"]["D2W2_TEST_0"] = {
        "status": "SUCCEEDED",
    }

    state["runs"]["D2W2_TEST_1"] = {
        "status": "FAILED",
    }

    selected, skipped = c.select_runs(
        _runs(3),
        state,
        start_index=0,
        max_runs=None,
        resume=True,
    )

    assert skipped == 1

    assert [
        x["extension_id"]
        for x in selected
    ] == [
        "D2W2_TEST_1",
        "D2W2_TEST_2",
    ]


def test_resume_max_runs_applies_after_skip() -> None:
    state = _state()

    state["runs"]["D2W2_TEST_0"] = {
        "status": "SUCCEEDED",
    }

    selected, skipped = c.select_runs(
        _runs(5),
        state,
        start_index=0,
        max_runs=2,
        resume=True,
    )

    assert skipped == 1

    assert [
        x["extension_id"]
        for x in selected
    ] == [
        "D2W2_TEST_1",
        "D2W2_TEST_2",
    ]


@pytest.mark.parametrize(
    "value",
    [-1, 6],
)
def test_invalid_start_index_rejected(
    value: int,
) -> None:
    with pytest.raises(RuntimeError):
        c.select_runs(
            _runs(5),
            _state(),
            start_index=value,
            max_runs=None,
            resume=False,
        )


@pytest.mark.parametrize(
    "value",
    [0, -1],
)
def test_invalid_max_runs_rejected(
    value: int,
) -> None:
    with pytest.raises(RuntimeError):
        c.select_runs(
            _runs(5),
            _state(),
            start_index=0,
            max_runs=value,
            resume=False,
        )


def test_run_state_identity_accepts_frozen_wave2() -> None:
    state = {
        "schema_version":
            c.STATE_SCHEMA_VERSION,
        "dataset_version":
            c.DATASET_VERSION,
        "plan_version":
            c.EXPECTED_PLAN_VERSION,
        "plan_file_sha256":
            c.EXPECTED_PLAN_FILE_SHA256,
        "plan_canonical_sha256":
            c.EXPECTED_PLAN_CANONICAL_SHA256,
        "plan_repo_git_sha":
            c.EXPECTED_PLAN_REPO_SHA,
        "teacher_profile":
            c.EXPECTED_TEACHER_PROFILE,
        "teacher_git_sha":
            c.EXPECTED_TEACHER_GIT_SHA,
        "runs": {},
    }

    c.validate_state_identity(state)


def test_run_state_rejects_wrong_teacher() -> None:
    state = {
        "schema_version":
            c.STATE_SCHEMA_VERSION,
        "dataset_version":
            c.DATASET_VERSION,
        "plan_version":
            c.EXPECTED_PLAN_VERSION,
        "plan_file_sha256":
            c.EXPECTED_PLAN_FILE_SHA256,
        "plan_canonical_sha256":
            c.EXPECTED_PLAN_CANONICAL_SHA256,
        "plan_repo_git_sha":
            c.EXPECTED_PLAN_REPO_SHA,
        "teacher_profile":
            c.EXPECTED_TEACHER_PROFILE,
        "teacher_git_sha":
            "wrong",
        "runs": {},
    }

    with pytest.raises(
        RuntimeError,
        match="teacher_git_sha",
    ):
        c.validate_state_identity(state)


def test_atomic_write_json_roundtrip(
    tmp_path: Path,
) -> None:
    path = tmp_path / "state.json"

    c.atomic_write_json(
        path,
        {
            "hello": "world",
            "runs": {},
        },
    )

    assert c.load_json(path) == {
        "hello": "world",
        "runs": {},
    }

    assert not (
        tmp_path / "state.json.tmp"
    ).exists()
