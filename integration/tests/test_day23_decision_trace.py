from integration.day20.decision_trace import (
    build_decision_trace,
)
from integration.day20.parser import parse_intent
from integration.day20.day20_intent_executor import (
    Day20IntentExecutor,
)


def test_set_speed_trace_is_consistent():
    raw_output = {
        "actions": [
            {
                "action": "SET_SPEED",
                "target_id": "vehicle_12",
                "target_speed_kmh": 10.0,
            }
        ],
        "confidence": 0.94,
        "reason": "前方车辆减速",
    }

    intent = parse_intent(raw_output)
    target = Day20IntentExecutor().execute(intent)

    control_result = {
        "current_speed_kmh": 18.0,
        "target_speed_kmh": 10.0,
        "raw_control": {
            "throttle": 0.0,
            "brake": 0.35,
            "steer": 0.0,
        },
        "control": {
            "throttle": 0.0,
            "brake": 0.35,
            "steer": 0.0,
        },
        "safety_override": False,
        "safety_reason": "",
    }

    trace = build_decision_trace(
        command="前方车辆减速，请降低速度",
        scene_state={
            "frame_id": 100,
            "ego": {"speed_kmh": 18.0},
            "objects": [
                {
                    "object_id": "vehicle_12",
                    "distance_m": 10.0,
                    "direction": "front",
                }
            ],
        },
        rgb_path="artifacts/frame_100.png",
        qwen_raw_output=raw_output,
        driving_intent=intent,
        executor_target=target,
        control_result=control_result,
    )

    assert trace["schema_version"] == "day23-trace-v1"
    assert trace["consistency"]["qwen_to_executor"] is True
    assert trace["consistency"]["executor_to_controller"] is True
    assert trace["consistency"]["final_control_recorded"] is True
    assert trace["consistency"]["status"] == "CONSISTENT"


def test_safety_override_is_recorded_as_consistent():
    raw_output = {
        "actions": [
            {
                "action": "SET_SPEED",
                "target_id": "",
                "target_speed_kmh": 20.0,
            }
        ],
        "confidence": 0.8,
        "reason": "保持安全速度",
    }

    intent = parse_intent(raw_output)
    target = Day20IntentExecutor().execute(intent)

    trace = build_decision_trace(
        command="继续行驶",
        scene_state={"frame_id": 101},
        rgb_path=None,
        qwen_raw_output=raw_output,
        driving_intent=intent,
        executor_target=target,
        control_result={
            "target_speed_kmh": 20.0,
            "control": {
                "throttle": 0.0,
                "brake": 1.0,
                "steer": 0.0,
            },
            "safety_override": True,
            "safety_reason": "collision risk",
        },
    )

    assert trace["consistency"]["safety_override"] is True
    assert (
        trace["consistency"]["status"]
        == "CONSISTENT_WITH_SAFETY_OVERRIDE"
    )


def test_mismatched_speed_is_inconsistent():
    raw_output = {
        "actions": [
            {
                "action": "SET_SPEED",
                "target_id": "",
                "target_speed_kmh": 10.0,
            }
        ],
        "confidence": 0.9,
        "reason": "减速",
    }

    intent = parse_intent(raw_output)
    target = Day20IntentExecutor().execute(intent)

    trace = build_decision_trace(
        command="减速",
        scene_state={"frame_id": 102},
        rgb_path=None,
        qwen_raw_output=raw_output,
        driving_intent=intent,
        executor_target=target,
        control_result={
            "target_speed_kmh": 30.0,
            "control": {
                "throttle": 0.3,
                "brake": 0.0,
                "steer": 0.0,
            },
            "safety_override": False,
        },
    )

    assert (
        trace["consistency"]["executor_to_controller"]
        is False
    )
    assert trace["consistency"]["status"] == "INCONSISTENT"
