"""PyTorch Student backend implementing the frozen planner boundary."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
from pathlib import Path
from typing import Any

import torch

from challenge.student.model import StudentPlannerV0
from challenge.student.preprocess import StudentPreprocessor
from runtime.interface_registry import InterfaceRegistry
from runtime.plan_validator import PlanValidator

from .common import validation_scene
from .frozen_contracts import assert_frozen_contracts
from .student_adapter import StudentPlanAdapter


class StudentBackend:
    model_id = StudentPlannerV0.model_id

    def __init__(
        self,
        model: StudentPlannerV0 | None = None,
        *,
        weights: str | Path | None = None,
        weights_manifest: str | Path | None = None,
        registry: InterfaceRegistry | None = None,
    ) -> None:
        self.model = model or StudentPlannerV0()
        self.model_id = str(getattr(self.model, "model_id", StudentPlannerV0.model_id))
        self.production_ready = False
        self._readiness_detail = "Student V0 structure is ready; A3-gated weights are not loaded"
        if weights_manifest is not None and weights is None:
            raise ValueError("weights_manifest requires weights")
        if weights is not None:
            weights_path = Path(weights)
            manifest = None
            if weights_manifest is not None:
                manifest = validate_weight_manifest(
                    weights_path,
                    Path(weights_manifest),
                    expected_model_id=self.model_id,
                )
            payload = torch.load(weights_path, map_location="cpu", weights_only=True)
            self.model.load_state_dict(payload)
            self._readiness_detail = "weights loaded without an A3 FP32 Gate manifest"
            if manifest is not None:
                self.production_ready = True
                self._readiness_detail = (
                    f"A3-gated Student weights loaded: {manifest['weights_sha256']}"
                )
        self.model.eval()
        self._registry = registry or InterfaceRegistry()
        assert_frozen_contracts(self._registry)
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
            return False, self._readiness_detail
        return True, f"Student planner ready: {self.model_id}"


def validate_weight_manifest(
    weights: str | Path,
    manifest_path: str | Path,
    *,
    expected_model_id: str,
) -> dict[str, Any]:
    path = Path(weights)
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    required = {
        "git_sha", "model_id", "weights_sha256", "dataset_version",
        "config_id", "gate_status",
    }
    missing = sorted(required.difference(manifest))
    if missing:
        raise ValueError(f"weight manifest missing candidate identity fields: {missing}")
    if manifest.get("model_id") != expected_model_id:
        raise ValueError("weight manifest model_id does not match Student structure")
    if manifest.get("gate_status") != "A3_FP32_GATE_PASSED":
        raise ValueError("weight manifest has not passed the A3 FP32 Gate")
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if manifest.get("weights_sha256") != actual:
        raise ValueError("weight manifest SHA256 does not match weights")
    return manifest


__all__ = ["StudentBackend", "validate_weight_manifest"]
