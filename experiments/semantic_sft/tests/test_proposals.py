from __future__ import annotations

import copy
import json

import pytest

from experiments.semantic_sft.data import HERE, audit_rows, canonical_hash, chat_record, load_jsonl
from experiments.semantic_sft.proposals import draft_packets, draft_markdown, draft_summary


def inputs():
    return load_jsonl(HERE / "seeds.jsonl"), load_jsonl(HERE / "draft_labels.jsonl")


def unit_approve(row):
    # UNIT TEST metadata only; this function is not part of preparation code.
    row = copy.deepcopy(row)
    row.update(label=copy.deepcopy(row["proposal"]["label"]), annotation_status="APPROVED", split="train")
    row["reviews"] = [{"reviewer_id": name, "approved": True, "source_sha256": row["source_sha256"],
                       "label_sha256": canonical_hash(row["label"]), "reviewed_at": "2026-10-28T12:00:00+08:00"}
                      for name in ("UNIT_ONLY_A", "UNIT_ONLY_B")]
    return row


def errors(rows):
    return [e for issue in audit_rows(rows)["issues"] for e in issue["errors"]]


def test_all_drafts_are_source_bound_and_never_approved():
    seeds, proposals = inputs()
    before = copy.deepcopy((seeds, proposals))
    rows = draft_packets(seeds, proposals)
    assert len(rows) == 24
    assert all(r["label"] is None and r["reviews"] == [] and r["annotation_status"] == "DRAFT" for r in rows)
    assert all(r["proposal"]["author_type"] == "AI_ASSISTANT" for r in rows)
    assert all(r["proposal"]["source_sha256"] == r["source_sha256"] for r in rows)
    assert (seeds, proposals) == before
    summary = draft_summary(rows)
    assert summary["approved_rows"] == summary["human_labels"] == 0
    assert summary["contract_gap_rows"] == 3
    assert {r["sample_id"] for r in rows if r["proposal"]["contract_gap"]} == {
        "SFT_DRAFT_013", "SFT_DRAFT_014", "SFT_DRAFT_023"}
    report = audit_rows(rows)
    assert report["issue_counts"]["MISSING_LABEL"] == 24
    assert report["issue_counts"]["HUMAN_REVIEW_NOT_APPROVED"] == 24
    assert report["issue_counts"]["PROPOSAL_CONTRACT_GAP_QUARANTINED"] == 3
    assert not report["ready_for_training"]


@pytest.mark.parametrize("change", ["missing", "extra", "duplicate", "wrong_source"])
def test_proposal_binding_never_skips_or_overwrites_cases(change):
    seeds, proposals = inputs()
    if change == "missing":
        proposals.pop()
    elif change == "extra":
        extra = copy.deepcopy(proposals[0])
        extra["sample_id"] = "UNEXPECTED"
        proposals.append(extra)
    elif change == "duplicate":
        proposals.append(copy.deepcopy(proposals[0]))
    else:
        proposals[0]["source_text"] += "现在"
    with pytest.raises(ValueError):
        draft_packets(seeds, proposals)


@pytest.mark.parametrize("field,value", [("label", {}), ("reviews", [{"reviewer_id": "EXISTING"}]),
                                         ("annotation_status", "APPROVED")])
def test_draft_mode_cannot_replace_existing_human_work(field, value):
    seeds, proposals = inputs()
    seeds[0][field] = value
    with pytest.raises(ValueError, match="existing"):
        draft_packets(seeds, proposals)


def test_stale_proposal_hashes_are_rejected():
    rows = draft_packets(*inputs())
    row = rows[0]
    row["proposal"]["label"]["requires_confirmation"] = True
    assert "PROPOSAL_LABEL_HASH_MISMATCH" in errors([row])
    row["proposal"]["source_sha256"] = "0" * 64
    assert "PROPOSAL_SOURCE_MISMATCH" in errors([row])


def test_known_contract_gap_is_blocked_even_if_review_fields_are_filled():
    rows = draft_packets(*inputs())
    gap = unit_approve(rows[12])
    assert "PROPOSAL_CONTRACT_GAP_QUARANTINED" in errors([gap])
    with pytest.raises(ValueError, match="contract gaps"):
        chat_record(gap)


def test_proposal_never_substitutes_for_human_label():
    row = draft_packets(*inputs())[0]
    with pytest.raises(ValueError, match="never substitutes"):
        chat_record(row)
    approved = unit_approve(row)
    approved["label"] = {"steps": [{"action": "HOLD", "target_text": None, "direction": None,
        "speed_kph": None, "gap_m": None, "condition": None, "evidence": row["source_text"]}],
        "prohibited_actions": {}, "requires_confirmation": True}
    for review in approved["reviews"]:
        review["label_sha256"] = canonical_hash(approved["label"])
    exported = chat_record(approved)
    assert json.loads(exported["messages"][-1]["content"]) == approved["label"]
    assert approved["proposal"]["label"] != approved["label"]


def test_review_sheet_is_explicitly_unapproved():
    text = draft_markdown(draft_packets(*inputs()))
    assert text.count("## SFT_DRAFT_") == 24
    assert "- [x]" not in text.lower()
    assert text.count("**合同缺口隔离**") == 3
    assert "不是人工真值" in text


def test_invalid_model_authored_label_is_rejected_before_packet_creation():
    seeds, proposals = inputs()
    proposals[0]["label"]["steps"][0]["evidence"] = "不存在的指令"
    with pytest.raises(ValueError, match="literal support"):
        draft_packets(seeds, proposals)


def test_cli_draft_then_export_remains_blocked(tmp_path, monkeypatch):
    from experiments.semantic_sft import prepare
    target = tmp_path / "draft"
    monkeypatch.setattr(prepare, "output_directory", lambda path: path)
    monkeypatch.setattr("sys.argv", ["prepare", "draft", "--output-dir", str(target)])
    assert prepare.main() == 0
    rows = load_jsonl(target / "draft_review_queue.jsonl")
    assert len(rows) == 24 and all(r["label"] is None for r in rows)
    export = tmp_path / "export"
    monkeypatch.setattr("sys.argv", ["prepare", "export", "--input", str(target / "draft_review_queue.jsonl"),
                                     "--output-dir", str(export)])
    assert prepare.main() == 1
    assert not (export / "train.jsonl").exists()
    assert not (export / "val.jsonl").exists()
