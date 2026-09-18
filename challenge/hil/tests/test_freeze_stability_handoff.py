from __future__ import annotations

import json
from pathlib import Path

import pytest

from ..freeze import freeze_snapshot, load_frozen_snapshot
from ..handoff import export_handoff
from ..identity import sha256_file
from ..stability import run_soak
from ..samplers import TelemetrySpec
from .fakes import FakeRuntime
from .test_replay_and_failures import _request, _write_delivery


def test_freeze_then_reload_is_byte_identical(tmp_path: Path):
    delivery = tmp_path / "delivery"
    _write_delivery(delivery, "placeholder")
    _write_delivery(delivery, sha256_file(delivery / "rgb" / "frame.jpg"))
    result = freeze_snapshot(
        delivery_root=delivery, out_root=tmp_path / "frozen", name="s1"
    )
    manifest = result["manifest"]
    assert manifest["counts"]["cases"] == 1
    assert manifest["counts"]["rgb_copied"] == 1

    cases, info = load_frozen_snapshot(result["snapshot"])
    assert info["case_set_digest_sha256"] == manifest["case_set_digest_sha256"]
    assert cases[0].rgb_resolved is True
    assert cases[0].request["rgb_ref"].endswith(".jpg")
    assert cases[0].teacher_plan is not None


def test_frozen_snapshot_detects_request_tampering(tmp_path: Path):
    delivery = tmp_path / "delivery"
    _write_delivery(delivery, "placeholder")
    result = freeze_snapshot(delivery_root=delivery, out_root=tmp_path / "frozen", name="s1")
    cases_path = Path(result["snapshot"]) / "cases.jsonl"
    records = [json.loads(line) for line in cases_path.read_text("utf-8").splitlines()]
    records[0]["request"]["source_text"] = "tampered"
    cases_path.write_text(
        "\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8"
    )
    with pytest.raises(ValueError):
        load_frozen_snapshot(result["snapshot"])


def test_freeze_rejects_unsafe_snapshot_names(tmp_path: Path):
    with pytest.raises(ValueError):
        freeze_snapshot(delivery_root=tmp_path, out_root=tmp_path, name="../escape")


def test_soak_reports_success_and_drift(tmp_path: Path):
    from ..replay import ReplayCase

    case = ReplayCase(
        case_id="c1",
        sample_id="s1",
        scenario_id="SCN",
        request=_request(),
        teacher_plan=None,
        rgb_path=None,
        rgb_sha256=None,
        rgb_resolved=True,
        rgb_source="test",
        source_file="test",
    )
    result = run_soak(
        FakeRuntime(),
        [case],
        run_id="r",
        duration_s=0.05,
        telemetry=TelemetrySpec(interval_s=0.02),
        recovery_probe_cases=2,
    )
    summary = result["summary"]
    assert summary["iterations"] > 0
    assert summary["success"] is True
    assert summary["memory_drift_kib"] is not None
    assert summary["recovery_probe"]["errors"] == 0
    assert "latency_note" in summary


def test_soak_fails_when_the_runtime_is_broken():
    from ..replay import ReplayCase

    case = ReplayCase(
        case_id="c1",
        sample_id="s1",
        scenario_id="SCN",
        request=_request(),
        teacher_plan=None,
        rgb_path=None,
        rgb_sha256=None,
        rgb_resolved=True,
        rgb_source="test",
        source_file="test",
    )
    result = run_soak(
        FakeRuntime(outcome="ERROR"),
        [case],
        run_id="r",
        duration_s=0.02,
        telemetry=TelemetrySpec(interval_s=0.02),
        recovery_probe_cases=1,
    )
    assert result["summary"]["success"] is False
    assert result["summary"]["error_count"] > 0


def test_handoff_separates_trainable_hard_cases_from_robustness_vectors(tmp_path: Path):
    replay_rows = [
        {
            "case_id": "case-1",
            "sample_id": "s-1",
            "scenario_id": "SCN",
            "round": 1,
            "outcome": "READY",
            "structural_failures": "must_stop_violated",
            "teacher_behavior_sequence": "STOP",
            "student_behavior_sequence": "FOLLOW",
        }
    ]
    plan_rows = [
        {
            "case_id": "case-1",
            "round": 1,
            "request": _request(),
            "teacher_plan": {"steps": [{"behavior": "STOP"}]},
            "student_plan": {"steps": [{"behavior": "FOLLOW"}]},
        }
    ]
    abnormal = {
        "cases": [{"case_id": "nan_target_distance", "verdict": "OBSERVED_FAIL_CLOSED", "outcome": "READY"}]
    }
    summary = export_handoff(
        out_dir=tmp_path / "handoff",
        run_id="run-1",
        replay_rows=replay_rows,
        plan_rows=plan_rows,
        abnormal_summary=abnormal,
    )
    assert summary["counts"]["semantic_failures"] == 1
    assert summary["counts"]["trainable"] == 1
    assert summary["counts"]["robustness_vectors"] == 1
    assert "SAFETY_CONSTRAINT" in summary["taxonomy_counts"]
    records = [
        json.loads(line)
        for line in (tmp_path / "handoff" / "handoff.jsonl").read_text("utf-8").splitlines()
    ]
    trainable = [r for r in records if r["usable_for_training"]]
    vectors = [r for r in records if not r["usable_for_training"]]
    assert len(trainable) == 1 and len(vectors) == 1
    assert all(record.get("record_sha256") for record in records)


def test_handoff_marks_cases_without_teacher_labels_as_untrainable(tmp_path: Path):
    summary = export_handoff(
        out_dir=tmp_path / "handoff",
        run_id="run-1",
        replay_rows=[
            {
                "case_id": "case-9",
                "sample_id": "s-9",
                "round": 1,
                "outcome": "ERROR",
                "structural_failures": "no_plan_returned",
            }
        ],
        plan_rows=[{"case_id": "case-9", "round": 1, "request": _request(), "teacher_plan": None}],
        abnormal_summary=None,
    )
    assert summary["counts"]["semantic_failures"] == 1
    assert summary["counts"]["trainable"] == 0
