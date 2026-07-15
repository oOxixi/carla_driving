"""Strict numeric validation shared by C's public control APIs."""

from __future__ import annotations

import math


def finite(name: str, value: object, *, minimum: float | None = None,
           maximum: float | None = None, positive: bool = False) -> float:
    if type(value) not in (int, float):
        raise TypeError(f"{name} must be an int or float, not {type(value).__name__}")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    if positive and result <= 0.0:
        raise ValueError(f"{name} must be positive")
    if minimum is not None and result < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    if maximum is not None and result > maximum:
        raise ValueError(f"{name} must be <= {maximum}")
    return result
