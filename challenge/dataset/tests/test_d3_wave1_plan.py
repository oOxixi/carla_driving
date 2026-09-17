from challenge.dataset import build_d3_wave1_plan as plan


def test_d3_wave1_identity():
    assert plan.PLAN_VERSION == "b1_d3_expansion_wave1_v1"

    assert plan.EXPECTED_TEACHER_PROFILE == "b1-pinned-teacher-v4"
    assert (
        plan.EXPECTED_TEACHER_GIT_SHA
        == "95e97b00def8ec36f12937da34ce8bb9082c4a04"
    )


def test_d3_wave1_exact_run_count():
    assert plan.PLANNED_RUNS == 2000
    assert sum(plan.QUOTAS.values()) == 2000


def test_d3_wave1_seed_namespace():
    assert plan.SEED_START == 2_200_000

    seeds = range(
        plan.SEED_START,
        plan.SEED_START + plan.PLANNED_RUNS,
    )

    assert min(seeds) == 2_200_000
    assert max(seeds) == 2_201_999
    assert len(seeds) == 2000

    # Frozen historical acquisition namespaces must not overlap.
    assert set(seeds).isdisjoint(range(2_000_000, 2_001_000))
    assert set(seeds).isdisjoint(range(2_100_000, 2_102_000))


def test_d3_wave1_quotas():
    assert plan.QUOTAS == {
        "UNDERCOVERED": 600,
        "VARIANT": 220,
        "SAFETY_COMPLEX": 400,
        "QWEN_CHAIN_ROUTING": 160,
        "HARD_NEGATIVE_TARGETED": 220,
        "BALANCED_SEEN": 400,
    }


def test_directional_recollection_not_a_d3_primary_bucket():
    assert "DIRECTIONAL_RECOLLECTION" not in plan.QUOTAS


def test_d3_safety_complex_pool_not_empty():
    assert len(plan.SAFETY_COMPLEX_HINTS) > 0

    required = {
        "ACC_A01_lead_brake",
        "ACC_A02_red_light_conflict",
        "D01_red_light_stop",
        "D07_low_ttc_emergency_brake",
        "CX_MAIN_01_safe_urban_mission",
    }

    assert required <= plan.SAFETY_COMPLEX_HINTS


def test_d3_wave1_builder_declares_formal_code_gate():
    from pathlib import Path

    source = Path(
        "challenge/dataset/build_d3_wave1_plan.py"
    ).read_text(encoding="utf-8")

    assert '"formal_code_gate": True' in source


def test_d3_wave1_builder_freezes_full_teacher_identity():
    from pathlib import Path

    source = Path(
        "challenge/dataset/build_d3_wave1_plan.py"
    ).read_text(encoding="utf-8")

    assert '"teacher_identity": {' in source
    assert '"teacher_profile": "b1-pinned-teacher-v4"' in source
    assert (
        '"teacher_baseline_git_sha": '
        '"95e97b00def8ec36f12937da34ce8bb9082c4a04"'
        in source
    )
    assert '"teacher_model_id": "Qwen/Qwen3.5-2B"' in source
    assert (
        '"teacher_model_revision": '
        '"15852e8c16360a2fea060d615a32b45270f8a8fc"'
        in source
    )
    assert (
        '"teacher_model_artifact_sha256": '
        '"4bbf183b7b7f1ab9fb9eb325f189f4449d65e9fe664cbfe4bcc58a33888657fa"'
        in source
    )
