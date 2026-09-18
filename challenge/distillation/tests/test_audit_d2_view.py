from __future__ import annotations

import json
from pathlib import Path

import pytest

from challenge.dataset.build_a3_d2_view import build_view
from challenge.distillation.audit_d2_view import audit_view


ROOT = Path(__file__).resolve().parents[3]
RELEASE = ROOT / "challenge" / "dataset" / "releases" / "d2_v1_1"


def test_audit_signed_view_reports_coverage_without_test_split(tmp_path: Path) -> None:
    build_view(RELEASE, tmp_path)
    report = audit_view(RELEASE, tmp_path)
    assert report["status"] == "PASS"
    assert report["splits"]["train"]["samples"] == 2332
    assert report["splits"]["val"]["samples"] == 489
    assert report["excluded_count"] == 231
    assert sum(report["splits"]["train"]["sample_classes"].values()) == 2332
    assert sum(report["splits"]["val"]["plan_lengths"].values()) == 489
    assert report["splits"]["val"]["class_by_family"]["safety_critical:safety_D"] == 1
    assert report["splits"]["val"]["missing_behavior_labels"]
    assert "Town03_Opt" not in report["splits"]["val"]["maps"]
    assert "reserved" not in json.dumps(report).lower()


def test_audit_rejects_changed_view(tmp_path: Path) -> None:
    build_view(RELEASE, tmp_path)
    with (tmp_path / "train.jsonl").open("a", encoding="utf-8") as stream:
        stream.write("{}\n")
    with pytest.raises(ValueError, match="view file changed"):
        audit_view(RELEASE, tmp_path)
