from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
import threading
import time

import pytest

from car_control_A import ExecutionStatus
from integration.contracts import DetectedObject, PerceptionFrame
from integration.second_group_runtime import CanonicalRuntimeBridge, _PendingSlow
from runtime import OrchestratorConfig, PipelineOrchestrator


class _VehicleRuntime:
    def __init__(self) -> None:
        self.submitted: list[dict] = []
        self.active_command_id: str | None = None
        self.requested_speed_mps = 10.0
        self.safety_latched = False

    def submit_voice(self, envelope, *, now_s):
        payload = dict(envelope)
        self.submitted.append(payload)
        self.active_command_id = payload["command_id"]
        command = SimpleNamespace(command_id=payload["command_id"])
        return SimpleNamespace(command=command, control_authorized=True, feedback=None)

    def fail_active(self, *, now_s, detail, resume_speed_mps=None):
        command_id = self.active_command_id
        self.active_command_id = None
        self.requested_speed_mps = (
            0.0 if resume_speed_mps is None else float(resume_speed_mps)
        )
        return SimpleNamespace(
            command_id=command_id, status="FAILED", emitted_at_s=now_s, detail=detail,
        )


@pytest.mark.parametrize(("intent", "behavior"), [("TURN", "TURN_RIGHT"), ("KEEP_LANE", "KEEP_LANE")])
@pytest.mark.parametrize(("case", "expected"), [
    ("same_wait", 3.0), ("completed_wait", 3.0), ("speed_cap", 2.0),
    ("different_command", None), ("override", None), ("watchdog", None),
    ("red", None), ("yellow", None), ("stale", None), ("explicit", None), ("zero_approach", None),
    ("mismatch", None),
])
def test_moving_plan_resumes_only_safe_approach_speed(intent, behavior, case, expected):
    runtime = _VehicleRuntime()
    runtime.safety_latched = case == "watchdog"
    runtime.active_command_id = {
        "different_command": "other", "completed_wait": None, "override": None,
    }.get(case, "wait")
    runtime.fsm = SimpleNamespace(terminal_feedback=lambda _: SimpleNamespace(
        status=ExecutionStatus.SAFETY_OVERRIDE if case == "override" else ExecutionStatus.SUCCEEDED,
    ))
    pending = _PendingSlow("cmd", "cmd", "wait", approach_speed_mps=0.0 if case == "zero_approach" else 3.0,
                           approach_intent=intent)
    result = SimpleNamespace(compiled_plan={"steps": []}, control_command={
        "behavior": ({"KEEP_LANE": "TURN_RIGHT", "TURN_RIGHT": "KEEP_LANE"}[behavior] if case == "mismatch" else behavior),
        "target": {"target_speed_mps": 4.0 if case == "explicit" else None},
    })
    scene = {"stale": case == "stale", "sync": {"within_tolerance": True}, "risk_level": "LOW",
             "traffic_light": {"red": "RED", "yellow": "YELLOW"}.get(case, "GREEN"),
             "speed_limit_mps": 2.0 if case == "speed_cap" else None}
    assert CanonicalRuntimeBridge(runtime, None)._resume_approach_speed(pending, result, scene) == expected


def _voice(command_id: str, intent: str, *, text: str, parameters=None, confirm=False):
    return {
        "schema_version": "1.0",
        "command_id": command_id,
        "source_text": text,
        "intent": intent,
        "parameters": parameters or {},
        "confidence": 0.95,
        "intent_confidence": 0.95,
        "status": "valid",
        "ambiguity_type": "NONE",
        "confirm_required": confirm,
        "errors": [],
        "warnings": [],
        "valid_duration_s": 3.0,
        "t_audio_start_ns": 1,
        "t_asr_end_ns": 2,
        "t_intent_end_ns": 3,
    }


def test_ambiguous_voice_still_calls_qwen_for_safe_confirmation() -> None:
    vehicle_runtime = _VehicleRuntime()
    envelope = _voice("ambiguous", "SLOW_DOWN", text="handle it safely", confirm=True)
    envelope["status"] = "ambiguous"
    envelope["ambiguity_type"] = "ASR_DISAGREEMENT"
    with PipelineOrchestrator(
        infer=lambda request: {},
        config=OrchestratorConfig(qwen_mode="planner_v2"),
    ) as orchestrator:
        bridge = CanonicalRuntimeBridge(vehicle_runtime, orchestrator)
        submitted = bridge.submit(
            envelope, _scene(), SimpleNamespace(speed_mps=3.0),
            sim_time_s=0.5, perception_mode="sensors",
            received_at_ns=1_000_000_000,
        )
    assert submitted.orchestration.disposition == "SLOW_PENDING"
    assert submitted.orchestration.model_request["routing"]["disposition"] == "CONFIRM_SAFE"


def _scene(frame: int = 10, *, with_vehicle: bool = True) -> PerceptionFrame:
    objects = ()
    if with_vehicle:
        objects = (DetectedObject(
            2, "car", 0.95, (0.4, 0.3, 0.6, 0.8), 12.0,
        ),)
    return PerceptionFrame(
        frame, frame * 0.05, lead_distance_m=12.0 if with_vehicle else None,
        lead_speed_mps=3.0 if with_vehicle else None,
        speed_limit_mps=8.0, detected_objects=objects,
    )


def test_validated_turn_recovers_pre_wait_speed_without_using_the_second_step():
    class Runtime(_VehicleRuntime):
        safety_latched = False

        def submit_voice(self, envelope, *, now_s):
            if envelope["intent"] == "STOP":
                self.requested_speed_mps = 0.0
            return super().submit_voice(envelope, now_s=now_s)

    example = Path(__file__).resolve().parents[2] / "interfaces/examples/maneuver_plan.json"

    def infer(request):
        value = json.loads(example.read_text(encoding="utf-8"))
        value.update(request_id=request["request_id"], command_id=request["command_id"],
                     created_at_ns=request["created_at_ns"] + 1, valid_until_ns=request["deadline_ns"])
        first, last = value["steps"]
        first.update(behavior="TURN_RIGHT", preconditions=["PERCEPTION_FRESH", "INTERSECTION_AHEAD"])
        first["target"].update(target_lane="ROUTE_BRANCH", route_direction="RIGHT", target_speed_mps=None)
        first["completion"].update(type="JUNCTION_EXITED", value=None)
        last.update(behavior="SET_SPEED", preconditions=["PERCEPTION_FRESH"])
        last["target"].update(target_lane="CURRENT", target_speed_mps=15/3.6)
        last["completion"].update(type="SPEED_REACHED", lane=None, value=15/3.6)
        return value

    runtime = Runtime()
    runtime.requested_speed_mps = 3.0
    with PipelineOrchestrator(infer=infer, config=OrchestratorConfig(qwen_mode="planner_v2")) as orchestrator:
        bridge = CanonicalRuntimeBridge(runtime, orchestrator)
        bridge.submit(_voice("turn", "TURN", text="前方右转，转弯后保持十五公里每小时",
                             parameters={"direction": "RIGHT", "target_speed_mps": 15/3.6}),
                      _scene(with_vehicle=False), SimpleNamespace(speed_mps=2.0),
                      sim_time_s=0.5, perception_mode="sensors", received_at_ns=1_000_000_000,
                      runtime_state={"intersection_ahead": True, "route_available": True})
        assert runtime.requested_speed_mps == 0
        resolved = bridge.poll(_scene(11, with_vehicle=False), SimpleNamespace(speed_mps=2.0),
                               sim_time_s=0.55, perception_mode="sensors", captured_at_ns=1_100_000_000, wait_timeout_ms=100)
        assert len(resolved) == 1 and resolved[0].disposition == "SLOW_READY", resolved
    assert runtime.requested_speed_mps == 3.0


@pytest.mark.parametrize(("previous", "requested", "expected"), [(0.0, 4.0, 4.0), (3.0, None, 3.0), (3.0, 0.0, 0.0)])
def test_validated_keep_lane_uses_existing_driving_speed_without_inventing_one(previous, requested, expected):
    from integration.runtime_loop import ControlRuntime
    from car_control_B.pure_pursuit import PurePursuitController

    example = Path(__file__).resolve().parents[2] / "interfaces/examples/maneuver_plan.json"

    def infer(request):
        plan = json.loads(example.read_text(encoding="utf-8"))
        plan.update(request_id=request["request_id"], command_id=request["command_id"],
                    created_at_ns=request["created_at_ns"] + 1, valid_until_ns=request["deadline_ns"])
        step = plan["steps"][0]
        step.update(behavior="KEEP_LANE", preconditions=["PERCEPTION_FRESH"])
        step["target"].update(target_speed_mps=None)
        step["completion"].update(type="HOLD_FRAMES", value=None)
        plan["steps"] = [step]
        return plan

    runtime = ControlRuntime(PurePursuitController(), default_speed_mps=previous)
    with PipelineOrchestrator(infer=infer, config=OrchestratorConfig(qwen_mode="planner_v2")) as orchestrator:
        bridge = CanonicalRuntimeBridge(runtime, orchestrator)
        bridge.submit(_voice("keep", "KEEP_LANE", text="保持当前车道行驶", parameters={
            "target_speed_mps": requested,
        }), _scene(with_vehicle=False), SimpleNamespace(speed_mps=0.0),
                      sim_time_s=0.5, perception_mode="sensors", received_at_ns=1_000_000_000)
        assert runtime.requested_speed_mps == 0.0
        resolved = bridge.poll(_scene(11, with_vehicle=False), SimpleNamespace(speed_mps=0.0),
                               sim_time_s=0.55, perception_mode="sensors", captured_at_ns=1_100_000_000, wait_timeout_ms=100)
        assert len(resolved) == 1 and resolved[0].disposition == "SLOW_READY", resolved
    assert runtime.requested_speed_mps == expected


def test_atomic_command_fails_closed_when_qwen_is_unavailable() -> None:
    vehicle_runtime = _VehicleRuntime()
    with PipelineOrchestrator() as orchestrator:
        bridge = CanonicalRuntimeBridge(vehicle_runtime, orchestrator)
        submitted = bridge.submit(
            _voice("speed", "SET_SPEED", text="速度设为40公里", parameters={
                "speed": 40, "unit": "km/h",
            }),
            _scene(), SimpleNamespace(speed_mps=0.0),
            sim_time_s=0.5, perception_mode="sensors", received_at_ns=1_000_000_000,
        )
    assert submitted.orchestration.disposition == "REJECTED"
    assert submitted.orchestration.reason_code == "QWEN_UNAVAILABLE"
    assert submitted.runtime_adapted is None
    assert submitted.safety_envelope is not None
    assert submitted.safety_envelope["intent"] == "STOP"


def test_emergency_command_calls_qwen_and_installs_emergency_pending_brake() -> None:
    vehicle_runtime = _VehicleRuntime()
    with PipelineOrchestrator(
        infer=lambda request: {},
        config=OrchestratorConfig(qwen_mode="planner_v2"),
    ) as orchestrator:
        bridge = CanonicalRuntimeBridge(vehicle_runtime, orchestrator)
        submitted = bridge.submit(
            _voice("emergency", "EMERGENCY_STOP", text="立即紧急停车"),
            _scene(), SimpleNamespace(speed_mps=5.0),
            sim_time_s=0.5, perception_mode="sensors",
            received_at_ns=1_000_000_000,
        )

    assert submitted.orchestration.disposition == "SLOW_PENDING"
    assert submitted.orchestration.model_request is not None
    assert submitted.safety_envelope is not None
    assert submitted.safety_envelope["intent"] == "EMERGENCY_STOP"
    assert vehicle_runtime.submitted[-1]["intent"] == "EMERGENCY_STOP"


def test_perception_preserves_tracker_owned_actor_id() -> None:
    scene = PerceptionFrame(
        10, 0.5, lead_distance_m=12.0, lead_speed_mps=3.0,
        detected_objects=(DetectedObject(
            2, "car", 0.95, (0.4, 0.3, 0.6, 0.8), 12.0, "lead_001",
        ),),
    )
    vehicle_runtime = _VehicleRuntime()
    with PipelineOrchestrator() as orchestrator:
        bridge = CanonicalRuntimeBridge(vehicle_runtime, orchestrator)
        submitted = bridge.submit(
            _voice("speed-track", "SET_SPEED", text="set speed", parameters={"speed": 5, "unit": "m/s"}),
            scene, SimpleNamespace(speed_mps=2.0), sim_time_s=0.5,
            perception_mode="sensors", received_at_ns=1_000_000_000,
        )
    assert submitted.perception_state["objects"][0]["track_id"] == "lead_001"


def test_submit_uses_sensor_ready_time_for_perception_and_model_request() -> None:
    vehicle_runtime = _VehicleRuntime()
    with PipelineOrchestrator(infer=lambda request: {}) as orchestrator:
        bridge = CanonicalRuntimeBridge(vehicle_runtime, orchestrator)
        submitted = bridge.submit(
            _voice("follow-clock", "FOLLOW_ROUTE", text="follow vehicle", confirm=True),
            _scene(), SimpleNamespace(speed_mps=5.0), sim_time_s=0.5,
            perception_mode="sensors", received_at_ns=1_000_000_000,
            captured_at_ns=1_020_000_000,
        )

    assert submitted.canonical_command["received_at_ns"] == 1_000_000_000
    assert submitted.perception_state["captured_at_ns"] == 1_020_000_000
    assert submitted.orchestration.model_request["created_at_ns"] == 1_020_000_000


def test_slow_qwen_path_holds_stop_without_blocking_then_dispatches_validated_plan() -> None:
    release = threading.Event()

    def infer(request):
        release.wait(10.0)
        return {
            "schema_version": "1.0",
            "request_id": request["request_id"],
            "command_id": request["command_id"],
            "intent": "FOLLOW",
            "target_id": "legacy-vehicle-000",
            "behavior": "FOLLOW",
            "parameters": {"target_speed_mps": 4.0, "time_gap_s": 2.0},
            "confidence": 0.95,
            "reason_code": "UNIQUE_TARGET",
            "created_at_ns": request["created_at_ns"] + 1,
            "valid_until_ns": request["deadline_ns"],
            "requires_confirmation": False,
            "model_id": "test-backend",
        }

    vehicle_runtime = _VehicleRuntime()
    with PipelineOrchestrator(
        infer=infer, config=OrchestratorConfig(model_timeout_ms=300.0),
    ) as orchestrator:
        bridge = CanonicalRuntimeBridge(vehicle_runtime, orchestrator)
        started = time.perf_counter()
        submitted = bridge.submit(
            _voice("follow", "FOLLOW_ROUTE", text="跟随前车"),
            _scene(), SimpleNamespace(speed_mps=5.0),
            sim_time_s=0.5, perception_mode="sensors", received_at_ns=1_000_000_000,
            rgb_ref="frames/follow.png",
        )
        # The assertion proves that submit does not wait for the 10 s model
        # callback while tolerating scheduler jitter on a loaded host.
        assert time.perf_counter() - started < 2.0
        assert submitted.orchestration.disposition == "SLOW_PENDING"
        assert submitted.orchestration.model_request["rgb_ref"] == "frames/follow.png"
        assert submitted.safety_envelope["intent"] == "STOP"
        release.set()
        deadline = time.monotonic() + 0.5
        resolutions = ()
        while time.monotonic() < deadline and not resolutions:
            resolutions = bridge.poll(
                _scene(11), SimpleNamespace(speed_mps=4.0),
                sim_time_s=0.55, perception_mode="sensors",
                captured_at_ns=1_100_000_000,
            )
            time.sleep(0.001)
    assert len(resolutions) == 1
    assert resolutions[0].disposition == "SLOW_READY"
    assert resolutions[0].runtime_envelope["intent"] == "SLOW_DOWN"
    assert resolutions[0].runtime_envelope["parameters"] == {"speed": 4.0, "unit": "m/s"}


def test_slow_target_missing_from_latest_frame_is_rejected_and_stop_remains() -> None:
    def infer(request):
        return {
            "schema_version": "1.0",
            "request_id": request["request_id"],
            "command_id": request["command_id"],
            "intent": "FOLLOW",
            "target_id": "legacy-vehicle-000",
            "behavior": "FOLLOW",
            "parameters": {"target_speed_mps": 4.0, "time_gap_s": 2.0},
            "confidence": 0.95,
            "reason_code": "UNIQUE_TARGET",
            "created_at_ns": request["created_at_ns"] + 1,
            "valid_until_ns": request["deadline_ns"],
            "requires_confirmation": False,
            "model_id": "test-backend",
        }

    vehicle_runtime = _VehicleRuntime()
    with PipelineOrchestrator(infer=infer) as orchestrator:
        bridge = CanonicalRuntimeBridge(vehicle_runtime, orchestrator)
        bridge.submit(
            _voice("follow-stale", "FOLLOW_ROUTE", text="跟随前车"),
            _scene(), SimpleNamespace(speed_mps=5.0),
            sim_time_s=0.5, perception_mode="sensors", received_at_ns=1_000_000_000,
        )
        deadline = time.monotonic() + 0.5
        resolutions = ()
        while time.monotonic() < deadline and not resolutions:
            resolutions = bridge.poll(
                _scene(11, with_vehicle=False), SimpleNamespace(speed_mps=4.0),
                sim_time_s=0.55, perception_mode="sensors",
                captured_at_ns=1_100_000_000,
            )
            time.sleep(0.001)
    assert resolutions[0].disposition == "REJECTED"
    assert resolutions[0].feedbacks[0]["terminal_reason"] == "QWEN_TARGET_STALE"
    assert resolutions[0].vehicle_feedback is not None
    assert vehicle_runtime.active_command_id is None
    assert vehicle_runtime.requested_speed_mps == 0.0
    assert resolutions[0].vehicle_feedback is not None
    assert resolutions[0].vehicle_feedback.detail.endswith("QWEN_TARGET_STALE")


def test_targetless_stop_ignores_model_supplied_stale_target() -> None:
    def infer(request):
        return {
            "schema_version": "1.0",
            "request_id": request["request_id"],
            "command_id": request["command_id"],
            "intent": "STOP",
            "target_id": "transient-obstacle",
            "behavior": "STOP",
            "parameters": {"target_speed_mps": 0.0},
            "confidence": 0.95,
            "reason_code": "STOP_NOW",
            "created_at_ns": request["created_at_ns"] + 1,
            "valid_until_ns": request["deadline_ns"],
            "requires_confirmation": False,
            "model_id": "test-backend",
        }

    vehicle_runtime = _VehicleRuntime()
    with PipelineOrchestrator(infer=infer) as orchestrator:
        bridge = CanonicalRuntimeBridge(vehicle_runtime, orchestrator)
        bridge.submit(
            _voice("stop-targetless", "EMERGENCY_STOP", text="紧急停车"),
            _scene(), SimpleNamespace(speed_mps=5.0),
            sim_time_s=0.5, perception_mode="sensors",
            received_at_ns=1_000_000_000,
        )
        deadline = time.monotonic() + 0.5
        resolutions = ()
        while time.monotonic() < deadline and not resolutions:
            resolutions = bridge.poll(
                _scene(11, with_vehicle=False), SimpleNamespace(speed_mps=4.0),
                sim_time_s=0.55, perception_mode="sensors",
                captured_at_ns=1_100_000_000,
            )
            time.sleep(0.001)

    assert resolutions[0].disposition == "SLOW_READY", (
        resolutions[0].orchestration.reason_code,
        resolutions[0].feedbacks,
    )
    assert resolutions[0].feedbacks[0]["status"] == "EXECUTING"


def test_live_grounded_target_can_outlive_empty_tracker_frame() -> None:
    def infer(request):
        return {
            "schema_version": "1.0",
            "request_id": request["request_id"],
            "command_id": request["command_id"],
            "intent": "FOLLOW",
            "target_id": "bicycle_lead",
            "behavior": "FOLLOW",
            "parameters": {"target_speed_mps": 4.0, "time_gap_s": 2.0},
            "confidence": 0.95,
            "reason_code": "GROUNDED_SCENARIO_TARGET",
            "created_at_ns": request["created_at_ns"] + 1,
            "valid_until_ns": request["deadline_ns"],
            "requires_confirmation": False,
            "model_id": "test-backend",
        }

    vehicle_runtime = _VehicleRuntime()
    with PipelineOrchestrator(infer=infer) as orchestrator:
        bridge = CanonicalRuntimeBridge(vehicle_runtime, orchestrator)
        bridge.submit(
            _voice("follow-grounded", "FOLLOW_ROUTE", text="跟随前方自行车"),
            _scene(), SimpleNamespace(speed_mps=5.0),
            sim_time_s=0.5, perception_mode="sensors",
            received_at_ns=1_000_000_000,
            runtime_state={"grounded_target_ids": ["bicycle_lead"]},
        )
        deadline = time.monotonic() + 0.5
        resolutions = ()
        while time.monotonic() < deadline and not resolutions:
            resolutions = bridge.poll(
                _scene(11, with_vehicle=False), SimpleNamespace(speed_mps=4.0),
                sim_time_s=0.55, perception_mode="sensors",
                captured_at_ns=1_100_000_000,
            )
            time.sleep(0.001)

    assert resolutions[0].disposition == "SLOW_READY"
    assert resolutions[0].runtime_adapted.control_authorized is True


def test_runtime_end_gives_pending_qwen_command_a_terminal() -> None:
    release = threading.Event()

    def infer(_request):
        release.wait(1.0)
        raise RuntimeError("released")

    vehicle_runtime = _VehicleRuntime()
    orchestrator = PipelineOrchestrator(infer=infer)
    try:
        bridge = CanonicalRuntimeBridge(vehicle_runtime, orchestrator)
        bridge.submit(
            _voice("pending-end", "FOLLOW_ROUTE", text="跟随前车", confirm=True),
            _scene(), SimpleNamespace(speed_mps=5.0),
            sim_time_s=0.5, perception_mode="sensors", received_at_ns=1_000_000_000,
        )
        terminal = bridge.fail_all_pending(
            sim_time_s=0.6, emitted_at_ns=1_100_000_000,
        )
        assert len(terminal) == 1
        assert terminal[0].feedbacks[0]["status"] == "FAILED"
        assert terminal[0].feedbacks[0]["terminal_reason"] == "RUNTIME_ENDED"
        assert terminal[0].vehicle_feedback is not None
        assert bridge.fail_all_pending(
            sim_time_s=0.7, emitted_at_ns=1_200_000_000,
        ) == ()
    finally:
        release.set()
        orchestrator.close()
