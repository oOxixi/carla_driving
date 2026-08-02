"""Cached strict validation for A-owned JSON interface files."""

from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Any, Mapping


INTERFACE_NAMES = frozenset({
    "driving_command",
    "model_request",
    "decision_plan",
    "perception_state",
    "control_command",
    "execution_feedback",
})


class InterfaceValidationError(ValueError):
    """One shared boundary payload failed its frozen V1 contract."""


class InterfaceRegistry:
    def __init__(self, root: str | Path | None = None) -> None:
        self.root = (
            Path(root).resolve()
            if root is not None
            else Path(__file__).resolve().parents[1] / "interfaces"
        )
        self._validators: dict[str, Any] = {}
        self._lock = Lock()

    def validate(self, name: str, payload: object) -> dict[str, Any]:
        if name not in INTERFACE_NAMES:
            raise ValueError(f"unknown interface: {name!r}")
        if not isinstance(payload, Mapping):
            raise InterfaceValidationError(f"{name} must be a JSON object")
        validator = self._validator(name)
        errors = sorted(validator.iter_errors(payload), key=lambda error: list(error.path))
        if errors:
            first = errors[0]
            location = ".".join(str(item) for item in first.absolute_path) or "<root>"
            raise InterfaceValidationError(f"{name}.{location}: {first.message}")
        # A JSON round-trip both detaches caller mutation and rejects NaN/objects.
        try:
            return json.loads(json.dumps(dict(payload), ensure_ascii=False, allow_nan=False))
        except (TypeError, ValueError) as error:
            raise InterfaceValidationError(f"{name} is not strict JSON: {error}") from error

    def _validator(self, name: str) -> Any:
        with self._lock:
            cached = self._validators.get(name)
            if cached is not None:
                return cached
            try:
                import jsonschema
            except ImportError as error:  # pragma: no cover - packaging guard
                raise RuntimeError("jsonschema is required for shared interface validation") from error
            path = self.root / f"{name}.schema.json"
            schema = json.loads(path.read_text(encoding="utf-8"))
            validator_type = jsonschema.validators.validator_for(schema)
            validator_type.check_schema(schema)
            validator = validator_type(schema)
            self._validators[name] = validator
            return validator


__all__ = [
    "INTERFACE_NAMES",
    "InterfaceRegistry",
    "InterfaceValidationError",
]
