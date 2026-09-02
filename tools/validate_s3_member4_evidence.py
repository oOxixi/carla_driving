"""Validate member-4 S3 emergency-chain evidence from a real CARLA run."""
from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Mapping
import json
from pathlib import Path
from typing import Any


SCENARIO_ID = "OFFICIAL_S3_EXTREME_EMERGENCY_6KM"
REQUIRED_EVENTS = {"cut_in_vehicle", "emergency_pedestrian"}
REQUIRED_ROUTES = {"QWEN_PLAN": 2, "FAST_LOCAL": 2}


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain one JSON object")
    return value


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number} must contain one JSON object")
        records.append(value)
    if not records:
        raise ValueError(f"{path} contains no evidence records")
    return records


def _extension_check(extension: Mapping[str, Any], key: str) -> Mapping[str, Any] | None:
    checks = extension.get("checks", ())
    if not isinstance(checks, list):
        return None
    return next(
        (item for item in checks if isinstance(item, Mapping) and item.get("key") == key),
        None,
    )


def validate_evidence(
    summary: Mapping[str, Any],
    records: list[Mapping[str, Any]],
    *,
    functional_only: bool = False,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def check(
        key: str,
        passed: bool,
        actual: Any,
        required: Any,
        *,
        category: str = "functional",
    ) -> None:
        checks.append({
            "key": key,
            "category": category,
            "status": "PASS" if passed else "FAIL",
            "actual": actual,
            "required": required,
        })

    start = next((item for item in records if item.get("record_type") == "run_start"), {})
    config = start.get("config", {}) if isinstance(start.get("config"), Mapping) else {}
    identifiers = {key: config.get(key) for key in ("seed", "code_version", "config_path")}
    model_id = str(config.get("qwen_model", ""))
    check("scenario_id", summary.get("scenario_id") == SCENARIO_ID, summary.get("scenario_id"), SCENARIO_ID)
    check("run_status", summary.get("status") == "SUCCEEDED", summary.get("status"), "SUCCEEDED")
    check(
        "required_identifiers",
        all(value not in (None, "", "UNKNOWN") for value in identifiers.values()),
        identifiers,
        "seed, code_version and config_path are present",
    )
    check("qwen_7b_model", "7B" in model_id.upper(), model_id, "existing 7B service model")

    command_records = [item for item in records if item.get("record_type") == "command"]
    external = [item for item in command_records if item.get("disposition") != "INTERNAL_QWEN_WAIT_STOP"]
    command_ids = [str(item.get("command_id", "")) for item in external]
    terminals = summary.get("command_terminal_statuses", {})
    terminals = terminals if isinstance(terminals, Mapping) else {}
    terminal_map = {command_id: terminals.get(command_id) for command_id in command_ids}
    accepted_terminals = {"SUCCEEDED", "SAFETY_OVERRIDE"}
    check("external_command_count", len(command_ids) == 4, len(command_ids), 4)
    check(
        "all_commands_succeeded",
        bool(command_ids) and all(status in accepted_terminals for status in terminal_map.values()),
        terminal_map,
        "four commands each have one SUCCEEDED or safety-preempted terminal",
    )

    acceptance = summary.get("acceptance", {})
    metrics = acceptance.get("metrics", {}) if isinstance(acceptance, Mapping) else {}
    metrics = metrics if isinstance(metrics, Mapping) else {}
    qwen = metrics.get("qwen_acceptance", {})
    qwen = qwen if isinstance(qwen, Mapping) else {}
    observed = qwen.get("observed", {}) if isinstance(qwen.get("observed"), Mapping) else {}
    route_counts = dict(Counter(str(item).upper() for item in observed.get("routes", ())))
    check("qwen_contract", qwen.get("passed") is True, qwen.get("failures"), [])
    check("qwen_call_count", observed.get("qwen_calls") == 2, observed.get("qwen_calls"), 2)
    check("mixed_route_counts", route_counts == REQUIRED_ROUTES, route_counts, REQUIRED_ROUTES)

    extension = metrics.get("extension_acceptance", {})
    extension = extension if isinstance(extension, Mapping) else {}
    evidence = extension.get("evidence", {}) if isinstance(extension.get("evidence"), Mapping) else {}
    events = evidence.get("emergency_events", {}) if isinstance(evidence.get("emergency_events"), Mapping) else {}
    check("extension_acceptance", extension.get("passed") is True, extension.get("failed_keys"), [])
    for key in (
        "expected_phase_count", "all_phases_must_complete",
        "required_emergency_event_ids", "required_emergency_recovery_ids",
        "emergency_response_p95_max_ms",
        "emergency_response_absolute_max_ms",
    ):
        item = _extension_check(extension, key)
        check(
            f"extension_{key}",
            item is not None and item.get("status") == "PASS",
            None if item is None else item.get("actual"),
            "PASS",
        )

    complete_event_fields = (
        "danger_timestamp_s", "perception_timestamp_s", "decision_timestamp_s",
        "safety_override_timestamp_s", "control_effect_timestamp_s", "response_ms",
    )
    event_completeness = {}
    for actor_id, event in events.items():
        if not isinstance(event, Mapping):
            continue
        values = [event.get(field) for field in complete_event_fields]
        complete = all(value is not None for value in values)
        timestamps = values[:-1]
        monotonic = complete and all(
            float(previous) <= float(current)
            for previous, current in zip(timestamps, timestamps[1:])
        )
        event_completeness[actor_id] = bool(complete and monotonic)
    check(
        "emergency_event_timestamps",
        REQUIRED_EVENTS.issubset(event_completeness) and all(
            event_completeness[actor_id] for actor_id in REQUIRED_EVENTS
        ),
        event_completeness,
        f"complete timestamps for {sorted(REQUIRED_EVENTS)}",
    )

    frames = [item for item in records if item.get("record_type") == "frame"]
    latency_samples = [
        item.get("latency", {}).get("sensor_to_control_ms")
        for item in frames if isinstance(item.get("latency"), Mapping)
    ]
    check(
        "frame_sensor_to_control_logged",
        bool(latency_samples) and all(isinstance(value, (int, float)) for value in latency_samples),
        len([value for value in latency_samples if isinstance(value, (int, float))]),
        f"all {len(frames)} frame records",
    )
    has_ttc = any(
        isinstance(item.get("longitudinal"), Mapping)
        and isinstance(item["longitudinal"].get("risk"), Mapping)
        and isinstance(item["longitudinal"]["risk"].get("ttc_s"), (int, float))
        for item in frames
    )
    check("ttc_logged", has_ttc, has_ttc, True)

    qwen_trajectories = [item for item in records if item.get("record_type") == "qwen_trajectory"]
    check("qwen_trajectory_count", len(qwen_trajectories) == 2, len(qwen_trajectories), 2)
    check("collision_count", summary.get("collision_count") == 0, summary.get("collision_count"), 0)
    violations = sum(int(summary.get(key, 0) or 0) for key in (
        "lane_invasion_count", "red_light_violation_count", "serious_route_deviation",
    ))
    check("traffic_violation_count", violations == 0, violations, 0)
    check(
        "safety_override_observed",
        int(summary.get("safety_override_frames", 0) or 0) > 0,
        summary.get("safety_override_frames"),
        "> 0",
    )
    hold_durations = {
        actor_id: event.get("hold_duration_s")
        for actor_id, event in events.items() if isinstance(event, Mapping)
    }
    check(
        "stop_hold",
        metrics.get("emergency_brake_seen") is True
        and REQUIRED_EVENTS.issubset(hold_durations)
        and all(
            isinstance(hold_durations[actor_id], (int, float))
            and float(hold_durations[actor_id]) >= 2.0
            for actor_id in REQUIRED_EVENTS
        ),
        {"emergency_brake_seen": metrics.get("emergency_brake_seen"), "hold_duration_s": hold_durations},
        "full brake observed and each emergency held for >= 2.0 s before recovery",
    )

    semantic_alignment = 1.0 if (
        qwen.get("passed") is True
        and extension.get("passed") is True
        and len(command_ids) == 4
        and all(status in accepted_terminals for status in terminal_map.values())
    ) else 0.0
    check("semantic_alignment", semantic_alignment >= 0.97, semantic_alignment, ">= 0.97")

    response_p95 = evidence.get("emergency_response_p95_ms")
    response_max = evidence.get("emergency_response_max_ms")
    check(
        "emergency_response_p95_ms",
        isinstance(response_p95, (int, float)) and float(response_p95) <= 100.0,
        response_p95,
        "<= 100.0",
        category="performance",
    )
    check(
        "emergency_response_max_ms",
        isinstance(response_max, (int, float)) and float(response_max) <= 120.0,
        response_max,
        "<= 120.0",
        category="performance",
    )

    functional_failed = [
        item["key"] for item in checks
        if item["category"] == "functional" and item["status"] == "FAIL"
    ]
    performance_failed = [
        item["key"] for item in checks
        if item["category"] == "performance" and item["status"] == "FAIL"
    ]
    blocking_failed = functional_failed + ([] if functional_only else performance_failed)
    return {
        "scenario_id": summary.get("scenario_id"),
        "evaluation_profile": "functional" if functional_only else "competition",
        "passed": not blocking_failed,
        "functional_passed": not functional_failed,
        "performance_passed": not performance_failed,
        "semantic_alignment": semantic_alignment,
        "emergency_response_p95_ms": response_p95,
        "emergency_response_max_ms": response_max,
        "failed_keys": blocking_failed,
        "functional_failed_keys": functional_failed,
        "performance_failed_keys": performance_failed,
        "checks": checks,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("jsonl", type=Path, help="S3 ScenarioEvidenceRecorder JSONL")
    parser.add_argument("--summary", type=Path, help="Adjacent summary JSON path")
    parser.add_argument("--output", type=Path, help="Optional member-4 report path")
    parser.add_argument("--functional-only", action="store_true")
    args = parser.parse_args()

    summary_path = args.summary or args.jsonl.with_suffix(".summary.json")
    report = validate_evidence(
        _load_json(summary_path), _load_jsonl(args.jsonl),
        functional_only=args.functional_only,
    )
    encoded = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
