from challenge.dataset import collect_d3_wave1 as collector


def test_d3_wave1_collector_identity():
    assert (
        collector.DATASET_VERSION
        == "teacher_distill_v0.5_d3_expansion_wave1_v4"
    )

    assert (
        collector.EXPECTED_PLAN_VERSION
        == "b1_d3_expansion_wave1_v1"
    )


def test_d3_wave1_frozen_plan_provenance():
    import hashlib
    import json
    from pathlib import Path

    plan_path = Path(collector.DEFAULT_PLAN)
    plan = json.loads(
        plan_path.read_text(encoding="utf-8")
    )

    assert (
        collector.EXPECTED_PLAN_REPO_SHA
        == plan["challenge_git_sha"]
    )

    assert (
        collector.EXPECTED_PLAN_CANONICAL_SHA256
        == plan["plan_canonical_sha256"]
    )

    assert (
        collector.EXPECTED_PLAN_FILE_SHA256
        == hashlib.sha256(
            plan_path.read_bytes()
        ).hexdigest()
    )


def test_d3_wave1_seed_namespace():
    assert collector.EXPECTED_RUNS == 2000
    assert collector.EXPECTED_SEED_START == 2_200_000
    assert collector.EXPECTED_SEED_END == 2_201_999


def test_d3_wave1_teacher_v4():
    assert (
        collector.EXPECTED_TEACHER_PROFILE
        == "b1-pinned-teacher-v4"
    )

    assert (
        collector.EXPECTED_TEACHER_GIT_SHA
        == "95e97b00def8ec36f12937da34ce8bb9082c4a04"
    )

    assert collector.EXPECTED_MODEL_ID == "Qwen/Qwen3.5-2B"
    assert collector.EXPECTED_QWEN_MODE == "planner_v2"


def test_d3_wave1_paths():
    assert (
        collector.DEFAULT_PLAN
        == "artifacts/b1_d3_expansion_plan_wave1_v1/"
           "d3_expansion_plan_wave1.json"
    )

    assert (
        collector.DEFAULT_OUTPUT_ROOT
        == "artifacts/b1_d3_wave1_2000_teacher_v4"
    )

    assert (
        collector.DEFAULT_SERVICE_URL
        == "http://127.0.0.1:18007"
    )
