"""Longitudinal speed PID operating exclusively in SI units."""

from __future__ import annotations

from dataclasses import dataclass
from .validation import finite


@dataclass(frozen=True, slots=True)
class PIDParameters:
    kp: float = 1.2
    ki: float = 0.15
    kd: float = 0.02
    integral_limit: float = 4.0
    accel_min_mps2: float = -5.0
    accel_max_mps2: float = 2.5
    target_step_reset_mps: float = 3.0

    def __post_init__(self) -> None:
        for name in ("kp", "ki", "kd"):
            finite(name, getattr(self, name), minimum=0.0)
        finite("integral_limit", self.integral_limit, positive=True)
        finite("accel_min_mps2", self.accel_min_mps2)
        finite("accel_max_mps2", self.accel_max_mps2, positive=True)
        finite("target_step_reset_mps", self.target_step_reset_mps, positive=True)
        if self.accel_min_mps2 >= self.accel_max_mps2:
            raise ValueError("accel_min_mps2 must be below accel_max_mps2")


class SpeedPID:
    """PID with bounded integral and conditional integration anti-windup."""

    def __init__(self, kp: float = 1.2, ki: float = 0.15, kd: float = 0.02,
                 integral_limit: float = 4.0, accel_min_mps2: float = -5.0,
                 accel_max_mps2: float = 2.5, target_step_reset_mps: float = 3.0) -> None:
        self.params = PIDParameters(kp, ki, kd, integral_limit, accel_min_mps2, accel_max_mps2, target_step_reset_mps)
        self.integral = 0.0
        self._previous_error: float | None = None
        self._previous_target: float | None = None

    def reset(self) -> None:
        self.integral = 0.0
        self._previous_error = None
        self._previous_target = None

    def step(self, target_speed_mps: float, speed_mps: float, dt_s: float) -> float:
        target_speed_mps = finite("target_speed_mps", target_speed_mps, minimum=0.0)
        speed_mps = finite("speed_mps", speed_mps, minimum=0.0)
        dt_s = finite("dt_s", dt_s, positive=True)
        if self._previous_target is not None and abs(target_speed_mps - self._previous_target) >= self.params.target_step_reset_mps:
            self.integral *= 0.25
        error = target_speed_mps - speed_mps
        derivative = 0.0 if self._previous_error is None else (error - self._previous_error) / dt_s
        candidate = max(-self.params.integral_limit, min(self.params.integral_limit, self.integral + error * dt_s))
        raw = self.params.kp * error + self.params.ki * candidate + self.params.kd * derivative
        clipped = max(self.params.accel_min_mps2, min(self.params.accel_max_mps2, raw))
        # Integrate only if it does not push an already saturated output farther out.
        if raw == clipped or (raw > clipped and error < 0.0) or (raw < clipped and error > 0.0):
            self.integral = candidate
        self._previous_error = error
        self._previous_target = target_speed_mps
        return clipped
