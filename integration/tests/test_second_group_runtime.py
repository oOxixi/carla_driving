from __future__ import annotations

from types import SimpleNamespace
import threading
import time

from integration.contracts import DetectedObject, PerceptionFrame
from integration.second_group_runtime import CanonicalRuntimeBridge
from runtime import OrchestratorConfig, PipelineOrchestrator


class _VehicleRuntime:
    def __init__(self) -> None:
        self.submitted: list[dict] = []
        self.active_command_id: str | None = None

    def submit_voice(self, envelope, *, now_s):
        payload = dict(envelope)
        self.submitted.append(payload)
        self.active_command_id = payload["command_id"]
        command = SimpleNamespace(command_id=payload["command_id"])
        return SimpleNamespace(command=command, control_authorized=True, feedback=None)

    def fail_active(self, *, now_s, detail):
        command_id = self.active_command_id
        self.active_command_id = None
        return SimpleNamespace(
            command_id=command_id, status="FAILED", emitted_at_s=now_s, detail=detail,
        )


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


def test_fast_command_is_validated_clamped_and_dispatched_without_qwen() -> None:
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
    assert submitted.orchestration.disposition == "FAST"
    assert submitted.runtime_adapted.control_authorized is True
    assert vehicle_runtime.submitted[-1]["parameters"] == {"speed": 8.0, "unit": "m/s"}
    assert vehicle_runtime.submitted[-1]["t_audio_start_ns"] == 1
    assert submitted.safety_envelope is None


def test_slow_qwen_path_holds_stop_without_blocking_then_dispatches_validated_plan() -> None:
    release = threading.Event()

    def infer(request):
        release.wait(1.0)
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
            _voice("follow", "FOLLOW_ROUTE", text="跟随前车", confirm=True),
            _scene(), SimpleNamespace(speed_mps=5.0),
            sim_time_s=0.5, perception_mode="sensors", received_at_ns=1_000_000_000,
            rgb_ref="frames/follow.png",
        )
        assert time.perf_counter() - started < 0.15
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
            _voice("follow-stale", "FOLLOW_ROUTE", text="跟随前车", confirm=True),
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
