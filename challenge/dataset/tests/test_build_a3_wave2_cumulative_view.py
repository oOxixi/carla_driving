from __future__ import annotations

import json
import importlib.util
from pathlib import Path

from challenge.dataset.build_a3_wave2_cumulative_view import (
    WAVE2_CUMULATIVE_VIEW_VERSION,
    build_wave2_cumulative_view,
)
ROOT = Path(__file__).resolve().parents[3]
D2 = ROOT / "challenge" / "dataset" / "releases" / "d2_v1_1"
D3_WAVE1 = ROOT / "challenge" / "dataset" / "releases" / "d3_wave1_addon_v1"
D3_WAVE2 = ROOT / "challenge" / "dataset" / "releases" / "d3_wave2_safe_short_v1"


def _audit_function():
    """Load the read-only audit without importing torch-heavy A3 package exports."""
    path = ROOT / "challenge" / "distillation" / "audit_wave2_cumulative_view.py"
    spec = importlib.util.spec_from_file_location("a3_wave2_view_audit", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.audit_wave2_cumulative_view


def test_wave2_cumulative_view_is_versioned_disjoint_and_auditable(tmp_path: Path) -> None:
    report = build_wave2_cumulative_view(
        D2, D3_WAVE1, D3_WAVE2, tmp_path, check_images=False,
    )
    assert report["view_version"] == WAVE2_CUMULATIVE_VIEW_VERSION
    assert report["counts"] == {
        "train": 4397,
        "val": 853,
        "excluded": 539,
        "d3_wave2_train_addition": 318,
        "d3_wave2_val_addition": 56,
        "d3_wave2_hard_negative_audit_only": 0,
    }
    assert report["policies"]["reserved_test_used"] is False
    assert report["policies"]["frozen_test_used"] is False
    assert report["policies"]["current_v3_candidate_identity_unchanged"] is True
    assert str(ROOT) not in json.dumps(report)

    train = [json.loads(line) for line in (tmp_path / "train.jsonl").open(encoding="utf-8")]
    val = [json.loads(line) for line in (tmp_path / "val.jsonl").open(encoding="utf-8")]
    assert not ({row["sample_id"] for row in train} & {row["sample_id"] for row in val})
    assert {row["metadata"]["dataset_version"] for row in train + val} == {
        WAVE2_CUMULATIVE_VIEW_VERSION
    }
    wave2 = [
        row for row in train + val
        if row["metadata"]["source_dataset_version"].endswith(
            "d3_expansion_wave2_targeted_v4_sync_v1"
        )
    ]
    assert len(wave2) == 374
    assert {row["metadata"]["source_view_version"] for row in wave2} == {
        "b1_d3_wave2_safe_short_v1"
    }
    assert {row["metadata"]["teacher_provenance_manifest"] for row in wave2} == {
        "challenge/teacher_pinned_manifest_wave2_sync_v1.json"
    }

    audit = _audit_function()(
        D2, D3_WAVE1, D3_WAVE2, tmp_path, check_images=False,
    )
    assert audit["status"] == "PASS"
    assert audit["counts"] == report["counts"]
