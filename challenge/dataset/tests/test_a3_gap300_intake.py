from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RELEASE = (
    ROOT
    / "challenge"
    / "dataset"
    / "releases"
    / "d3_gap300_strict_v1"
)

EXPECTED_GIT_COUNTS = {
    "95668ba3a466ae0dfcd73982f5a4a0d210b524c1": 770,
    "e150ae598d95cb024faebc1699b872d0de899e91": 50,
}


def _audit_module():
    path = (
        ROOT
        / "challenge"
        / "distillation"
        / "audit_gap300_intake.py"
    )
    spec = importlib.util.spec_from_file_location(
        "a3_gap300_intake",
        path,
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _assert_common_release_contract(report: dict) -> None:
    assert report["release_integrity"]["valid"] is True
    assert report["strict_positive_counts"] == {
        "train": 697,
        "val": 123,
    }

    provenance = report["teacher_provenance"]

    assert provenance["model_ids"] == [
        "Qwen/Qwen3.5-2B"
    ]

    # Historical rows themselves intentionally do not contain
    # exact revision/fingerprint fields. Those are supplied by
    # the detached immutable provenance attestation.
    assert provenance["model_revisions"] == []
    assert provenance["artifact_fingerprints"] == []

    assert (
        provenance["acquisition_git_sha_counts"]
        == EXPECTED_GIT_COUNTS
    )

    assert report["prior_release_overlap"] == {
        "sample_ids_with_any_prior_release": 0,
        "gap300_train_groups_in_prior_val": 0,
        "gap300_val_groups_in_prior_train": 0,
    }

    assert report["behavior_step_counts"]["TURN_LEFT"] == 230
    assert report["behavior_step_counts"]["YIELD"] == 75

    assert (
        report["count_policy"][
            "a3_strict_positive_train_rows_after_gap300"
        ]
        == 5826
    )


def test_gap300_intake_ready_with_exact_teacher_attestation() -> None:
    module = _audit_module()

    report = module.audit_gap300_intake(
        RELEASE,
        repo=ROOT,
        check_rgb=False,
    )

    _assert_common_release_contract(report)

    assert report["status"] == "READY"
    assert report["eligible_for_a3_final_view"] is True
    assert report["blockers"] == []
    assert report["required_b1_followup"] == []

    attestation = (
        report["teacher_provenance"][
            "immutable_attestation"
        ]
    )

    assert attestation["valid"] is True
    assert attestation["errors"] == []
    assert (
        attestation["signature_status"]
        == "CONTENT_BOUND_UNSIGNED"
    )

    teacher = attestation["teacher"]

    assert teacher == {
        "artifact_fingerprint_sha256": (
            "4bbf183b7b7f1ab9fb9eb325f189f4449d65e9fe664cbfe4bcc58a33888657fa"
        ),
        "dtype": "bfloat16",
        "model_id": "Qwen/Qwen3.5-2B",
        "model_revision": (
            "15852e8c16360a2fea060d615a32b45270f8a8fc"
        ),
        "quantization": None,
        "qwen_mode": "planner_v2",
    }

    coverage = attestation["coverage"]

    assert coverage["canonical_samples"] == 820
    assert (
        coverage["all_samples_share_teacher_identity"]
        is True
    )
    assert (
        coverage["acquisition_git_sha_counts"]
        == EXPECTED_GIT_COUNTS
    )


def test_gap300_intake_blocks_when_teacher_attestation_missing() -> None:
    module = _audit_module()

    original = module.DEFAULT_ATTESTATION

    try:
        module.DEFAULT_ATTESTATION = (
            "challenge/dataset/attestations/"
            "__missing_gap300_teacher_attestation_for_test__"
        )

        report = module.audit_gap300_intake(
            RELEASE,
            repo=ROOT,
            check_rgb=False,
        )
    finally:
        module.DEFAULT_ATTESTATION = original

    _assert_common_release_contract(report)

    assert report["status"] == "BLOCKED"
    assert report["eligible_for_a3_final_view"] is False

    attestation = (
        report["teacher_provenance"][
            "immutable_attestation"
        ]
    )

    assert attestation["valid"] is False
    assert attestation["errors"]

    assert any(
        "Teacher attestation file missing"
        in error
        for error in attestation["errors"]
    )

    assert report["blockers"]
    assert report["required_b1_followup"]
