from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from challenge.dataset.build_a3_recovery_cumulative_view import (
    RECOVERY_VIEW_VERSION,
    build_recovery_cumulative_view,
)


ROOT = Path(__file__).resolve().parents[3]
RELEASES = ROOT / "challenge/dataset/releases"


def _audit_function():
    path = ROOT / "challenge/distillation/audit_recovery_cumulative_view.py"
    spec = importlib.util.spec_from_file_location("audit_recovery_view", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.audit_recovery_cumulative_view


def test_recovery_view_is_versioned_disjoint_and_reproducible(tmp_path: Path) -> None:
    sources = (
        RELEASES / "d2_v1_1",
        RELEASES / "d3_wave1_addon_v1",
        RELEASES / "d3_wave2_safe_short_v1",
        RELEASES / "d3_targeted_gap_strict_v1",
        RELEASES / "d3_turn_gap_60_strict_v1",
    )
    report = build_recovery_cumulative_view(
        *sources, tmp_path, check_images=False,
    )
    assert report["view_version"] == RECOVERY_VIEW_VERSION
    assert report["counts"] == {
        "train": 5129,
        "val": 981,
        "excluded": 539,
        "targeted_gap_train_addition": 561,
        "targeted_gap_val_addition": 99,
        "turn_gap_train_addition": 171,
        "turn_gap_val_addition": 29,
    }
    assert report["policies"]["frozen_test_used"] is False
    assert report["policies"]["current_v3_candidate_identity_unchanged"] is True
    assert str(ROOT) not in json.dumps(report)

    train = [json.loads(line) for line in (tmp_path / "train.jsonl").open(encoding="utf-8")]
    val = [json.loads(line) for line in (tmp_path / "val.jsonl").open(encoding="utf-8")]
    assert not ({row["sample_id"] for row in train} & {row["sample_id"] for row in val})
    assert not (
        {row["metadata"]["group_key"] for row in train}
        & {row["metadata"]["group_key"] for row in val}
    )
    assert {row["metadata"]["dataset_version"] for row in train + val} == {
        RECOVERY_VIEW_VERSION
    }
    assert sum(
        row["metadata"]["source_dataset_version"] == "b1_d3_targeted_gap_strict_v1"
        for row in train + val
    ) == 660
    assert sum(
        row["metadata"]["source_dataset_version"] == "b1_d3_turn_gap_60_strict_v1"
        for row in train + val
    ) == 200

    audit = _audit_function()(*sources, tmp_path, check_images=False)
    assert audit["status"] == "PASS"
    assert audit["counts"] == report["counts"]
