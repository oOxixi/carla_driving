from __future__ import annotations

import json
from pathlib import Path

from ..failure_cases import build_failure_cases, run_failure_cases
from ..identity import sha256_file
from ..columns import REPLAY_COLUMNS
from ..replay import (
    REQUEST_SOURCE_PREFERENCE,
    ReplayCase,
    load_replay_cases,
    run_replay,
    structural_checks,
)
from .fakes import FakeRuntime


def _request(**overrides):
    request = {
        "schema_version": "1.0",
        "request_id": "req-1",
        "command_id": "cmd-1",
        "created_at_ns": 1_000,
        "deadline_ns": 2_000,
        "source_text": "follow the lead vehicle",
        "rgb_ref": None,
        "targets": [
            {
                "target_id": "C-0001",
                "class": "vehicle",
                "distance_m": 12.0,
                "relative_speed_mps": -1.0,
                "confidence": 0.9,
                "relation": "center_ahead",
            }
        ],
        "constraints": {"must_stop": False, "allowed_behaviors": ["FOLLOW", "STOP"]},
        "scene_summary": {"traffic_light": "UNKNOWN", "risk_level": "LOW"},
    }
    request.update(overrides)
    return request


def _case(request=None, teacher=None) -> ReplayCase:
    return ReplayCase(
        case_id="case-1",
        sample_id="sample-1",
        scenario_id="SCN_1",
        request=request or _request(),
        teacher_plan=teacher,
        rgb_path=None,
        rgb_sha256=None,
        rgb_resolved=True,
        rgb_source="test",
        source_file="test",
    )


def _plan(**overrides):
    plan = {
        "schema_version": "2.0",
        "plan_type": "MANEUVER_SEQUENCE",
        "request_id": "req-1",
        "command_id": "cmd-1",
        "confidence": 0.9,
        "reason_code": "OK",
        "steps": [{"behavior": "FOLLOW"}],
    }
    plan.update(overrides)
    return plan


def test_structural_checks_accept_a_minimal_plan():
    assert structural_checks(_request(), _plan()) == ()


def test_structural_checks_catch_forbidden_outputs_and_bad_ids():
    failures = structural_checks(
        _request(), _plan(request_id="other", throttle=0.4)
    )
    assert "forbidden_output:throttle" in failures
    assert "request_id_echo_mismatch" in failures


def test_structural_checks_enforce_must_stop():
    request = _request(constraints={"must_stop": True, "allowed_behaviors": ["STOP"]})
    assert "must_stop_violated" in structural_checks(request, _plan())


def test_structural_checks_reject_too_many_steps():
    plan = _plan(steps=[{"behavior": "FOLLOW"}] * 5)
    assert "step_count_out_of_range:5" in structural_checks(_request(), plan)


def test_run_replay_records_diagnostics_not_accuracy():
    teacher = {"steps": [{"behavior": "STOP", "target": {"target_id": None}}]}
    result = run_replay(FakeRuntime(), [_case(teacher=teacher)], run_id="r", round_index=1)
    assert result.summary["ready"] == 1
    row = result.rows[0]
    assert row["diagnostic_only"] is True
    assert row["teacher_behavior_sequence"] == "STOP"
    assert row["student_behavior_sequence"] == "FOLLOW"
    assert row["behavior_match_ratio"] == 0.0
    assert result.summary["teacher_comparison"] == "DIAGNOSTIC_ONLY"


def test_run_replay_returns_traces_for_the_collector():
    result = run_replay(FakeRuntime(), [_case()], run_id="r", round_index=1)
    assert len(result.traces) == 1
    assert result.traces[0].outcome == "READY"


def test_replay_row_matches_the_frozen_column_set():
    result = run_replay(FakeRuntime(), [_case()], run_id="r", round_index=1)
    assert set(result.rows[0]) == set(REPLAY_COLUMNS)


def test_failure_case_library_is_unique_and_expectation_coded():
    cases = build_failure_cases(_request())
    ids = [case.case_id for case in cases]
    assert len(ids) == len(set(ids))
    assert {case.expectation_code for case in cases} <= {
        "MAY_PLAN",
        "MUST_NOT_CRASH",
        "MUST_FAIL_CLOSED",
    }
    assert "must_stop_with_narrow_allowlist" in ids
    assert "missing_targets_key" in ids


def test_failure_cases_record_verdicts_and_survive_nan(tmp_path: Path):
    cases = build_failure_cases(_request())
    summary = run_failure_cases(
        FakeRuntime(), cases, run_id="r", output_dir=tmp_path / "failure_cases"
    )
    assert summary["case_count"] == len(cases)
    nan_case = json.loads(
        (tmp_path / "failure_cases" / "nan_target_distance.json").read_text("utf-8")
    )
    assert nan_case["request"]["targets"][0]["distance_m"] == "NaN"
    assert nan_case["policy_owner"] == "B2"
    assert nan_case["expectation_owner"].startswith("B3 harness")


def test_failure_cases_flag_expectation_mismatch(tmp_path: Path):
    # A runtime that always returns a propulsion plan cannot satisfy the
    # hard-stop case, so the mismatch must be reported rather than hidden.
    case = [
        item
        for item in build_failure_cases(_request())
        if item.case_id == "must_stop_with_narrow_allowlist"
    ]
    summary = run_failure_cases(
        FakeRuntime(behavior="FOLLOW"), case, run_id="r", output_dir=tmp_path / "fc"
    )
    assert summary["expectation_match"] == 0
    assert summary["expectation_mismatch"][0]["case_id"] == "must_stop_with_narrow_allowlist"


def test_request_source_preference_is_declared():
    assert REQUEST_SOURCE_PREFERENCE[0] == "data/smoke_valid.jsonl"


def _write_delivery(delivery: Path, digest: str) -> None:
    (delivery / "data").mkdir(parents=True, exist_ok=True)
    (delivery / "manifests").mkdir(parents=True, exist_ok=True)
    (delivery / "rgb").mkdir(parents=True, exist_ok=True)
    (delivery / "rgb" / "frame.jpg").write_bytes(b"jpeg-bytes")
    record = {
        "sample_id": "s-1",
        "metadata": {"scenario_id": "SCN_1"},
        "model_request": _request(rgb_ref="some/original/path.jpg"),
        "teacher_plan": {"steps": [{"behavior": "FOLLOW"}]},
    }
    (delivery / "data" / "smoke_valid.jsonl").write_text(
        json.dumps(record) + "\n", encoding="utf-8"
    )
    (delivery / "manifests" / "rgb_manifest.json").write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "sample_id": "s-1",
                        "packaged_rgb_path": "rgb/frame.jpg",
                        "rgb_sha256": digest,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )


def test_load_replay_cases_from_a_synthetic_delivery(tmp_path: Path):
    delivery = tmp_path / "delivery"
    _write_delivery(delivery, "placeholder")
    digest = sha256_file(delivery / "rgb" / "frame.jpg")
    _write_delivery(delivery, digest)
    cases, info = load_replay_cases(delivery_root=delivery)
    assert info["records"] == 1
    assert info["rgb_unresolved"] == 0
    assert cases[0].rgb_resolved is True
    assert cases[0].rgb_source == "delivery_rgb_manifest"
    assert cases[0].request["rgb_ref"] == str((delivery / "rgb" / "frame.jpg").resolve())


def test_rgb_hash_mismatch_is_reported_not_hidden(tmp_path: Path):
    delivery = tmp_path / "delivery"
    _write_delivery(delivery, "0" * 64)
    cases, info = load_replay_cases(delivery_root=delivery)
    assert cases[0].rgb_resolved is False
    assert cases[0].rgb_source == "sha256_mismatch"
    assert info["rgb_unresolved"] == 1


def _write_release_layout(delivery: Path, repo_root: Path) -> None:
    """B1 D2 release layout: val.jsonl + rgb_mapping.json + images/."""
    (delivery / "images").mkdir(parents=True, exist_ok=True)
    image = delivery / "images" / "td_s1.jpg"
    image.write_bytes(b"jpeg-bytes")
    record = {
        "sample_id": "td_s1",
        "sample_class": "train",
        "metadata": {"scenario_id": "D2W2_S03_stop"},
        "model_request": _request(rgb_ref="artifacts/b1_d2/qwen_images/frame.jpg"),
        "teacher_plan": {"steps": [{"behavior": "STOP"}]},
    }
    (delivery / "val.jsonl").write_text(json.dumps(record) + "\n", encoding="utf-8")
    (delivery / "train.jsonl").write_text(json.dumps(record) + "\n", encoding="utf-8")
    (delivery / "rgb_mapping.json").write_text(
        json.dumps(
            {
                "td_s1": {
                    "original_rgb_ref": "artifacts/b1_d2/qwen_images/frame.jpg",
                    # repository-relative, exactly as B1 ships it
                    "release_rgb_ref": str(image.relative_to(repo_root)),
                }
            }
        ),
        encoding="utf-8",
    )


def test_release_layout_resolves_rgb_and_prefers_val(tmp_path: Path):
    delivery = tmp_path / "d2_v1_1"
    _write_release_layout(delivery, tmp_path)
    cases, info = load_replay_cases(delivery_root=delivery, repo_root=tmp_path)
    assert info["requests_path"].endswith("val.jsonl")
    assert info["rgb_unresolved"] == 0
    assert cases[0].rgb_resolved is True
    assert cases[0].rgb_source == "delivery_rgb_manifest"
    assert cases[0].rgb_sha256
    assert cases[0].request["rgb_ref"].endswith("td_s1.jpg")


def test_release_layout_never_auto_selects_reserved_test_candidates(tmp_path: Path):
    delivery = tmp_path / "d2_v1_1"
    _write_release_layout(delivery, tmp_path)
    (delivery / "reserved_test_candidates.jsonl").write_text("{}\n", encoding="utf-8")
    cases, info = load_replay_cases(delivery_root=delivery, repo_root=tmp_path)
    assert "reserved_test_candidates" not in info["requests_path"]
    assert all("reserved_test_candidates" not in case.source_file for case in cases)
