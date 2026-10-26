from __future__ import annotations

import json
import hashlib
from pathlib import Path
import subprocess

import pytest

from car_control_A import ControlOutput
from integration.carla_perception import sensor_specs_for_profile, sensor_specs_for_scenario
from integration.evidence_provenance import collect_provenance
from integration.evidence_reporting import LaneOffsetStatistics, scoped_command_statistics
from integration.scenario_evidence import ScenarioEvidenceRecorder
from integration.scenario_extensions import ScenarioExtensionRuntime
from integration.tests.test_scenario_evidence import _vehicle, _timing
from integration.contracts import PerceptionFrame
from tools.run_s2_optimization_matrix import build_matrix, evaluate_segment, reevaluate_manifest
from tools.summarize_optimization_evidence import audit_evidence
from tools.summarize_s2_optimization_matrix import summarize_manifests

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("fail_fast, count", [(True, 1), (False, 2)])
def test_matrix_can_stop_before_followup_events_when_an_issue_remains(tmp_path, monkeypatch, fail_fast, count):
    from types import SimpleNamespace
    import tools.run_s2_optimization_matrix as runner
    output = tmp_path / "experiment"
    monkeypatch.setattr(runner, "collect_provenance", lambda *a: {})
    calls = []
    def fake_run(command, **kwargs):
        calls.append(command)
        log_dir = Path(command[command.index("--log-dir") + 1])
        (log_dir / "mock.summary.json").write_text("{}", encoding="utf-8")
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    argv = ["matrix", "--output-dir", str(output), "--run", "--case-index", "1",
            "--event", "bus_stop", "--event", "bicycle"]
    monkeypatch.setattr(runner.sys, "argv", argv + (["--fail-fast"] if fail_fast else []))
    assert runner.main() == 1
    report = json.loads((output / "matrix_manifest.json").read_text(encoding="utf-8"))
    assert len(calls) == report["executed_task_count"] == count
    assert report["stopped_after_failure"] is fail_fast
    assert report["not_run_task_count"] == 60 - count


def test_provenance_identifies_clean_dirty_and_untracked_sources(tmp_path):
    def git(*args):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)
    git("init")
    (tmp_path / "model.py").write_text("value = 1\n")
    git("add", "model.py")
    git("-c", "user.name=test", "-c", "user.email=test@example.invalid", "commit", "-m", "base")
    clean = collect_provenance(tmp_path, "model.py")
    assert clean["source"]["dirty"] is False
    (tmp_path / "model.py").write_text("value = 2\n")
    (tmp_path / "config.json").write_text("{}")
    dirty = collect_provenance(tmp_path, "model.py")
    assert dirty["source"]["git_sha"] == clean["source"]["git_sha"]
    assert dirty["source"]["dirty"] is True
    assert "config.json" in dirty["source"]["untracked_sha256"]
    assert dirty["source"]["changes_sha256"] != clean["source"]["changes_sha256"]
    assert dirty["scenario"]["sha256"] != clean["scenario"]["sha256"]


def test_matrix_sensor_perturbations_reach_actual_blueprint_specs(tmp_path):
    manifest = build_matrix(tmp_path, ROOT / "config/s2_optimization_matrix.json")
    assert manifest["event_task_count"] == 60
    assert manifest["closed_loop_status"] == "NOT_RUN"
    assert len({case["perturbation"]["seed"] for case in manifest["cases"]}) == 5
    for case in manifest["cases"]:
        raw = json.loads((tmp_path / case["scenario_path"]).read_text(encoding="utf-8"))
        assert raw["map"] == "Town03_Opt"
        actual = {item.sensor_id: item.attributes for item in sensor_specs_for_scenario("competition_multiview", raw["sensors"])}
        condition = case["perturbation"]["sensor_condition"]
        if condition == "sparse_lidar":
            assert actual["lidar_roof"]["channels"] == "16"
        if condition == "reduced_rgb":
            for key in ("rgb_front", "rgb_left", "rgb_right", "rgb_rear"):
                assert actual[key]["image_size_x"] == "600"
                assert actual[key]["image_size_y"] == "338"
    assert sensor_specs_for_scenario("default") == sensor_specs_for_profile("default")


def test_invalid_sensor_resolution_rejected_before_spawn():
    with pytest.raises(ValueError):
        sensor_specs_for_scenario("default", {"front_rgb": {"width": 0}})


def test_internal_failures_remain_visible_without_polluting_external_counts():
    stats = scoped_command_statistics(
        {"business": {}, "qwen-wait-a": {"disposition": "INTERNAL_QWEN_WAIT_STOP"}},
        {"business": "SUCCEEDED", "qwen-wait-a": "FAILED", "qwen-step-business-1": "SUCCEEDED"},
    )
    assert stats["external"]["status_counts"] == {"SUCCEEDED": 1}
    assert stats["internal_wait"]["status_counts"] == {"FAILED": 1}
    assert stats["internal_step"]["status_counts"] == {"SUCCEEDED": 1}


def test_extension_failed_phase_is_terminal_but_not_completed():
    runtime = ScenarioExtensionRuntime({})
    runtime.note_command_submitted({"command_id": "business", "phase_id": "P1"}, qwen=True)
    runtime.note_terminal("qwen-wait-a", "FAILED")
    runtime.note_terminal("business", "FAILED")
    evidence = runtime.evidence()
    assert evidence["external_qwen_status_counts"] == {"FAILED": 1}
    assert "P1" not in evidence["completed_phase_ids"]


def test_override_report_distinguishes_signal_wait_from_front_hazard(tmp_path):
    recorder = ScenarioEvidenceRecorder(tmp_path / "evidence.jsonl")
    recorder.start_run(scenario_id="variant", config={"provenance": {"source": {"dirty": True}}})
    for frame, reason in enumerate(("RED_LIGHT_STOP_LINE_GUARD", "RED_LIGHT_STOP_LINE_GUARD", "CAUTION_TTC"), 1):
        recorder.record_frame(
            vehicle=_vehicle(frame, 0.0), scene=PerceptionFrame(frame, frame * .05),
            raw_control=ControlOutput(0., 1., 0.), final_control=ControlOutput(0., 1., 0.),
            safety_reason=reason, safety_override=True, timing=_timing(frame * 100),
            mission_route_progress_m=7300.,
        )
    summary = recorder.complete(completion=True)
    assert summary["mission_route_progress_m"] == 7300.
    assert summary["safety_override_episodes"] == 1
    assert summary["safety_overrides_by_reason"]["RED_LIGHT_STOP_LINE_GUARD"] == {
        "frames": 2, "episodes": 1, "category": "traffic_signal",
    }
    assert summary["safety_overrides_by_reason"]["CAUTION_TTC"]["category"] == "front_hazard"
    assert summary["provenance"]["source"]["dirty"] is True
    audited = audit_evidence(recorder.path)
    assert audited["safety_overrides_by_reason"] == summary["safety_overrides_by_reason"]
    assert audited["provenance"] == summary["provenance"]


def test_segment_missing_qwen_or_exit_evidence_cannot_pass():
    report = evaluate_segment({}, {"end_m": 7300., "actor_ids": ["ped"]}, "P6")
    assert report["functional_passed"] is False
    assert report["full_8km"] == "NOT_EVALUATED"
    assert report["checks"]["qwen_plan_used"]["passed"] is False
    assert report["checks"]["event_exit_reached"]["passed"] is False
    assert report["checks"]["lateral_acceptance_evidence"]["passed"] is False


def test_passing_the_wrong_actor_cannot_satisfy_overtake_evidence():
    window = {"end_m": 2830., "actor_ids": ["slow"], "required_passed_actor_ids": ["slow"]}
    summary = {"acceptance": {"metrics": {"extension_acceptance": {"evidence": {
        "passed_actor_ids_by_phase": {"P3": ["pedestrian"]},
    }}}}}
    assert not evaluate_segment(summary, window, "P3")["checks"]["required_actors_physically_passed"]["passed"]
    summary["acceptance"]["metrics"]["extension_acceptance"]["evidence"][
        "passed_actor_ids_by_phase"]["P3"].append("slow")
    assert evaluate_segment(summary, window, "P3")["checks"]["required_actors_physically_passed"]["passed"]


@pytest.mark.parametrize("actual, expected", [(None, False), (38., False), (10., False), (31., True)])
def test_event_gate_requires_the_declared_reduced_speed(actual, expected):
    evidence = {"closest_speed_to_target_kph_by_phase": {"bus": actual},
                "target_speed_kph_by_phase": {"bus": 30.}}
    summary = {"acceptance": {"metrics": {"extension_acceptance": {"evidence": evidence}}}}
    report = evaluate_segment(summary, {"end_m": 1200., "actor_ids": []}, "bus",
                              {"phase_target_speed_tolerance_kph": {"bus": 2.}})
    assert report["checks"]["phase_target_speed_tolerance_kph:bus"]["passed"] == expected


def test_legacy_lane_offset_without_authorization_field_is_not_assumed_lane_follow():
    stats = LaneOffsetStatistics()
    stats.observe(3.2, planned_crossing=None, route_error_m=.1)
    assert stats.report()["unclassified"]["frames"] == 1
    assert "lane_follow" not in stats.report()


def test_missing_lane_and_route_values_cannot_hide_invalid_planned_transition():
    stats = LaneOffsetStatistics()
    stats.observe(.1, planned_crossing=False, route_error_m=.1)
    stats.observe(None, planned_crossing=True, route_error_m=None)
    assert stats.planned_reference_valid is False


def test_lane_offset_context_is_diagnostic_and_does_not_waive_raw_contract(tmp_path):
    recorder = ScenarioEvidenceRecorder(tmp_path / "lane-context.jsonl")
    recorder.start_run(scenario_id="lane-context")
    for frame, (offset, planned, error) in enumerate((
        (.1, False, .1), (3.25, True, .13), (4., True, 2.), (3., True, None),
    ), 1):
        recorder.record_frame(
            vehicle=_vehicle(frame, 5.), scene=PerceptionFrame(frame, frame * .05,
                lane_offset_m=offset, route_deviation_m=error),
            raw_control=ControlOutput(.1, 0., 0.), final_control=ControlOutput(.1, 0., 0.),
            safety_reason="NONE", safety_override=False, timing=_timing(frame * 100),
            lane_marking_crossing_expected=planned,
        )
    summary = recorder.complete(expected={"max_lane_center_offset_m": 2.2})
    metrics = summary["acceptance"]["metrics"]
    assert metrics["max_abs_lane_offset_m"] == 4.
    assert summary["acceptance"]["passed"] is False
    scopes = metrics["lane_offset_by_context"]
    assert scopes["lane_follow"]["max_abs_m"] == .1
    assert scopes["planned_maneuver"]["max_abs_m"] == 3.25
    assert scopes["off_plan_maneuver"]["max_abs_m"] == 4.
    assert scopes["unverified_maneuver"]["frames"] == 1
    assert metrics["planned_lane_change_reference_valid"] is False
    assert audit_evidence(recorder.path)["lane_offset_by_context"] == scopes


def test_scoped_lane_follow_gate_keeps_unplanned_drift_and_invalid_transition_failing(tmp_path):
    from integration.scenario_acceptance import evaluate_expected
    from integration.carla_runner import _road_fit_expected_contract
    contract = _road_fit_expected_contract({})
    metrics = {"max_abs_lane_offset_m": 3.25, "max_abs_lane_follow_offset_m": .44,
               "planned_lane_change_reference_valid": True}
    assert evaluate_expected(contract, metrics)["passed"] is True
    assert not evaluate_expected({"max_lane_center_offset_m": 2.2}, metrics)["passed"]
    assert not evaluate_expected(contract, {**metrics, "max_abs_lane_follow_offset_m": 2.3})["passed"]
    assert not evaluate_expected(contract, {**metrics, "planned_lane_change_reference_valid": False})["passed"]
    assert not evaluate_expected(contract, {**metrics, "max_abs_lane_follow_offset_m": None})["passed"]


def test_saved_segment_recheck_preserves_scope_and_detects_tampering(tmp_path):
    matrix = build_matrix(tmp_path, ROOT / "config/s2_optimization_matrix.json")
    summary = {
        "mission_route_progress_m": 7400., "collision_count": 0, "lane_invasion_count": 0,
        "red_light_violation_count": 0, "route_deviation_count": 0,
        "provenance": {"qwen": {"status": "READY", "production_ready": True,
                                  "model_id": "Qwen/Qwen3.5-2B", "qwen_mode": "planner_v2"}},
        "acceptance": {"checks": [
            {"key": "max_lane_follow_center_offset_m", "status": "PASS"},
            {"key": "must_follow_planned_lane_change_reference", "status": "PASS"},
        ], "metrics": {
            "qwen_acceptance": {"observed": {"routes": ["QWEN_PLAN"], "terminal_counts": {"cmd": 1}}},
            "extension_acceptance": {"evidence": {
                "completed_phase_ids": ["S2_P6_LATE_PEDESTRIAN_YIELD"],
                "external_qwen_terminal_statuses": {"cmd": "SUCCEEDED"},
                "qwen_invalid_result_count": 0, "qwen_timeout_count": 0,
                "max_route_deviation_m": .5,
                "actor_activation_progress_m": {"late_crossing_pedestrian": 6936.},
                "actor_trigger_ids": ["late_crossing_pedestrian"],
                "max_speed_after_phase_kph": {"S2_P6_LATE_PEDESTRIAN_YIELD": 38.},
                "command_progress_m_by_phase": {"S2_P6_LATE_PEDESTRIAN_YIELD": 7060.},
                "command_approach_speed_kph_by_phase": {"S2_P6_LATE_PEDESTRIAN_YIELD": 38.},
            }},
        }},
    }
    run = tmp_path / "runs/case_005_late_pedestrian"
    run.mkdir(parents=True)
    saved = run / "event.summary.json"
    saved.write_text(json.dumps(summary), encoding="utf-8")
    matrix["results"] = [{"case_index": 5, "event": "late_pedestrian", "runner_exit_code": 1,
                          "report": {"summary_sha256": hashlib.sha256(saved.read_bytes()).hexdigest()}}]
    manifest = tmp_path / "matrix_manifest.json"
    manifest.write_text(json.dumps(matrix), encoding="utf-8")
    report = reevaluate_manifest(manifest, ROOT / "config/s2_optimization_matrix.json")
    assert report["selected_tasks_status"] == "PASS"
    assert report["not_run_task_count"] == 59
    assert report["full_8km"] == "NOT_EVALUATED"
    missing_lateral = json.loads(json.dumps(summary))
    missing_lateral["acceptance"].pop("checks")
    assert not evaluate_segment(missing_lateral, matrix["event_windows"]["late_pedestrian"],
                                "S2_P6_LATE_PEDESTRIAN_YIELD")["functional_passed"]
    coverage = summarize_manifests([manifest, manifest], ROOT / "config/s2_optimization_matrix.json")
    assert coverage["executed_unique_tasks"] == 1
    assert coverage["passed_tasks"] == 1
    assert coverage["not_run_tasks"] == 59
    assert coverage["frozen_baseline_gate_passed"] is False
    late_summary = json.loads(json.dumps(summary))
    late_summary["acceptance"]["metrics"]["extension_acceptance"]["evidence"][
        "command_progress_m_by_phase"]["S2_P6_LATE_PEDESTRIAN_YIELD"] = 7120.
    raw = json.loads((tmp_path / matrix["cases"][5]["scenario_path"]).read_text(encoding="utf-8"))
    late = evaluate_segment(late_summary, matrix["event_windows"]["late_pedestrian"],
                            "S2_P6_LATE_PEDESTRIAN_YIELD", raw["extensions"]["proposed_acceptance"])
    assert late["functional_passed"] is False
    assert late["phase_contract_enforced"] is True
    assert not late["checks"]["command_progress_windows_m:S2_P6_LATE_PEDESTRIAN_YIELD"]["passed"]
    matrix["event_windows"]["late_pedestrian"]["required_actor_trigger_ids"] = []
    manifest.write_text(json.dumps(matrix), encoding="utf-8")
    revised = summarize_manifests([manifest], ROOT / "config/s2_optimization_matrix.json")
    assert revised["latest_tasks"]["005:late_pedestrian"]["requirements_revised"] is True
    assert revised["passed_tasks"] == 1  # Current, stricter trigger check is satisfied by saved evidence.
    matrix["event_windows"]["late_pedestrian"]["start_m"] += 1
    manifest.write_text(json.dumps(matrix), encoding="utf-8")
    with pytest.raises(ValueError, match="event geometry/window changed"):
        summarize_manifests([manifest], ROOT / "config/s2_optimization_matrix.json")
    matrix["event_windows"]["late_pedestrian"]["start_m"] -= 1
    matrix["event_windows"]["late_pedestrian"]["required_actor_trigger_ids"] = ["late_crossing_pedestrian"]
    matrix["cases"][5]["perturbation"]["seed"] += 1
    manifest.write_text(json.dumps(matrix), encoding="utf-8")
    with pytest.raises(ValueError, match="perturbations changed"):
        summarize_manifests([manifest], ROOT / "config/s2_optimization_matrix.json")
    saved.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="summary hash"):
        reevaluate_manifest(manifest, ROOT / "config/s2_optimization_matrix.json")
