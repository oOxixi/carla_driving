"""Frozen ModelRequest V1 -> ManeuverPlan V2 backend boundary."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class PlannerBackend(Protocol):
    """The only planner substitution point used by the challenge track.

    Implementations may be the Qwen Teacher or the lightweight Student.  They
    must not emit low-level vehicle controls or modify the existing A/B/C/D
    execution chain.
    """

    model_id: str
    production_ready: bool

    def infer(self, request: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def health(self) -> tuple[bool, str]: ...


__all__ = ["PlannerBackend"]

