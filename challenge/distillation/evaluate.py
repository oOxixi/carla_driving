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
        weights = metric_denominators(moved["labels"], batch["sample_classes"])
        # Emit every class for every batch, including absent classes with zero
        # denominators. This keeps global aggregation correct across mixed batches.
        for sample_class in ("normal", "complex", "safety_critical"):
            selected = [
                index for index, value in enumerate(batch["sample_classes"])
                if value == sample_class
            ]
            subset_outputs = {name: value[selected] for name, value in outputs.items()}
            subset_labels = {name: value[selected] for name, value in moved["labels"].items()}
            subset_classes = [sample_class] * len(selected)
            class_metrics = compute_batch_metrics(
                subset_outputs, subset_labels, subset_classes,
            )
            class_weights = metric_denominators(subset_labels, subset_classes)
            for name, value in class_metrics.items():
                if name == "safety_critical_behavior_recall":
                    # The global safety slice already reports this quantity.
                    continue
                key = f"{sample_class}_{name}"
                metrics[key] = value
                weights[key] = class_weights[name]
        rows.append(metrics)
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
