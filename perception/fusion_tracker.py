"""RGB/radar/LiDAR association, stable IDs, TTC and risk summarization."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import math
from typing import Any

from runtime.interface_registry import InterfaceRegistry
from .sensor_adapter import AlignedSensorFrame, Modality


SOURCE_WEIGHT = {
    Modality.RGB: 0.35,
    Modality.RADAR: 1.0,
    Modality.LIDAR: 0.9,
    Modality.VEHICLE_STATE: 0.5,
}


@dataclass(frozen=True, slots=True)
class Observation:
    source: Modality
    class_name: str
    position_m: tuple[float, float, float]
    velocity_mps: tuple[float, float, float]
    confidence: float
    source_id: str | None = None
    bbox_xyxy_norm: tuple[float, float, float, float] | None = None

    def __post_init__(self) -> None:
        if self.source not in {Modality.RGB, Modality.RADAR, Modality.LIDAR}:
            raise ValueError("observation source must be RGB/RADAR/LIDAR")
        if self.class_name not in {"vehicle", "pedestrian", "cyclist", "obstacle", "unknown"}:
            raise ValueError("unsupported observation class")
        for name in ("position_m", "velocity_mps"):
            values = getattr(self, name)
            if type(values) is not tuple or len(values) != 3 or not all(
                type(value) in (int, float) and not isinstance(value, bool) and math.isfinite(float(value))
                for value in values
            ):
                raise ValueError(f"{name} must be a finite three-number tuple")
            object.__setattr__(self, name, tuple(float(value) for value in values))
        if type(self.confidence) not in (int, float) or isinstance(self.confidence, bool) or not math.isfinite(float(self.confidence)) or not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be finite and in [0, 1]")
        object.__setattr__(self, "confidence", float(self.confidence))


@dataclass(frozen=True, slots=True)
class FusedObject:
    track_id: str
    class_name: str
    position_m: tuple[float, float, float]
    velocity_mps: tuple[float, float, float]
    distance_m: float
    ttc_s: float | None
    confidence: float
    sources: tuple[Modality, ...]
    bbox_xyxy_norm: tuple[float, float, float, float] | None
    last_frame_id: int


@dataclass(frozen=True, slots=True)
class FusionTrackerConfig:
    observation_association_m: float = 2.5
    track_association_m: float = 4.0
    max_track_age_frames: int = 5
    emergency_ttc_s: float = 1.5
    high_ttc_s: float = 2.5
    emergency_gap_m: float = 5.0
    caution_gap_m: float = 10.0

    def __post_init__(self) -> None:
        for name in ("observation_association_m", "track_association_m", "emergency_ttc_s", "high_ttc_s", "emergency_gap_m", "caution_gap_m"):
            value = getattr(self, name)
            if type(value) not in (int, float) or isinstance(value, bool) or not math.isfinite(float(value)) or value <= 0:
                raise ValueError(f"{name} must be finite and positive")
        if type(self.max_track_age_frames) is not int or self.max_track_age_frames < 1:
            raise ValueError("max_track_age_frames must be positive")


@dataclass(frozen=True, slots=True)
class FusionResult:
    objects: tuple[FusedObject, ...]
    min_gap_m: float | None
    ttc_s: float | None
    risk_level: str
    perception_state: Mapping[str, Any]


@dataclass(slots=True)
class _TrackState:
    fused: FusedObject
    misses: int = 0


class FusionTracker:
    def __init__(self, config: FusionTrackerConfig | None = None, *, registry: InterfaceRegistry | None = None) -> None:
        self.config = config or FusionTrackerConfig()
        self.registry = registry or InterfaceRegistry()
        self._tracks: dict[str, _TrackState] = {}
        self._next_track = 1

    def update(
        self,
        aligned: AlignedSensorFrame,
        observations: Iterable[Observation],
        *,
        ego_speed_mps: float,
        traffic_light: str = "UNKNOWN",
        distance_to_stop_line_m: float | None = None,
        speed_limit_mps: float | None = None,
    ) -> FusionResult:
        if not isinstance(aligned, AlignedSensorFrame):
            raise TypeError("aligned must be AlignedSensorFrame")
        if type(ego_speed_mps) not in (int, float) or isinstance(ego_speed_mps, bool) or not math.isfinite(float(ego_speed_mps)) or ego_speed_mps < 0:
            raise ValueError("ego_speed_mps must be finite and non-negative")
        if traffic_light not in {"RED", "YELLOW", "GREEN", "UNKNOWN"}:
            raise ValueError("traffic_light is invalid")
        observations = tuple(observations)
        if any(not isinstance(item, Observation) for item in observations):
            raise TypeError("observations must contain Observation values")
        clusters = self._cluster(observations)
        fused_candidates = [self._fuse_cluster(cluster, aligned.reference_frame_id, float(ego_speed_mps)) for cluster in clusters]
        objects = self._associate_tracks(fused_candidates, aligned.reference_frame_id)
        min_gap = min((item.distance_m for item in objects if item.position_m[0] > 0), default=None)
        ttc = min((item.ttc_s for item in objects if item.ttc_s is not None), default=None)
        risk = self._risk(min_gap, ttc, aligned)
        state = {
            "schema_version": "1.0",
            "frame_id": aligned.reference_frame_id,
            "sim_time_s": aligned.reference_sim_time_s,
            "captured_at_ns": aligned.reference_captured_at_ns,
            "coordinate_frame": "ego_front_x_left_y_up_z_m",
            "objects": [self._object_payload(item) for item in objects],
            "traffic_light": traffic_light,
            "distance_to_stop_line_m": distance_to_stop_line_m,
            "speed_limit_mps": speed_limit_mps,
            "ttc_s": ttc,
            "min_gap_m": min_gap,
            "risk_level": risk,
            "modality_valid": {
                "rgb": bool(aligned.modality_valid.get(Modality.RGB, False)),
                "radar": bool(aligned.modality_valid.get(Modality.RADAR, False)),
                "lidar": bool(aligned.modality_valid.get(Modality.LIDAR, False)),
                "vehicle_state": bool(aligned.modality_valid.get(Modality.VEHICLE_STATE, False)),
            },
            "stale": aligned.stale,
            "sync": {
                "reference_frame_id": aligned.reference_frame_id,
                "max_skew_ms": aligned.max_skew_ms,
                "within_tolerance": aligned.within_tolerance,
                "missing_modalities": [item.value for item in aligned.missing_modalities],
            },
            "degraded_reason_codes": list(aligned.degraded_reason_codes),
        }
        canonical = self.registry.validate("perception_state", state)
        return FusionResult(objects, min_gap, ttc, risk, canonical)

    def _cluster(self, observations: tuple[Observation, ...]) -> list[list[Observation]]:
        clusters: list[list[Observation]] = []
        for observation in sorted(observations, key=lambda item: (
            item.class_name, math.dist((0.0, 0.0, 0.0), item.position_m), item.source.value, item.source_id or "",
        )):
            best: tuple[float, int] | None = None
            for index, cluster in enumerate(clusters):
                if not self._class_compatible(observation.class_name, cluster[0].class_name):
                    continue
                center = tuple(sum(item.position_m[axis] for item in cluster) / len(cluster) for axis in range(3))
                distance = math.dist(observation.position_m, center)
                if distance <= self.config.observation_association_m and (best is None or distance < best[0]):
                    best = distance, index
            if best is None:
                clusters.append([observation])
            else:
                clusters[best[1]].append(observation)
        return clusters

    def _fuse_cluster(self, cluster: list[Observation], frame_id: int, ego_speed_mps: float) -> FusedObject:
        weights = [SOURCE_WEIGHT[item.source] * max(item.confidence, 0.05) for item in cluster]
        total = sum(weights)
        position = tuple(sum(item.position_m[axis] * weight for item, weight in zip(cluster, weights)) / total for axis in range(3))
        velocity = tuple(sum(item.velocity_mps[axis] * weight for item, weight in zip(cluster, weights)) / total for axis in range(3))
        best_class = max(cluster, key=lambda item: (item.confidence, SOURCE_WEIGHT[item.source])).class_name
        distance = math.dist((0.0, 0.0, 0.0), position)
        closing = ego_speed_mps - velocity[0]
        ttc = position[0] / closing if position[0] > 0.0 and closing > 0.05 else None
        confidence = min(1.0, 1.0 - math.prod(1.0 - item.confidence * SOURCE_WEIGHT[item.source] for item in cluster))
        sources = tuple(sorted({item.source for item in cluster}, key=lambda item: item.value))
        bbox = next((item.bbox_xyxy_norm for item in sorted(cluster, key=lambda item: item.confidence, reverse=True) if item.bbox_xyxy_norm is not None), None)
        return FusedObject("", best_class, position, velocity, distance, ttc, confidence, sources, bbox, frame_id)

    def _associate_tracks(self, candidates: list[FusedObject], frame_id: int) -> tuple[FusedObject, ...]:
        unmatched = set(self._tracks)
        next_tracks: dict[str, _TrackState] = {}
        for candidate in sorted(candidates, key=lambda item: (item.distance_m, item.class_name)):
            matches = [
                (track_id, math.dist(candidate.position_m, self._tracks[track_id].fused.position_m))
                for track_id in unmatched
                if self._class_compatible(candidate.class_name, self._tracks[track_id].fused.class_name)
            ]
            track_id: str | None = None
            if matches:
                candidate_id, distance = min(matches, key=lambda item: (item[1], item[0]))
                if distance <= self.config.track_association_m:
                    track_id = candidate_id
                    unmatched.remove(candidate_id)
            if track_id is None:
                track_id = f"fused-{self._next_track:06d}"
                self._next_track += 1
            next_tracks[track_id] = _TrackState(FusedObject(
                track_id, candidate.class_name, candidate.position_m, candidate.velocity_mps,
                candidate.distance_m, candidate.ttc_s, candidate.confidence, candidate.sources,
                candidate.bbox_xyxy_norm, frame_id,
            ))
        for track_id in unmatched:
            previous = self._tracks[track_id]
            previous.misses += 1
            if previous.misses <= self.config.max_track_age_frames:
                next_tracks[track_id] = previous
        self._tracks = next_tracks
        visible = [state.fused for state in next_tracks.values() if state.misses == 0]
        visible.sort(key=lambda item: (item.distance_m, item.track_id))
        return tuple(visible)

    def _risk(self, gap: float | None, ttc: float | None, aligned: AlignedSensorFrame) -> str:
        if aligned.stale or not aligned.modality_valid.get(Modality.VEHICLE_STATE, False):
            return "UNKNOWN"
        if (ttc is not None and ttc <= self.config.emergency_ttc_s) or (gap is not None and gap <= self.config.emergency_gap_m):
            return "EMERGENCY"
        if ttc is not None and ttc <= self.config.high_ttc_s:
            return "HIGH"
        if gap is not None and gap <= self.config.caution_gap_m:
            return "CAUTION"
        return "LOW"

    @staticmethod
    def _class_compatible(first: str, second: str) -> bool:
        return first == second or "unknown" in {first, second} or "obstacle" in {first, second}

    @staticmethod
    def _object_payload(item: FusedObject) -> dict[str, Any]:
        return {
            "track_id": item.track_id,
            "class": item.class_name,
            "position_m": list(item.position_m),
            "velocity_mps": list(item.velocity_mps),
            "distance_m": item.distance_m,
            "ttc_s": item.ttc_s,
            "confidence": item.confidence,
            "sources": [source.value for source in item.sources],
            "bbox_xyxy_norm": None if item.bbox_xyxy_norm is None else list(item.bbox_xyxy_norm),
        }


__all__ = [
    "FusedObject",
    "FusionResult",
    "FusionTracker",
    "FusionTrackerConfig",
    "Observation",
]
