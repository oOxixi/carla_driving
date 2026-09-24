from __future__ import annotations

import json
from pathlib import Path

from challenge.dataset.build_a3_cumulative_view import (
    CUMULATIVE_VIEW_VERSION,
    build_cumulative_view,
)


ROOT = Path(__file__).resolve().parents[3]
D2 = ROOT / "challenge" / "dataset" / "releases" / "d2_v1_1"
D3 = ROOT / "challenge" / "dataset" / "releases" / "d3_wave1_addon_v1"


def test_build_cumulative_view_is_strict_portable_and_disjoint(tmp_path: Path) -> None:
    report = build_cumulative_view(D2, D3, tmp_path, check_d3_images=False)
    assert report["view_version"] == CUMULATIVE_VIEW_VERSION
    assert report["counts"] == {
        "train": 4079,
        "val": 797,
        "excluded": 539,
        "d3_hard_negative_audit_only": 308,
    }
    assert report["policies"]["reserved_test_used"] is False
    assert report["policies"]["d3_hard_negative_used_for_training"] is False
    assert report["source_evidence"]["d2"]["release_dir"].startswith("challenge/")
    assert report["source_evidence"]["d3"]["release_dir"].startswith("challenge/")
    assert str(ROOT) not in json.dumps(report)

    train_rows = [json.loads(line) for line in (tmp_path / "train.jsonl").open(encoding="utf-8")]
    val_rows = [json.loads(line) for line in (tmp_path / "val.jsonl").open(encoding="utf-8")]
    assert not ({row["sample_id"] for row in train_rows} & {row["sample_id"] for row in val_rows})
    assert {row["metadata"]["dataset_version"] for row in train_rows + val_rows} == {
        CUMULATIVE_VIEW_VERSION
    }
    d3_rows = [
        row for row in train_rows + val_rows
        if row["metadata"]["source_dataset_version"].endswith("d3_expansion_wave1_v4")
    ]
    assert len(d3_rows) == 2055
    assert {row["metadata"]["source_view_version"] for row in d3_rows} == {
        "b1_d3_wave1_addon_v1"
    }
