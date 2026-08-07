from __future__ import annotations

import json
from pathlib import Path
import time

from integration.qwen_fault_injection import ScenarioQwenFaultInjector
from runtime import OrchestratorConfig, PipelineOrchestrator


ROOT = Path(__file__).resolve().parents[2]


def _example(name):
    return json.loads((ROOT / "interfaces/examples" / f"{name}.json").read_text(encoding="utf-8"))


def test_planner_v2_routes_validates_compiles_and_exposes_auditable_metadata():
    command = _example("driving_command")
    command.update({
        "command_id": "turn-complex", "source_text": "前方第一个路口右转",
        "intent": "TURN", "parameters": {"direction": "RIGHT"},
    })
    scene = _example("perception_state")

    def infer(request):
        return {
            "schema_version": "2.0",
            "request_id": request["request_id"],
            "command_id": request["command_id"],
            "plan_id": "plan-turn",
            "plan_type": "MANEUVER_SEQUENCE",
            "steps": [{
                "step_id": "turn", "behavior": "TURN_RIGHT",
                "target": {
                    "target_id": None, "target_lane": "ROUTE_BRANCH",
                    "target_speed_mps": 3.0, "time_gap_s": None,
                    "route_direction": "RIGHT",
                },
                "preconditions": [
                    "PERCEPTION_FRESH", "ROUTE_AVAILABLE", "INTERSECTION_AHEAD",
                    "NO_EMERGENCY_RISK",
                ],
                "completion": {
                    "type": "JUNCTION_EXITED", "value": None,
                    "lane": "ROUTE_BRANCH", "hold_frames": 5,
                },
                "timeout_s": 8.0, "on_failure": "SAFE_STOP",
            }],
            "replan_conditions": ["ROUTE_MISMATCH", "PROGRESS_STALLED"],
            "confidence": 0.95,
            "requires_confirmation": False,
            "created_at_ns": request["created_at_ns"],
            "valid_until_ns": request["deadline_ns"],
            "reason_code": "TURN_AT_FIRST_JUNCTION",
            "model_id": "deterministic-planner-v2",
        }

    with PipelineOrchestrator(
        infer=infer, config=OrchestratorConfig(qwen_mode="planner_v2"),
    ) as runtime:
        queued = runtime.submit_command(
            command, scene, now_ns=1_100_000_000,
            runtime_state={"route_available": True, "intersection_ahead": True},
        )
        assert queued.disposition == "SLOW_PENDING"
        assert queued.routing_reasons == ("ROUTE_REFERENCE", "COMPLEX_MANEUVER")
        assert queued.qwen_mode == "planner_v2"
        deadline = time.monotonic() + 1.0
        ready = ()
        while time.monotonic() < deadline and not ready:
            ready = runtime.poll_slow(now_ns=1_150_000_000)
            time.sleep(0.001)
        routing_logs = runtime.drain_logs()
    assert ready[0].disposition == "SLOW_READY"
    assert ready[0].control_command["behavior"] == "TURN_RIGHT"
    assert ready[0].compiled_plan["steps"][0]["behavior"] == "TURN_RIGHT"
    assert routing_logs[0]["record_type"] == "qwen_routing_event"
    assert routing_logs[0]["route"] == "QWEN_PLAN"


def test_ambiguous_target_is_not_sent_to_backend():
    calls = []
    command = _example("driving_command")
    command.update({
        "command_id": "ambiguous", "source_text": "跟着那辆白车",
        "intent": "FOLLOW", "parameters": {},
    })
    scene = _example("perception_state")
    with PipelineOrchestrator(
        infer=lambda request: calls.append(request),
        config=OrchestratorConfig(qwen_mode="planner_v2"),
    ) as runtime:
        result = runtime.submit_command(
            command, scene, now_ns=1_100_000_000,
            runtime_state={"target_candidate_count": 2},
        )
    assert result.disposition == "CONFIRM_SAFE"
    assert result.reason_code == "TARGET_AMBIGUOUS"
    assert calls == []


def test_planner_v2_low_level_fault_is_rejected_not_dispatched():
    command = _example("driving_command")
    command.update({
        "command_id": "unsafe-plan", "source_text": "前方第一个路口右转",
        "intent": "TURN", "parameters": {"direction": "RIGHT"},
    })
    scene = _example("perception_state")

    def valid_plan(request):
        return {
            "schema_version": "2.0",
            "request_id": request["request_id"],
            "command_id": request["command_id"],
            "plan_id": "unsafe-injected-plan",
            "plan_type": "MANEUVER_SEQUENCE",
            "steps": [{
                "step_id": "turn", "behavior": "TURN_RIGHT",
                "target": {
                    "target_id": None, "target_lane": "ROUTE_BRANCH",
                    "target_speed_mps": 3.0, "time_gap_s": None,
                    "route_direction": "RIGHT",
                },
                "preconditions": [
                    "PERCEPTION_FRESH", "ROUTE_AVAILABLE", "INTERSECTION_AHEAD",
                    "NO_EMERGENCY_RISK",
                ],
                "completion": {
                    "type": "JUNCTION_EXITED", "value": None,
                    "lane": "ROUTE_BRANCH", "hold_frames": 5,
                },
                "timeout_s": 8.0, "on_failure": "SAFE_STOP",
            }],
            "replan_conditions": [],
            "confidence": 0.95,
            "requires_confirmation": False,
            "created_at_ns": request["created_at_ns"],
            "valid_until_ns": request["deadline_ns"],
            "reason_code": "TURN_AT_FIRST_JUNCTION",
            "model_id": "test-planner-v2",
        }

    infer = ScenarioQwenFaultInjector(
        valid_plan,
        {"type": "LOW_LEVEL_FIELD", "field": "steer", "value": 0.8},
    )
    with PipelineOrchestrator(
        infer=infer, config=OrchestratorConfig(qwen_mode="planner_v2"),
    ) as runtime:
        queued = runtime.submit_command(
            command, scene, now_ns=1_100_000_000,
            runtime_state={"route_available": True, "intersection_ahead": True},
        )
        deadline = time.monotonic() + 1.0
        rejected = ()
        while time.monotonic() < deadline and not rejected:
            rejected = runtime.poll_slow(now_ns=1_150_000_000)
            time.sleep(0.001)

    assert queued.disposition == "SLOW_PENDING"
    assert rejected[0].disposition == "REJECTED"
    assert rejected[0].feedback["status"] == "REJECTED"
    assert rejected[0].reason_code == "QWEN_PLAN_REJECTED"
    assert rejected[0].control_command is None


def test_forced_qwen_set_speed_is_an_allowed_model_behavior():
    command = _example("driving_command")
    scene = _example("perception_state")
    with PipelineOrchestrator(
        infer=lambda _request: {},
        config=OrchestratorConfig(force_qwen_all_voice=True),
    ) as runtime:
        queued = runtime.submit_command(command, scene, now_ns=1_100_000_000)

    assert queued.disposition == "SLOW_PENDING"
    assert "SET_SPEED" in queued.model_request["constraints"]["allowed_behaviors"]


def test_emergency_stop_bypasses_forced_qwen_and_returns_immediate_fast_control():
    command = _example("driving_command")
    command.update({"intent": "EMERGENCY_STOP", "parameters": {}})
    scene = _example("perception_state")
    with PipelineOrchestrator(
        infer=lambda _request: (_ for _ in ()).throw(AssertionError("Qwen must not run")),
        config=OrchestratorConfig(force_qwen_all_voice=True),
    ) as runtime:
        result = runtime.submit_command(command, scene, now_ns=1_100_000_000)

    assert result.disposition == "FAST"
    assert result.control_command["behavior"] == "EMERGENCY_STOP"


def test_non_maneuver_keep_lane_request_cannot_hallucinate_lane_change():
    command = _example("driving_command")
    command.update({
        "intent": "KEEP_LANE",
        "source_text": "keep the lane at the intersection",
        "parameters": {"target_speed_mps": 4.0},
    })
    scene = _example("perception_state")
    with PipelineOrchestrator(
        infer=lambda _request: {},
        config=OrchestratorConfig(force_qwen_all_voice=True, qwen_mode="planner_v2"),
    ) as runtime:
        queued = runtime.submit_command(
            command,
            scene,
            now_ns=1_100_000_000,
            runtime_state={"route_available": True, "intersection_ahead": True},
        )

    assert queued.disposition == "SLOW_PENDING"
    assert queued.model_request["constraints"]["allowed_behaviors"] == ["KEEP_LANE"]


def test_conditional_keep_lane_request_cannot_hallucinate_yield():
    command = _example("driving_command")
    command.update({
        "intent": "KEEP_LANE",
        "source_text": "保持车道，感知异常时降低速度",
        "parameters": {"target_speed_mps": 4.0},
    })
    scene = _example("perception_state")
    with PipelineOrchestrator(
        infer=lambda _request: {},
        config=OrchestratorConfig(force_qwen_all_voice=True, qwen_mode="planner_v2"),
    ) as runtime:
        queued = runtime.submit_command(
            command,
            scene,
            now_ns=1_100_000_000,
            runtime_state={"route_available": True, "intersection_ahead": True},
        )

    assert queued.disposition == "SLOW_PENDING"
    assert queued.model_request["constraints"]["allowed_behaviors"] == [
        "KEEP_LANE", "SLOW_DOWN", "STOP",
    ]


def test_visual_target_keep_lane_request_allows_slow_or_stop_response():
    command = _example("driving_command")
    command.update({
        "intent": "KEEP_LANE",
        "source_text": "前方有障碍物，安全处理",
        "parameters": {"target_speed_mps": 5.0},
    })
    scene = _example("perception_state")
    with PipelineOrchestrator(
        infer=lambda _request: {},
        config=OrchestratorConfig(force_qwen_all_voice=True, qwen_mode="planner_v2"),
    ) as runtime:
        queued = runtime.submit_command(
            command,
            scene,
            now_ns=1_100_000_000,
            runtime_state={"target_candidate_count": 1},
        )

    assert queued.model_request["constraints"]["allowed_behaviors"] == [
        "KEEP_LANE", "SLOW_DOWN", "STOP",
    ]


def test_explicit_right_avoid_request_excludes_unrelated_complex_behaviors():
    command = _example("driving_command")
    command.update({
        "intent": "AVOID_OBSTACLE",
        "source_text": "从右侧安全绕过前方静止车辆",
        "parameters": {"direction": "RIGHT"},
    })
    scene = _example("perception_state")
    with PipelineOrchestrator(
        infer=lambda _request: {},
        config=OrchestratorConfig(force_qwen_all_voice=True, qwen_mode="planner_v2"),
    ) as runtime:
        queued = runtime.submit_command(
            command,
            scene,
            now_ns=1_100_000_000,
            runtime_state={
                "right_lane_exists": True, "right_gap_safe": True,
                "available_lanes": ["CURRENT", "RIGHT_ADJACENT"],
            },
        )

    assert queued.disposition == "SLOW_PENDING"
    assert queued.model_request["constraints"]["allowed_behaviors"] == [
        "SLOW_DOWN", "STOP", "CHANGE_LANE", "AVOID_OBSTACLE", "RETURN_TO_LANE",
    ]


def test_forced_qwen_safety_scene_is_audited_while_waiting_stopped():
    command = _example("driving_command")
    command["intent"] = "KEEP_LANE"
    command["parameters"] = {}
    scene = _example("perception_state")
    scene["traffic_light"] = "RED"
    scene["distance_to_stop_line_m"] = 8.0
    with PipelineOrchestrator(
        infer=lambda _request: {},
        config=OrchestratorConfig(force_qwen_all_voice=True),
    ) as runtime:
        queued = runtime.submit_command(command, scene, now_ns=1_100_000_000)

    assert queued.disposition == "SLOW_PENDING"
    assert queued.model_request["constraints"]["must_stop"] is True
    assert queued.model_request["constraints"]["allowed_behaviors"] == ["STOP"]
    assert queued.feedback["safety_event"]["reason_code"] == "TRAFFIC_LIGHT_STOP"


def test_close_center_lead_forces_targeted_stop_plan() -> None:
    command = _example("driving_command")
    command["intent"] = "KEEP_LANE"
    command["parameters"] = {"target_speed_mps": 20.0 / 3.6}
    scene = _example("perception_state")
    lead = scene["objects"][0]
    lead.update({
        "track_id": "stationary_lead",
        "position_m": [12.0, 0.0, 0.0],
        "velocity_mps": [0.0, 0.0, 0.0],
        "distance_m": 12.0,
    })
    scene["min_gap_m"] = 12.0
    with PipelineOrchestrator(
        infer=lambda _request: {},
        config=OrchestratorConfig(force_qwen_all_voice=True, qwen_mode="planner_v2"),
    ) as runtime:
        queued = runtime.submit_command(command, scene, now_ns=1_100_000_000)

    assert queued.model_request["constraints"]["must_stop"] is True
    assert queued.model_request["constraints"]["allowed_behaviors"] == ["STOP"]
    assert queued.model_request["targets"][0]["target_id"] == "stationary_lead"
    assert queued.feedback["safety_event"]["reason_code"] == "FRONT_OBJECT_STOP"


def test_occlusion_warning_forces_proactive_stop_plan() -> None:
    command = _example("driving_command")
    command["intent"] = "KEEP_LANE"
    command["source_text"] = "保持车道并注意遮挡区域"
    command["parameters"] = {"target_speed_mps": 18.0 / 3.6}
    scene = _example("perception_state")
    scene["objects"] = []
    scene["min_gap_m"] = None
    with PipelineOrchestrator(
        infer=lambda _request: {},
        config=OrchestratorConfig(force_qwen_all_voice=True, qwen_mode="planner_v2"),
    ) as runtime:
        queued = runtime.submit_command(command, scene, now_ns=1_100_000_000)

    assert queued.model_request["constraints"]["must_stop"] is True
    assert queued.model_request["constraints"]["allowed_behaviors"] == ["STOP"]
    assert queued.feedback["safety_event"]["reason_code"] == "COMMAND_OCCLUSION_STOP"


def test_partially_occluded_follow_target_does_not_force_stop() -> None:
    command = _example("driving_command")
    command["intent"] = "KEEP_LANE"
    command["source_text"] = "跟随正前方被部分遮挡的车辆"
    command["parameters"] = {"target_speed_mps": 16.0 / 3.6}
    scene = _example("perception_state")
    with PipelineOrchestrator(
        infer=lambda _request: {},
        config=OrchestratorConfig(force_qwen_all_voice=True, qwen_mode="planner_v2"),
    ) as runtime:
        queued = runtime.submit_command(command, scene, now_ns=1_100_000_000)

    assert queued.model_request["constraints"]["must_stop"] is False
    assert queued.model_request["constraints"]["allowed_behaviors"] != ["STOP"]


def test_blocked_maneuver_without_safe_adjacent_lane_forces_stop() -> None:
    command = _example("driving_command")
    command["intent"] = "KEEP_LANE"
    command["source_text"] = "绕过前方障碍，确认旁边车道安全"
    command["parameters"] = {"target_speed_mps": 16.0 / 3.6}
    scene = _example("perception_state")
    obstacle = scene["objects"][0]
    obstacle.update({
        "track_id": "lane_blocker",
        "class": "obstacle",
        "position_m": [22.5, 0.0, 0.0],
        "distance_m": 22.5,
    })
    with PipelineOrchestrator(
        infer=lambda _request: {},
        config=OrchestratorConfig(force_qwen_all_voice=True, qwen_mode="planner_v2"),
    ) as runtime:
        queued = runtime.submit_command(
            command,
            scene,
            now_ns=1_100_000_000,
            runtime_state={
                "available_lanes": ["CURRENT"],
                "left_lane_exists": False,
                "right_lane_exists": False,
                "left_gap_safe": False,
                "right_gap_safe": False,
            },
        )

    assert queued.model_request["constraints"]["must_stop"] is True
    assert queued.model_request["constraints"]["allowed_behaviors"] == ["STOP"]
    assert queued.feedback["safety_event"]["reason_code"] == "NO_SAFE_ADJACENT_LANE"


def test_ambiguous_voice_command_is_constrained_to_audited_hold() -> None:
    command = _example("driving_command")
    command.update({
        "intent": "UNKNOWN",
        "source_text": "主识别：左转；备选识别：右转",
        "parameters": {},
        "confidence": 0.55,
        "ambiguity": "AMBIGUOUS",
        "requires_confirmation": True,
    })
    scene = _example("perception_state")
    with PipelineOrchestrator(
        infer=lambda _request: {},
        config=OrchestratorConfig(force_qwen_all_voice=True, qwen_mode="planner_v2"),
    ) as runtime:
        queued = runtime.submit_command(command, scene, now_ns=1_100_000_000)

    assert queued.disposition == "SLOW_PENDING"
    assert queued.model_request["constraints"]["allowed_behaviors"] == ["STOP"]
    assert queued.model_request["routing"]["disposition"] == "CONFIRM_SAFE"
