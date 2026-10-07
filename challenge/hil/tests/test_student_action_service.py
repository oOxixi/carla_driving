"""Unit tests for the Student decision service used in the CARLA loop."""
from __future__ import annotations

import json
from pathlib import Path

from ..carla.student_action_service import (
    build_student_request,
    parse_prompt_payload,
    plan_to_action,
    plan_to_letter,
    voice_intent,
)


def test_voice_intent_table_covers_the_acceptance_vocabulary() -> None:
    assert voice_intent("紧急停车") == ("EMERGENCY_STOP", None)
    assert voice_intent("请靠边停车") == ("PULL_OVER", None)
    assert voice_intent("把速度设定为二十公里每小时") == ("SET_SPEED", None)
    assert voice_intent("慢一点") == ("SLOW_DOWN", None)
    assert voice_intent("跟着前面的车") == ("FOLLOW", None)
    assert voice_intent("向左变道") == ("CHANGE_LANE", "LEFT")
    assert voice_intent("保持车道") == ("KEEP_LANE", None)


def test_live_model_request_is_passed_through_untouched(tmp_path: Path) -> None:
    """planner_v2 already sends the training-shaped request; do not synthesise."""
    payload = {
        "schema_version": "1.0",
        "request_id": "qwen-abc",
        "command_id": "scenario_cmd_000",
        "created_at_ns": 1,
        "deadline_ns": 2,
        "source_text": "保持车道",
        "command_hint": {"intent": "KEEP_LANE", "target_speed_mps": 4.0},
        "constraints": {"allowed_behaviors": ["KEEP_LANE"], "must_stop": False},
        "scene_summary": {"traffic_light": "GREEN", "risk_level": "LOW"},
        "scene_capabilities": {"route_available": True, "intersection_ahead": True},
    }
    image = tmp_path / "frame.jpg"
    image.write_bytes(b"jpeg")
    request = build_student_request(payload, rgb_path=image, request_id="ignored")
    assert request["request_id"] == "qwen-abc"
    assert request["command_id"] == "scenario_cmd_000"
    assert request["scene_capabilities"] == payload["scene_capabilities"]
    assert request["constraints"] == payload["constraints"]
    assert request["rgb_ref"] == str(image)


def test_synthesised_request_fills_missing_capabilities() -> None:
    payload = {
        "voice_command": "紧急停车",
        "scene_state": {"speed_mps": 6.0},
        "perception": {
            "traffic_light": "GREEN", "lead_distance_m": 5.0,
            "detected_objects": [
                {"class_name": "car", "distance_m": 5.0, "confidence": 0.8, "track_id": "T1"},
            ],
        },
        "safety_state": {"minimum_ttc_s": 1.1, "recommended_action": "STOP"},
    }
    request = build_student_request(payload, rgb_path=None, request_id="req-1")
    assert request["command_hint"]["intent"] == "EMERGENCY_STOP"
    assert request["constraints"]["must_stop"] is True
    assert request["scene_summary"]["risk_level"] == "HIGH"
    assert request["targets"][0]["class"] == "vehicle"
    assert request["scene_capabilities"]["route_available"] is True
    assert request["scene_capabilities"]["left_lane_exists"] is False


def test_plan_mappings_cover_stop_slow_speed_and_progress() -> None:
    def plan(behaviour: str, speed: float | None = None) -> dict:
        return {"steps": [{"behavior": behaviour, "target": {"target_speed_mps": speed}}]}

    assert plan_to_letter(plan("STOP"))[0] == "B"
    assert plan_to_letter(plan("SLOW_DOWN"))[0] == "C"
    assert plan_to_letter(plan("SET_SPEED"))[0] == "D"
    assert plan_to_letter(plan("KEEP_LANE"))[0] == "A"
    assert plan_to_letter({"steps": []}) == ("B", "")

    request = {"constraints": {"speed_limit_mps": 5.0, "max_target_speed_mps": 8.0}}
    action, speed, _ = plan_to_action(plan("SET_SPEED", 9.0), request)
    assert (action, speed) == ("SET_SPEED", 5.0)  # clamped to the scene limit
    action, speed, _ = plan_to_action(plan("KEEP_LANE", 4.0), request)
    assert action == "START" and speed is None
    assert plan_to_action({"steps": []}, request)[0] == "STOP"


def test_prompt_payload_parsing_ignores_the_trailing_reread_sentence() -> None:
    payload = {"voice": "慢一点", "vehicle": {"speed_mps": 8.0}}
    prompt = "融合图像与四模态状态…输入:" + json.dumps(payload, ensure_ascii=False) + "\n复核：最终只输出一个代码。"
    assert parse_prompt_payload(prompt) == payload
