from __future__ import annotations

import json
from pathlib import Path

from challenge.dataset import build_d2_expansion_plan as d2


def _write_scenario(
    repo: Path,
    rel: str,
    *,
    tags: list[str],
    planning_mode: str,
) -> dict[str, str]:
    path = repo / "scenarios" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "scenario_id": Path(rel).stem,
                "tags": tags,
                "route": {
                    "planning_mode": planning_mode,
                },
            }
        ),
        encoding="utf-8",
    )

    return {
        "scenario_path": rel,
        "scenario_id": Path(rel).stem,
        "family": "development",
        "source_bucket": "SEEN",
        "policy_class": "TRAIN_POSITIVE",
        "map": "Town03_Opt",
        "seed": "0",
        "command_count": "1",
    }


def test_route_generalization_destination_is_not_seed_expandable(
    tmp_path: Path,
) -> None:
    row = _write_scenario(
        tmp_path,
        "development/ROUTE_GEN_FIXTURE.json",
        tags=["route_generalization", "destination"],
        planning_mode="destination",
    )

    allowed, reason = d2.seed_expansion_policy(tmp_path, row)

    assert allowed is False
    assert reason == "ROUTE_GENERALIZATION_DESTINATION_FIXED_FIXTURE"


def test_ordinary_destination_without_route_generalization_remains_eligible(
    tmp_path: Path,
) -> None:
    row = _write_scenario(
        tmp_path,
        "development/ORDINARY_DESTINATION.json",
        tags=["ordinary"],
        planning_mode="destination",
    )

    allowed, reason = d2.seed_expansion_policy(tmp_path, row)

    assert allowed is True
    assert reason == "SEED_EXPANSION_ELIGIBLE"


def test_route_generalization_non_destination_is_not_blanket_excluded(
    tmp_path: Path,
) -> None:
    row = _write_scenario(
        tmp_path,
        "development/ROUTE_GENERALIZATION_OTHER.json",
        tags=["route_generalization"],
        planning_mode="local_polyline",
    )

    allowed, reason = d2.seed_expansion_policy(tmp_path, row)

    assert allowed is True
    assert reason == "SEED_EXPANSION_ELIGIBLE"


def test_zero_target_bucket_can_have_empty_candidate_pool(
    tmp_path: Path,
) -> None:
    rows = []

    # A zero-sized quota is a valid governance state. In particular,
    # NON_TOWN03 may intentionally be zero when the frozen registry
    # contains no seed-expansion-safe cross-map Teacher sources.
    original_quotas = dict(d2.QUOTAS)
    original_planned_runs = d2.PLANNED_RUNS

    try:
        d2.QUOTAS.clear()
        d2.QUOTAS.update({
            "BALANCED_SEEN": 0,
            "VARIANT": 0,
            "UNDERCOVERED_MANEUVER": 0,
            "QWEN_CHAIN_ROUTING": 0,
            "SAFETY_COMPLEX": 0,
            "NON_TOWN03": 0,
        })
        d2.PLANNED_RUNS = 0

        plan = d2.build_plan(
            tmp_path,
            rows,
            prior_seeds=set(),
        )

        assert plan == []
    finally:
        d2.QUOTAS.clear()
        d2.QUOTAS.update(original_quotas)
        d2.PLANNED_RUNS = original_planned_runs
