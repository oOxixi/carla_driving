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


def test_targeted_gap_intake_accepts_content_bound_teacher_addendum() -> None:
    report = _audit_function()(RELEASE, repo=ROOT, check_rgb=False)
    assert report["status"] == "READY"
    assert report["eligible_for_a3_derived_view"] is True
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
    assert report["teacher_provenance"]["matching_repository_manifests"] == [
        "challenge/teacher_targeted_gap_manifest.json"
    ]
    attestation = report["teacher_provenance"]["immutable_attestation"]
    assert attestation["valid"] is True
    assert attestation["signature_status"] == "CONTENT_BOUND_UNSIGNED"
    assert attestation["cryptographic_signature_present"] is False
    assert attestation["coverage"]["canonical_samples"] == 660
    assert attestation["teacher"]["model_revision"] == (
        "15852e8c16360a2fea060d615a32b45270f8a8fc"
    )
    assert report["blockers"] == []
    assert report["required_b1_followup"] == []
