"""The process-CPU sampler must not report physically impossible percentages.

The v3 soak on 2026-10-07 reported ``cpu_percent_max = 27009.8`` inside a
20-core container, because ``BackgroundMonitor.stop`` samples once right after
the monitor thread sampled, collapsing the measurement window to microseconds
while the CPU-time delta still covered the whole second.  These tests pin the
lock + minimum-window behaviour against a fake psutil.
"""
from __future__ import annotations

import sys
import time
import types

import pytest

from ..samplers import BackgroundMonitor


class _FakeProcess:
    """CPU time advances at ``rate`` cores, i.e. 100 * rate percent."""

    def __init__(self, rate: float) -> None:
        self.rate = rate
        self._start = time.monotonic()

    def cpu_times(self) -> tuple[float, float, float, float]:
        elapsed = time.monotonic() - self._start
        return (self.rate * elapsed, 0.0, 0.0, 0.0)


@pytest.fixture()
def fake_psutil(monkeypatch: pytest.MonkeyPatch):
    module = types.ModuleType("psutil")
    process = _FakeProcess(5.0)
    module.Process = lambda: process  # type: ignore[attr-defined]
    module.cpu_count = lambda logical=True: 20  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "psutil", module)
    return process


def test_first_call_is_a_baseline_not_a_measurement(fake_psutil) -> None:
    sampler = BackgroundMonitor._cpu_percent_sampler()
    assert sampler() == 0.0


def test_measured_value_is_bounded_by_core_count(fake_psutil) -> None:
    sampler = BackgroundMonitor._cpu_percent_sampler()
    sampler()
    time.sleep(0.2)
    value = sampler()
    assert value is not None
    assert 400.0 < value < 600.0, value  # 5 cores -> ~500%


def test_back_to_back_sample_repeats_the_reading_instead_of_spiking(fake_psutil) -> None:
    sampler = BackgroundMonitor._cpu_percent_sampler()
    sampler()
    time.sleep(0.2)
    measured = sampler()
    immediate = sampler()  # the stop()-right-after-loop race
    assert immediate == measured
    assert immediate <= 100.0 * sys.modules["psutil"].cpu_count()
    # the refused call must not consume the window
    time.sleep(0.2)
    after = sampler()
    assert after is not None and 400.0 < after < 600.0, after
