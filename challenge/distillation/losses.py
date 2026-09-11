"""Masked, risk-weighted multi-head distillation objective."""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any, Mapping

import torch
from torch import Tensor, nn
import torch.nn.functional as F


@dataclass(frozen=True, slots=True)
class LossWeights:
    behavior: float = 2.0
    target_pointer: float = 1.5
    target_lane: float = 0.5
    target_speed: float = 0.5
    completion: float = 0.5
    on_failure: float = 0.3
    confidence: float = 0.2
    replan: float = 0.2
    plan_length: float = 0.5
    requires_confirmation: float = 0.2

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any] | None) -> "LossWeights":
        raw = {} if value is None else dict(value)
        names = {item.name for item in fields(cls)}
        unknown = set(raw).difference(names)
        if unknown:
            raise ValueError("unknown loss weight(s): " + ", ".join(sorted(unknown)))
        result = cls(**{key: float(item) for key, item in raw.items()})
        if any(getattr(result, name) < 0.0 for name in names):
            raise ValueError("loss weights must be non-negative")
        return result


class MultiHeadDistillationLoss(nn.Module):
    """Compute hard-label losses and optional Teacher probability KL terms."""

    def __init__(
        self,
        weights: LossWeights | None = None,
        *,
        soft_alpha: float = 0.0,
        temperature: float = 1.0,
        class_weights: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__()
        self.weights = weights or LossWeights()
        if not 0.0 <= float(soft_alpha) <= 1.0:
            raise ValueError("soft_alpha must be in [0, 1]")
        if float(temperature) <= 0.0:
            raise ValueError("temperature must be positive")
        self.soft_alpha = float(soft_alpha)
        self.temperature = float(temperature)
        allowed_class_weights = {
            "behavior", "target_pointer", "target_lane", "completion",
            "on_failure", "plan_length",
        }
        raw_class_weights = dict(class_weights or {})
        unknown = set(raw_class_weights).difference(allowed_class_weights)
        if unknown:
            raise ValueError("unknown class weight head(s): " + ", ".join(sorted(unknown)))
        self.class_weights = {
            name: torch.as_tensor(value, dtype=torch.float32)
            for name, value in raw_class_weights.items()
        }
        if any(
            tensor.ndim != 1 or not torch.isfinite(tensor).all() or (tensor <= 0).any()
            for tensor in self.class_weights.values()
        ):
            raise ValueError("class weights must be finite positive vectors")

    def forward(
        self,
        outputs: Mapping[str, Tensor],
        labels: Mapping[str, Tensor],
    ) -> tuple[Tensor, dict[str, Tensor]]:
        step_mask = labels["step_mask"].bool()
        speed_mask = labels["target_speed_mask"].bool() & step_mask
        sample_weight = labels["sample_weight"].float()

        behavior = _masked_cross_entropy(
            outputs["behavior_logits"], labels["behavior"], step_mask, sample_weight,
            self._class_weight("behavior", outputs["behavior_logits"]),
        )
        behavior = self._mix_soft(
            behavior, outputs["behavior_logits"], labels.get("behavior_soft_probs"),
            step_mask, sample_weight,
        )
        target_pointer = _masked_cross_entropy(
            outputs["target_pointer_logits"], labels["target_pointer"],
            step_mask, sample_weight,
            self._class_weight("target_pointer", outputs["target_pointer_logits"]),
        )
        target_pointer = self._mix_soft(
            target_pointer, outputs["target_pointer_logits"],
            labels.get("target_pointer_soft_probs"), step_mask, sample_weight,
        )
        components = {
            "behavior": behavior,
            "target_pointer": target_pointer,
            "target_lane": _masked_cross_entropy(
                outputs["target_lane_logits"], labels["target_lane"],
                step_mask, sample_weight,
                self._class_weight("target_lane", outputs["target_lane_logits"]),
            ),
            "target_speed": _masked_smooth_l1(
                outputs["target_speed_mps"], labels["target_speed_mps"],
                speed_mask, sample_weight,
            ),
            "completion": _masked_cross_entropy(
                outputs["completion_type_logits"], labels["completion_type"],
                step_mask, sample_weight,
                self._class_weight("completion", outputs["completion_type_logits"]),
            ),
            "on_failure": _masked_cross_entropy(
                outputs["on_failure_logits"], labels["on_failure"],
                step_mask, sample_weight,
                self._class_weight("on_failure", outputs["on_failure_logits"]),
            ),
            "confidence": _weighted_mean(
                F.smooth_l1_loss(
                    outputs["confidence"].reshape(-1),
                    labels["confidence"].reshape(-1), reduction="none",
                ),
                torch.ones_like(sample_weight, dtype=torch.bool), sample_weight,
            ),
            "replan": _weighted_multilabel_bce(
                outputs["replan_condition_logits"],
                labels["replan_conditions"], sample_weight,
            ),
            "plan_length": _weighted_vector_cross_entropy(
                outputs["plan_length_logits"], labels["plan_length"], sample_weight,
                self._class_weight("plan_length", outputs["plan_length_logits"]),
            ),
            "requires_confirmation": _weighted_mean(
                F.binary_cross_entropy_with_logits(
                    outputs["requires_confirmation_logits"].reshape(-1),
                    labels["requires_confirmation"].reshape(-1), reduction="none",
                ),
                torch.ones_like(sample_weight, dtype=torch.bool), sample_weight,
            ),
        }
        total = sum(
            getattr(self.weights, name) * value
            for name, value in components.items()
        )
        return total, components

    def _class_weight(self, name: str, logits: Tensor) -> Tensor | None:
        value = self.class_weights.get(name)
        if value is None:
            return None
        if value.numel() != logits.shape[-1]:
            raise ValueError(
                f"class weights for {name!r} have {value.numel()} values; "
                f"expected {logits.shape[-1]}"
            )
        return value.to(device=logits.device, dtype=logits.dtype)

    def _mix_soft(
        self,
        hard_loss: Tensor,
        logits: Tensor,
        teacher_probs: Tensor | None,
        mask: Tensor,
        sample_weight: Tensor,
    ) -> Tensor:
        if teacher_probs is None or self.soft_alpha <= 0.0:
            return hard_loss
        if teacher_probs.shape != logits.shape:
            raise ValueError("Teacher soft probabilities must match Student logits")
        temperature = self.temperature
        safe_teacher = teacher_probs.float().clamp_min(1e-8)
        safe_teacher = safe_teacher / safe_teacher.sum(dim=-1, keepdim=True)
        kl = F.kl_div(
            F.log_softmax(logits / temperature, dim=-1),
            safe_teacher,
            reduction="none",
        ).sum(dim=-1) * temperature * temperature
        soft_loss = _weighted_mean(kl, mask, sample_weight)
        return (1.0 - self.soft_alpha) * hard_loss + self.soft_alpha * soft_loss


def _masked_cross_entropy(
    logits: Tensor,
    targets: Tensor,
    mask: Tensor,
    sample_weight: Tensor,
    class_weight: Tensor | None = None,
) -> Tensor:
    if logits.shape[:-1] != targets.shape or targets.shape != mask.shape:
        raise ValueError("masked classification tensors have incompatible shapes")
    raw = F.cross_entropy(
        logits.reshape(-1, logits.shape[-1]), targets.reshape(-1),
        weight=class_weight, reduction="none",
    ).reshape_as(targets)
    return _weighted_mean(raw, mask, sample_weight)


def _masked_smooth_l1(
    predicted: Tensor,
    target: Tensor,
    mask: Tensor,
    sample_weight: Tensor,
) -> Tensor:
    if predicted.shape != target.shape or target.shape != mask.shape:
        raise ValueError("masked regression tensors have incompatible shapes")
    raw = F.smooth_l1_loss(predicted, target, reduction="none")
    return _weighted_mean(raw, mask, sample_weight)


def _weighted_mean(values: Tensor, mask: Tensor, sample_weight: Tensor) -> Tensor:
    if values.shape != mask.shape or values.shape[0] != sample_weight.shape[0]:
        raise ValueError("weighted loss tensors have incompatible shapes")
    weights = sample_weight
    while weights.ndim < values.ndim:
        weights = weights.unsqueeze(-1)
    effective = mask.to(values.dtype) * weights
    denominator = effective.sum()
    if denominator.item() <= 0.0:
        return values.sum() * 0.0
    return (values * effective).sum() / denominator


def _weighted_vector_cross_entropy(
    logits: Tensor, targets: Tensor, sample_weight: Tensor,
    class_weight: Tensor | None = None,
) -> Tensor:
    raw = F.cross_entropy(logits, targets, weight=class_weight, reduction="none")
    return _weighted_mean(raw, torch.ones_like(raw, dtype=torch.bool), sample_weight)


def _weighted_multilabel_bce(
    logits: Tensor, targets: Tensor, sample_weight: Tensor,
) -> Tensor:
    if logits.shape != targets.shape:
        raise ValueError("replan tensors have incompatible shapes")
    raw = F.binary_cross_entropy_with_logits(logits, targets, reduction="none").mean(dim=-1)
    return _weighted_mean(raw, torch.ones_like(raw, dtype=torch.bool), sample_weight)


__all__ = ["LossWeights", "MultiHeadDistillationLoss"]
