from __future__ import annotations

import json
from pathlib import Path

import pytest

from challenge.dataset import build_d2_wave2_plan as wave2


def _row(
    scenario_id: str,
    scenario_path: str,
    *,
    family: str = "acceptance_suite",
    source_bucket: str = "SEEN",
    policy_class: str = "TRAIN_POSITIVE",
    map_name: str = "Town03",
) -> dict[str, str]:
    return {
        "scenario_id": scenario_id,
        "scenario_path": scenario_path,
        "family": family,
        "source_bucket": source_bucket,
        "policy_class": policy_class,
        "command_count": "1",
        "map": map_name,
        "seed": "0",
    }


def _write_scenario(
    root: Path,
    rel: str,
    *,
    tags: list[str] | None = None,
    planning_mode: str | None = None,
) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)

    route = {
        "coordinate_type": "scenario_local_xy_m",
        "points_xy_m": [[0, 0], [10, 0]],
    }

    if planning_mode is not None:
        route["planning_mode"] = planning_mode

    payload = {
        "schema_version": "1.0",
        "scenario_id": path.stem,
        "tags": tags or [],
        "route": route,
    }

    path.write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )


def test_wave2_quota_accounting_is_frozen() -> None:
    assert wave2.PLAN_VERSION == "b1_d2_expansion_wave2_v1"
    assert wave2.SEED_START == 2_100_000

    assert wave2.QUOTAS == {
        "DIRECTIONAL_RECOLLECTION": 240,
        "QWEN_CHAIN_ROUTING": 128,
        "SAFETY_COMPLEX": 240,
        "VARIANT": 358,
        "BALANCED_SEEN": 1034,
        "NON_TOWN03": 0,
    }

    assert wave2.PLANNED_RUNS == 2000
    assert sum(wave2.QUOTAS.values()) == 2000


def test_directional_recollection_sources_are_exactly_frozen_eight() -> None:
    assert wave2.DIRECTIONAL_RECOLLECTION == {
        "B06_left_turn",
        "B07_right_turn",
        "B08_lane_change_left",
        "B09_lane_change_right",
        "REG_004_advanced_rain_left_turn",
        "REG_005_advanced_rain_right_turn",
        "REG_009_challenge_lane_change_left",
        "REG_010_challenge_lane_change_right",
    }


@pytest.mark.parametrize(
    "scenario_id",
    sorted(wave2.DIRECTIONAL_RECOLLECTION),
)
def test_directional_recollection_cap_is_exactly_30(
    scenario_id: str,
) -> None:
    row = {
        "scenario_id": scenario_id,
        "family": "regression",
        "source_bucket": "SEEN",
    }

    assert (
        wave2.cap_for(row, "DIRECTIONAL_RECOLLECTION")
        == 30
    )

    # Semantic repair sources must not silently re-enter
    # general Wave2 expansion.
    assert wave2.cap_for(row, "BALANCED_SEEN") == 0


def test_route_generalization_destination_fixture_is_excluded(
    tmp_path: Path,
) -> None:
    rel = "scenarios/regression/fixed_destination.json"

    _write_scenario(
        tmp_path,
        rel,
        tags=["route_generalization"],
        planning_mode="destination",
    )

    row = _row(
        "fixed_destination",
        rel,
    )

    allowed, reason = wave2.seed_expansion_policy(
        tmp_path,
        row,
    )

    assert allowed is False
    assert (
        reason
        == "ROUTE_GENERALIZATION_DESTINATION_FIXED_FIXTURE"
    )


def test_normal_seed_expandable_scenario_is_allowed(
    tmp_path: Path,
) -> None:
    rel = "scenarios/regression/normal.json"

    _write_scenario(
        tmp_path,
        rel,
        tags=["regression"],
    )

    row = _row(
        "normal",
        rel,
    )

    allowed, reason = wave2.seed_expansion_policy(
        tmp_path,
        row,
    )

    assert allowed is True
    assert reason == "SEED_EXPANSION_ELIGIBLE"


def test_candidate_pool_fail_closed_on_policy_and_source_bucket(
    tmp_path: Path,
) -> None:
    rel_seen = "scenarios/a/seen.json"
    rel_variant = "scenarios/a/variant.json"
    rel_unseen = "scenarios/a/unseen.json"
    rel_reserved = "scenarios/a/reserved.json"

    for rel in (
        rel_seen,
        rel_variant,
        rel_unseen,
        rel_reserved,
    ):
        _write_scenario(tmp_path, rel)

    rows = [
        _row(
            "seen",
            rel_seen,
            source_bucket="SEEN",
        ),
        _row(
            "variant",
            rel_variant,
            source_bucket="VARIANT",
        ),
        _row(
            "unseen",
            rel_unseen,
            source_bucket="UNSEEN",
        ),
        _row(
            "reserved",
            rel_reserved,
            source_bucket="SEEN",
            policy_class="RESERVED_TEST_CANDIDATE",
        ),
    ]

    seen_pool = wave2.candidate_pool(
        tmp_path,
        rows,
        "BALANCED_SEEN",
    )

    variant_pool = wave2.candidate_pool(
        tmp_path,
        rows,
        "VARIANT",
    )

    assert [x["scenario_id"] for x in seen_pool] == ["seen"]
    assert [x["scenario_id"] for x in variant_pool] == ["variant"]


def test_directional_candidates_are_isolated_from_general_pool(
    tmp_path: Path,
) -> None:
    rows = []

    for scenario_id in sorted(
        wave2.DIRECTIONAL_RECOLLECTION
    ):
        rel = f"scenarios/test/{scenario_id}.json"
        _write_scenario(tmp_path, rel)

        rows.append(
            _row(
                scenario_id,
                rel,
                source_bucket="SEEN",
            )
        )

    recollection = wave2.candidate_pool(
        tmp_path,
        rows,
        "DIRECTIONAL_RECOLLECTION",
    )

    balanced_seen = wave2.candidate_pool(
        tmp_path,
        rows,
        "BALANCED_SEEN",
    )

    assert {
        x["scenario_id"]
        for x in recollection
    } == wave2.DIRECTIONAL_RECOLLECTION

    assert balanced_seen == []


def test_teacher_v4_identity_constants_are_frozen() -> None:
    assert (
        wave2.EXPECTED_TEACHER_PROFILE
        == "b1-pinned-teacher-v4"
    )

    assert (
        wave2.EXPECTED_TEACHER_GIT_SHA
        == "95e97b00def8ec36f12937da34ce8bb9082c4a04"
    )


def test_wave2_seed_namespace_does_not_overlap_wave1_namespace() -> None:
    wave1 = set(range(2_000_000, 2_001_000))

    wave2_seeds = set(
        range(
            wave2.SEED_START,
            wave2.SEED_START + wave2.PLANNED_RUNS,
        )
    )

    assert len(wave2_seeds) == 2000
    assert not (wave1 & wave2_seeds)

    assert min(wave2_seeds) == 2_100_000
    assert max(wave2_seeds) == 2_101_999


def test_formal_builder_identity_path_can_be_json_serialized() -> None:
    identity = {
        "path": Path("challenge/dataset/build_d2_wave2_plan.py"),
        "git_sha": "a" * 40,
        "sha256": "b" * 64,
        "tracked_matches_head": True,
    }

    normalized = dict(identity)

    if isinstance(normalized.get("path"), Path):
        normalized["path"] = str(normalized["path"])

    payload = {
        "builder_identity": normalized,
    }

    digest = wave2.canonical_json_sha256(payload)

    assert isinstance(normalized["path"], str)
    assert len(digest) == 64
