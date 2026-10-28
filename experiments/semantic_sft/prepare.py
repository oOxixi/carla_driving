"""Isolated review packets, data audit and SFT chat export; NO train command."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from integration.evidence_provenance import collect_provenance
from .data import (ROOT, HERE, PLAN, audit_rows, baseline_guard, canonical_hash, chat_record,
                   load_jsonl, output_directory, review_packet, SFT_SYSTEM)
from .environment import inventory


def external_registry(path: Path | None) -> set[str] | None:
    if path is None:
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("normalization") != "nfkc_casefold_remove_whitespace_v1" or not payload.get("publisher"):
        raise ValueError("external exclusion registry needs publisher and matching normalization")
    hashes = payload.get("text_sha256")
    if not isinstance(hashes, list) or not hashes or any(
        not isinstance(h, str) or len(h) != 64 or any(c not in "0123456789abcdef" for c in h) for h in hashes
    ):
        raise ValueError("external exclusion registry must contain non-empty SHA256 text hashes")
    return set(hashes)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("review", "hashes", "preflight", "export", "environment"))
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--external-protected-registry", type=Path)
    parser.add_argument("--model-path", type=Path)
    parser.add_argument("--tokenizer-smoke", action="store_true")
    args = parser.parse_args()
    guard = baseline_guard()
    if not guard["passed"]:
        raise ValueError(f"changes outside isolated preparation directory: {guard['outside_changes']}")
    output = output_directory(args.output_dir)
    input_path = args.input or (HERE / "seeds.jsonl" if args.mode == "review" else None)
    if args.mode in {"hashes", "preflight", "export"} and input_path is None:
        parser.error("--input reviewed JSONL is required")
    rows = load_jsonl(input_path) if input_path else None
    report = None
    if args.mode in {"preflight", "export"}:
        report = audit_rows(rows, external_protected=external_registry(args.external_protected_registry))
    output.mkdir(parents=True, exist_ok=False)
    manifest = {"scope": "PREPARATION_ONLY_NO_TRAINING_OR_SERVING", "mode": args.mode,
                "data_contract_version": "semantic_intent_review_v1",
                "baseline_guard": guard, "plan_sha256": canonical_hash(PLAN),
                "source_provenance": collect_provenance(ROOT),
                "base_model": PLAN["base_model"], "base_revision": PLAN["base_revision"],
                "expected_base_artifact_sha256": PLAN["expected_base_artifact_sha256"],
                "prompt_contract_sha256": hashlib.sha256(SFT_SYSTEM.encode()).hexdigest(),
                "input_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest() if input_path else None,
                "exclusion_registry_sha256": hashlib.sha256(args.external_protected_registry.read_bytes()).hexdigest()
                    if args.external_protected_registry else None,
                "status": "RUNNING", "training_started": False, "production_changed": False}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if args.mode == "review":
        packets = [review_packet(seed) for seed in rows]
        with (output / "review_queue.jsonl").open("x", encoding="utf-8") as stream:
            for packet in packets:
                stream.write(json.dumps(packet, ensure_ascii=False) + "\n")
        lines = ["# 语义数据人工复核清单", "", "全部为DRAFT，尚无批准标签；不可直接用于训练。", "",
                 "标注格式与审批要求见实验目录 README.md / ANNOTATION_GUIDE.md。", "",
                 "|编号|语义类别|同组改写标识|原始指令|", "|---|---|---|---|"]
        for packet in packets:
            values = [packet[k].replace("|", "\\|").replace("\n", " ")
                      for k in ("sample_id", "semantic_family", "group_id", "source_text")]
            lines.append("|" + "|".join(values) + "|")
        (output / "review_sheet.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        report = {"draft_rows": len(packets), "approved_rows": 0, "ready_for_training": False}
    elif args.mode == "hashes":
        report = {"approval_records_created": 0, "ready_for_training": False, "rows": [
            {"sample_id": row.get("sample_id"), "source_sha256": review_packet(row)["source_sha256"],
             "label_sha256": canonical_hash(row["label"]) if isinstance(row.get("label"), dict) else None}
            for row in rows]}
    elif args.mode == "environment":
        report = inventory(args.model_path, tokenizer_smoke=args.tokenizer_smoke)
    elif args.mode == "export" and report["data_ready_for_tokenization"]:
        for split in ("train", "val"):
            with (output / f"{split}.jsonl").open("x", encoding="utf-8") as stream:
                for row in rows:
                    if row["split"] == split:
                        stream.write(json.dumps(chat_record(row), ensure_ascii=False, allow_nan=False) + "\n")
        report["exported_sha256"] = {split: hashlib.sha256((output / f"{split}.jsonl").read_bytes()).hexdigest()
                                     for split in ("train", "val")}
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest["status"] = "COMPLETE"
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"mode": args.mode, "output_dir": str(output),
                      "data_ready_for_tokenization": report.get("data_ready_for_tokenization", False),
                      "ready_for_training": False, "baseline_unchanged": True}, ensure_ascii=False))
    if args.mode == "environment" and args.tokenizer_smoke and report.get("tokenizer_smoke", {}).get("status") != "PASS":
        return 1
    return 0 if args.mode in {"review", "hashes", "environment"} or report["data_ready_for_tokenization"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
