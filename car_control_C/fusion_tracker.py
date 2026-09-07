"""C-role multi-sensor association and risk summary helpers."""

from __future__ import annotations

from dataclasses import dataclass, replace
from strategy_config import DEFAULT_STRATEGY, dynamic_safety_distance


@dataclass(frozen=True, slots=True)
class PerceptionTarget:
    class_name: str
    distance_m: float
    speed_mps: float
    confidence: float
    source: str
    x_m: float | None = None
    y_m: float | None = None
    target_id: str | None = None
    ttc_s: float | None = None
    risk_level: str = "CLEAR"

    def __post_init__(self) -> None:
        if not self.class_name.strip():
            raise ValueError("class_name must be non-empty")
        if float(self.distance_m) < 0.0:
            raise ValueError("distance_m must be non-negative")
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("confidence must be in [0, 1]")
        if not self.source.strip():
            raise ValueError("source must be non-empty")

    def to_dict(self) -> dict[str, object]:
        return {
            "target_id": self.target_id,
            "class_name": self.class_name,
            "distance_m": float(self.distance_m),
            "speed_mps": float(self.speed_mps),
            "confidence": float(self.confidence),
            "source": self.source,
            "position_m": {"x": self.x_m, "y": self.y_m},
            "ttc_s": self.ttc_s,
            "risk_level": self.risk_level,
        }


class StableTargetTracker:
    """Assign stable target IDs using class and nearest-range continuity."""

    def __init__(self, *, ego_speed_mps: float = 4.0,
                 road_curvature_per_m: float = 0.0,
                 sensor_margin_scale: float = 1.0,
                 max_association_distance_m: float = 2.0) -> None:
        self.ego_speed_mps = float(ego_speed_mps)
        self.road_curvature_per_m = float(road_curvature_per_m)
        self.sensor_margin_scale = float(sensor_margin_scale)
        self.max_association_distance_m = float(max_association_distance_m)
        self._next_index = 1
        self._tracks: dict[str, PerceptionTarget] = {}

    def update(self, target: PerceptionTarget) -> PerceptionTarget:
        target_id = self._match_target(target)
        if target_id is None:
            target_id = f"C-{self._next_index:03d}"
            self._next_index += 1
        enriched = replace(
            target,
            target_id=target_id,
            ttc_s=self._ttc_s(target),
            risk_level=self._risk_level(target),
        )
        self._tracks[target_id] = enriched
        return enriched

    def _match_target(self, target: PerceptionTarget) -> str | None:
        if target.target_id in self._tracks:
            return target.target_id
        for track_id, previous in self._tracks.items():
            if previous.class_name.lower() != target.class_name.lower():
                continue
            if abs(previous.distance_m - target.distance_m) <= self.max_association_distance_m:
                return track_id
        return None

    def _ttc_s(self, target: PerceptionTarget) -> float | None:
        closing_speed = self.ego_speed_mps - float(target.speed_mps)
        if closing_speed <= 0.0:
            return None
        return round(float(target.distance_m) / closing_speed, 3)

    def _risk_level(self, target: PerceptionTarget) -> str:
        ttc_s = self._ttc_s(target)
        closing_speed = max(0.0, self.ego_speed_mps - float(target.speed_mps))
        envelope = dynamic_safety_distance(
            ego_speed_mps=self.ego_speed_mps,
            closing_speed_mps=closing_speed,
            curvature_per_m=self.road_curvature_per_m,
            actor_type=target.class_name,
            sensor_margin_scale=self.sensor_margin_scale,
        )
        if ttc_s is not None and ttc_s <= DEFAULT_STRATEGY.common.emergency_ttc_s:
            return "EMERGENCY"
        if float(target.distance_m) <= envelope.emergency_distance_m:
            return "EMERGENCY"
        if ttc_s is not None and ttc_s <= DEFAULT_STRATEGY.common.caution_ttc_s:
            return "CAUTION"
        if float(target.distance_m) <= envelope.caution_distance_m:
            return "CAUTION"
        return "CLEAR"
