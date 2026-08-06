from __future__ import annotations

import copy
import json
from pathlib import Path
import threading
import time

import pytest

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


ROOT = Path(__file__).resolve().parents[2]


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


def test_vllm_keep_lane_without_speed_has_valid_hold_completion() -> None:
    backend = VllmQwenPlannerBackend.__new__(VllmQwenPlannerBackend)
    request = _request()
    request["scene_capabilities"] = {}
    request["command_hint"] = {"intent": "KEEP_LANE", "target_speed_mps": None}
    step = backend._step(request, "KEEP_LANE", index=1)
    assert step["completion"]["type"] == "HOLD_FRAMES"
    assert step["completion"]["value"] is None


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
