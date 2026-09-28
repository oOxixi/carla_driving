from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RELEASE = ROOT / "challenge" / "dataset" / "releases" / "d3_gap300_strict_v1"


def _audit_function():
    path = ROOT / "challenge" / "distillation" / "audit_gap300_intake.py"
    spec = importlib.util.spec_from_file_location("a3_gap300_intake", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.audit_gap300_intake


def test_gap300_intake_blocks_missing_exact_teacher_provenance() -> None:
    report = _audit_function()(RELEASE, repo=ROOT, check_rgb=False)
    assert report["status"] == "BLOCKED"
    assert report["eligible_for_a3_final_view"] is False
    assert report["release_integrity"]["valid"] is True
    assert report["strict_positive_counts"] == {"train": 697, "val": 123}
    assert report["teacher_provenance"]["model_ids"] == ["Qwen/Qwen3.5-2B"]
    assert report["teacher_provenance"]["model_revisions"] == []
    assert report["teacher_provenance"]["artifact_fingerprints"] == []
    assert report["teacher_provenance"]["acquisition_git_sha_counts"] == {
        "95668ba3a466ae0dfcd73982f5a4a0d210b524c1": 770,
        "e150ae598d95cb024faebc1699b872d0de899e91": 50,
    }
    assert report["prior_release_overlap"] == {
        "sample_ids_with_any_prior_release": 0,
        "gap300_train_groups_in_prior_val": 0,
        "gap300_val_groups_in_prior_train": 0,
    }
    assert report["behavior_step_counts"]["TURN_LEFT"] == 230
    assert report["behavior_step_counts"]["YIELD"] == 75
    assert report["count_policy"]["a3_strict_positive_train_rows_after_gap300"] == 5826
    assert report["blockers"]
