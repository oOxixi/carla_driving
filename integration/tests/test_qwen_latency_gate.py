from __future__ import annotations

import pytest

from tools.run_qwen_latency_gate import (
    latency_gate_exit_code,
    summarize_latency_gate,
)


def test_latency_gate_reports_interpolated_p95_and_early_stop() -> None:
    report = summarize_latency_gate(
        [100.0, 200.0, 300.0, 400.0, 500.0],
        threshold_ms=300.0,
    )

    assert report == {
        "count": 5,
        "mean_ms": 300.0,
        "p50_ms": 300.0,
        "p95_ms": pytest.approx(480.0),
        "max_ms": 500.0,
        "threshold_ms": 300.0,
        "status": "EARLY_STOP",
        "run_correctness_next": False,
    }
    assert latency_gate_exit_code(report) == 2


def test_latency_gate_allows_correctness_only_after_latency_passes() -> None:
    report = summarize_latency_gate(
        [210.0, 220.0, 230.0, 240.0, 250.0],
        threshold_ms=300.0,
    )

    assert report["p95_ms"] == pytest.approx(248.0)
    assert report["status"] == "PASS"
    assert report["run_correctness_next"] is True
    assert latency_gate_exit_code(report) == 0
