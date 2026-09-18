from __future__ import annotations

from challenge.distillation.dataset import build_mock_records
from challenge.distillation.shortcut_probe import probe_records


def test_probe_keeps_hint_baseline_distinct_from_full_plan() -> None:
    rows = build_mock_records(10)
    for index in range(5):
        rows[index + 5]["input"]["source_text"] = rows[index]["input"]["source_text"]
    report = probe_records(rows[:5], rows[5:])
    assert report["val_samples"] == 5
    assert report["val_resolved_hint"] == 5
    assert report["val_rule_first_behavior_accuracy"] == 1.0
    assert report["val_text_only_plan_accuracy_on_covered"] == 1.0
    assert "text-lookup" in report["note"]
