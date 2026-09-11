"""Validation loop shared by smoke training and the future A1 Student."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import torch

from .metrics import average_metrics, compute_batch_metrics, metric_denominators
from .student_contract import forward_student, validate_student_outputs


@torch.no_grad()
def evaluate(
    model: torch.nn.Module,
    batches: Iterable[dict[str, Any]],
    loss_fn: torch.nn.Module,
    *,
    device: torch.device,
    max_targets: int,
) -> dict[str, float]:
    model.eval()
    rows = []
    weight_rows = []
    for batch in batches:
        moved = move_batch_to_device(batch, device)
        outputs = forward_student(model, moved["model_inputs"])
        validate_student_outputs(outputs, moved["labels"], max_targets=max_targets)
        total, components = loss_fn(outputs, moved["labels"])
        metrics = compute_batch_metrics(
            outputs, moved["labels"], batch["sample_classes"],
        )
        metrics["loss"] = float(total.item())
        metrics.update({f"loss_{key}": float(value.item()) for key, value in components.items()})
        rows.append(metrics)
        weights = metric_denominators(moved["labels"], batch["sample_classes"])
        batch_size = float(moved["labels"]["step_mask"].shape[0])
        weights.update({name: batch_size for name in metrics if name.startswith("loss")})
        weight_rows.append(weights)
    return average_metrics(rows, weight_rows)


def move_batch_to_device(batch: dict[str, Any], device: torch.device) -> dict[str, Any]:
    return {
        **batch,
        "model_inputs": {
            key: value.to(device) if torch.is_tensor(value) else value
            for key, value in batch["model_inputs"].items()
        },
        "labels": {
            key: value.to(device) if torch.is_tensor(value) else value
            for key, value in batch["labels"].items()
        },
    }


__all__ = ["evaluate", "move_batch_to_device"]
