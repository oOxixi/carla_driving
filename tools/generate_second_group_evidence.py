"""Generate current-run second-group summaries and a hash-verified index.

Historical artifacts are registered only as pre-change context.  The script
never promotes a deterministic backend, synthetic benchmark, or historical
model run to current production evidence.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
from typing import Any
import xml.etree.ElementTree as ET


CURRENT_RUN_GLOBS = {
    "S01_set_speed_20": (
        "artifacts/second_group_20260731/s01_sensor_rerun_with_full_timing/"
        "S01_set_speed_20/seed_0/run_01/*.jsonl"
    ),
    "D03_front_vehicle_brake": (
        "artifacts/second_group_20260731/d03_d08_sensor_rerun_with_full_timing/"
        "D03_front_vehicle_brake/seed_0/run_01/*.jsonl"
    ),
    "D08_command_conflict_red_light_continue": (
        "artifacts/second_group_20260731/d08_terminal_feedback_rerun/"
        "D08_command_conflict_red_light_continue/seed_0/run_01/*.jsonl"
    ),
}

COLD_FAILURE_GLOB = (
    "artifacts/second_group_20260731/scenario_smoke_after_changes/"
    "S01_set_speed_20/seed_0/run_01/*.jsonl"
)
TOWN10_FIXED_GLOB = (
    "artifacts/second_group_20260731/town10hd_speed20_watchdog_fixed/*.jsonl"
)


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _entry(root: Path, path: Path, *, status: str = "CURRENT") -> dict[str, Any]:
    resolved = path if path.is_absolute() else root / path
    if not resolved.is_file():
        raise FileNotFoundError(resolved)
    return {
        "path": resolved.relative_to(root).as_posix(),
        "sha256": _sha256(resolved),
        "bytes": resolved.stat().st_size,
        "status": status,
    }


def _one(root: Path, pattern: str) -> Path:
    matches = sorted(root.glob(pattern))
    if len(matches) != 1:
        raise RuntimeError(f"expected one match for {pattern!r}, found {len(matches)}")
    return matches[0]


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def _latency(frames: list[dict[str, Any]], field: str) -> dict[str, float | None]:
    values = [
        float(frame["latency"][field])
        for frame in frames
        if frame.get("latency", {}).get(field) is not None
    ]
    return {
        "count": len(values),
        "mean": statistics.fmean(values) if values else None,
        "p95": _percentile(values, 0.95),
        "p99": _percentile(values, 0.99),
        "max": max(values, default=None),
    }


def _run_summary(root: Path, path: Path) -> dict[str, Any]:
    records = _read_jsonl(path)
    frames = [record for record in records if record.get("record_type") == "frame"]
    terminal = records[-1]
    if terminal.get("record_type") != "run_complete":
        raise RuntimeError(f"run has no run_complete terminal: {path}")
    summary = terminal["summary"]
    return {
        "scenario_id": summary["scenario_id"],
        "status": summary["status"],
        "score": summary["score"]["final_score"],
        "frames": len(frames),
        "collision_count": summary["collision_count"],
        "red_light_violation_count": summary["red_light_violation_count"],
        "route_deviation_count": summary["route_deviation_count"],
        "min_gap_m": summary["min_gap_m"],
        "final_speed_mps": summary["final_speed_mps"],
        "command_terminal_statuses": summary["command_terminal_statuses"],
        "safety_reasons": dict(Counter(
            frame.get("safety", {}).get("reason", "UNKNOWN") for frame in frames
        )),
        "latency_ms": {
            field: _latency(frames, field)
            for field in (
                "simulator_tick_ms",
                "perception_acquire_ms",
                "pipeline_active_ms",
                "sensor_to_control_ms",
                "decision_ms",
            )
        },
        "acceptance": summary.get("acceptance"),
        "jsonl": path.relative_to(root).as_posix(),
        "summary_json": path.with_suffix(".summary.json").relative_to(root).as_posix(),
    }


def _pytest_result(root: Path) -> tuple[dict[str, Any], Path]:
    xml_path = root / "artifacts/second_group_20260731/tests/pytest_full.xml"
    xml_root = ET.parse(xml_path).getroot()
    suites = list(xml_root.findall("testsuite"))
    result = {
        "schema_version": "1.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": (
            "conda run -n carla312 env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 "
            "python -m pytest -q --junitxml=artifacts/second_group_20260731/tests/pytest_full.xml"
        ),
        "tests": sum(int(suite.attrib.get("tests", 0)) for suite in suites),
        "passed": sum(
            int(suite.attrib.get("tests", 0))
            - int(suite.attrib.get("failures", 0))
            - int(suite.attrib.get("errors", 0))
            - int(suite.attrib.get("skipped", 0))
            for suite in suites
        ),
        "failures": sum(int(suite.attrib.get("failures", 0)) for suite in suites),
        "errors": sum(int(suite.attrib.get("errors", 0)) for suite in suites),
        "skipped": sum(int(suite.attrib.get("skipped", 0)) for suite in suites),
        "duration_s": sum(float(suite.attrib.get("time", 0.0)) for suite in suites),
        "plugin_autoload_disabled": True,
        "junit_xml": xml_path.relative_to(root).as_posix(),
    }
    output = root / "artifacts/second_group_20260731/tests/pytest_full_result.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result, output


def _git(root: Path, *arguments: str) -> str:
    return subprocess.check_output(
        ["git", *arguments], cwd=root, text=True, encoding="utf-8"
    ).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("submission/second_group_20260731/evidence_index.json"),
    )
    args = parser.parse_args()
    root = args.repo_root.resolve()

    pytest_result, pytest_json_path = _pytest_result(root)
    current_paths = {
        scenario: _one(root, pattern)
        for scenario, pattern in CURRENT_RUN_GLOBS.items()
    }
    current_runs = {
        scenario: _run_summary(root, path)
        for scenario, path in current_paths.items()
    }
    cold_path = _one(root, COLD_FAILURE_GLOB)
    cold_failure = _run_summary(root, cold_path)
    town10_path = _one(root, TOWN10_FIXED_GLOB)
    town10 = _run_summary(root, town10_path)

    real_perception_p95 = {
        scenario: run["latency_ms"]["perception_acquire_ms"]["p95"]
        for scenario, run in current_runs.items()
    }
    real_pipeline_p95 = {
        scenario: run["latency_ms"]["pipeline_active_ms"]["p95"]
        for scenario, run in current_runs.items()
    }
    live_summary = {
        "schema_version": "1.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "current-host CARLA 0.9.16 representative runs; one seed and one accepted run per scenario",
        "not_formal_matrix": True,
        "runs": current_runs,
        "cold_start_failure_retained": cold_failure,
        "town10hd_speed20_regression": town10,
        "targets": {
            "real_perception_p95_ms_max": 30.0,
            "real_perception_p95_by_scenario_ms": real_perception_p95,
            "real_perception_target_met": all(
                value is not None and value <= 30.0
                for value in real_perception_p95.values()
            ),
            "pipeline_period_p95_ms_max_for_20hz": 50.0,
            "pipeline_active_p95_by_scenario_ms": real_pipeline_p95,
            "pipeline_20hz_target_met": all(
                value is not None and value <= 50.0
                for value in real_pipeline_p95.values()
            ),
            "decision_p95_ms_max": 5.0,
            "decision_target_met": all(
                run["latency_ms"]["decision_ms"]["p95"] <= 5.0
                for run in current_runs.values()
            ),
        },
    }
    live_summary_path = (
        root / "artifacts/second_group_20260731/live_carla_acceptance_summary.json"
    )
    live_summary_path.write_text(
        json.dumps(live_summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    source_paths = [
        *(root / "interfaces").glob("*.schema.json"),
        root / "integration/second_group_runtime.py",
        root / "integration/canonical_bridge.py",
        root / "integration/carla_perception.py",
        root / "integration/carla_runner.py",
        root / "integration/qwen_image_stager.py",
        root / "integration/route_planner.py",
        root / "integration/runtime_loop.py",
        root / "integration/scenario_evidence.py",
        root / "car_control_A/watchdog.py",
        root / "car_control_D/control_runtime.py",
        root / "car_control_D/execution_feedback.py",
        root / "qwen_service/server.py",
        root / "qwen_service/service.py",
        root / "run_full_pipeline.sh",
        root / "docs/SECOND_GROUP_RUNBOOK.md",
    ]
    current_artifacts = [
        root / "artifacts/second_group_20260731/tests/pytest_full.xml",
        pytest_json_path,
        live_summary_path,
        root / "artifacts/second_group_20260731/perception_benchmark.json",
        root / "artifacts/second_group_20260731/environment_snapshot.json",
        root / "car_control_D/control_benchmark.json",
        root / "artifacts/second_group_20260731/sensor_probe_all_town10hd.log",
        root / "qwen_service/model_benchmark.json",
        root / "qwen_service/latency_report.json",
        *current_paths.values(),
        *(path.with_suffix(".summary.json") for path in current_paths.values()),
        cold_path,
        cold_path.with_suffix(".summary.json"),
        town10_path,
        town10_path.with_suffix(".summary.json"),
    ]
    report_path = root / "docs/第二组实施与验收总结_20260731.md"
    if report_path.is_file():
        current_artifacts.append(report_path)

    historical_paths = [
        root / "artifacts/scenario_matrix_0727_final/scenario_matrix_report.json",
        root / "artifacts/long_stability_0728/report_30min.json",
        root / "artifacts/four_modal_0728/full_chain_report_v2.json",
        root / "artifacts/four_modal_0728/qwen_model_manifest.json",
    ]
    status = _git(root, "status", "--porcelain=v1").splitlines()
    diff = subprocess.check_output(["git", "diff", "--binary"], cwd=root)
    evidence = {
        "schema_version": "1.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "repository": "https://github.com/oOxixi/carla_driving.git",
        "branch": _git(root, "branch", "--show-current"),
        "base_commit": _git(root, "rev-parse", "HEAD"),
        "working_tree_clean": not status,
        "working_tree_status": status,
        "tracked_diff_sha256": _sha256_bytes(diff),
        "tracked_diff_bytes": len(diff),
        "carla_version": "0.9.16",
        "source_files": [_entry(root, path) for path in sorted(source_paths)],
        "current_evidence": [_entry(root, path) for path in sorted(current_artifacts)],
        "historical_pre_change_context": [
            _entry(root, path, status="HISTORICAL_PRE_CHANGE")
            for path in historical_paths
        ],
        "machine_results": {
            "pytest": pytest_result,
            "representative_carla": live_summary,
            "formal_matrix": {
                "status": "NOT_RUN_STAGE_GATE_FAILED",
                "required": "S01/D03/D08, at least 5 seeds and 20 total runs per scenario",
                "reason": "current-host real perception P95 exceeds 30 ms and Qwen production weights are missing",
            },
            "stability_60_min": {
                "status": "NOT_RUN_STAGE_GATE_FAILED",
                "reason": "formal real-model/real-sensor stage gate is not satisfied; historical 30-minute run is not promoted",
            },
            "qwen_current_host": {
                "status": "BLOCKED_MODEL_MISSING",
                "production_ready": False,
                "historical_7b_p95_ms": 2478.4190806,
                "target_p95_ms": 300.0,
            },
        },
        "integrity_policy": {
            "synthetic_perception_benchmark_is_live_carla_evidence": False,
            "deterministic_qwen_backend_is_production_evidence": False,
            "historical_matrix_is_current_change_evidence": False,
            "historical_30_min_is_60_min_evidence": False,
        },
    }
    output = args.output if args.output.is_absolute() else root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "pytest_result": pytest_json_path.relative_to(root).as_posix(),
        "live_summary": live_summary_path.relative_to(root).as_posix(),
        "evidence_index": output.relative_to(root).as_posix(),
        "current_artifacts": len(current_artifacts),
        "source_files": len(source_paths),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
