"""Stable first-failure classification for CARLA run triage."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class FailureStage(str, Enum):
    SETUP = "SETUP"
    ROUTE = "ROUTE"
    ACTOR_SPAWN = "ACTOR_SPAWN"
    PERCEPTION = "PERCEPTION"
    QWEN = "QWEN"
    PLAN = "PLAN"
    CONTROL = "CONTROL"
    SCORING = "SCORING"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class RuntimeFailureDiagnosis:
    stage: FailureStage
    code: str
    exception_type: str
    detail: str

    def to_dict(self) -> dict[str, str]:
        return {
            "stage": self.stage.value,
            "code": self.code,
            "exception_type": self.exception_type,
            "detail": self.detail,
        }


def diagnose_runtime_failure(error: BaseException) -> RuntimeFailureDiagnosis:
    message = str(error)
    normalized = message.lower()
    rules = (
        (FailureStage.ROUTE, "ROUTE_CONTRACT", ("route", "topology", "waypoint", "destination")),
        (FailureStage.ACTOR_SPAWN, "ACTOR_SPAWN", ("spawn", "blueprint", "actor is not alive")),
        (FailureStage.PERCEPTION, "PERCEPTION_INPUT", ("rgb", "lidar", "radar", "sensor", "perception")),
        (FailureStage.QWEN, "QWEN_BOUNDARY", ("qwen", "model", "inference")),
        (FailureStage.PLAN, "PLAN_EXECUTION", ("maneuver", "plan", "precondition")),
        (FailureStage.CONTROL, "CONTROL_SAFETY", ("control", "safety", "watchdog")),
        (FailureStage.SCORING, "SCORING_CONTRACT", ("score", "acceptance", "evidence")),
        (FailureStage.SETUP, "RUNTIME_SETUP", ("carla", "connect", "map", "port")),
    )
    for stage, code, tokens in rules:
        if any(token in normalized for token in tokens):
            return RuntimeFailureDiagnosis(stage, code, type(error).__name__, message)
    return RuntimeFailureDiagnosis(
        FailureStage.UNKNOWN, "UNCLASSIFIED_RUNTIME_FAILURE", type(error).__name__, message,
    )


__all__ = ["FailureStage", "RuntimeFailureDiagnosis", "diagnose_runtime_failure"]
