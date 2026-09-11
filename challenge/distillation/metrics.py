"""Per-head validation metrics for Student plans."""

from __future__ import annotations

import math
from typing import Mapping, Sequence

import torch
from torch import Tensor


def compute_batch_metrics(
    outputs: Mapping[str, Tensor],
    labels: Mapping[str, Tensor],
    sample_classes: Sequence[str],
) -> dict[str, float]:
    mask = labels["step_mask"].bool()
    speed_mask = labels["target_speed_mask"].bool() & mask
    behavior_correct = outputs["behavior_logits"].argmax(-1).eq(labels["behavior"])
    target_correct = outputs["target_pointer_logits"].argmax(-1).eq(labels["target_pointer"])
    lane_correct = outputs["target_lane_logits"].argmax(-1).eq(labels["target_lane"])
    completion_correct = outputs["completion_type_logits"].argmax(-1).eq(
        labels["completion_type"],
    )
    failure_correct = outputs["on_failure_logits"].argmax(-1).eq(labels["on_failure"])
    plan_length_correct = outputs["plan_length_logits"].argmax(-1).eq(labels["plan_length"])
    confirmation_correct = outputs["requires_confirmation_logits"].reshape(-1).ge(0).eq(
        labels["requires_confirmation"].bool(),
    )
    replan_predicted = outputs["replan_condition_logits"].ge(0)
    replan_truth = labels["replan_conditions"].bool()

    result = {
        "behavior_accuracy": _accuracy(behavior_correct, mask),
        "target_pointer_accuracy": _accuracy(target_correct, mask),
        "target_lane_accuracy": _accuracy(lane_correct, mask),
        "target_speed_mae": _masked_mae(
            outputs["target_speed_mps"], labels["target_speed_mps"], speed_mask,
        ),
        "completion_accuracy": _accuracy(completion_correct, mask),
        "failure_accuracy": _accuracy(failure_correct, mask),
        "plan_length_accuracy": plan_length_correct.float().mean().item(),
        "confirmation_accuracy": confirmation_correct.float().mean().item(),
        "replan_recall": _recall(replan_predicted, replan_truth),
    }
    per_sample_steps_correct = (
        behavior_correct & target_correct & lane_correct & completion_correct & failure_correct
    ) | ~mask
    sequence_correct = per_sample_steps_correct.all(dim=-1) & plan_length_correct
    result["plan_sequence_accuracy"] = sequence_correct.float().mean().item()

    safety_mask = torch.tensor(
        [item == "safety_critical" for item in sample_classes],
        dtype=torch.bool,
        device=mask.device,
    ).unsqueeze(-1) & mask
    result["safety_critical_behavior_recall"] = _accuracy(
        behavior_correct, safety_mask,
    )
    return result


def metric_denominators(
    labels: Mapping[str, Tensor], sample_classes: Sequence[str],
) -> dict[str, float]:
    mask = labels["step_mask"].bool()
    active = float(mask.sum().item())
    batch = float(mask.shape[0])
    speed = float((labels["target_speed_mask"].bool() & mask).sum().item())
    replan = float(labels["replan_conditions"].bool().sum().item())
    safety = float(sum(
        int(mask[index].sum().item())
        for index, value in enumerate(sample_classes)
        if value == "safety_critical"
    ))
    return {
        "behavior_accuracy": active,
        "target_pointer_accuracy": active,
        "target_lane_accuracy": active,
        "target_speed_mae": speed,
        "completion_accuracy": active,
        "failure_accuracy": active,
        "plan_length_accuracy": batch,
        "confirmation_accuracy": batch,
        "replan_recall": replan,
        "plan_sequence_accuracy": batch,
        "safety_critical_behavior_recall": safety,
    }


def average_metrics(
    rows: Sequence[Mapping[str, float]],
    weights: Sequence[Mapping[str, float]] | None = None,
) -> dict[str, float]:
    if not rows:
        return {}
    keys = set.intersection(*(set(row) for row in rows))
    weight_rows = weights or [{} for _ in rows]
    if len(weight_rows) != len(rows):
        raise ValueError("metric rows and weight rows must have the same length")
    result = {}
    for key in sorted(keys):
        pairs = [
            (float(row[key]), float(weight.get(key, 1.0)))
            for row, weight in zip(rows, weight_rows, strict=True)
        ]
        usable = [(value, weight) for value, weight in pairs if math.isfinite(value) and weight > 0]
        result[key] = (
            float("nan") if not usable
            else sum(value * weight for value, weight in usable) / sum(weight for _, weight in usable)
        )
    return result


def _accuracy(correct: Tensor, mask: Tensor) -> float:
    count = int(mask.sum().item())
    return float("nan") if count == 0 else (correct & mask).float().sum().item() / count


def _masked_mae(predicted: Tensor, target: Tensor, mask: Tensor) -> float:
    count = int(mask.sum().item())
    if count == 0:
        return float("nan")
    return (predicted.sub(target).abs() * mask).sum().item() / count


def _recall(predicted: Tensor, truth: Tensor) -> float:
    positives = int(truth.sum().item())
    return float("nan") if positives == 0 else (predicted & truth).sum().item() / positives


__all__ = ["average_metrics", "compute_batch_metrics", "metric_denominators"]
