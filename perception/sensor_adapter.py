"""Timestamp, frame, coordinate and bounded-buffer normalization for C."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from enum import Enum
import json
import math
from pathlib import Path
from threading import Lock
from typing import Any


class Modality(str, Enum):
    RGB = "RGB"
    RADAR = "RADAR"
    LIDAR = "LIDAR"
    VEHICLE_STATE = "VEHICLE_STATE"


def _finite(name: str, value: object) -> float:
    if type(value) not in (int, float) or isinstance(value, bool):
        raise TypeError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


@dataclass(frozen=True, slots=True)
class Extrinsics:
    """Rigid transform from one sensor frame to ego x-front/y-left/z-up."""

    translation_m: tuple[float, float, float] = (0.0, 0.0, 0.0)
    roll_deg: float = 0.0
    pitch_deg: float = 0.0
    yaw_deg: float = 0.0

    def __post_init__(self) -> None:
        if type(self.translation_m) is not tuple or len(self.translation_m) != 3:
            raise TypeError("translation_m must be a three-number tuple")
        object.__setattr__(self, "translation_m", tuple(
            _finite(f"translation_m[{index}]", value)
            for index, value in enumerate(self.translation_m)
        ))
        for name in ("roll_deg", "pitch_deg", "yaw_deg"):
            object.__setattr__(self, name, _finite(name, getattr(self, name)))

    def transform_point(self, point_xyz_m: Iterable[float]) -> tuple[float, float, float]:
        point = tuple(point_xyz_m)
        if len(point) != 3:
            raise ValueError("point_xyz_m must contain exactly three coordinates")
        x, y, z = (_finite("point", value) for value in point)
        roll, pitch, yaw = (
            math.radians(value) for value in (self.roll_deg, self.pitch_deg, self.yaw_deg)
        )
        cr, sr = math.cos(roll), math.sin(roll)
        cp, sp = math.cos(pitch), math.sin(pitch)
        cy, sy = math.cos(yaw), math.sin(yaw)
        # Rz(yaw) @ Ry(pitch) @ Rx(roll)
        rx = (cy * cp) * x + (cy * sp * sr - sy * cr) * y + (cy * sp * cr + sy * sr) * z
        ry = (sy * cp) * x + (sy * sp * sr + cy * cr) * y + (sy * sp * cr - cy * sr) * z
        rz = (-sp) * x + (cp * sr) * y + (cp * cr) * z
        tx, ty, tz = self.translation_m
        return rx + tx, ry + ty, rz + tz

    def rotate_vector(self, vector_xyz: Iterable[float]) -> tuple[float, float, float]:
        origin = self.transform_point((0.0, 0.0, 0.0))
        point = self.transform_point(vector_xyz)
        return tuple(point[index] - origin[index] for index in range(3))

    def to_dict(self) -> dict[str, Any]:
        return {
            "translation_m": list(self.translation_m),
            "roll_deg": self.roll_deg,
            "pitch_deg": self.pitch_deg,
            "yaw_deg": self.yaw_deg,
        }


@dataclass(frozen=True, slots=True)
class SensorSample:
    modality: Modality
    frame_id: int
    sim_time_s: float
    captured_at_ns: int
    payload: Any
    extrinsics: Extrinsics = Extrinsics()
    valid: bool = True
    error_code: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.modality, Modality):
            raise TypeError("modality must be Modality")
        if type(self.frame_id) is not int or self.frame_id < 0:
            raise ValueError("frame_id must be a non-negative integer")
        sim_time = _finite("sim_time_s", self.sim_time_s)
        if sim_time < 0:
            raise ValueError("sim_time_s must be non-negative")
        if type(self.captured_at_ns) is not int or self.captured_at_ns < 0:
            raise ValueError("captured_at_ns must be a non-negative integer")
        if not isinstance(self.extrinsics, Extrinsics):
            raise TypeError("extrinsics must be Extrinsics")
        if type(self.valid) is not bool:
            raise TypeError("valid must be bool")
        if not self.valid and (type(self.error_code) is not str or not self.error_code):
            raise ValueError("invalid samples require a non-empty error_code")
        object.__setattr__(self, "sim_time_s", sim_time)

    def invalidated(self, error_code: str, *, payload: Any = None) -> "SensorSample":
        return replace(self, payload=payload, valid=False, error_code=error_code)


@dataclass(frozen=True, slots=True)
class AlignedSensorFrame:
    reference_frame_id: int
    reference_sim_time_s: float
    reference_captured_at_ns: int
    samples: Mapping[Modality, SensorSample]
    modality_valid: Mapping[Modality, bool]
    max_skew_ms: float
    within_tolerance: bool
    stale: bool
    missing_modalities: tuple[Modality, ...]
    degraded_reason_codes: tuple[str, ...]

    def sample(self, modality: Modality) -> SensorSample | None:
        return self.samples.get(modality)


class SensorSynchronizer:
    """Align exact CARLA frames without blocking and without false validity."""

    def __init__(
        self,
        *,
        required_modalities: tuple[Modality, ...] = tuple(Modality),
        tolerance_ms: float = 50.0,
        max_age_ms: float = 150.0,
        buffer_size: int = 8,
        require_same_frame: bool = True,
    ) -> None:
        if not required_modalities or len(set(required_modalities)) != len(required_modalities):
            raise ValueError("required_modalities must be non-empty and unique")
        if any(not isinstance(item, Modality) for item in required_modalities):
            raise TypeError("required_modalities entries must be Modality")
        self.tolerance_ms = _finite("tolerance_ms", tolerance_ms)
        self.max_age_ms = _finite("max_age_ms", max_age_ms)
        if self.tolerance_ms < 0 or self.max_age_ms <= 0:
            raise ValueError("tolerance_ms must be non-negative and max_age_ms positive")
        if type(buffer_size) is not int or buffer_size < 1:
            raise ValueError("buffer_size must be a positive integer")
        self.required_modalities = required_modalities
        self.require_same_frame = bool(require_same_frame)
        self._buffers = {item: deque(maxlen=buffer_size) for item in required_modalities}
        self._lock = Lock()

    def push(self, sample: SensorSample) -> None:
        if not isinstance(sample, SensorSample):
            raise TypeError("sample must be SensorSample")
        if sample.modality not in self._buffers:
            raise ValueError(f"unconfigured modality: {sample.modality.value}")
        with self._lock:
            buffer = self._buffers[sample.modality]
            # Replace duplicate modality/frame samples deterministically.
            retained = [item for item in buffer if item.frame_id != sample.frame_id]
            retained.append(sample)
            retained.sort(key=lambda item: (item.frame_id, item.captured_at_ns))
            buffer.clear()
            buffer.extend(retained[-buffer.maxlen:])

    def align(
        self,
        *,
        reference_frame_id: int,
        reference_sim_time_s: float,
        reference_captured_at_ns: int,
        now_ns: int,
    ) -> AlignedSensorFrame:
        if type(reference_frame_id) is not int or reference_frame_id < 0:
            raise ValueError("reference_frame_id must be non-negative")
        sim_time = _finite("reference_sim_time_s", reference_sim_time_s)
        for name, value in (("reference_captured_at_ns", reference_captured_at_ns), ("now_ns", now_ns)):
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        with self._lock:
            snapshots = {name: tuple(buffer) for name, buffer in self._buffers.items()}
        selected: dict[Modality, SensorSample] = {}
        missing: list[Modality] = []
        reasons: list[str] = []
        skews: list[float] = []
        validity: dict[Modality, bool] = {}
        for modality in self.required_modalities:
            candidates = snapshots[modality]
            if self.require_same_frame:
                candidates = tuple(item for item in candidates if item.frame_id == reference_frame_id)
            if not candidates:
                missing.append(modality)
                validity[modality] = False
                reasons.append(f"{modality.value}_MISSING")
                continue
            sample = min(
                candidates,
                key=lambda item: (
                    abs(item.captured_at_ns - reference_captured_at_ns),
                    abs(item.frame_id - reference_frame_id),
                ),
            )
            skew_ms = abs(sample.captured_at_ns - reference_captured_at_ns) / 1e6
            skews.append(skew_ms)
            selected[modality] = sample
            valid = sample.valid and skew_ms <= self.tolerance_ms
            validity[modality] = valid
            if not sample.valid:
                reasons.append(sample.error_code or f"{modality.value}_INVALID")
            if skew_ms > self.tolerance_ms:
                reasons.append(f"{modality.value}_SYNC_TOLERANCE_EXCEEDED")
            if self.require_same_frame and sample.frame_id != reference_frame_id:
                valid = False
                validity[modality] = False
                reasons.append(f"{modality.value}_FRAME_MISMATCH")
        max_skew = max(skews, default=0.0)
        age_ms = max(0.0, (now_ns - reference_captured_at_ns) / 1e6)
        if age_ms > self.max_age_ms:
            reasons.append("PERCEPTION_STALE")
        within = not missing and max_skew <= self.tolerance_ms and all(validity.values())
        stale = age_ms > self.max_age_ms or not within
        return AlignedSensorFrame(
            reference_frame_id,
            sim_time,
            reference_captured_at_ns,
            selected,
            validity,
            max_skew,
            within,
            stale,
            tuple(missing),
            tuple(dict.fromkeys(reasons)),
        )


class SensorRecorder:
    """Append strict JSON samples for deterministic replay."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self.path.open("x", encoding="utf-8", newline="\n")

    def record(self, sample: SensorSample) -> None:
        if not isinstance(sample, SensorSample):
            raise TypeError("sample must be SensorSample")
        payload = sample.payload
        try:
            import numpy as np
            if isinstance(payload, np.ndarray):
                payload = {"array": payload.tolist(), "dtype": str(payload.dtype), "shape": list(payload.shape)}
        except ImportError:  # pragma: no cover
            pass
        record = {
            "schema_version": "1.0",
            "modality": sample.modality.value,
            "frame_id": sample.frame_id,
            "sim_time_s": sample.sim_time_s,
            "captured_at_ns": sample.captured_at_ns,
            "payload": payload,
            "extrinsics": sample.extrinsics.to_dict(),
            "valid": sample.valid,
            "error_code": sample.error_code,
        }
        self._handle.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
        self._handle.flush()

    def close(self) -> None:
        if not self._handle.closed:
            self._handle.close()

    def __enter__(self) -> "SensorRecorder":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


class SensorReplayer:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def __iter__(self):
        for line_number, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), start=1):
            try:
                record = json.loads(line)
                ext = record["extrinsics"]
                payload = record["payload"]
                if isinstance(payload, dict) and set(payload) == {"array", "dtype", "shape"}:
                    import numpy as np
                    payload = np.asarray(payload["array"], dtype=payload["dtype"]).reshape(payload["shape"])
                yield SensorSample(
                    Modality(record["modality"]),
                    record["frame_id"],
                    record["sim_time_s"],
                    record["captured_at_ns"],
                    payload,
                    Extrinsics(tuple(ext["translation_m"]), ext["roll_deg"], ext["pitch_deg"], ext["yaw_deg"]),
                    record["valid"],
                    record["error_code"],
                )
            except Exception as error:
                raise ValueError(f"invalid sensor replay line {line_number}: {error}") from error


__all__ = [
    "AlignedSensorFrame",
    "Extrinsics",
    "Modality",
    "SensorRecorder",
    "SensorReplayer",
    "SensorSample",
    "SensorSynchronizer",
]
