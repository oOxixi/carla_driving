"""Bind explicitly authored AI drafts to source, without creating approvals."""
from __future__ import annotations

from collections import Counter
import copy
import json

from qwen_service.task_understanding import validate_extraction
from .data import canonical_hash, protected_hashes, review_packet, source_hash, text_hash


def draft_packets(seeds: list[dict], proposals: list[dict]) -> list[dict]:
    seed_ids = [s["sample_id"] for s in seeds]
    proposal_ids = [p["sample_id"] for p in proposals]
    if len(set(seed_ids)) != len(seed_ids) or len(set(proposal_ids)) != len(proposal_ids):
        raise ValueError("duplicate seed/proposal ID; no implicit last-write wins")
    if set(seed_ids) != set(proposal_ids):
        raise ValueError("every seed must have exactly one proposal; no missing or extra cases")
    by_id = {p["sample_id"]: p for p in proposals}
    protected = protected_hashes()
    packets = []
    for seed in seeds:
        if seed.get("label") is not None or seed.get("reviews") or seed.get("annotation_status", "DRAFT") != "DRAFT":
            raise ValueError("draft mode cannot replace an existing label, review or approval")
        proposal = by_id[seed["sample_id"]]
        if seed["source_text"] != proposal["source_text"]:
            raise ValueError(f"proposal source mismatch: {seed['sample_id']}")
        if text_hash(seed["source_text"]) in protected:
            raise ValueError("protected evaluation/prompt text cannot become new training proposals")
        notes = proposal.get("review_notes")
        if not isinstance(notes, list) or not notes or any(not isinstance(n, str) or not n.strip() for n in notes):
            raise ValueError("proposal needs explicit human review notes")
        if type(proposal.get("contract_gap")) is not bool:
            raise ValueError("proposal must declare whether a contract gap is known")
        validate_extraction(seed["source_text"], proposal["label"])
        packet = review_packet(seed)
        packet["proposal"] = {
            "author_type": "AI_ASSISTANT", "status": "UNREVIEWED",
            "source_sha256": source_hash(seed["source_text"]),
            "label_sha256": canonical_hash(proposal["label"]),
            "label": copy.deepcopy(proposal["label"]),
            "review_notes": list(notes), "contract_gap": proposal["contract_gap"],
        }
        # Deliberately do not copy the draft into packet.label or generate reviews.
        packets.append(packet)
    return packets


def draft_summary(packets: list[dict]) -> dict:
    return {"scope": "AI_DRAFTS_NOT_GROUND_TRUTH_NOT_TRAINING_DATA", "draft_rows": len(packets),
            "approved_rows": 0, "human_labels": 0,
            "contract_gap_rows": sum(p["proposal"]["contract_gap"] for p in packets),
            "families": dict(Counter(p["semantic_family"] for p in packets)),
            "ready_for_training": False}


def draft_markdown(packets: list[dict]) -> str:
    def cell(value):
        if value is None:
            return "—"
        return str(value).replace("|", "\\|").replace("\n", " ")

    lines = ["# AI待审标签", "", "以下不是人工真值，不可直接训练；所有label仍为空、审批记录仍为空。",
             "合同缺口样本保留并隔离，不得直接批准。请按ANNOTATION_GUIDE.md进行真实双人复核。", ""]
    for packet in packets:
        proposal = packet["proposal"]
        label = proposal["label"]
        lines.extend([f"## {packet['sample_id']}", "", f"原句：{packet['source_text']}", "",
                      f"类别：{packet['semantic_family']}；改写组：{packet['group_id']}。", "",
                      "状态：**合同缺口隔离**。" if proposal["contract_gap"] else "状态：AI草稿，待人工确认。", "",
                      "|顺序|动作|目标|方向|km/h|距离m|条件|引用证据|", "|---|---|---|---|---|---|---|---|"])
        for index, step in enumerate(label["steps"], 1):
            values = [index, step["action"], step["target_text"], step["direction"],
                      step["speed_kph"], step["gap_m"], step["condition"], step["evidence"]]
            lines.append("|" + "|".join(cell(v) for v in values) + "|")
        lines.extend(["", "禁止事项候选：`" + json.dumps(label["prohibited_actions"], ensure_ascii=False) + "`。",
                      f"需要确认候选：`{str(label['requires_confirmation']).lower()}`。", "",
                      "复核提示：", ""])
        lines.extend("- " + note for note in proposal["review_notes"])
        lines.extend(["", "- [ ] 复核人1已独立核对原句、任务、参数及条件。",
                      "- [ ] 复核人2已独立核对并处理分歧。",
                      "", "以上勾选不自动产生JSON审批记录。", ""])
    return "\n".join(lines) + "\n"
