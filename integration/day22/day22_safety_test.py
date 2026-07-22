from __future__ import annotations

from .day22_context import Day22Context
from .qwen_day22_adapter import Day22QwenAdapter


def infer(voice: str, safety: dict) -> dict:
    return Day22QwenAdapter().infer(
        Day22Context(
            voice_command=voice,
            safety_state=safety,
            perception={},
            scene_state={},
        )
    )


def main() -> None:
    red = infer(
        "继续走",
        {
            "traffic_light": "RED",
            "distance_to_stop_line_m": 3.0,
        },
    )
    assert red["action"] == "STOP"

    far_red = infer(
        "继续走",
        {
            "traffic_light": "RED",
            "distance_to_stop_line_m": 20.0,
        },
    )
    assert far_red["action"] == "SLOW_DOWN"

    ttc = infer(
        "继续",
        {
            "ttc_s": 1.0,
            "lidar_valid": True,
        },
    )
    assert ttc["action"] == "EMERGENCY_STOP"

    low_confidence = infer(
        "继续",
        {
            "input_confidence": 0.4,
        },
    )
    assert low_confidence["action"] == "STOP"
    assert low_confidence["requires_confirmation"] is True

    no_hallucination = infer(
        "前面有人吗",
        {
            "visual_valid": False,
            "lidar_valid": True,
            "front_distance_m": 50.0,
            "object_class": None,
            "object_confidence": 0.0,
        },
    )
    assert no_hallucination["action"] == "START"
    assert "行人" not in no_hallucination["reason_zh"]

    print("DAY22 SAFETY PASS")


if __name__ == "__main__":
    main()
