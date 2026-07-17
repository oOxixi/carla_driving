"""Auditable evidence and score summaries for CARLA scenario runs.

The recorder is intentionally CARLA-free.  ``integration.carla_runner`` (or a
ScenarioRunner adapter) supplies plain controller contracts after each tick.
One JSONL file then contains the complete causal chain for a run:

``run_start -> command -> frame/feedback -> run_complete|run_failed``.

Only vehicle-side contracts are imported here; voice output is retained as an
opaque mapping so this module never depends on, or modifies, ``voice_group``.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timezone
from enum import Enum
import json
import math
from pathlib import Path
import time
from typing import Any, Mapping
from uuid import uuid4

from car_control_D.official_score import OfficialScorer


@dataclass(frozen=True, slots=True)
class FrameTiming:
    """Monotonic timestamps around one control decision.

    All values use the same monotonic clock.  Optional sensor timing allows an
    initial runner implementation to omit sensor instrumentation without
    fabricating a latency value.
    """

    decision_start_ns: int
    decision_end_ns: int
    control_applied_ns: int
    sensor_ready_ns: int | None = None

    def __post_init__(self) -> None:
        values = {
            "sensor_ready_ns": self.sensor_ready_ns,
            "decision_start_ns": self.decision_start_ns,
            "decision_end_ns": self.decision_end_ns,
            "control_applied_ns": self.control_applied_ns,
        }
        for name, value in values.items():
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError(f"{name} must be a non-negative integer or None")
        ordered = [value for value in (
            self.sensor_ready_ns,
            self.decision_start_ns,
            self.decision_end_ns,
            self.control_applied_ns,
        ) if value is not None]
        if ordered != sorted(ordered):
            raise ValueError("frame timestamps must be monotonic")

    def to_dict(self) -> dict[str, float | int | None]:
        sensor_to_control = None
        sensor_to_decision = None
        if self.sensor_ready_ns is not None:
            sensor_to_control = (self.control_applied_ns - self.sensor_ready_ns) / 1e6
            sensor_to_decision = (self.decision_start_ns - self.sensor_ready_ns) / 1e6
        return {
            "sensor_ready_ns": self.sensor_ready_ns,
            "decision_start_ns": self.decision_start_ns,
            "decision_end_ns": self.decision_end_ns,
            "control_applied_ns": self.control_applied_ns,
            "sensor_to_decision_ms": sensor_to_decision,
            "decision_ms": (self.decision_end_ns - self.decision_start_ns) / 1e6,
            "decision_to_apply_ms": (self.control_applied_ns - self.decision_end_ns) / 1e6,
            "sensor_to_control_ms": sensor_to_control,
        }


def _jsonable(value: Any) -> Any:
    """Convert controller contracts to strict JSON without lossy string reprs."""
    if value is None or type(value) in (str, int, bool):
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("evidence values must be finite")
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        return _jsonable(to_dict())
    if is_dataclass(value):
        return _jsonable(asdict(value))
    raise TypeError(f"unsupported evidence value: {type(value).__name__}")


def _field(value: object, name: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


class ScenarioEvidenceRecorder:
    """Write a unified JSONL audit trail and an adjacent score summary.

    The class is deliberately stateful: invalid event order raises immediately,
    preventing a successful-looking log that omitted ``run_start`` or emitted
    frames after a terminal record.
    """

    def __init__(self, path: str | Path, *, scorer: OfficialScorer | None = None,
                 clock_ns: Any = time.monotonic_ns) -> None:
        self.path = Path(path)
        self.summary_path = self.path.with_suffix(".summary.json")
        self.scorer = scorer or OfficialScorer()
        self._clock_ns = clock_ns
        self._handle: Any | None = None
        self._run_id: str | None = None
        self._scenario_id = "UNKNOWN"
        self._difficulty = "basic"
        self._sequence = 0
        self._terminal = False
        self._frames = 0
        self._commands: dict[str, dict[str, Any]] = {}
        self._feedback_keys: set[tuple[str, str]] = set()
        self._terminal_statuses: dict[str, str] = {}
        self._min_gap_m: float | None = None
        self._min_ttc_s: float | None = None
        self._stationary_stop_error_m: float | None = None
        self._last_speed_mps: float | None = None
        self._safety_override_frames = 0
        self._safety_override_episodes = 0
        self._override_active = False
        self._collisions = 0
        self._red_violations = 0
        self._route_deviations = 0
        self._last_collision = False
        self._last_red_violation = False
        self._last_route_deviation = False
        self._frame_decision_ms: list[float] = []
        self._frame_sensor_to_control_ms: list[float] = []

    @property
    def run_id(self) -> str | None:
        return self._run_id

    def start_run(self, *, scenario_id: str, difficulty: str = "basic",
                  config: Mapping[str, object] | None = None,
                  run_id: str | None = None) -> str:
        if self._handle is not None or self._terminal:
            raise RuntimeError("recorder can only start one run")
        if not scenario_id or not difficulty:
            raise ValueError("scenario_id and difficulty must be non-empty")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self.path.open("x", encoding="utf-8", newline="\n")
        self._run_id = run_id or uuid4().hex
        self._scenario_id = scenario_id
        self._difficulty = difficulty
        self._write("run_start", scenario_id=scenario_id, difficulty=difficulty,
                    config=dict(config or {}))
        return self._run_id

    def record_command(self, command: Mapping[str, object], *, disposition: str,
                       adapted_command: object | None = None,
                       received_ns: int | None = None) -> None:
        self._ensure_active()
        command_id = command.get("command_id")
        if type(command_id) is not str or not command_id:
            raise ValueError("command.command_id must be a non-empty string")
        stamp = self._clock_ns() if received_ns is None else received_ns
        if type(stamp) is not int or stamp < 0:
            raise ValueError("received_ns must be a non-negative integer")
        record = {
            "command_id": command_id,
            "disposition": disposition,
            "received_ns": stamp,
            "command": _jsonable(command),
            "adapted_command": _jsonable(adapted_command),
        }
        # Keep canonical timestamp fields at the record root as well as inside
        # the immutable command payload. D's existing latency scorer consumes
        # this flat representation.
        for name in ("t_audio_start_ns", "t_asr_end_ns", "t_intent_end_ns"):
            if name in record["command"]:
                record[name] = record["command"][name]
        record["latency"] = self._command_latency(record["command"], stamp)
        self._commands[command_id] = record
        self._write("command", **record)

    def record_frame(self, *, vehicle: object, scene: object, raw_control: object,
                     final_control: object, safety_reason: str,
                     safety_override: bool, timing: FrameTiming,
                      command_id: str | None = None,
                      fsm_state: str | None = None,
                      longitudinal: object | None = None,
                      lateral: object | None = None,
                      perception_sources: Mapping[str, str] | None = None) -> None:
        """Record one applied control frame and update scenario aggregates."""
        self._ensure_active()
        if type(safety_override) is not bool:
            raise TypeError("safety_override must be bool")
        frame = _field(vehicle, "frame")
        sim_time_s = _field(vehicle, "sim_time_s")
        speed_mps = _field(vehicle, "speed_mps")
        if type(frame) is not int or type(sim_time_s) not in (int, float) or type(speed_mps) not in (int, float):
            raise TypeError("vehicle must provide frame, sim_time_s and speed_mps")
        latency = timing.to_dict()
        self._frame_decision_ms.append(float(latency["decision_ms"]))
        if latency["sensor_to_control_ms"] is not None:
            self._frame_sensor_to_control_ms.append(float(latency["sensor_to_control_ms"]))

        risk = _field(longitudinal, "risk")
        ttc_s = _field(risk, "ttc_s") if risk is not None else None
        lead_distance_m = _field(scene, "lead_distance_m")
        stop_distance_m = _field(scene, "distance_to_stop_line_m")
        self._min_gap_m = self._minimum(self._min_gap_m, lead_distance_m)
        self._min_ttc_s = self._minimum(self._min_ttc_s, ttc_s)
        self._last_speed_mps = float(speed_mps)
        if stop_distance_m is not None and float(speed_mps) <= 0.15:
            self._stationary_stop_error_m = abs(float(stop_distance_m))

        collision = bool(_field(scene, "collision", False))
        red_violation = bool(_field(scene, "red_light_violation", False))
        route_deviation_m = _field(scene, "route_deviation_m")
        route_deviation = route_deviation_m is not None and abs(float(route_deviation_m)) > 1.0
        self._collisions += int(collision and not self._last_collision)
        self._red_violations += int(red_violation and not self._last_red_violation)
        self._route_deviations += int(route_deviation and not self._last_route_deviation)
        self._last_collision = collision
        self._last_red_violation = red_violation
        self._last_route_deviation = route_deviation

        if safety_override:
            self._safety_override_frames += 1
            if not self._override_active:
                self._safety_override_episodes += 1
        self._override_active = safety_override

        if command_id in self._commands:
            command_record = self._commands[command_id]
            if "first_control_applied_ns" not in command_record:
                applied_ns = timing.control_applied_ns
                command_record["first_control_applied_ns"] = applied_ns
                origin_ns = self._latency_origin_ns(command_record)
                if origin_ns is not None and applied_ns >= origin_ns:
                    command_record["e2e_latency_ms"] = (applied_ns - origin_ns) / 1e6

        self._frames += 1
        self._write(
            "frame", frame=frame, sim_time_s=float(sim_time_s), speed_mps=float(speed_mps),
            vehicle=_jsonable(vehicle),
            command_id=command_id, fsm_state=fsm_state,
            scene=_jsonable(scene), perception_sources=_jsonable(perception_sources or {}),
            longitudinal=_jsonable(longitudinal), lateral=_jsonable(lateral),
            raw_control=_jsonable(raw_control), final_control=_jsonable(final_control),
            safety={"override": safety_override, "reason": safety_reason},
            latency=latency,
        )

    def record_runtime_frame(self, result: object, scene: object, *, raw_control: object,
                             timing: FrameTiming, command_id: str | None = None,
                             fsm_state: str | None = None,
                             perception_sources: Mapping[str, str] | None = None) -> None:
        """Convenience adapter for :class:`integration.contracts.FrameResult`.

        ``raw_control`` stays mandatory: silently reconstructing it from the
        final steer value would make a safety takeover impossible to audit.
        All terminal feedback carried by the frame is emitted exactly once.
        """
        self.record_frame(
            vehicle=_field(result, "vehicle"), scene=scene,
            raw_control=raw_control, final_control=_field(result, "final_control"),
            safety_reason=_field(result, "safety_reason", "UNKNOWN"),
            safety_override=_field(result, "safety_override", False),
            timing=timing, command_id=command_id, fsm_state=fsm_state,
            longitudinal=_field(result, "longitudinal"), lateral=_field(result, "lateral"),
            perception_sources=perception_sources,
        )
        for feedback in _field(result, "feedback", ()):
            self.record_feedback(feedback)

    def record_feedback(self, feedback: object) -> None:
        self._ensure_active()
        command_id = _field(feedback, "command_id")
        status_value = _field(feedback, "status")
        status = status_value.value if isinstance(status_value, Enum) else status_value
        if type(command_id) is not str or type(status) is not str:
            raise TypeError("feedback must provide string command_id and status")
        key = (command_id, status)
        if key in self._feedback_keys:
            return
        self._feedback_keys.add(key)
        self._terminal_statuses[command_id] = status
        self._write("feedback", feedback=_jsonable(feedback))

    def complete(self, *, completion: bool | None = None, detail: str = "") -> dict[str, Any]:
        self._ensure_active()
        if completion is None:
            if self._commands:
                completion = any(status == "SUCCEEDED" for status in self._terminal_statuses.values())
                basis = "command_terminal_status"
            else:
                completion = self._frames > 0
                basis = "frames_without_command"
        else:
            basis = "explicit"
        status = "SUCCEEDED" if completion else "FAILED"
        summary = self._summary(status=status, completion=completion, completion_basis=basis, detail=detail)
        self._write("run_complete", summary=summary)
        self._write_summary(summary)
        self._finish()
        return summary

    def fail(self, error: BaseException | str, *, detail: str = "") -> dict[str, Any]:
        self._ensure_active()
        error_type = type(error).__name__ if isinstance(error, BaseException) else "RuntimeError"
        error_message = str(error)
        summary = self._summary(status="FAILED", completion=False,
                                completion_basis="runtime_failure", detail=detail)
        self._write("run_failed", error={"type": error_type, "message": error_message}, summary=summary)
        self._write_summary(summary)
        self._finish()
        return summary

    def close(self) -> None:
        """Close an unterminated recorder as a failed run, preserving evidence."""
        if self._handle is not None and not self._terminal:
            self.fail("recorder closed before a terminal run event")

    def _summary(self, *, status: str, completion: bool,
                 completion_basis: str, detail: str) -> dict[str, Any]:
        result: dict[str, Any] = {
            "run_id": self._run_id,
            "scenario_id": self._scenario_id,
            "difficulty": self._difficulty,
            "status": status,
            "completion": completion,
            "completion_basis": completion_basis,
            "detail": detail,
            "frames": self._frames,
            "command_count": len(self._commands),
            "command_terminal_statuses": dict(self._terminal_statuses),
            "stop_error_m": self._stationary_stop_error_m,
            "final_speed_mps": self._last_speed_mps,
            "min_gap_m": self._min_gap_m,
            "min_ttc_s": self._min_ttc_s,
            "collision_count": self._collisions,
            "red_light_violation_count": self._red_violations,
            "route_deviation_count": self._route_deviations,
            "unfinished_task_count": 0 if completion else 1,
            "safety_override_frames": self._safety_override_frames,
            "safety_override_episodes": self._safety_override_episodes,
            "latency": {
                "decision_avg_ms": self._average(self._frame_decision_ms),
                "decision_max_ms": max(self._frame_decision_ms, default=None),
                "sensor_to_control_avg_ms": self._average(self._frame_sensor_to_control_ms),
                "sensor_to_control_max_ms": max(self._frame_sensor_to_control_ms, default=None),
            },
        }
        # D remains the only owner of official deduction/score semantics.
        result["score"] = self.scorer.score_scenario(result).to_dict()
        result["score_report"] = self.scorer.summarize(
            [result], command_records=self._commands.values()
        )
        return result

    def _write(self, record_type: str, **fields: Any) -> None:
        if self._handle is None:
            raise RuntimeError("run has not started")
        record = {
            "record_type": record_type,
            "schema_version": "1.0",
            "run_id": self._run_id,
            "sequence": self._sequence,
            "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
            **fields,
        }
        encoded = json.dumps(_jsonable(record), ensure_ascii=False, allow_nan=False, sort_keys=True)
        self._handle.write(encoded + "\n")
        self._handle.flush()
        self._sequence += 1

    def _write_summary(self, summary: Mapping[str, Any]) -> None:
        self.summary_path.write_text(
            json.dumps(_jsonable(summary), ensure_ascii=False, allow_nan=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _ensure_active(self) -> None:
        if self._handle is None:
            raise RuntimeError("run has not started")
        if self._terminal:
            raise RuntimeError("run is already terminal")

    def _finish(self) -> None:
        self._terminal = True
        assert self._handle is not None
        self._handle.close()
        self._handle = None

    @staticmethod
    def _minimum(current: float | None, candidate: object) -> float | None:
        if candidate is None:
            return current
        value = float(candidate)
        if not math.isfinite(value) or value < 0.0:
            raise ValueError("distance and TTC metrics must be finite and non-negative")
        return value if current is None else min(current, value)

    @staticmethod
    def _average(values: list[float]) -> float | None:
        return sum(values) / len(values) if values else None

    @staticmethod
    def _command_latency(command: Mapping[str, Any], received_ns: int) -> dict[str, float | None]:
        audio = command.get("t_audio_start_ns")
        asr = command.get("t_asr_end_ns")
        intent = command.get("t_intent_end_ns")
        return {
            "asr_ms": (asr - audio) / 1e6 if type(audio) is int and type(asr) is int and asr >= audio else None,
            "intent_ms": (intent - asr) / 1e6 if type(asr) is int and type(intent) is int and intent >= asr else None,
            "intent_to_submit_ms": (received_ns - intent) / 1e6
            if type(intent) is int and received_ns >= intent else None,
        }

    @staticmethod
    def _latency_origin_ns(command_record: Mapping[str, Any]) -> int | None:
        command = command_record.get("command")
        if isinstance(command, Mapping) and type(command.get("t_audio_start_ns")) is int:
            return command["t_audio_start_ns"]
        received = command_record.get("received_ns")
        return received if type(received) is int else None


__all__ = ["FrameTiming", "ScenarioEvidenceRecorder"]
