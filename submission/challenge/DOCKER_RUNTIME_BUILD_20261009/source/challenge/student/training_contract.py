"""Executable padding and loss-mask rules for 1--4 step supervision."""

from __future__ import annotations

from collections.abc import Mapping

import torch
from torch import Tensor

from .contract import (
    BEHAVIOR_TO_ID,
    COMPLETION_TYPE_TO_ID,
    ON_FAILURE_TO_ID,
    StudentShapeContract,
    TARGET_LANE_TO_ID,
)


# Neutral values written into step slots at and after plan_length. The mask, not
# these values, is authoritative: padded slots must contribute zero step loss.
PAD_CLASS_INDICES: Mapping[str, int] = {
    "behavior": BEHAVIOR_TO_ID["HOLD"],
    "target_lane": TARGET_LANE_TO_ID["NONE"],
    "completion_type": COMPLETION_TYPE_TO_ID["HOLD_FRAMES"],
    "on_failure": ON_FAILURE_TO_ID["HOLD_CURRENT_LANE"],
}
PAD_TARGET_SPEED_MPS = 0.0


def plan_length_to_class(plan_length: Tensor, *, max_steps: int = 4) -> Tensor:
    """Map integer lengths 1..max_steps to zero-based classification labels."""
    _validate_plan_length(plan_length, max_steps=max_steps)
    return plan_length.to(dtype=torch.long) - 1


def build_step_mask(plan_length: Tensor, *, max_steps: int = 4) -> Tensor:
    """Return bool[B,max_steps], true only where step index < plan_length."""
    _validate_plan_length(plan_length, max_steps=max_steps)
    indices = torch.arange(max_steps, device=plan_length.device)
    return indices.unsqueeze(0) < plan_length.to(dtype=torch.long).unsqueeze(1)


def padded_target_pointer_index(
    contract: StudentShapeContract | None = None,
) -> int:
    """The extra pointer class after target indices 0..max_targets-1 means NONE."""
    return (contract or StudentShapeContract()).max_targets


def masked_step_mean(loss: Tensor, step_mask: Tensor) -> Tensor:
    """Reduce a per-step loss without letting padded slots affect training."""
    if loss.shape[:2] != step_mask.shape:
        raise ValueError("loss first two dimensions must match step_mask [B,max_steps]")
    mask = step_mask.to(dtype=loss.dtype)
    while mask.ndim < loss.ndim:
        mask = mask.unsqueeze(-1)
    expanded = mask.expand_as(loss)
    return (loss * expanded).sum() / expanded.sum().clamp_min(1.0)


def _validate_plan_length(plan_length: Tensor, *, max_steps: int) -> None:
    if plan_length.ndim != 1:
        raise ValueError("plan_length must be rank-1 [B]")
    if plan_length.dtype not in {
        torch.int8, torch.int16, torch.int32, torch.int64, torch.uint8,
    }:
        raise TypeError("plan_length must use an integer dtype")
    if bool(torch.any(plan_length < 1)) or bool(torch.any(plan_length > max_steps)):
        raise ValueError(f"plan_length values must be in [1,{max_steps}]")


__all__ = [
    "PAD_CLASS_INDICES", "PAD_TARGET_SPEED_MPS", "build_step_mask",
    "masked_step_mean", "padded_target_pointer_index", "plan_length_to_class",
]
