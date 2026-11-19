import copy

import pytest

from experiments.semantic_sft.data import HERE, audit_rows, chat_record, load_jsonl
from experiments.semantic_sft.proposals import draft_packets
from experiments.semantic_sft.review import first_review, token_audit
from experiments.semantic_sft.tests.test_preparation import ToyTokenizer


def packets():
    return draft_packets(load_jsonl(HERE / "seeds.jsonl"), load_jsonl(HERE / "draft_labels.jsonl"))


def reviewed(rows=None, **overrides):
    kwargs = dict(reviewer_id="UNIT_ONLY_HUMAN", reviewed_at="2026-10-29T20:02:20+08:00",
                  approval_reference="UNIT_ONLY_AUTHORIZATION", approval_quote="UNIT_ONLY_APPROVAL")
    kwargs.update(overrides)
    return first_review(packets() if rows is None else rows, **kwargs)


def test_single_review_preserves_quarantine_and_does_not_claim_final_approval():
    original = packets()
    before = copy.deepcopy(original)
    rows, receipt = reviewed(original)
    assert original == before
    assert len(receipt["accepted_rows"]) == 21
    assert len(receipt["quarantined_sample_ids"]) == 3
    assert all(r["annotation_status"] == "DRAFT" and r["split"] == "UNASSIGNED" for r in rows)
    assert sum(len(r["reviews"]) for r in rows) == 21
    assert sum(r["label"] is not None for r in rows) == 21
    report = audit_rows(rows)
    assert report["issue_counts"]["TWO_INDEPENDENT_LABEL_REVIEWS_REQUIRED"] == 21
    assert not report["data_ready_for_tokenization"]
    with pytest.raises(ValueError):
        chat_record(rows[0])


@pytest.mark.parametrize("field,value", [("reviewer_id", ""), ("approval_reference", ""),
    ("approval_quote", ""), ("reviewed_at", "2026-10-29T20:02:20")])
def test_review_needs_explicit_metadata_and_timezone(field, value):
    with pytest.raises(ValueError):
        reviewed(**{field: value})


def test_existing_human_work_is_not_overwritten():
    rows, _ = reviewed()
    with pytest.raises(ValueError):
        reviewed(rows)


def test_stale_proposal_is_not_recorded_as_approved():
    rows = packets()
    rows[0]["source_sha256"] = "0" * 64
    with pytest.raises(ValueError):
        reviewed(rows)


def test_token_audit_masks_21_and_never_exports_tokens_or_certifies_training():
    rows, _ = reviewed()
    report = token_audit(rows, ToyTokenizer())
    assert report["checked_rows"] == 21 and len(report["skipped_sample_ids"]) == 3
    assert report["all_checked_passed"] and not report["ready_for_training"]
    assert not report["model_weights_loaded"]
    assert all("input_ids" not in c and "labels" not in c for c in report["checks"])
    assert all(c["prompt_loss_masked"] for c in report["checks"])


def test_token_audit_rejects_unbound_human_review_and_reports_truncation():
    rows, _ = reviewed()
    rows[0]["reviews"][0]["label_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="bound human review"):
        token_audit(rows, ToyTokenizer())
    class TooLong(ToyTokenizer):
        def __call__(self, text, **kwargs):
            return {"input_ids": super().__call__(text, **kwargs)["input_ids"] * 5000}
    report = token_audit(reviewed()[0], TooLong())
    assert not report["all_checked_passed"]
