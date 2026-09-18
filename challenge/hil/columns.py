"""Single source of truth for every raw evidence file column set.

The CSV headers are derived from these tuples, so a schema change and the code
that writes the files can never drift apart.  `cli schema` dumps them to
`schemas/*.columns.json` for reviewers who do not read Python.
"""

from __future__ import annotations

LATENCY_COLUMNS: tuple[str, ...] = (
    "run_id",
    "round",
    "phase",
    "case_id",
    "request_id",
    "outcome",
    "reason_code",
    "t0_input_arrival_ns",
    "t1_preprocess_end_ns",
    "t2_packing_end_ns",
    "t3_inference_start_ns",
    "t4_inference_end_ns",
    "t5_postprocess_end_ns",
    "t6_adapter_end_ns",
    "t7_plan_ready_ns",
    "preprocess_ms",
    "packing_ms",
    "inference_setup_ms",
    "model_inference_ms",
    "postprocess_ms",
    "adapter_ms",
    "plan_validation_ms",
    "pre_model_ms",
    "post_model_ms",
    "planner_e2e_ms",
    "model_only_ms",
    "planner_overhead_ms",
    "missing_stages",
    "stage_source",
    "outcome_detail",
    "model_id",
    "model_sha256",
    "config_id",
    "dataset_version",
    "git_sha",
    "wall_time_utc",
)

MEMORY_COLUMNS: tuple[str, ...] = (
    "run_id",
    "round",
    "sample_index",
    "wall_time_utc",
    "monotonic_ns",
    "scope",
    "rss_kib",
    "peak_rss_kib",
    "source",
    "notes",
)

POWER_COLUMNS: tuple[str, ...] = (
    "run_id",
    "round",
    "sample_index",
    "wall_time_utc",
    "monotonic_ns",
    "scope",
    "source",
    "probe_point",
    "voltage_v",
    "current_a",
    "power_w",
    "notes",
)

UTILIZATION_COLUMNS: tuple[str, ...] = (
    "run_id",
    "round",
    "sample_index",
    "wall_time_utc",
    "monotonic_ns",
    "scope",
    "source",
    "cpu_percent",
    "bpu_percent",
    "ddr_bandwidth_gbps",
    "notes",
)

SOAK_COLUMNS: tuple[str, ...] = (
    "wall_time_utc",
    "monotonic_ns",
    "iteration",
    "outcome",
    "latency_ms",
    "rss_kib",
    "power_w",
    "bpu_percent",
    "temperature_c",
    "notes",
)

REPLAY_COLUMNS: tuple[str, ...] = (
    "run_id",
    "round",
    "case_id",
    "sample_id",
    "scenario_id",
    "request_id",
    "outcome",
    "rgb_resolved",
    "rgb_sha256",
    "teacher_behavior_sequence",
    "student_behavior_sequence",
    "behavior_match_ratio",
    "teacher_target_sequence",
    "student_target_sequence",
    "target_match_ratio",
    "plan_step_count",
    "structural_failures",
    "diagnostic_only",
    "model_id",
    "model_sha256",
    "config_id",
    "dataset_version",
    "git_sha",
)

FILE_SCHEMAS: dict[str, tuple[str, ...]] = {
    "latency_raw": LATENCY_COLUMNS,
    "memory_raw": MEMORY_COLUMNS,
    "power_raw": POWER_COLUMNS,
    "utilization_raw": UTILIZATION_COLUMNS,
    "soak": SOAK_COLUMNS,
    "hil_replay": REPLAY_COLUMNS,
}

__all__ = [
    "LATENCY_COLUMNS",
    "MEMORY_COLUMNS",
    "POWER_COLUMNS",
    "UTILIZATION_COLUMNS",
    "SOAK_COLUMNS",
    "REPLAY_COLUMNS",
    "FILE_SCHEMAS",
]
