from __future__ import annotations

import copy

from tools.analyze_v3_field_normalization import normalize_student_records


def _record(steps: list[dict]) -> dict:
    return {
        "sample_id": "td_test",
        "status": "SUCCESS",
        "prediction": {"steps": steps},
    }


def _step(behavior: str, lane: str | None) -> dict:
    return {
        "behavior": behavior,
        "target": {"target_lane": lane},
    }


def test_materializes_only_implicit_current_lane_behaviors() -> None:
    source = [
        _record(
            [
                _step("KEEP_LANE", None),
                _step("SET_SPEED", None),
                _step("TURN_LEFT", None),
                _step("CHANGE_LANE_RIGHT", "RIGHT_ADJACENT"),
            ]
        )
    ]
    untouched = copy.deepcopy(source)

    normalized, evidence = normalize_student_records(source)

    assert source == untouched
    lanes = [
        step["target"]["target_lane"]
        for step in normalized[0]["prediction"]["steps"]
    ]
    assert lanes == ["CURRENT", "CURRENT", None, "RIGHT_ADJACENT"]
    assert evidence == {
        "adjusted_step_count": 2,
        "adjusted_sample_count": 1,
        "adjustments_by_behavior": {
            "KEEP_LANE": 1,
            "SET_SPEED": 1,
        },
    }


def test_failed_prediction_is_not_modified() -> None:
    source = [
        {
            "sample_id": "td_failed",
            "status": "INFERENCE_ERROR",
            "prediction": None,
        }
    ]

    normalized, evidence = normalize_student_records(source)

    assert normalized == source
    assert normalized is not source
    assert evidence == {
        "adjusted_step_count": 0,
        "adjusted_sample_count": 0,
        "adjustments_by_behavior": {},
    }
