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
