"""PyTorch Student backend implementing the frozen planner boundary."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import torch

from challenge.student.model import StudentPlannerV0
from challenge.student.preprocess import StudentPreprocessor
from runtime.interface_registry import InterfaceRegistry
from runtime.plan_validator import PlanValidator

from .common import validation_scene
from .student_adapter import StudentPlanAdapter


class StudentBackend:
    model_id = StudentPlannerV0.model_id

    def __init__(
        self,
        model: StudentPlannerV0 | None = None,
        *,
        weights: str | Path | None = None,
        trained: bool = False,
        registry: InterfaceRegistry | None = None,
    ) -> None:
        self.model = model or StudentPlannerV0()
        if weights is not None:
            payload = torch.load(Path(weights), map_location="cpu", weights_only=True)
            self.model.load_state_dict(payload)
        self.model.eval()
        self.production_ready = bool(trained)
        self._registry = registry or InterfaceRegistry()
        self._validator = PlanValidator(registry=self._registry)
        self._preprocess = StudentPreprocessor(self.model.contract)
        self._adapter = StudentPlanAdapter(model_id=self.model_id)

    def infer(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        frozen_request = self._registry.validate("model_request", request)
        tensorized = self._preprocess(frozen_request)
        with torch.inference_mode():
            outputs = self.model(*tensorized.as_tuple())
        plan = self._adapter.decode(frozen_request, outputs)
        return self._validator.validate(
            plan,
            scene=validation_scene(frozen_request),
            expected_request_id=frozen_request["request_id"],
            expected_command_id=frozen_request["command_id"],
            now_ns=frozen_request["created_at_ns"],
            allow_confirmation=True,
        )

    def health(self) -> tuple[bool, str]:
        if not self.production_ready:
            return False, "Student V0 structure is ready; trained A3 weights are not loaded"
        return True, f"Student planner ready: {self.model_id}"


__all__ = ["StudentBackend"]

