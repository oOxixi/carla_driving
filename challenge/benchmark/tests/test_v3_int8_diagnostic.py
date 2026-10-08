from __future__ import annotations

import pytest

from challenge.benchmark.metric_evidence import GATE_METRICS
from tools.run_v3_int8_diagnostic import (
    compare_metrics,
    pairwise_decode_diagnostics,
)


def _evidence(value: float) -> dict:
    return {
        "metrics": {
            name: {
                "value": 1.0 if name == "safety_critical_behavior_recall" else value,
                "numerator": 99,
                "denominator": 100,
            }
            for name in GATE_METRICS
        }
    }


def _record(*, speed: float, lane: str = "CURRENT") -> dict:
    return {
        "sample_id": "td_test",
        "status": "SUCCESS",
        "prediction": {
            "steps": [
                {
                    "behavior": "SLOW_DOWN",
                    "target": {
                        "target_id": "C-0001",
                        "target_lane": lane,
                        "target_speed_mps": speed,
                    },
                    "completion": {"type": "SPEED_BELOW"},
                }
            ]
        },
    }


def test_metric_comparison_applies_fixed_drop_limit() -> None:
    comparison, passed = compare_metrics(
        _evidence(1.0), _evidence(0.99), core_limit=0.01,
    )
    assert passed is True
    assert comparison["behavior_accuracy"]["absolute_drop"] == pytest.approx(0.01)
    assert comparison["behavior_accuracy"]["pass"] is True

    comparison, passed = compare_metrics(
        _evidence(1.0), _evidence(0.989), core_limit=0.01,
    )
    assert passed is False
    assert comparison["behavior_accuracy"]["pass"] is False


def test_pairwise_diagnostic_separates_semantics_from_speed_drift() -> None:
    report = pairwise_decode_diagnostics(
        [_record(speed=4.0)],
        [_record(speed=3.75)],
    )
    assert report["plan_gate_field_agreement"]["value"] == 1.0
    assert all(
        item["value"] == 1.0
        for item in report["step_field_agreement"].values()
    )
    assert report["target_speed_abs_delta_mps"] == {
        "count": 1,
        "mean": 0.25,
        "p95": 0.25,
        "max": 0.25,
    }


def test_pairwise_diagnostic_exposes_lane_mismatch() -> None:
    report = pairwise_decode_diagnostics(
        [_record(speed=4.0)],
        [_record(speed=4.0, lane="LEFT_ADJACENT")],
    )
    assert report["plan_gate_field_agreement"] == {
        "numerator": 0,
        "denominator": 1,
        "value": 0.0,
        "mismatched_sample_ids": ["td_test"],
    }
    assert report["step_field_agreement"]["target_lane"]["value"] == 0.0
