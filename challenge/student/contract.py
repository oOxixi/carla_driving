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

BEHAVIOR_TO_ID = {name: index for index, name in enumerate(BEHAVIORS)}
TARGET_LANE_TO_ID = {name: index for index, name in enumerate(TARGET_LANES)}
COMPLETION_TYPE_TO_ID = {name: index for index, name in enumerate(COMPLETION_TYPES)}
ON_FAILURE_TO_ID = {name: index for index, name in enumerate(ON_FAILURE)}
REPLAN_CONDITION_TO_ID = {name: index for index, name in enumerate(REPLAN_CONDITIONS)}


@dataclass(frozen=True, slots=True)
class StudentShapeContract:
    batch: int = 1
    rgb_channels: int = 3
    rgb_height: int = 224
    rgb_width: int = 224
    text_length: int = 32
    max_targets: int = 8
    target_features: int = 14
    state_features: int = 64
    max_steps: int = 4

    @property
    def input_shapes(self) -> dict[str, tuple[int, ...]]:
        return {
            "rgb": (self.batch, self.rgb_channels, self.rgb_height, self.rgb_width),
            "text_tokens": (self.batch, self.text_length),
            "targets": (self.batch, self.max_targets, self.target_features),
            "state": (self.batch, self.state_features),
        }

    @property
    def output_shapes(self) -> dict[str, tuple[int, ...]]:
        return {
            "plan_length_logits": (self.batch, self.max_steps),
            "behavior_logits": (self.batch, self.max_steps, len(BEHAVIORS)),
            "target_pointer_logits": (
                self.batch, self.max_steps, self.max_targets + 1,
            ),
            "target_lane_logits": (self.batch, self.max_steps, len(TARGET_LANES)),
            "target_speed_mps": (self.batch, self.max_steps),
            "completion_type_logits": (
                self.batch, self.max_steps, len(COMPLETION_TYPES),
            ),
            "on_failure_logits": (self.batch, self.max_steps, len(ON_FAILURE)),
            "confidence": (self.batch, 1),
            "requires_confirmation_logits": (self.batch, 1),
            "replan_condition_logits": (self.batch, len(REPLAN_CONDITIONS)),
        }


__all__ = [
    "BEHAVIORS", "BEHAVIOR_TO_ID", "COMPLETION_TYPES", "COMPLETION_TYPE_TO_ID",
    "ON_FAILURE", "ON_FAILURE_TO_ID", "OUTPUT_NAMES", "REPLAN_CONDITIONS",
    "REPLAN_CONDITION_TO_ID", "StudentShapeContract", "TARGET_LANES",
    "TARGET_LANE_TO_ID",
]
