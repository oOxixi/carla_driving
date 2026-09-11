"""A1 Student V0 construction and fixed four-modal batch packing for A3."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import torch

from challenge.student import StudentPlannerV0, StudentPreprocessor, StudentShapeContract


class A1StudentInputPacker:
    def __init__(self, *, max_steps: int = 4, max_targets: int = 8) -> None:
        _require_frozen_shape(max_steps=max_steps, max_targets=max_targets)
        self.contract = StudentShapeContract(max_steps=max_steps, max_targets=max_targets)
        self.preprocessor = StudentPreprocessor(self.contract)

    def __call__(self, requests: Sequence[Mapping[str, Any]]) -> dict[str, torch.Tensor]:
        if not requests:
            raise ValueError("A1 input packer requires at least one ModelRequest")
        packed = [self.preprocessor(request) for request in requests]
        return {
            "rgb": torch.cat([item.rgb for item in packed], dim=0),
            "text_tokens": torch.cat([item.text_tokens for item in packed], dim=0),
            "targets": torch.cat([item.targets for item in packed], dim=0),
            "state": torch.cat([item.state for item in packed], dim=0),
        }


def build_a1_input_packer(
    config: Mapping[str, Any] | None = None,
) -> A1StudentInputPacker:
    raw = dict(config or {})
    unknown = set(raw).difference({"max_steps", "max_targets"})
    if unknown:
        raise ValueError("unknown A1 input option(s): " + ", ".join(sorted(unknown)))
    return A1StudentInputPacker(**raw)


def build_a1_student(config: Mapping[str, Any] | None = None) -> StudentPlannerV0:
    raw = dict(config or {})
    unknown = set(raw).difference({"max_steps", "max_targets"})
    if unknown:
        raise ValueError("unknown A1 Student option(s): " + ", ".join(sorted(unknown)))
    max_steps = int(raw.get("max_steps", 4))
    max_targets = int(raw.get("max_targets", 8))
    _require_frozen_shape(max_steps=max_steps, max_targets=max_targets)
    return StudentPlannerV0(
        contract=StudentShapeContract(max_steps=max_steps, max_targets=max_targets),
    )


def _require_frozen_shape(*, max_steps: int, max_targets: int) -> None:
    if int(max_steps) != 4 or int(max_targets) != 8:
        raise ValueError("A1 Student V0 is frozen at max_steps=4 and max_targets=8")


__all__ = ["A1StudentInputPacker", "build_a1_input_packer", "build_a1_student"]
