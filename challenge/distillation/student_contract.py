"""Runtime gate for the A1 Student/A3 trainer handoff."""

from __future__ import annotations

from typing import Any, Mapping

import torch
from torch import Tensor

from .label_encoder import (
    BEHAVIORS,
    COMPLETION_TYPES,
    FAILURE_ACTIONS,
    REPLAN_CONDITIONS,
    TARGET_LANES,
)


def validate_student_outputs(
    outputs: Mapping[str, Tensor],
    labels: Mapping[str, Tensor],
    *,
    max_targets: int,
) -> None:
    """Raise a focused error before malformed Student heads reach the loss."""
    if not isinstance(outputs, Mapping):
        raise TypeError("Student forward must return a mapping of named heads")
    batch_size, max_steps = labels["step_mask"].shape
    expected = {
        "plan_length_logits": (batch_size, max_steps),
        "behavior_logits": (batch_size, max_steps, len(BEHAVIORS)),
        "target_pointer_logits": (batch_size, max_steps, max_targets + 1),
        "target_lane_logits": (batch_size, max_steps, len(TARGET_LANES)),
        "target_speed_mps": (batch_size, max_steps),
        "completion_type_logits": (batch_size, max_steps, len(COMPLETION_TYPES)),
        "on_failure_logits": (batch_size, max_steps, len(FAILURE_ACTIONS)),
        "confidence": (batch_size, 1),
        "requires_confirmation_logits": (batch_size, 1),
        "replan_condition_logits": (batch_size, len(REPLAN_CONDITIONS)),
    }
    missing = sorted(set(expected).difference(outputs))
    if missing:
        raise ValueError("Student output is missing head(s): " + ", ".join(missing))
    label_device = labels["step_mask"].device
    for name, shape in expected.items():
        value = outputs[name]
        if not torch.is_tensor(value):
            raise TypeError(f"Student head {name!r} must be a torch.Tensor")
        if tuple(value.shape) != tuple(shape):
            raise ValueError(
                f"Student head {name!r} has shape {tuple(value.shape)}; expected {shape}"
            )
        if not value.is_floating_point():
            raise TypeError(f"Student head {name!r} must use a floating dtype")
        if value.device != label_device:
            raise ValueError(
                f"Student head {name!r} is on {value.device}; labels are on {label_device}"
            )
        if not torch.isfinite(value).all():
            raise ValueError(f"Student head {name!r} contains NaN or infinity")


def validate_finite_gradients(model: torch.nn.Module) -> None:
    bad = []
    for name, parameter in model.named_parameters():
        if parameter.grad is not None and not torch.isfinite(parameter.grad).all():
            bad.append(name)
    if bad:
        raise RuntimeError("non-finite Student gradient(s): " + ", ".join(bad[:20]))


def forward_student(
    model: torch.nn.Module,
    model_inputs: Mapping[str, Any],
) -> Mapping[str, Tensor]:
    """Call either the frozen A1 four-input model or the D1 mapping-style dummy."""
    a1_names = ("rgb", "text_tokens", "targets", "state")
    if all(name in model_inputs for name in a1_names):
        return model(*(model_inputs[name] for name in a1_names))
    return model(model_inputs)


__all__ = ["forward_student", "validate_finite_gradients", "validate_student_outputs"]
