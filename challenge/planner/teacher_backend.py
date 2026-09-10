"""Strict adapter around the frozen Qwen Teacher backend."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from runtime.interface_registry import InterfaceRegistry
from runtime.plan_validator import PlanValidator

from .common import validation_scene


class QwenTeacherBackend:
    """Validate both sides of an existing Qwen Planner V2 implementation."""

    def __init__(self, delegate: Any, *, registry: InterfaceRegistry | None = None) -> None:
        if not callable(getattr(delegate, "infer", None)):
            raise TypeError("delegate must provide infer(request)")
        self._delegate = delegate
        self._registry = registry or InterfaceRegistry()
        self._validator = PlanValidator(registry=self._registry)
        self.model_id = str(getattr(delegate, "model_id", "QWEN_TEACHER_UNKNOWN"))
        self.production_ready = bool(getattr(delegate, "production_ready", False))

    def infer(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        frozen_request = self._registry.validate("model_request", request)
        raw_plan = self._delegate.infer(frozen_request)
        return self._validator.validate(
            raw_plan,
            scene=validation_scene(frozen_request),
            expected_request_id=frozen_request["request_id"],
            expected_command_id=frozen_request["command_id"],
            now_ns=frozen_request["created_at_ns"],
            allow_confirmation=True,
        )

    def health(self) -> tuple[bool, str]:
        health = getattr(self._delegate, "health", None)
        if callable(health):
            ready, detail = health()
            return bool(ready), str(detail)
        return self.production_ready, f"teacher backend configured: {self.model_id}"


__all__ = ["QwenTeacherBackend"]

