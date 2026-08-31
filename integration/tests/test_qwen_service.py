from __future__ import annotations

import base64
import copy
import json
from pathlib import Path
import socket
import threading
import time

import pytest
from PIL import Image

from integration.qwen_plan_adapter import QwenPlanParseError
from qwen_service import (
    DeterministicPlannerV2Backend,
    DeterministicTestBackend,
    QwenDecisionService,
    QwenServiceConfig,
    ServiceFailure,
    UnavailableBackend,
    VllmQwenPlannerBackend,
)
from qwen_service.server import _configure_low_latency_socket


ROOT = Path(__file__).resolve().parents[2]


def test_qwen_http_socket_disables_nagle_delay() -> None:
    calls: list[tuple[int, int, int]] = []

    class Connection:
        def setsockopt(self, level: int, option: int, value: int) -> None:
            calls.append((level, option, value))

    _configure_low_latency_socket(Connection())

    assert calls == [(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)]


def _request() -> dict:
    payload = json.loads((ROOT / "interfaces" / "examples" / "model_request.json").read_text(encoding="utf-8"))
    now = time.monotonic_ns()
    payload["created_at_ns"] = now
    payload["deadline_ns"] = now + 1_000_000_000
    return payload


def test_service_returns_strict_high_level_plan_and_metrics() -> None:
    service = QwenDecisionService(DeterministicTestBackend())
    try:
        result = service.infer(_request())
        assert result["behavior"] == "FOLLOW"
        assert result["target_id"] == "vehicle-right-01"
        assert not {"throttle", "brake", "steer"}.intersection(result)
        metrics = service.metrics()
        assert metrics["counts"]["success"] == 1
        assert metrics["latency_ms"]["count"] == 1
        assert service.health()["production_ready"] is False
    finally:
        service.close()


def test_service_rejects_expired_and_unknown_fields() -> None:
    service = QwenDecisionService(DeterministicTestBackend())
    try:
        expired = _request()
        expired["created_at_ns"] = 1
        expired["deadline_ns"] = 2
        with pytest.raises(ServiceFailure) as caught:
            service.infer(expired)
        assert caught.value.error_code == "REQUEST_EXPIRED"
        unknown = _request()
        unknown["unexpected"] = True
        with pytest.raises(ServiceFailure) as caught:
            service.infer(unknown)
        assert caught.value.error_code == "INVALID_REQUEST"
    finally:
        service.close()


def test_service_unavailable_is_explicit_503() -> None:
    service = QwenDecisionService(UnavailableBackend("weights absent"))
    try:
        with pytest.raises(ServiceFailure) as caught:
            service.infer(_request())
        assert caught.value.status_code == 503
        assert caught.value.error_code == "MODEL_UNAVAILABLE"
        assert service.health()["status"] == "DEGRADED"
    finally:
        service.close()


def test_service_enforces_timeout_and_keeps_capacity_bounded() -> None:
    release = threading.Event()

    class SlowBackend(DeterministicTestBackend):
        production_ready = True

        def infer(self, request):
            release.wait(1.0)
            return super().infer(request)

    service = QwenDecisionService(
        SlowBackend(), config=QwenServiceConfig(timeout_ms=5.0, max_concurrency=1),
    )
    try:
        with pytest.raises(ServiceFailure) as timeout:
            service.infer(_request())
        assert timeout.value.error_code == "MODEL_TIMEOUT"
        with pytest.raises(ServiceFailure) as busy:
            service.infer(_request())
        assert busy.value.error_code == "CONCURRENCY_LIMIT"
    finally:
        release.set()
        service.close(wait=True)


def test_service_rejects_model_id_mismatch() -> None:
    class WrongBackend(DeterministicTestBackend):
        def infer(self, request):
            plan = dict(super().infer(request))
            plan["command_id"] = "wrong"
            return plan

    service = QwenDecisionService(WrongBackend())
    try:
        with pytest.raises(ServiceFailure) as caught:
            service.infer(_request())
        assert caught.value.error_code == "MODEL_ID_MISMATCH"
    finally:
        service.close()


def test_planner_v2_service_returns_strict_maneuver_plan():
    request = _request()
    request["source_text"] = "跟随前方车辆"
    request["routing"] = {
        "disposition": "QWEN_PLAN", "score": 5,
        "reasons": ["VISUAL_REFERENCE", "COMPLEX_MANEUVER"],
        "safe_wait_behavior": "SLOW_DOWN",
    }
    request["scene_capabilities"] = {}
    service = QwenDecisionService(
        DeterministicPlannerV2Backend(), qwen_mode="planner_v2",
    )
    try:
        result = service.infer(request)
        assert result["schema_version"] == "2.0"
        assert result["steps"][0]["behavior"] == "FOLLOW"
        assert result["steps"][0]["target"]["target_id"] == "vehicle-right-01"
        assert service.health()["qwen_mode"] == "planner_v2"
        assert service.metrics()["counts"]["success"] == 1
    finally:
        service.close()


def test_planner_v2_service_rejects_low_level_model_output():
    class UnsafePlanner(DeterministicPlannerV2Backend):
        def infer(self, request):
            plan = copy.deepcopy(super().infer(request))
            plan["steps"][0]["steer"] = 0.8
            return plan

    request = _request()
    service = QwenDecisionService(UnsafePlanner(), qwen_mode="planner_v2")
    try:
        with pytest.raises(ServiceFailure) as caught:
            service.infer(request)
        assert caught.value.error_code == "LOW_LEVEL_OUTPUT_FORBIDDEN"
        assert caught.value.status_code == 502
    finally:
        service.close()


def test_planner_v2_service_classifies_malformed_generation_as_bad_gateway():
    class MalformedPlanner(DeterministicPlannerV2Backend):
        def infer(self, request):
            raise QwenPlanParseError("MODEL_OUTPUT_MUST_BE_BARE_JSON_OBJECT")

    service = QwenDecisionService(MalformedPlanner(), qwen_mode="planner_v2")
    try:
        with pytest.raises(ServiceFailure) as caught:
            service.infer(_request())
        assert caught.value.status_code == 502
        assert caught.value.error_code == "INVALID_MODEL_OUTPUT"
        assert service.metrics()["counts"]["invalid"] == 1
    finally:
        service.close()


def test_planner_v2_stub_preserves_lane_change_then_speed_sequence():
    request = _request()
    request["source_text"] = "确认安全后向左变道并保持二十公里每小时"
    request["routing"] = {
        "disposition": "QWEN_PLAN", "score": 8,
        "reasons": ["MULTI_ACTION", "SEQUENCE", "COMPLEX_MANEUVER"],
        "safe_wait_behavior": "SLOW_DOWN",
    }
    request["scene_capabilities"] = {
        "available_lanes": ["CURRENT", "LEFT_ADJACENT"],
        "left_lane_exists": True,
        "left_gap_safe": True,
    }
    service = QwenDecisionService(
        DeterministicPlannerV2Backend(), qwen_mode="planner_v2",
    )
    try:
        plan = service.infer(request)
        assert [step["behavior"] for step in plan["steps"]] == [
            "CHANGE_LANE_LEFT", "SET_SPEED",
        ]
        assert plan["steps"][0]["timeout_s"] >= 12.0
    finally:
        service.close()


def test_planner_v2_stub_grounds_avoid_and_return_in_sensor_target():
    request = _request()
    request["source_text"] = "绕过前方障碍物后回到当前车道"
    request["routing"] = {
        "disposition": "QWEN_PLAN", "score": 9,
        "reasons": ["MULTI_ACTION", "SEQUENCE", "VISUAL_REFERENCE"],
        "safe_wait_behavior": "SLOW_DOWN",
    }
    request["targets"] = [{
        "target_id": "legacy-obstacle-000", "class": "obstacle",
        "distance_m": 18.0, "relative_speed_mps": 0.0,
        "confidence": 1.0, "relation": "center_ahead",
    }]
    request["scene_capabilities"] = {
        "available_lanes": ["CURRENT", "LEFT_ADJACENT"],
        "left_lane_exists": True,
        "left_gap_safe": True,
    }
    service = QwenDecisionService(
        DeterministicPlannerV2Backend(), qwen_mode="planner_v2",
    )
    try:
        plan = service.infer(request)
        assert [step["behavior"] for step in plan["steps"]] == [
            "AVOID_OBSTACLE", "RETURN_TO_LANE",
        ]
        assert plan["steps"][0]["target"]["target_id"] == "legacy-obstacle-000"
        assert plan["steps"][0]["target"]["target_lane"] == "LEFT_ADJACENT"
    finally:
        service.close()


def test_vllm_prompt_does_not_leak_hint_and_is_bounded() -> None:
    backend = VllmQwenPlannerBackend.__new__(VllmQwenPlannerBackend)
    request = _request()
    request["source_text"] = "follow the vehicle directly ahead " * 100
    request["command_hint"] = {"intent": "KEEP_LANE", "target_speed_mps": 9.0}
    request["targets"] = [
        {"target_id": f"target-{index}", "class": "vehicle", "distance_m": 10 + index,
         "relative_speed_mps": 0.0, "confidence": 0.9, "relation": "center_ahead"}
        for index in range(20)
    ]
    request["scene_capabilities"] = {"left_lane_exists": True, "right_lane_exists": True}
    prompt = backend._choice_prompt(request)
    assert '"hint"' not in prompt
    assert "KEEP_LANE\",\"target_speed_mps" not in prompt
    assert len(prompt) < 3000


def test_vllm_choice_constraint_excludes_disallowed_lane_changes() -> None:
    backend = VllmQwenPlannerBackend.__new__(VllmQwenPlannerBackend)
    request = _request()
    request["constraints"]["allowed_behaviors"] = [
        "KEEP_LANE", "SLOW_DOWN", "STOP", "YIELD",
    ]

    codes = backend._choice_codes(request)
    prompt = backend._choice_prompt(request, choice_codes=codes)

    assert codes == ["A", "C", "D", "E"]
    assert "G=CHANGE_LANE_LEFT" not in prompt
    assert "H=CHANGE_LANE_RIGHT" not in prompt


def test_vllm_choice_constraint_narrows_explicit_right_avoid_to_whole_maneuver() -> None:
    backend = VllmQwenPlannerBackend.__new__(VllmQwenPlannerBackend)
    request = _request()
    request["command_hint"] = {
        "intent": "AVOID_OBSTACLE", "direction": "RIGHT",
        "target_speed_mps": None, "target": None,
    }
    request["constraints"]["allowed_behaviors"] = [
        "CHANGE_LANE", "TURN", "AVOID_OBSTACLE", "RETURN_TO_LANE", "STOP",
    ]

    codes = backend._choice_codes(request)

    assert codes == ["D", "K"]


def test_vllm_choice_constraint_narrows_pedestrian_slow_down_to_longitudinal_actions() -> None:
    backend = VllmQwenPlannerBackend.__new__(VllmQwenPlannerBackend)
    request = _request()
    request["command_hint"] = {
        "intent": "SLOW_DOWN", "direction": None,
        "target_speed_mps": None, "target": "crossing_pedestrian",
    }
    request["constraints"]["allowed_behaviors"] = [
        "KEEP_LANE", "SET_SPEED", "SLOW_DOWN", "STOP", "YIELD", "FOLLOW",
        "CHANGE_LANE", "TURN", "AVOID_OBSTACLE", "RETURN_TO_LANE", "PULL_OVER",
    ]
    request["scene_capabilities"] = {
        "available_lanes": ["CURRENT", "RIGHT_ADJACENT"],
        "left_lane_exists": False,
        "right_lane_exists": True,
    }

    codes = backend._choice_codes(request)

    assert codes == ["C"]


def test_vllm_pedestrian_slow_down_preserves_resume_subcommand() -> None:
    backend = VllmQwenPlannerBackend.__new__(VllmQwenPlannerBackend)
    request = _request()
    request["source_text"] = "看到横穿行人，减速避让，确认行人离开后继续"
    request["command_hint"] = {
        "intent": "SLOW_DOWN", "direction": None,
        "target_speed_mps": None, "target": "crossing_pedestrian",
    }
    request["constraints"]["max_target_speed_mps"] = 8.0
    request["targets"] = [{
        "target_id": "crossing_pedestrian", "class": "pedestrian",
        "distance_m": 20.0, "relation": "center_ahead",
    }]

    steps = backend._expanded_steps(request, "SLOW_DOWN")

    assert [step["behavior"] for step in steps] == ["SLOW_DOWN", "KEEP_LANE"]
    assert steps[0]["target"]["target_id"] == "crossing_pedestrian"
    assert steps[0]["target"]["target_speed_mps"] == pytest.approx(3.0)
    assert steps[1]["target"]["target_id"] is None
    assert steps[1]["target"]["target_speed_mps"] == pytest.approx(8.0)
    assert steps[1]["preconditions"] == ["PERCEPTION_FRESH", "NO_EMERGENCY_RISK"]


def test_vllm_grounds_unavailable_named_target_to_visible_forward_object() -> None:
    backend = VllmQwenPlannerBackend.__new__(VllmQwenPlannerBackend)
    request = _request()
    request["command_hint"] = {
        "intent": "AVOID_OBSTACLE", "direction": "LEFT",
        "target_speed_mps": 7.0, "target": "slow_vehicle",
    }
    request["targets"] = [{
        "target_id": "crossing_pedestrian", "class": "pedestrian",
        "distance_m": 20.0, "relation": "center_ahead",
    }]

    step = backend._step(request, "AVOID_OBSTACLE", index=1)

    assert step["target"]["target_id"] == "crossing_pedestrian"


def test_vllm_keep_lane_does_not_require_a_named_context_actor() -> None:
    backend = VllmQwenPlannerBackend.__new__(VllmQwenPlannerBackend)
    request = _request()
    request["command_hint"] = {
        "intent": "KEEP_LANE", "direction": None,
        "target_speed_mps": 8.0, "target": "bus_at_stop",
    }

    step = backend._step(request, "KEEP_LANE", index=1)

    assert step["target"]["target_id"] is None


def test_vllm_avoid_step_preserves_explicit_right_target_lane() -> None:
    backend = VllmQwenPlannerBackend.__new__(VllmQwenPlannerBackend)
    request = _request()
    request["command_hint"] = {
        "intent": "AVOID_OBSTACLE", "direction": "RIGHT",
        "target_speed_mps": None, "target": None,
    }
    request["scene_capabilities"] = {
        "available_lanes": ["CURRENT", "RIGHT_ADJACENT"],
        "right_lane_exists": True, "right_gap_safe": True,
    }

    step = backend._step(request, "AVOID_OBSTACLE", index=1)

    assert step["target"]["target_lane"] == "RIGHT_ADJACENT"
    assert step["target"]["target_speed_mps"] == pytest.approx(3.0)


def test_vllm_lane_change_without_requested_speed_uses_safe_maneuver_default() -> None:
    backend = VllmQwenPlannerBackend.__new__(VllmQwenPlannerBackend)
    request = _request()
    request["command_hint"] = {
        "intent": "CHANGE_LANE", "direction": "RIGHT",
        "target_speed_mps": None, "target": None,
    }

    step = backend._step(request, "CHANGE_LANE_RIGHT", index=1)

    assert step["target"]["target_speed_mps"] == pytest.approx(3.0)


def test_vllm_set_speed_is_clamped_to_runtime_limit() -> None:
    backend = VllmQwenPlannerBackend.__new__(VllmQwenPlannerBackend)
    request = _request()
    request["command_hint"] = {"intent": "SET_SPEED", "target_speed_mps": 33.3}
    request["constraints"]["max_target_speed_mps"] = 8.0

    step = backend._step(request, "SET_SPEED", index=1)

    assert step["target"]["target_speed_mps"] == 8.0


def test_vllm_reuses_already_normalized_jpeg_without_reencoding(tmp_path) -> None:
    path = tmp_path / "normalized.jpg"
    Image.new("RGB", (224, 224), (32, 64, 96)).save(path, format="JPEG", quality=75)
    original = path.read_bytes()
    backend = VllmQwenPlannerBackend.__new__(VllmQwenPlannerBackend)
    backend.image_max_side = 224
    backend.jpeg_quality = 75

    data_url = backend._image_data_url(path)

    assert base64.b64decode(data_url.split(",", 1)[1]) == original


def test_vllm_follow_binds_center_ahead_not_nearest_distractor() -> None:
    backend = VllmQwenPlannerBackend.__new__(VllmQwenPlannerBackend)
    request = _request()
    request["source_text"] = "跟随正前方同车道车辆，不要跟左右车辆"
    request["scene_capabilities"] = {}
    request["targets"] = [
        {"target_id": "left-distractor", "distance_m": 10.0, "relation": "left_ahead"},
        {"target_id": "lead-target", "distance_m": 20.0, "relation": "center_ahead"},
    ]
    step = backend._step(request, "FOLLOW", index=1)
    assert step["target"]["target_id"] == "lead-target"
    assert step["completion"]["type"] == "TARGET_GAP_REACHED"
    assert step["completion"]["value"] == 2.0


def test_vllm_follow_prefers_vehicle_over_nearer_center_obstacle() -> None:
    backend = VllmQwenPlannerBackend.__new__(VllmQwenPlannerBackend)
    request = _request()
    request["source_text"] = "跟随正前方车辆"
    request["scene_capabilities"] = {}
    request["targets"] = [
        {
            "target_id": "temporary_occluder", "class": "obstacle",
            "distance_m": 22.0, "relation": "center_ahead",
        },
        {
            "target_id": "target_front", "class": "vehicle",
            "distance_m": 28.0, "relation": "center_ahead",
        },
    ]

    step = backend._step(request, "FOLLOW", index=1)

    assert step["target"]["target_id"] == "target_front"


def test_vllm_visual_slow_down_binds_target_and_reduces_hinted_speed() -> None:
    backend = VllmQwenPlannerBackend.__new__(VllmQwenPlannerBackend)
    request = _request()
    request["scene_capabilities"] = {}
    request["command_hint"] = {"intent": "KEEP_LANE", "target_speed_mps": 5.0}
    request["targets"] = [{
        "target_id": "blocker-001", "distance_m": 26.0, "relation": "center_ahead",
    }]

    step = backend._step(request, "SLOW_DOWN", index=1)

    assert step["target"]["target_id"] == "blocker-001"
    assert step["target"]["target_speed_mps"] == pytest.approx(3.0)


def test_vllm_keep_lane_without_speed_has_valid_hold_completion() -> None:
    backend = VllmQwenPlannerBackend.__new__(VllmQwenPlannerBackend)
    request = _request()
    request["scene_capabilities"] = {}
    request["command_hint"] = {"intent": "KEEP_LANE", "target_speed_mps": None}
    step = backend._step(request, "KEEP_LANE", index=1)
    assert step["completion"]["type"] == "HOLD_FRAMES"
    assert step["completion"]["value"] is None


def test_vllm_pull_over_uses_validator_compatible_completion() -> None:
    backend = VllmQwenPlannerBackend.__new__(VllmQwenPlannerBackend)
    request = _request()
    request["scene_capabilities"] = {"available_lanes": ["CURRENT", "SHOULDER"]}
    request["command_hint"] = {
        "intent": "PULL_OVER", "target_speed_mps": 2.0, "target": None,
    }

    step = backend._step(request, "PULL_OVER", index=1)

    assert step["target"]["target_lane"] == "SHOULDER"
    assert step["target"]["target_speed_mps"] == 0.0
    assert step["completion"]["type"] == "STOPPED"


def test_vllm_ambiguous_route_is_forced_to_hold_after_model_choice() -> None:
    class _Completions:
        @staticmethod
        def create(**_kwargs):
            message = type("Message", (), {"content": "G"})()
            return type("Response", (), {"choices": [type("Choice", (), {"message": message})()]})()

    backend = VllmQwenPlannerBackend.__new__(VllmQwenPlannerBackend)
    backend._client = type("Client", (), {
        "chat": type("Chat", (), {"completions": _Completions()})(),
    })()
    backend.model_id = "test"
    backend.image_root = None
    backend.max_new_tokens = 1
    request = _request()
    request["rgb_ref"] = None
    request["routing"] = {
        "disposition": "CONFIRM_SAFE", "score": 9,
        "reasons": ["CONFIRMATION_REQUIRED"], "safe_wait_behavior": "STOP",
    }
    request["scene_capabilities"] = {}
    plan = backend.infer(request)
    assert plan["steps"][0]["behavior"] == "HOLD"
