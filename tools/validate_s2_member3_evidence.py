"""Validate the member-3 S2 full-chain evidence bundle.

This checker never infers success from a scene configuration.  It requires an
actual JSONL run plus the adjacent recorder summary and verifies the complete
Qwen-to-control chain, both obstacle-avoidance returns, and the S2 safety
metrics assigned to member 3.
"""
from __future__ import annotations

import argparse
from collections.abc import Mapping
import json
from pathlib import Path
import sys
from typing import Any


SCENARIO_ID = "OFFICIAL_S2_COMPLEX_AVOIDANCE_8KM"
EXPECTED_BEHAVIORS = {
    "KEEP_LANE",
    "SLOW_DOWN",
    "WAIT_SAFE_GAP",
    "CHANGE_LANE_LEFT",
    "PASS_TARGET",
    "RETURN_TO_LANE",
}


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
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def check(key: str, passed: bool, actual: Any, required: Any) -> None:
        checks.append({
            "key": key,
            "status": "PASS" if passed else "FAIL",
            "actual": actual,
            "required": required,
        })

    start = next((item for item in records if item.get("record_type") == "run_start"), {})
    config = start.get("config", {}) if isinstance(start.get("config"), Mapping) else {}
    identifiers = {key: config.get(key) for key in ("seed", "code_version", "config_path")}
    check("scenario_id", summary.get("scenario_id") == SCENARIO_ID, summary.get("scenario_id"), SCENARIO_ID)
    check("run_status", summary.get("status") == "SUCCEEDED", summary.get("status"), "SUCCEEDED")
    check(
        "required_identifiers",
        all(value not in (None, "", "UNKNOWN") for value in identifiers.values()),
        identifiers,
        "seed, code_version and config_path are present",
    )

    command_records = [item for item in records if item.get("record_type") == "command"]
    external_commands = [
        item for item in command_records
        if item.get("disposition") != "INTERNAL_QWEN_WAIT_STOP"
    ]
    external_ids = [str(item.get("command_id", "")) for item in external_commands]
    terminals = summary.get("command_terminal_statuses", {})
    terminals = terminals if isinstance(terminals, Mapping) else {}
    external_terminal_statuses = {command_id: terminals.get(command_id) for command_id in external_ids}
    check("external_command_count", len(external_ids) == 5, len(external_ids), 5)
    check(
        "all_external_commands_succeeded",
        bool(external_ids) and all(status == "SUCCEEDED" for status in external_terminal_statuses.values()),
        external_terminal_statuses,
        "every external command has exactly one SUCCEEDED terminal",
    )

    acceptance = summary.get("acceptance", {})
    metrics = acceptance.get("metrics", {}) if isinstance(acceptance, Mapping) else {}
    metrics = metrics if isinstance(metrics, Mapping) else {}
    qwen = metrics.get("qwen_acceptance", {})
    qwen = qwen if isinstance(qwen, Mapping) else {}
    qwen_observed = qwen.get("observed", {}) if isinstance(qwen.get("observed"), Mapping) else {}
    qwen_checks = qwen.get("checks", {}) if isinstance(qwen.get("checks"), Mapping) else {}
    routes = list(qwen_observed.get("routes", ()))
    behaviors = {str(item).upper() for item in qwen_observed.get("behaviors", ())}
    terminal_counts = qwen_observed.get("terminal_counts", {})
    terminal_counts = terminal_counts if isinstance(terminal_counts, Mapping) else {}
    check("qwen_contract", qwen.get("passed") is True, qwen_checks, "all Qwen contract checks PASS")
    check("qwen_request_count", qwen_observed.get("qwen_calls") == 5, qwen_observed.get("qwen_calls"), 5)
    check("qwen_route", routes == ["QWEN_PLAN"] * 5, routes, ["QWEN_PLAN"] * 5)
    check(
        "qwen_high_level_behaviors",
        EXPECTED_BEHAVIORS.issubset(behaviors) and qwen_checks.get("low_level_boundary") is True,
        sorted(behaviors),
        sorted(EXPECTED_BEHAVIORS),
    )
    check(
        "unique_qwen_terminals",
        len(terminal_counts) == 5 and all(value == 1 for value in terminal_counts.values()),
        dict(terminal_counts),
        "one terminal per Qwen-routed command",
    )

    restored = [
        item for item in records
        if item.get("record_type") == "canonical_routing"
        and item.get("phase") == "MISSION_ROUTE_RESTORED"
    ]
    check("mission_route_restored", len(restored) == 2, len(restored), 2)

    extension = metrics.get("extension_acceptance", {})
    extension = extension if isinstance(extension, Mapping) else {}
    check("extension_acceptance", extension.get("passed") is True, extension.get("failed_keys"), [])
    for key in (
        "expected_phase_count",
        "all_phases_must_complete",
        "must_return_to_original_lane",
        "minimum_actor_distances_m",
        "maximum_route_deviation_m",
    ):
        item = _extension_check(extension, key)
        check(
            f"extension_{key}",
            item is not None and item.get("status") == "PASS",
            None if item is None else item.get("actual"),
            "PASS",
        )

    check("collision_count", summary.get("collision_count") == 0, summary.get("collision_count"), 0)
    check("lane_invasion_count", summary.get("lane_invasion_count") == 0, summary.get("lane_invasion_count"), 0)
    latency = summary.get("latency", {})
    latency = latency if isinstance(latency, Mapping) else {}
    max_qwen_latency = latency.get("sensor_to_trajectory_max_ms")
    check(
        "sensor_to_trajectory_max_ms",
        isinstance(max_qwen_latency, (int, float)) and max_qwen_latency <= 150.0,
        max_qwen_latency,
        "<= 150.0",
    )

    failed = [item["key"] for item in checks if item["status"] == "FAIL"]
    return {
        "scenario_id": summary.get("scenario_id"),
        "passed": not failed,
        "failed_keys": failed,
        "checks": checks,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("jsonl", type=Path, help="S2 ScenarioEvidenceRecorder JSONL")
    parser.add_argument("--summary", type=Path, help="Adjacent summary JSON path")
    parser.add_argument("--output", type=Path, help="Optional member-3 report path")
    args = parser.parse_args()

    summary_path = args.summary or args.jsonl.with_suffix(".summary.json")
    report = validate_evidence(_load_json(summary_path), _load_jsonl(args.jsonl))
    encoded = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
