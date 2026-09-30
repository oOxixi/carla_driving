from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from challenge.dataset.build_a3_final_cumulative_view import (
    FINAL_VIEW_VERSION,
    build_final_cumulative_view,
)


ROOT = Path(__file__).resolve().parents[3]
RELEASES = ROOT / "challenge/dataset/releases"


def _audit_function():
    path = ROOT / "challenge/distillation/audit_final_cumulative_view.py"
    spec = importlib.util.spec_from_file_location("audit_final_view", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.audit_final_cumulative_view


def test_final_view_is_strict_disjoint_and_reproducible(tmp_path: Path) -> None:
    sources = (
        RELEASES / "d2_v1_1",
        RELEASES / "d3_wave1_addon_v1",
        RELEASES / "d3_wave2_safe_short_v1",
        RELEASES / "d3_targeted_gap_strict_v1",
        RELEASES / "d3_turn_gap_60_strict_v1",
        RELEASES / "d3_gap300_strict_v1",
    )
    report = build_final_cumulative_view(
        *sources, tmp_path, check_images=False,
    )
    assert report["view_version"] == FINAL_VIEW_VERSION
    assert report["counts"] == {
        "raw_governed_train": 6007,
        "raw_governed_val": 1154,
        "train": 5826,
        "val": 1104,
        "excluded": 539,
        "gap300_train_addition": 697,
        "gap300_val_addition": 123,
    }
    assert report["count_policy"] == {
        "raw_release_rows_are_not_optimizer_rows": True,
        "d2_hard_negative_train_rows": 181,
        "d2_hard_negative_val_rows": 50,
        "all_hard_negatives_audit_only": True,
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
        FINAL_VIEW_VERSION
    }
    gap300 = [
        row for row in train + val
        if row["metadata"]["source_dataset_version"] == "b1_d3_gap300_strict_v1"
    ]
    assert len(gap300) == 820
    assert {row["metadata"]["teacher_model_revision"] for row in gap300} == {
        "15852e8c16360a2fea060d615a32b45270f8a8fc"
    }

    audit = _audit_function()(*sources, tmp_path, check_images=False)
    assert audit["status"] == "PASS"
    assert audit["counts"] == report["counts"]
