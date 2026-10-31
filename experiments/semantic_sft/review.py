"""Record an explicitly authorized first review, or audit CPU token masks; never train."""
from __future__ import annotations

import argparse
import copy
from datetime import datetime
import hashlib
import json
from pathlib import Path

from .data import (PLAN, SFT_SYSTEM, audit_rows, baseline_guard, canonical_hash,
                   load_jsonl, output_directory)
from .environment import assistant_token_mask


def first_review(rows, *, reviewer_id, reviewed_at, approval_reference, approval_quote):
    """Caller must possess direct human authorization. Metadata is not a signature."""
    for value in (reviewer_id, approval_reference, approval_quote):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("real reviewer identity, authorization reference and quote are required")
    timestamp = datetime.fromisoformat(reviewed_at.replace("Z", "+00:00"))
    if timestamp.utcoffset() is None:
        raise ValueError("review recording timestamp needs a timezone")
    initial = audit_rows(rows)
    permitted = {"SPLIT_UNASSIGNED", "HUMAN_REVIEW_NOT_APPROVED", "MISSING_LABEL",
                 "PROPOSAL_CONTRACT_GAP_QUARANTINED"}
    if any(set(issue["errors"]) - permitted for issue in initial["issues"]):
        raise ValueError("invalid draft input; repair source/schema/proposal before recording review")
    updated = copy.deepcopy(rows)
    accepted, quarantined = [], []
    for row in updated:
        if row["label"] is not None or row["reviews"] or row["annotation_status"] != "DRAFT":
            raise ValueError("never overwrite existing human labels or reviews")
        proposal = row.get("proposal")
        if not proposal:
            raise ValueError("first-review mode requires source-bound proposals")
        if proposal["contract_gap"]:
            quarantined.append(row["sample_id"])
            continue
        row["label"] = copy.deepcopy(proposal["label"])
        row["reviews"] = [{"reviewer_id": reviewer_id.strip(), "approved": True,
            "source_sha256": row["source_sha256"], "label_sha256": canonical_hash(row["label"]),
            "reviewed_at": reviewed_at}]
        if (PLAN['data_smoke_thresholds']['independent_reviewers'] == 1
                and reviewer_id.strip().casefold() == PLAN['review_owner_id'].casefold()):
            row['annotation_status'] = 'APPROVED'
        # Other reviewers or legacy two-person policy remain pending; no split is invented.
        accepted.append({"sample_id": row["sample_id"], "source_sha256": row["source_sha256"],
                         "label_sha256": canonical_hash(row["label"])})
    return updated, {"scope": "HUMAN_REVIEW_RECORD_NOT_TRAINING_GATE", "reviewer_id": reviewer_id,
        "owner_finalized_rows": sum(row['annotation_status'] == 'APPROVED' for row in updated),
        "review_policy": PLAN.get('review_policy'),
        "approval_reference": approval_reference, "approval_quote": approval_quote,
        "review_recorded_at": reviewed_at, "timestamp_note": "Authorization recorded now; not an inferred message timestamp.",
        "identity_note": "Caller-provided identity, not a verified signature; retain actual human authorization.",
        "accepted_rows": accepted, "quarantined_sample_ids": quarantined,
        "ready_for_training": False, "second_reviewer_created": False}


def token_audit(rows, tokenizer):
    """Read labels only for mask diagnostics. Never export token IDs or training records."""
    checks, skipped = [], []
    structural = audit_rows(rows)
    permitted = {"SPLIT_UNASSIGNED", "HUMAN_REVIEW_NOT_APPROVED", "MISSING_LABEL",
                 "PROPOSAL_CONTRACT_GAP_QUARANTINED", "TWO_INDEPENDENT_LABEL_REVIEWS_REQUIRED", "OWNER_LABEL_REVIEW_REQUIRED"}
    if any(set(issue["errors"]) - permitted for issue in structural["issues"]):
        raise ValueError("invalid review records cannot enter token diagnostics")
    for row in rows:
        if row.get("proposal", {}).get("contract_gap") or row.get("label") is None:
            skipped.append(row["sample_id"])
            continue
        digest = canonical_hash(row["label"])
        if not any(r["approved"] and r["source_sha256"] == row["source_sha256"] and
                   r["label_sha256"] == digest for r in row["reviews"]):
            raise ValueError("token audit requires at least one source/label-bound human review")
        messages = [{"role": "system", "content": SFT_SYSTEM},
                    {"role": "user", "content": row["source_text"]},
                    {"role": "assistant", "content": json.dumps(row["label"], ensure_ascii=False,
                                              sort_keys=True, separators=(",", ":"))}]
        check = {"sample_id": row["sample_id"], "source_sha256": row["source_sha256"], "label_sha256": digest}
        try:
            tokens = assistant_token_mask(tokenizer, messages, max_length=PLAN["max_sequence_length_candidate"])
            boundary = tokens["prompt_tokens"]
            masked = all(value == -100 for value in tokens["labels"][:boundary])
            if not masked:
                raise ValueError("prompt loss is not fully masked")
            check.update(status="PASS", prompt_tokens=boundary,
                         assistant_tokens=tokens["assistant_tokens"], prompt_loss_masked=masked)
        except ValueError as exc:
            check.update(status="FAIL", reason=str(exc))
        checks.append(check)
    return {"scope": "CPU_TOKEN_DIAGNOSTICS_NOT_APPROVED_TRAINING_DATA", "checks": checks,
        "checked_rows": len(checks), "skipped_sample_ids": skipped,
        "all_checked_passed": bool(checks) and all(c["status"] == "PASS" for c in checks),
        "max_total_tokens": max((c.get("prompt_tokens", 0) + c.get("assistant_tokens", 0) for c in checks), default=0),
        "ready_for_training": False, "model_weights_loaded": False, "training_started": False,
        "full_training_pipeline_verified": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("first-review", "token-audit"))
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--reviewer-id")
    parser.add_argument("--reviewed-at")
    parser.add_argument("--approval-reference")
    parser.add_argument("--approval-quote")
    parser.add_argument("--model-path", type=Path)
    args = parser.parse_args()
    guard = baseline_guard()
    if not guard["passed"]:
        raise ValueError("changes outside isolated preparation directory")
    output = output_directory(args.output_dir)
    rows = load_jsonl(args.input)
    if args.mode == "first-review":
        if not args.reviewed_at:
            parser.error("first-review requires the actual review recording timestamp")
        updated, report = first_review(rows, reviewer_id=args.reviewer_id, reviewed_at=args.reviewed_at,
            approval_reference=args.approval_reference, approval_quote=args.approval_quote)
    else:
        if not args.model_path:
            parser.error("token-audit requires a read-only local model path")
        from transformers import AutoTokenizer
        model_path = args.model_path.resolve(strict=True)
        tokenizer = AutoTokenizer.from_pretrained(str(model_path), local_files_only=True, trust_remote_code=False)
        if not getattr(tokenizer, "chat_template", None):
            tokenizer.chat_template = (model_path / "chat_template.jinja").read_text(encoding="utf-8")
        report = token_audit(rows, tokenizer)
    output.mkdir(parents=True, exist_ok=False)
    if args.mode == "first-review":
        with (output / "review_queue.jsonl").open("x", encoding="utf-8") as stream:
            for row in updated:
                stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
    report["input_sha256"] = hashlib.sha256(args.input.read_bytes()).hexdigest()
    report["baseline_guard"] = guard
    report["base_model"] = PLAN["base_model"]
    report["expected_base_revision"] = PLAN["base_revision"]
    report["base_artifact_fingerprint_verified_by_this_tool"] = False
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"mode": args.mode, "output_dir": str(output), "ready_for_training": False}))
    return 0 if args.mode == "first-review" or report["all_checked_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
