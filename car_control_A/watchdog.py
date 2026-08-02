"""Narrow runtime health fail-safe, deliberately not D's safety arbiter."""

from __future__ import annotations

import math

from .contracts import ControlOutput


class RuntimeWatchdog:
    def __init__(self, *, timeout_s: float = 1.0, required_modules: tuple[str, ...] = (),
                 startup_grace_s: float = 0.0, started_at_s: float = 0.0) -> None:
        if timeout_s <= 0.0 or startup_grace_s < 0.0 or started_at_s < 0.0:
            raise ValueError("timeout_s must be positive; grace and start must be non-negative")
        if any(type(module) is not str or not module for module in required_modules):
            raise ValueError("required_modules must contain non-empty strings")
        self._timeout_s = float(timeout_s)
        self._required_modules = frozenset(required_modules)
        self._startup_deadline_s = float(started_at_s) + float(startup_grace_s) + self._timeout_s
        self._heartbeats: dict[str, float] = {}
        self._paused_at_s: float | None = None

    @staticmethod
    def _time(value: float, name: str) -> float:
        converted = float(value)
        if not math.isfinite(converted) or converted < 0.0:
            raise ValueError(f"{name} must be finite and non-negative")
        return converted

    def heartbeat(self, module: str, *, now_s: float) -> None:
        if type(module) is not str or not module:
            raise ValueError("module must be a non-empty string")
        if self._paused_at_s is not None:
            raise RuntimeError("cannot record a heartbeat while watchdog is paused")
        self._heartbeats[module] = self._time(now_s, "now_s")

    def pause(self, *, now_s: float) -> None:
        """Exclude an external wait during which the controlled system is frozen.

        CARLA synchronous ``world.tick()`` can block in the renderer while
        simulation time does not advance.  Counting that wait as a B/C/D
        module outage creates a false permanent stop.  The caller must bracket
        only the simulator/pacing wait; control, perception and logging remain
        inside the active watchdog interval.
        """
        if self._paused_at_s is not None:
            raise RuntimeError("watchdog is already paused")
        self._paused_at_s = self._time(now_s, "now_s")

    def resume(self, *, now_s: float) -> None:
        if self._paused_at_s is None:
            raise RuntimeError("watchdog is not paused")
        resumed_at_s = self._time(now_s, "now_s")
        if resumed_at_s < self._paused_at_s:
            raise ValueError("resume time must not precede pause time")
        paused_s = resumed_at_s - self._paused_at_s
        self._startup_deadline_s += paused_s
        for module in tuple(self._heartbeats):
            self._heartbeats[module] += paused_s
        self._paused_at_s = None

    def check(self, *, now_s: float) -> ControlOutput | None:
        if self._paused_at_s is not None:
            raise RuntimeError("cannot check watchdog while it is paused")
        checked_at_s = self._time(now_s, "now_s")
        if checked_at_s >= self._startup_deadline_s and any(module not in self._heartbeats for module in self._required_modules):
            return self._full_brake()
        if any(checked_at_s - timestamp > self._timeout_s for timestamp in self._heartbeats.values()):
            return self._full_brake()
        return None

    def module_failed(self, module: str, error: BaseException) -> ControlOutput:
        if type(module) is not str or not module:
            raise ValueError("module must be a non-empty string")
        return self._full_brake()

    @staticmethod
    def _full_brake() -> ControlOutput:
        return ControlOutput(throttle=0.0, brake=1.0, steer=0.0)
