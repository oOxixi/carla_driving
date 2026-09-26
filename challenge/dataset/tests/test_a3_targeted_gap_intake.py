from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RELEASE = ROOT / "challenge" / "dataset" / "releases" / "d3_targeted_gap_strict_v1"


def _audit_function():
    path = ROOT / "challenge" / "distillation" / "audit_targeted_gap_intake.py"
    spec = importlib.util.spec_from_file_location("a3_targeted_gap_intake", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.audit_targeted_gap_intake


def test_targeted_gap_intake_passes_bytes_but_blocks_unsigned_teacher() -> None:
    report = _audit_function()(RELEASE, repo=ROOT, check_rgb=False)
    assert report["status"] == "BLOCKED"
    assert report["eligible_for_a3_derived_view"] is False
    assert report["release_integrity"]["status"] == "PASS"
    assert report["release_integrity"]["counts"] == {
        "train": 561,
        "val": 99,
        "hard_negative": 0,
    }
    assert report["prior_release_overlap"] == {
        "sample_ids_with_any_prior_release": 0,
        "targeted_train_groups_in_prior_val": 0,
        "targeted_val_groups_in_prior_train": 0,
    }
    assert report["teacher_provenance"]["model_ids"] == ["Qwen/Qwen3.5-2B"]
    assert report["teacher_provenance"]["model_revisions"] == []
    assert report["teacher_provenance"]["artifact_fingerprints"] == []
    assert report["teacher_provenance"]["matching_repository_manifests"] == []
    assert len(report["blockers"]) == 4
