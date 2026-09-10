from __future__ import annotations

import json
from pathlib import Path

from tools.validate_scenarios import validate_one


ROOT = Path(__file__).resolve().parents[2]


def test_explicit_vehicle_lane_relation_rejects_cross_lane_offset(
    tmp_path: Path,
) -> None:
    source = ROOT / "scenarios" / "official_competition" / "S2_complex_avoidance_8km.json"
    data = json.loads(source.read_text(encoding="utf-8"))
    bicycle = next(actor for actor in data["actors"] if actor["actor_id"] == "bicycle_right")
    bicycle["route_position"].update(
        {"lane_relation": "CURRENT", "lateral_offset_m": 7.0},
    )
    scenario = tmp_path / "invalid_actor_lane.json"
    scenario.write_text(json.dumps(data), encoding="utf-8")

    errors = validate_one(scenario)

    assert any("lane-local lateral_offset_m" in error for error in errors)
