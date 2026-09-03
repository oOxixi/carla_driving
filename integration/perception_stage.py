"""Perception/control source boundary for the CARLA runtime.

Ground truth remains useful for event triggers and scoring, but a sensor-mode
controller must never become dependent on it.  This module makes that boundary
explicit and independently testable.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Mapping


class ObservationAuthority(str, Enum):
    SENSOR = "SENSOR"
    MAP = "MAP"
    ORACLE = "ORACLE"
    SYNTHETIC = "SYNTHETIC"
    DERIVED = "DERIVED"
    UNKNOWN = "UNKNOWN"


_ORACLE_TOKENS = (
    "SCENARIO_CONFIG_TRUTH",
    "CARLA_WORLD_TRUTH",
    "CARLA_TRUTH_",
    "CARLA_SCENARIO_TRAFFIC_LIGHT_ACTOR",
)
_SYNTHETIC_TOKENS = ("VIRTUAL_ACCEPTANCE_TRUTH", "DETERMINISTIC_TEST")
_SENSOR_TOKENS = ("RGB", "LIDAR", "RADAR", "COLLISION_EVENT", "LANE_INVASION_EVENT")
_MAP_TOKENS = ("CARLA_MAP_", "MAP_WAYPOINT", "MAP_STOP_WAYPOINT")


def classify_observation_source(source: str) -> ObservationAuthority:
    normalized = str(source).strip().upper()
    if any(token in normalized for token in _ORACLE_TOKENS):
        return ObservationAuthority.ORACLE
    if any(token in normalized for token in _SYNTHETIC_TOKENS):
        return ObservationAuthority.SYNTHETIC
    if any(token in normalized for token in _SENSOR_TOKENS):
        return ObservationAuthority.SENSOR
    if any(token in normalized for token in _MAP_TOKENS):
        return ObservationAuthority.MAP
    if normalized and normalized not in {"UNKNOWN", "UNAVAILABLE"}:
        return ObservationAuthority.DERIVED
    return ObservationAuthority.UNKNOWN


@dataclass(frozen=True, slots=True)
class PerceptionSourceAudit:
    authority_by_field: Mapping[str, str]
    forbidden_control_fields: tuple[str, ...]

    @property
    def control_clean(self) -> bool:
        return not self.forbidden_control_fields

    def to_dict(self) -> dict[str, object]:
        return {
            "authority_by_field": dict(self.authority_by_field),
            "forbidden_control_fields": list(self.forbidden_control_fields),
            "control_clean": self.control_clean,
        }


def audit_control_sources(
    source_by_field: Mapping[str, str],
    *,
    strict_sensor_mode: bool,
) -> PerceptionSourceAudit:
    authorities = {
        str(field): classify_observation_source(str(source)).value
        for field, source in source_by_field.items()
    }
    forbidden = tuple(sorted(
        field
        for field, authority in authorities.items()
        if strict_sensor_mode and authority in {
            ObservationAuthority.ORACLE.value,
            ObservationAuthority.SYNTHETIC.value,
        }
    ))
    return PerceptionSourceAudit(
        MappingProxyType(authorities), forbidden,
    )


__all__ = [
    "ObservationAuthority",
    "PerceptionSourceAudit",
    "audit_control_sources",
    "classify_observation_source",
]
