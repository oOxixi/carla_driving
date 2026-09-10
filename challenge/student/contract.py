"""Frozen Student V0 tensor dimensions and structured vocabularies."""

from __future__ import annotations

from dataclasses import dataclass


BEHAVIORS = (
    "KEEP_LANE", "SET_SPEED", "SLOW_DOWN", "STOP", "YIELD", "FOLLOW",
    "TURN_LEFT", "TURN_RIGHT", "CHANGE_LANE_LEFT", "CHANGE_LANE_RIGHT",
    "AVOID_OBSTACLE", "RETURN_TO_LANE", "PULL_OVER", "HOLD",
)
TARGET_LANES = (
    "CURRENT", "LEFT_ADJACENT", "RIGHT_ADJACENT", "ROUTE_BRANCH", "SHOULDER", "NONE",
)
COMPLETION_TYPES = (
    "SPEED_BELOW", "SPEED_REACHED", "LANE_CENTERED", "JUNCTION_EXITED",
    "TARGET_GAP_REACHED", "TARGET_PASSED", "STOPPED", "HOLD_FRAMES",
)
ON_FAILURE = ("SAFE_STOP", "HOLD_CURRENT_LANE", "REPLAN", "CONFIRM")
REPLAN_CONDITIONS = (
    "TARGET_LOST", "LANE_BLOCKED", "ROUTE_MISMATCH", "NEW_EMERGENCY_OBJECT",
    "PROGRESS_STALLED", "ROUTE_DEVIATION", "PLAN_EXPIRING",
)
OUTPUT_NAMES = (
    "plan_length_logits", "behavior_logits", "target_pointer_logits",
    "target_lane_logits", "target_speed_mps", "completion_type_logits",
    "on_failure_logits", "confidence", "requires_confirmation_logits",
    "replan_condition_logits",
)


@dataclass(frozen=True, slots=True)
class StudentShapeContract:
    batch: int = 1
    rgb_channels: int = 3
    rgb_height: int = 224
    rgb_width: int = 224
    text_length: int = 32
    max_targets: int = 8
    target_features: int = 8
    state_features: int = 32
    max_steps: int = 4

    @property
    def input_shapes(self) -> dict[str, tuple[int, ...]]:
        return {
            "rgb": (self.batch, self.rgb_channels, self.rgb_height, self.rgb_width),
            "text_tokens": (self.batch, self.text_length),
            "targets": (self.batch, self.max_targets, self.target_features),
            "state": (self.batch, self.state_features),
        }


__all__ = [
    "BEHAVIORS", "COMPLETION_TYPES", "ON_FAILURE", "OUTPUT_NAMES",
    "REPLAN_CONDITIONS", "StudentShapeContract", "TARGET_LANES",
]

