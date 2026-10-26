"""Materialize or execute reproducible Town03_Opt event regressions with real Qwen."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from integration.evidence_provenance import collect_provenance
from integration.generalization_gate import load_generalization_matrix, perturb_scenario
from integration.scenario_execution import ScenarioSpec


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_matrix(output: Path, matrix_path: Path) -> dict:
    source = ROOT / "scenarios/official_competition/S2_complex_avoidance_8km.json"
    raw = json.loads(source.read_text(encoding="utf-8"))
    matrix = load_generalization_matrix(matrix_path)
    if matrix.maps != ("Town03_Opt",):
        raise ValueError("S2 optimization regressions require Town03_Opt")
    windows = json.loads(matrix_path.read_text(encoding="utf-8"))["event_windows"]
    scenarios = output / "scenarios"
    scenarios.mkdir(parents=True, exist_ok=True)
    cases = []
    for index, case in enumerate(matrix.cases(raw["scenario_id"])):
        variant = perturb_scenario(raw, case)
        path = scenarios / f"{case.case_id}.json"
        path.write_text(json.dumps(variant, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        ScenarioSpec.load(path)
        cases.append({"index": index, "case_id": case.case_id,
                      "scenario_path": str(path.relative_to(output)),
                      "scenario_sha256": _sha(path), "perturbation": asdict(case)})
    return {
        "schema_version": "1.0", "scope": "event_segment",
        "validation": "STATIC_ONLY", "closed_loop_status": "NOT_RUN",
        "source_scenario_sha256": _sha(source), "matrix_sha256": _sha(matrix_path),
        "provenance": collect_provenance(ROOT, str(source)),
        "cases": cases, "event_windows": windows,
        "event_task_count": len(cases) * len(windows),
    }


def evaluate_segment(summary: dict, window: dict, phase_id: str, phase_contract: dict | None = None) -> dict:
    metrics = summary.get("acceptance", {}).get("metrics", {})
    evidence = metrics.get("extension_acceptance", metrics.get("scenario_extension_acceptance", {})).get("evidence", {})
    qwen = metrics.get("qwen_acceptance", {}).get("observed", {})
    checks = {}
    def check(key, passed, actual):
        checks[key] = {"passed": bool(passed), "actual": actual}
    phase_status = evidence.get("external_qwen_terminal_statuses", {})
    health = (summary.get("provenance") or {}).get("qwen", {})
    check("production_qwen_2b", health.get("status") == "READY" and health.get("production_ready") is True
          and health.get("model_id") == "Qwen/Qwen3.5-2B" and health.get("qwen_mode") == "planner_v2",
          health)
    # Map phases through the measured successful phase set; no submitted-only pass.
    check("phase_succeeded", phase_id in evidence.get("completed_phase_ids", []), phase_id)
    check("qwen_plan_used", "QWEN_PLAN" in qwen.get("routes", []), qwen.get("routes"))
    check("external_terminals", bool(phase_status) and all(v == "SUCCEEDED" for v in phase_status.values()), phase_status)
    counts = qwen.get("terminal_counts", {})
    check("unique_terminals", bool(phase_status) and all(counts.get(key) == 1 for key in phase_status), counts)
    check("qwen_input_valid", evidence.get("qwen_invalid_result_count") == 0 and evidence.get("qwen_timeout_count") == 0,
          {key: evidence.get(key) for key in ("qwen_invalid_result_count", "qwen_timeout_count")})
    progress = summary.get("mission_route_progress_m")
    check("event_exit_reached", isinstance(progress, (int, float)) and progress >= window["end_m"], progress)
    for key in ("collision_count", "lane_invasion_count", "red_light_violation_count", "route_deviation_count"):
        check(key, summary.get(key) == 0, summary.get(key))
    deviation = evidence.get("max_route_deviation_m")
    check("route_error", isinstance(deviation, (int, float)) and deviation <= 1.0, deviation)
    activations = evidence.get("actor_activation_progress_m", {})
    check("actors_activated", all(key in activations for key in window["actor_ids"]), activations)
    trigger_ids = evidence.get("actor_trigger_ids", [])
    check("actor_events_triggered", all(key in trigger_ids for key in window.get("required_actor_trigger_ids", [])), trigger_ids)
    recovered = evidence.get("max_speed_after_phase_kph", {}).get(phase_id)
    check("speed_recovered", isinstance(recovered, (int, float)) and recovered >= 32.0, recovered)
    if window.get("require_route_restore"):
        check("route_restored", evidence.get("mission_route_restore_count", 0) >= 1, evidence.get("mission_route_restore_count"))
    if window.get("required_passed_actor_ids"):
        passed_actors = evidence.get("passed_actor_ids_by_phase", {}).get(phase_id, [])
        check("required_actors_physically_passed", all(actor in passed_actors for actor in window["required_passed_actor_ids"]),
              {"actual": passed_actors, "required": window["required_passed_actor_ids"]})
    for actor, minimum in window.get("minimum_actor_gaps_m", {}).items():
        gap = evidence.get("minimum_actor_distances_m", {}).get(actor)
        check(f"gap_{actor}", isinstance(gap, (int, float)) and gap >= minimum, gap)
    lateral_checks = set()
    for item in summary.get("acceptance", {}).get("checks", []):
        if item.get("key") in {
            "max_lane_center_offset_m", "max_lane_follow_center_offset_m",
            "must_follow_planned_lane_change_reference",
        }:
            lateral_checks.add(item["key"])
            check(f"acceptance:{item['key']}", item.get("status") == "PASS", item)
    check("lateral_acceptance_evidence", bool(lateral_checks.intersection({
        "max_lane_center_offset_m", "max_lane_follow_center_offset_m",
    })) and "must_follow_planned_lane_change_reference" in lateral_checks,
          sorted(lateral_checks))
    # Only the selected event's requirements apply here. Missing future phases
    # must not fail a segment, but a successful plan must not hide a late
    # command or a missed activation window for the event actually exercised.
    if phase_contract is not None:
        for requirement, observed, ids in (
            ("command_progress_windows_m", "command_progress_m_by_phase", [phase_id]),
            ("actor_activation_progress_windows_m", "actor_activation_progress_m", window["actor_ids"]),
        ):
            required_windows = phase_contract.get(requirement, {})
            actual_values = evidence.get(observed, {})
            for key in ids:
                if key not in required_windows:
                    continue
                low, high = required_windows[key]
                value = actual_values.get(key)
                check(f"{requirement}:{key}", isinstance(value, (int, float)) and low <= value <= high,
                      {"actual": value, "required": [low, high]})
        for requirement, observed in (
            ("minimum_approach_speed_kph_by_phase", "command_approach_speed_kph_by_phase"),
            ("minimum_resumed_speed_kph_by_phase", "max_speed_after_phase_kph"),
        ):
            minimum = phase_contract.get(requirement, {}).get(phase_id)
            if minimum is not None:
                value = evidence.get(observed, {}).get(phase_id)
                check(f"{requirement}:{phase_id}", isinstance(value, (int, float)) and value >= minimum,
                      {"actual": value, "required": minimum})
        tolerance = phase_contract.get("phase_target_speed_tolerance_kph", {}).get(phase_id)
        if tolerance is not None:
            actual = evidence.get("closest_speed_to_target_kph_by_phase", {}).get(phase_id)
            target = evidence.get("target_speed_kph_by_phase", {}).get(phase_id)
            measured = all(type(v) in (int, float) and math.isfinite(v) for v in (actual, target))
            check(f"phase_target_speed_tolerance_kph:{phase_id}",
                  measured and abs(actual - target) <= tolerance,
                  {"actual": actual, "target": target, "tolerance": tolerance})
    return {"scope": "event_segment", "full_8km": "NOT_EVALUATED",
            "phase_contract_enforced": phase_contract is not None,
            "functional_passed": all(c["passed"] for c in checks.values()), "checks": checks,
            "performance": {"enforced": False, "sensor_to_trajectory_max_ms": summary.get("latency", {}).get("sensor_to_trajectory_max_ms")}}


def reevaluate_manifest(source: Path, matrix_path: Path) -> dict:
    """Apply current event checks to immutable saved evidence without driving again."""
    previous = json.loads(source.read_text(encoding="utf-8"))
    windows = json.loads(matrix_path.read_text(encoding="utf-8"))["event_windows"]
    results = []
    for item in previous["results"]:
        index, event = item["case_index"], item["event"]
        case = previous["cases"][index]
        scenario = source.parent / case["scenario_path"]
        log_dir = source.parent / "runs" / f"case_{index:03d}_{event}"
        summaries = list(log_dir.glob("*.summary.json"))
        if len(summaries) != 1 or _sha(scenario) != case["scenario_sha256"]:
            raise ValueError("saved evidence is missing or its scenario hash changed")
        if item.get("report", {}).get("summary_sha256") != _sha(summaries[0]):
            raise ValueError("saved summary hash differs from recorded experiment manifest")
        for key in ("start_m", "end_m", "completed_commands", "command_index", "duration_s"):
            if windows[event][key] != previous["event_windows"][event][key]:
                raise ValueError("event geometry/window changed; new driving evidence is required")
        raw = json.loads(scenario.read_text(encoding="utf-8"))
        summary = json.loads(summaries[0].read_text(encoding="utf-8"))
        report = evaluate_segment(summary, windows[event], raw["commands"][windows[event]["command_index"]]["phase_id"],
                                  raw.get("extensions", {}).get("proposed_acceptance", {}))
        results.append({"case_index": index, "event": event, "report": report,
                        "summary_sha256": _sha(summaries[0])})
    passed = bool(results) and all(item["report"]["functional_passed"] for item in results)
    return {"scope": "SELECTED_TASKS_ONLY", "source_manifest": str(source),
            "source_manifest_sha256": _sha(source), "evaluation_matrix_sha256": _sha(matrix_path),
            "selected_tasks_status": "PASS" if passed else "FAIL",
            "executed_task_count": len(results), "not_run_task_count": previous["event_task_count"] - len(results),
            "results": results, "full_8km": "NOT_EVALUATED"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, default=ROOT / "config/s2_optimization_matrix.json")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--fail-fast", action="store_true", help="stop the selected batch after the first failed/error event")
    parser.add_argument("--evaluate-manifest", type=Path, help="recheck saved evidence without CARLA")
    parser.add_argument("--case-index", type=int, action="append")
    parser.add_argument("--event", action="append")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=2100)
    parser.add_argument("--qwen-url", default="http://127.0.0.1:18005")
    args = parser.parse_args()
    output = args.output_dir.resolve()
    # Each output directory is an immutable experiment; avoid overwriting evidence.
    if output.exists():
        parser.error("output directory already exists; choose a fresh experiment directory")
    if args.evaluate_manifest:
        if args.run:
            parser.error("--run and --evaluate-manifest cannot be combined")
        report = reevaluate_manifest(args.evaluate_manifest.resolve(), args.matrix.resolve())
        output.mkdir(parents=True)
        (output / "reevaluation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({key: report[key] for key in ("selected_tasks_status", "executed_task_count", "not_run_task_count")}))
        return 0 if report["selected_tasks_status"] == "PASS" else 1
    if args.run and (not args.case_index or not args.event):
        parser.error("--run requires explicit --case-index and --event selections")
    matrix = build_matrix(output, args.matrix.resolve())
    matrix["results"] = []
    manifest = output / "matrix_manifest.json"
    def save():
        manifest.write_text(json.dumps(matrix, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    save()
    if not args.run:
        print(json.dumps({"status": "STATIC_PASS", "manifest": str(manifest), "tasks": matrix["event_task_count"]}))
        return 0
    if any(index < 0 or index >= len(matrix["cases"]) for index in args.case_index):
        parser.error("case index is outside the generated matrix")
    if any(event not in matrix["event_windows"] for event in args.event):
        parser.error("unknown event")
    matrix["closed_loop_status"] = "RUNNING"
    matrix["fail_fast"] = args.fail_fast
    save()
    stop_requested = False
    for index in dict.fromkeys(args.case_index):
        case = matrix["cases"][index]
        scenario = output / case["scenario_path"]
        raw = json.loads(scenario.read_text(encoding="utf-8"))
        for event in dict.fromkeys(args.event):
            window = matrix["event_windows"][event]
            log_dir = output / "runs" / f"case_{index:03d}_{event}"
            log_dir.mkdir(parents=True)
            command = [sys.executable, "-m", "integration.carla_runner",
                "--host", args.host, "--port", str(args.port), "--timeout-s", "60",
                "--warmup-frames", "20", "--sensor-warmup-frames", "20", "--sensor-timeout-s", "1.0",
                "--perception-mode", "sensors", "--scenario-facts-mode", "perception",
                "--print-every", "40", "--log-dir", str(log_dir),
                "--qwen-service-url", args.qwen_url, "--qwen-mode", "planner_v2",
                "--qwen-timeout-ms", "5000", "--qwen-queue-size", "1",
                "--qwen-image-root", str(ROOT), "--qwen-image-prefix", "artifacts/runtime/qwen_optimization",
                "--scenario-file", str(scenario), "--resume-route-progress-m", str(window["start_m"]),
                "--resume-command-count", str(window["completed_commands"]), "--resume-target-speed-kph", "40",
                "--max-frames", str(math.ceil(window["duration_s"] / raw["runtime"]["fixed_delta_seconds"]))]
            result = {"case_index": index, "event": event, "status": "RUNNING", "command": command,
                      "started_at": datetime.now(timezone.utc).isoformat()}
            matrix["results"].append(result)
            save()
            try:
                with (log_dir / "console.log").open("w", encoding="utf-8") as stream:
                    completed = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
                                               check=False, timeout=max(300., window["duration_s"] * 12.))
                result["runner_exit_code"] = completed.returncode
                summaries = list(log_dir.glob("*.summary.json"))
                if len(summaries) != 1:
                    raise ValueError("expected exactly one completed recorder summary")
                summary = json.loads(summaries[0].read_text(encoding="utf-8"))
                report = evaluate_segment(summary, window, raw["commands"][window["command_index"]]["phase_id"],
                                          raw.get("extensions", {}).get("proposed_acceptance", {}))
                report["recorder_summary_status"] = summary.get("status")
                report["summary_sha256"] = _sha(summaries[0])
                report["scenario_sha256"] = _sha(scenario)
                if completed.returncode not in {0, 1}:
                    report["functional_passed"] = False
                result["report"] = report
                result["status"] = "PASS" if report["functional_passed"] else "FAIL"
            except (OSError, ValueError, subprocess.TimeoutExpired) as error:
                result.update(status="ERROR", error=f"{type(error).__name__}: {error}")
            result["finished_at"] = datetime.now(timezone.utc).isoformat()
            save()
            print(json.dumps({"case_index": index, "event": event, "status": result["status"]}), flush=True)
            if args.fail_fast and result["status"] != "PASS":
                stop_requested = True
                break
        if stop_requested:
            break
    selected_passed = all(item["status"] == "PASS" for item in matrix["results"])
    matrix["selected_tasks_status"] = "PASS" if selected_passed else "FAIL"
    matrix["executed_task_count"] = len(matrix["results"])
    matrix["not_run_task_count"] = matrix["event_task_count"] - len(matrix["results"])
    matrix["closed_loop_status"] = (
        "PASS" if selected_passed and matrix["not_run_task_count"] == 0
        else "PARTIAL_PASS" if selected_passed else "FAIL"
    )
    matrix["closed_loop_scope"] = "SELECTED_TASKS_ONLY"
    matrix["stopped_after_failure"] = stop_requested
    save()
    return 0 if selected_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
