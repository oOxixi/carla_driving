"""CARLA-free replay acceptance for recorded RGB/LiDAR/control frames."""
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np

from car_control_A import RuntimeVehicleState
from car_control_A.high_level_command import HighLevelCommandAdapter
from car_control_A.routing import RouteReference
from car_control_B.pure_pursuit import PurePursuitController

from .carla_perception import front_lidar_distance_m
from .contracts import DetectedObject, PerceptionFrame
from .day22.command_adapter import build_high_level_command
from .perception_bridge import safety_vehicle_state
from .qwen_boundary import QwenInputContext, fail_closed, validate_qwen_response
from .rgb_detector import OnnxYoloDetector
from .runtime_loop import ControlRuntime


REPLAY_SCHEMA_VERSION = "1.0"
_PERCEPTION_FIELDS = frozenset({
    "lead_distance_m", "lead_speed_mps", "traffic_light",
    "distance_to_stop_line_m", "speed_limit_mps", "lane_offset_m",
    "route_deviation_m", "collision", "red_light_violation",
    "lane_invasion", "detected_objects",
})
_EXPECTED_FIELDS = frozenset({
    "qwen_status", "safety_override", "safety_reason", "min_brake",
    "max_throttle", "min_detection_count", "lead_distance_range_m",
    "rgb_loaded", "lidar_loaded",
})


@dataclass(frozen=True, slots=True)
class ReplayFrameResult:
    frame: int
    qwen_status: str
    qwen_error: str | None
    watchdog_alerts: tuple[str, ...]
    rgb_loaded: bool
    lidar_loaded: bool
    detection_count: int
    lead_distance_m: float | None
    safety_override: bool
    safety_reason: str
    throttle: float
    brake: float
    steer: float
    passed: bool
    failures: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ReplayReport:
    manifest: str
    frame_count: int
    passed_frames: int
    failed_frames: int
    passed: bool
    results: tuple[ReplayFrameResult, ...]

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema_version": REPLAY_SCHEMA_VERSION,
            "manifest": self.manifest,
            "frame_count": self.frame_count,
            "passed_frames": self.passed_frames,
            "failed_frames": self.failed_frames,
            "passed": self.passed,
            "results": [asdict(item) for item in self.results],
        }


def load_replay_manifest(path: str | Path) -> tuple[dict[str, Any], ...]:
    """Read strict JSONL records and enforce increasing aligned frame time."""
    manifest = Path(path).resolve()
    records: list[dict[str, Any]] = []
    previous_frame = -1
    previous_time = -1.0
    with manifest.open("r", encoding="utf-8") as stream:
        for line_number, raw_line in enumerate(stream, start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"{manifest}:{line_number}: invalid JSON"
                ) from error
            if type(payload) is not dict:
                raise TypeError(f"{manifest}:{line_number}: record must be an object")
            if payload.get("schema_version") != REPLAY_SCHEMA_VERSION:
                raise ValueError(
                    f"{manifest}:{line_number}: unsupported schema_version"
                )
            frame = _integer(payload.get("frame"), "frame", minimum=0)
            sim_time = _number(payload.get("sim_time_s"), "sim_time_s", minimum=0.0)
            if frame <= previous_frame or sim_time <= previous_time:
                raise ValueError(
                    f"{manifest}:{line_number}: frame and sim_time_s must increase"
                )
            previous_frame, previous_time = frame, sim_time
            payload["_line_number"] = line_number
            records.append(payload)
    if not records:
        raise ValueError("replay manifest contains no frame records")
    return tuple(records)


def run_replay_manifest(
    manifest_path: str | Path,
    *,
    detector: OnnxYoloDetector | None = None,
) -> ReplayReport:
    """Run recorded frames through perception, Qwen boundary and A/B/C/D."""
    manifest = Path(manifest_path).resolve()
    records = load_replay_manifest(manifest)
    runtime = ControlRuntime(PurePursuitController())
    results: list[ReplayFrameResult] = []
    for payload in records:
        results.append(
            _run_frame(payload, manifest.parent, runtime, detector=detector)
        )
    passed_frames = sum(item.passed for item in results)
    return ReplayReport(
        manifest=str(manifest),
        frame_count=len(results),
        passed_frames=passed_frames,
        failed_frames=len(results) - passed_frames,
        passed=passed_frames == len(results),
        results=tuple(results),
    )


def _run_frame(
    payload: Mapping[str, Any],
    dataset_root: Path,
    runtime: ControlRuntime,
    *,
    detector: OnnxYoloDetector | None,
) -> ReplayFrameResult:
    frame = _integer(payload.get("frame"), "frame", minimum=0)
    sim_time = _number(payload.get("sim_time_s"), "sim_time_s", minimum=0.0)
    vehicle = _vehicle(payload.get("vehicle"), frame, sim_time)
    perception_data = _mapping(payload.get("perception", {}), "perception")
    unknown_perception = set(perception_data) - _PERCEPTION_FIELDS
    if unknown_perception:
        raise ValueError(f"unknown perception fields: {sorted(unknown_perception)}")

    recorded_detections = _detections(perception_data.pop("detected_objects", ()))
    rgb_loaded = False
    rgb_ref: str | None = None
    detections = recorded_detections
    if payload.get("rgb_path") is not None:
        rgb_path = _dataset_path(dataset_root, payload["rgb_path"], "rgb_path")
        image = _load_rgb(rgb_path)
        rgb_loaded = True
        rgb_ref = str(rgb_path)
        if detector is not None:
            detections = detector.detect_rgb(image)

    lidar_loaded = False
    lead_distance = perception_data.get("lead_distance_m")
    if payload.get("lidar_path") is not None or payload.get("lidar_points") is not None:
        points = _load_lidar(payload, dataset_root)
        lidar_loaded = True
        lead_distance = front_lidar_distance_m(SimpleNamespace(points=points))
        if lead_distance is not None and perception_data.get("lead_speed_mps") is None:
            # A single LiDAR scan does not provide velocity.  Zero is the
            # conservative replay assumption and is explicitly auditable.
            perception_data["lead_speed_mps"] = 0.0
    perception_data["lead_distance_m"] = lead_distance
    perception_data["detected_objects"] = detections
    scene = PerceptionFrame(frame=frame, sim_time_s=sim_time, **perception_data)

    route = _route(payload.get("route_points"), vehicle)
    qwen_status = "NOT_REQUESTED"
    qwen_error: str | None = None
    watchdog_alerts: tuple[str, ...] = ()
    qwen = payload.get("qwen")
    if qwen is not None:
        qwen_data = _mapping(qwen, "qwen")
        voice = qwen_data.get("voice_command", "")
        if type(voice) is not str:
            raise TypeError("qwen.voice_command must be a string")
        context = QwenInputContext(
            request_id=f"replay_{frame:08d}",
            frame=frame,
            sim_time_s=sim_time,
            voice_command=voice,
            rgb_ref=rgb_ref,
            scene_state={
                "traffic_light": scene.traffic_light,
                "speed_limit_mps": scene.speed_limit_mps,
                "lane_offset_m": scene.lane_offset_m,
            },
            perception={
                "lead_distance_m": scene.lead_distance_m,
                "lead_speed_mps": scene.lead_speed_mps,
                "detected_objects": [asdict(item) for item in detections],
            },
            safety_state=safety_vehicle_state(vehicle, scene),
        )
        # Materialize once so replay exercises JSON serialization at the real
        # model boundary, even when the response is pre-recorded.
        context.to_payload()
        if "response" not in qwen_data:
            failure = fail_closed("PENDING", "record has no Qwen response")
            qwen_status, qwen_error = failure.status, failure.error
            watchdog_alerts = failure.watchdog_alerts
        else:
            try:
                decision = validate_qwen_response(qwen_data["response"])
                high_level = build_high_level_command(
                    decision,
                    voice,
                    command_id=f"replay_qwen_{frame:08d}",
                )
                envelope = HighLevelCommandAdapter().adapt(high_level)
                if envelope.get("status") != "valid":
                    raise ValueError("validated Qwen decision failed A boundary")
                adapted = runtime.submit_voice(envelope, now_s=sim_time)
                if not adapted.control_authorized:
                    raise ValueError("Qwen command was not authorized by runtime")
                qwen_status = "READY"
            except Exception as error:
                failure = fail_closed(
                    "ERROR", f"{type(error).__name__}: {error}",
                )
                qwen_status, qwen_error = failure.status, failure.error
                watchdog_alerts = failure.watchdog_alerts

    dt_s = _number(payload.get("dt_s", 0.05), "dt_s", minimum=1e-6)
    control = runtime.step(
        vehicle,
        scene,
        route,
        dt_s=dt_s,
        watchdog_alerts=watchdog_alerts,
    )
    failures = _evaluate_expected(
        payload.get("expected", {}),
        qwen_status=qwen_status,
        rgb_loaded=rgb_loaded,
        lidar_loaded=lidar_loaded,
        scene=scene,
        control=control,
    )
    return ReplayFrameResult(
        frame=frame,
        qwen_status=qwen_status,
        qwen_error=qwen_error,
        watchdog_alerts=watchdog_alerts,
        rgb_loaded=rgb_loaded,
        lidar_loaded=lidar_loaded,
        detection_count=len(detections),
        lead_distance_m=scene.lead_distance_m,
        safety_override=control.safety_override,
        safety_reason=control.safety_reason,
        throttle=control.final_control.throttle,
        brake=control.final_control.brake,
        steer=control.final_control.steer,
        passed=not failures,
        failures=tuple(failures),
    )


def _evaluate_expected(
    raw_expected: object,
    *,
    qwen_status: str,
    rgb_loaded: bool,
    lidar_loaded: bool,
    scene: PerceptionFrame,
    control: Any,
) -> list[str]:
    expected = _mapping(raw_expected, "expected")
    unknown = set(expected) - _EXPECTED_FIELDS
    if unknown:
        raise ValueError(f"unknown expected fields: {sorted(unknown)}")
    failures: list[str] = []

    def equality(name: str, actual: object) -> None:
        if name in expected and actual != expected[name]:
            failures.append(f"{name}: expected {expected[name]!r}, got {actual!r}")

    equality("qwen_status", qwen_status)
    equality("safety_override", control.safety_override)
    equality("safety_reason", control.safety_reason)
    equality("rgb_loaded", rgb_loaded)
    equality("lidar_loaded", lidar_loaded)
    if "min_brake" in expected and control.final_control.brake < _number(
        expected["min_brake"], "expected.min_brake", minimum=0.0,
    ):
        failures.append("brake below expected minimum")
    if "max_throttle" in expected and control.final_control.throttle > _number(
        expected["max_throttle"], "expected.max_throttle", minimum=0.0,
    ):
        failures.append("throttle above expected maximum")
    if "min_detection_count" in expected and len(scene.detected_objects) < _integer(
        expected["min_detection_count"], "expected.min_detection_count", minimum=0,
    ):
        failures.append("detection count below expected minimum")
    if "lead_distance_range_m" in expected:
        bounds = expected["lead_distance_range_m"]
        if (
            type(bounds) is not list
            or len(bounds) != 2
            or scene.lead_distance_m is None
        ):
            failures.append("lead distance is unavailable for range check")
        else:
            minimum = _number(bounds[0], "lead_distance_range_m[0]", minimum=0.0)
            maximum = _number(bounds[1], "lead_distance_range_m[1]", minimum=minimum)
            if not minimum <= scene.lead_distance_m <= maximum:
                failures.append("lead distance outside expected range")
    return failures


def _vehicle(raw: object, frame: int, sim_time_s: float) -> RuntimeVehicleState:
    data = _mapping(raw, "vehicle")
    expected = {"speed_mps", "x_m", "y_m", "z_m", "yaw_deg", "lane_id"}
    if set(data) != expected:
        raise ValueError(
            f"vehicle fields mismatch; missing={sorted(expected - set(data))}, "
            f"unknown={sorted(set(data) - expected)}"
        )
    return RuntimeVehicleState(frame=frame, sim_time_s=sim_time_s, **data)


def _route(raw: object, vehicle: RuntimeVehicleState) -> RouteReference:
    if raw is None:
        points = ((vehicle.x_m, vehicle.y_m), (vehicle.x_m + 30.0, vehicle.y_m))
    else:
        if type(raw) is not list or len(raw) < 2:
            raise ValueError("route_points must contain at least two [x, y] points")
        points = tuple(
            (
                _number(item[0], "route x"),
                _number(item[1], "route y"),
            )
            for item in raw
            if type(item) is list and len(item) == 2
        )
        if len(points) != len(raw):
            raise ValueError("each route point must be [x, y]")
    return RouteReference(points, 0.0, 5.0)


def _detections(raw: object) -> tuple[DetectedObject, ...]:
    if raw in (None, ()):
        return ()
    if type(raw) is not list:
        raise TypeError("perception.detected_objects must be a list")
    return tuple(
        DetectedObject(
            class_id=item["class_id"],
            class_name=item["class_name"],
            confidence=item["confidence"],
            bbox_xyxy_norm=tuple(item["bbox_xyxy_norm"]),
            distance_m=item.get("distance_m"),
        )
        for item in (_mapping(value, "detected object") for value in raw)
    )


def _load_rgb(path: Path) -> np.ndarray:
    if path.suffix.lower() == ".npy":
        image = np.load(path, allow_pickle=False)
    else:
        try:
            from PIL import Image
        except ImportError as error:
            raise RuntimeError("Pillow is required to replay PNG/JPEG RGB") from error
        image = np.asarray(Image.open(path).convert("RGB"))
    image = np.asarray(image)
    if image.ndim != 3 or image.shape[2] != 3 or image.dtype != np.uint8:
        raise ValueError("replay RGB must be a uint8 array with shape (H, W, 3)")
    return image


def _load_lidar(payload: Mapping[str, Any], dataset_root: Path) -> np.ndarray:
    if payload.get("lidar_path") is not None:
        path = _dataset_path(dataset_root, payload["lidar_path"], "lidar_path")
        if path.suffix.lower() != ".npy":
            raise ValueError("lidar_path must point to a .npy file")
        points = np.load(path, allow_pickle=False)
    else:
        points = np.asarray(payload.get("lidar_points"), dtype=np.float32)
    points = np.asarray(points, dtype=np.float32)
    if points.ndim != 2 or points.shape[1] not in {3, 4}:
        raise ValueError("replay LiDAR must have shape (N, 3) or (N, 4)")
    if not np.isfinite(points).all():
        raise ValueError("replay LiDAR points must be finite")
    return points


def _dataset_path(root: Path, raw: object, name: str) -> Path:
    if type(raw) is not str or not raw.strip():
        raise ValueError(f"{name} must be a non-empty relative path")
    candidate = (root / raw).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as error:
        raise ValueError(f"{name} must stay inside the dataset directory") from error
    if not candidate.is_file():
        raise FileNotFoundError(f"{name} does not exist: {candidate}")
    return candidate


def _mapping(value: object, name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be a mapping")
    return dict(value)


def _integer(value: object, name: str, *, minimum: int) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def _number(
    value: object,
    name: str,
    *,
    minimum: float | None = None,
) -> float:
    if type(value) not in (int, float) or isinstance(value, bool):
        raise TypeError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result) or (minimum is not None and result < minimum):
        raise ValueError(f"{name} must be finite and >= {minimum}")
    return result


def write_replay_report(report: ReplayReport, path: str | Path) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report.to_payload(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


__all__ = [
    "REPLAY_SCHEMA_VERSION",
    "ReplayFrameResult",
    "ReplayReport",
    "load_replay_manifest",
    "run_replay_manifest",
    "write_replay_report",
]
