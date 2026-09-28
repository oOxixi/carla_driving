from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "challenge" / "hil" / "evidence" / "a3_fp32_candidate_v3_20260926"


def _audit_function():
    path = ROOT / "challenge" / "distillation" / "audit_b3_v3_diagnostic.py"
    spec = importlib.util.spec_from_file_location("audit_b3_v3_diagnostic", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.audit_b3_v3_diagnostic


def test_b3_v3_evidence_is_accepted_without_promotion() -> None:
    report = _audit_function()(EVIDENCE)
    assert report["status"] == "DIAGNOSTIC_EVIDENCE_ACCEPTED"
    assert report["eligible_for_promotion"] is False
    assert report["errors"] == []
    assert report["checks"] == {
        "handoff_integrity": "PASS",
        "files_checked": 9,
        "diagnostic_runs_fail_closed": True,
        "torch_onnx_consistency": True,
        "soak_duration_met": True,
        "soak_errors": 0,
    }
    assert report["diagnostic_metrics"]["d2_v1_1"]["behavior_match"] == 0.951763
    assert report["diagnostic_metrics"]["targeted_gap"]["behavior_match"] == 0.919192
    assert report["diagnostic_metrics"]["targeted_gap"]["student_outputs"] == 6
    assert report["diagnostic_metrics"]["targeted_gap"]["teacher_outputs"] == 9
    assert report["diagnostic_metrics"]["int8_target_speed"] == {
        "targeted_gap_min_cosine": 0.999835,
        "d3_wave2_min_cosine": 0.989066,
        "d3_wave2_below_0_99": 8,
    }
    assert report["formal_scope"]["b3_diagnostic_can_open_a3_gate"] is False
    assert len(report["evidence_sha256"]) == 7


def test_missing_b3_evidence_fails_closed(tmp_path: Path) -> None:
    report = _audit_function()(tmp_path)
    assert report["status"] == "INVALID"
    assert report["eligible_for_promotion"] is False
    assert len(report["errors"]) == 7
