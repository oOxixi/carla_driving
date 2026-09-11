"""Tiny D1-only Student used to prove the training path before A1 handoff."""

from __future__ import annotations

from typing import Any, Mapping

import torch
from torch import Tensor, nn

from .label_encoder import (
    BEHAVIORS,
    COMPLETION_TYPES,
    FAILURE_ACTIONS,
    REPLAN_CONDITIONS,
    TARGET_LANES,
)


class DummyStudent(nn.Module):
    """A shared MLP with the exact structured output dictionary A3 expects."""

    def __init__(
        self,
        *,
        feature_dim: int = 32,
        hidden_dim: int = 48,
        max_steps: int = 4,
        max_targets: int = 8,
    ) -> None:
        super().__init__()
        self.max_steps = int(max_steps)
        self.max_targets = int(max_targets)
        self.backbone = nn.Sequential(
            nn.Linear(feature_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
        )
        self.plan_length = nn.Linear(hidden_dim, max_steps)
        self.behavior = nn.Linear(hidden_dim, max_steps * len(BEHAVIORS))
        self.target_pointer = nn.Linear(hidden_dim, max_steps * (max_targets + 1))
        self.target_lane = nn.Linear(hidden_dim, max_steps * len(TARGET_LANES))
        self.target_speed = nn.Linear(hidden_dim, max_steps)
        self.completion = nn.Linear(hidden_dim, max_steps * len(COMPLETION_TYPES))
        self.failure = nn.Linear(hidden_dim, max_steps * len(FAILURE_ACTIONS))
        self.confidence = nn.Linear(hidden_dim, 1)
        self.confirmation = nn.Linear(hidden_dim, 1)
        self.replan = nn.Linear(hidden_dim, len(REPLAN_CONDITIONS))

    def forward(self, model_inputs: Mapping[str, Tensor]) -> dict[str, Tensor]:
        features = model_inputs["features"]
        hidden = self.backbone(features)
        batch = hidden.shape[0]
        return {
            "plan_length_logits": self.plan_length(hidden),
            "behavior_logits": self.behavior(hidden).reshape(
                batch, self.max_steps, len(BEHAVIORS),
            ),
            "target_pointer_logits": self.target_pointer(hidden).reshape(
                batch, self.max_steps, self.max_targets + 1,
            ),
            "target_lane_logits": self.target_lane(hidden).reshape(
                batch, self.max_steps, len(TARGET_LANES),
            ),
            "target_speed_mps": self.target_speed(hidden),
            "completion_type_logits": self.completion(hidden).reshape(
                batch, self.max_steps, len(COMPLETION_TYPES),
            ),
            "on_failure_logits": self.failure(hidden).reshape(
                batch, self.max_steps, len(FAILURE_ACTIONS),
            ),
            "confidence": self.confidence(hidden).sigmoid(),
            "requires_confirmation_logits": self.confirmation(hidden),
            "replan_condition_logits": self.replan(hidden),
        }


def build_dummy_student(config: Mapping[str, Any] | None = None) -> DummyStudent:
    raw = {} if config is None else dict(config)
    allowed = {"feature_dim", "hidden_dim", "max_steps", "max_targets"}
    unknown = set(raw).difference(allowed)
    if unknown:
        raise ValueError("unknown DummyStudent option(s): " + ", ".join(sorted(unknown)))
    return DummyStudent(**raw)


__all__ = ["DummyStudent", "build_dummy_student"]
