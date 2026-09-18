from __future__ import annotations

import pytest

from ..stages import (
    STAGES,
    LatencyCollector,
    StageOrderError,
    StageTrace,
    percentile,
    summarize,
)


def _full_trace(**kwargs):
    trace = StageTrace(trace_id="t1", **kwargs)
    for index, stage in enumerate(STAGES):
        trace.mark(stage, timestamp_ns=1_000_000 * (index + 1))
    trace.finish("READY")
    return trace


def test_segment_math_matches_the_schema():
    durations = _full_trace().durations_ms()
    assert durations["planner_e2e_ms"] == pytest.approx(7.0)
    assert durations["model_only_ms"] == pytest.approx(1.0)
    assert durations["planner_overhead_ms"] == pytest.approx(6.0)
    assert durations["preprocess_ms"] == pytest.approx(1.0)
    assert durations["plan_validation_ms"] == pytest.approx(1.0)


def test_stage_order_is_enforced():
    trace = StageTrace(trace_id="t")
    trace.mark("packing_end", timestamp_ns=10)
    with pytest.raises(StageOrderError):
        trace.mark("preprocess_end", timestamp_ns=20)


def test_timestamps_must_not_decrease():
    trace = StageTrace(trace_id="t")
    trace.mark("input_arrival", timestamp_ns=100)
    with pytest.raises(StageOrderError):
        trace.mark("preprocess_end", timestamp_ns=50)


def test_duplicate_mark_is_rejected():
    trace = StageTrace(trace_id="t")
    trace.mark("input_arrival", timestamp_ns=1)
    with pytest.raises(StageOrderError):
        trace.mark("input_arrival", timestamp_ns=2)


def test_unfinished_trace_cannot_be_collected():
    trace = StageTrace(trace_id="t")
    trace.mark("input_arrival")
    with pytest.raises(ValueError):
        LatencyCollector().add(trace)


def test_percentile_is_linear_interpolation():
    assert percentile([0.0, 10.0], 0.5) == pytest.approx(5.0)
    assert percentile([1.0], 0.95) == 1.0
    assert percentile([], 0.5) is None
    assert summarize([])["count"] == 0


def test_partial_trace_reports_missing_stages_without_zero_filling():
    trace = StageTrace(trace_id="t", case_id="c", round_index=2)
    trace.mark("input_arrival", timestamp_ns=1_000)
    trace.mark("inference_start", timestamp_ns=2_000)
    trace.mark("inference_end", timestamp_ns=3_000)
    trace.finish("ERROR", reason_code="BOOM")
    row = trace.to_csv_row(run_id="r", identity={"model_id": "m"})
    assert row["t4_inference_end_ns"] == 3_000
    assert row["t7_plan_ready_ns"] == ""
    assert row["planner_e2e_ms"] == ""
    assert row["model_only_ms"] == pytest.approx(0.001)
    assert "plan_ready" in row["missing_stages"]
    assert row["model_id"] == "m"


def test_collector_only_counts_ready_measured_rows():
    collector = LatencyCollector()
    collector.add(_full_trace(case_id="measured", round_index=1))
    collector.add(_full_trace(case_id="warm", round_index=0, phase="warmup"))
    rejected = StageTrace(trace_id="rej", round_index=1)
    rejected.mark("input_arrival", timestamp_ns=1)
    rejected.finish("REJECTED")
    collector.add(rejected)
    report = collector.report(run_id="r", identity={})
    assert report["measured_ready_count"] == 1
    assert report["warmup_count"] == 1
    assert report["outcome_counts"] == {"READY": 2, "REJECTED": 1}
    assert report["metrics_ms"]["planner_e2e_ms"]["count"] == 1
