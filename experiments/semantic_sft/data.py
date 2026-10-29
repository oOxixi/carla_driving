"""Reviewed semantic data preparation. No model/optimizer/serving imports."""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import subprocess
import unicodedata
from typing import Any

from qwen_service.task_understanding import EXAMPLES, validate_extraction
from qwen_service.clause_understanding import CLAUSE_EXAMPLES
from integration.qwen_profiles import PRODUCTION_QWEN_MODEL, PRODUCTION_QWEN_REVISION, PRODUCTION_QWEN_ARTIFACT_SHA256

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PLAN = json.loads((HERE / "plan.json").read_text(encoding="utf-8"))


def validate_plan_safety(plan: dict) -> None:
    expected = {"base_model": PRODUCTION_QWEN_MODEL, "base_revision": PRODUCTION_QWEN_REVISION,
                "expected_base_artifact_sha256": PRODUCTION_QWEN_ARTIFACT_SHA256,
                "protected_baseline_sha": "f92ac6fcc8e8c55e3b3a63825b6f4386d49b6d78",
                "stage": "PREPARATION_ONLY_NOT_TRAINING_APPROVED", "training_entrypoint": None,
                "model_outputs": "SEPARATE_ADAPTER_ONLY_NO_BASE_MERGE", "push_to_hub": False,
                "production_gpu_policy": "DO_NOT_SHARE_WITH_RUNNING_PRODUCTION"}
    for field, value in expected.items():
        if plan.get(field) != value:
            raise ValueError(f"unsafe preparation plan: {field}")


validate_plan_safety(PLAN)
SFT_SYSTEM = (
    "将原始驾驶指令分解为有序语义任务，返回JSON：steps、prohibited_actions、requires_confirmation。"
    "每步包含action、target_text、direction、speed_kph、gap_m、condition、evidence。"
    "动作码为KEEP_LANE、SET_SPEED、SLOW_DOWN、STOP、YIELD、FOLLOW、TURN_LEFT、TURN_RIGHT、"
    "CHANGE_LANE_LEFT、CHANGE_LANE_RIGHT、AVOID_OBSTACLE、RETURN_TO_LANE、PULL_OVER、HOLD。"
    "目标/条件/证据逐字引用原文；未给定参数为null。"
    "背景不是动作，禁止事项单独列出，不添加任务。仅理解指令，不输出车辆控制。"
)


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                                     separators=(",", ":")).encode()).hexdigest()


def text_hash(text: str) -> str:
    normalized = "".join(unicodedata.normalize("NFKC", text).casefold().split())
    return hashlib.sha256(normalized.encode()).hexdigest()


def source_hash(text: str) -> str:
    """Exact source identity for approvals, separate from normalized dedup keys."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def baseline_guard(root: Path = ROOT) -> dict:
    baseline = PLAN["protected_baseline_sha"]
    changed = subprocess.run(["git", "diff", "--name-only", baseline], cwd=root,
                             check=True, capture_output=True, text=True).stdout.splitlines()
    untracked = subprocess.run(["git", "ls-files", "--others", "--exclude-standard"], cwd=root,
                               check=True, capture_output=True, text=True).stdout.splitlines()
    prohibited = [p for p in changed + untracked if not p.startswith("experiments/semantic_sft/")]
    return {"baseline_sha": baseline, "passed": not prohibited, "outside_changes": sorted(set(prohibited))}


def output_directory(path: Path, root: Path = ROOT) -> Path:
    allowed = (root / "artifacts/semantic_sft").resolve()
    target = path.expanduser().resolve()
    if target == allowed or not target.is_relative_to(allowed):
        raise ValueError("output must be a new run directory under this workspace's artifacts/semantic_sft")
    if target.exists():
        raise FileExistsError("never overwrite an existing preparation artifact")
    return target


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise ValueError("each JSONL row must be an object")
                rows.append(row)
    if not rows:
        raise ValueError("empty data input")
    return rows


def protected_hashes() -> set[str]:
    texts = [text for text, _, _ in (*EXAMPLES, *CLAUSE_EXAMPLES)]
    for name in ("qwen_task_understanding_dev.jsonl", "qwen_task_understanding_probe.jsonl"):
        texts.extend(row["source_text"] for row in load_jsonl(ROOT / "config" / name))
    # Previously inspected real replay, not fresh training/validation material.
    texts.append("看到前方横穿马路的行人，先减速避让，确认行人离开后向左变道超越前方慢车，超越完成后回到原车道并恢复40公里每小时行驶")
    return {text_hash(text) for text in texts}


def review_packet(seed: dict) -> dict:
    for field in ("sample_id", "source_text", "semantic_family", "group_id"):
        if not isinstance(seed.get(field), str) or not seed[field].strip():
            raise ValueError(f"seed missing {field}")
    return {"sample_id": seed["sample_id"], "source_text": seed["source_text"],
            "source_sha256": source_hash(seed["source_text"]), "semantic_family": seed["semantic_family"],
            "group_id": seed["group_id"], "split": "UNASSIGNED", "label": None,
            "annotation_status": "DRAFT", "reviews": [],
            "origin": {"kind": "AUTHORED_TEXT_REQUIRES_HUMAN_REVIEW", "from_frozen_test": False,
                       "used_for_prompting": False, "used_for_tuning": False}}


def audit_rows(rows: list[dict], *, external_protected: set[str] | None = None,
               minimum_train: int | None = None, minimum_val: int | None = None) -> dict:
    import jsonschema
    validator = jsonschema.Draft202012Validator(
        json.loads((HERE / "record.schema.json").read_text(encoding="utf-8")),
        format_checker=jsonschema.FormatChecker())
    limits = PLAN["data_smoke_thresholds"]
    protected = protected_hashes() | (external_protected or set())
    issues = []
    splits = Counter()
    families = defaultdict(Counter)
    groups = defaultdict(set)
    actions = defaultdict(Counter)
    first_reviewed_groups = defaultdict(set)
    seen_ids = set()
    seen_texts = set()
    for number, row in enumerate(rows):
        schema_errors = list(validator.iter_errors(row))
        if schema_errors:
            issues.append({"row": number, "sample_id": row.get("sample_id") if isinstance(row, dict) else None,
                           "errors": ["INVALID_RECORD_SCHEMA:" + ".".join(map(str, schema_errors[0].absolute_path))]})
            continue
        errors = []
        sample_id = row.get("sample_id")
        if not isinstance(sample_id, str) or not sample_id.strip():
            errors.append("MISSING_SAMPLE_ID")
        if sample_id in seen_ids:
            errors.append("DUPLICATE_SAMPLE_ID")
        seen_ids.add(sample_id)
        source = row.get("source_text")
        if not isinstance(source, str) or not source.strip() or len(source) > 1000:
            errors.append("INVALID_SOURCE")
        else:
            digest = text_hash(source)
            if source_hash(source) != row.get("source_sha256"):
                errors.append("SOURCE_HASH_MISMATCH")
            if digest in protected:
                errors.append("PROTECTED_EVALUATION_OR_PROMPT_TEXT")
            if digest in seen_texts:
                errors.append("DUPLICATE_NORMALIZED_TEXT")
            seen_texts.add(digest)
        split = row.get("split")
        if split not in {"train", "val"}:
            errors.append("SPLIT_UNASSIGNED")
        else:
            splits[split] += 1
            family = row.get("semantic_family")
            if not isinstance(family, str) or not family.strip():
                errors.append("MISSING_SEMANTIC_FAMILY")
            else:
                families[split][family] += 1
            group = row.get("group_id")
            if not isinstance(group, str) or not group.strip():
                errors.append("MISSING_PARAPHRASE_GROUP")
            else:
                groups[group].add(split)
        origin = row.get("origin", {})
        if not isinstance(origin, dict) or origin.get("from_frozen_test") is not False or any(
            origin.get(key) is not False for key in ("used_for_prompting", "used_for_tuning")
        ):
            errors.append("ORIGIN_NOT_ELIGIBLE")
        if row.get("annotation_status") != "APPROVED":
            errors.append("HUMAN_REVIEW_NOT_APPROVED")
        proposal = row.get("proposal")
        if proposal is not None:
            if proposal["source_sha256"] != row["source_sha256"]:
                errors.append("PROPOSAL_SOURCE_MISMATCH")
            if proposal["label_sha256"] != canonical_hash(proposal["label"]):
                errors.append("PROPOSAL_LABEL_HASH_MISMATCH")
            try:
                validate_extraction(source, proposal["label"])
            except Exception:
                errors.append("INVALID_AI_PROPOSAL")
            if proposal["contract_gap"]:
                errors.append("PROPOSAL_CONTRACT_GAP_QUARANTINED")
        label = row.get("label")
        if not isinstance(label, dict):
            errors.append("MISSING_LABEL")
        elif isinstance(source, str):
            try:
                validate_extraction(source, label)
            except Exception as error:
                errors.append("INVALID_SEMANTIC_LABEL:" + type(error).__name__)
            else:
                if split in {"train", "val"}:
                    actions[split].update(step["action"] for step in label["steps"])
            approved_ids = set()
            for review in row.get("reviews", []):
                if isinstance(review, dict) and review.get("approved") is True and (
                    isinstance(review.get("reviewer_id"), str) and review["reviewer_id"].strip()
                ) and review.get("label_sha256") == canonical_hash(label) and (
                    review.get("source_sha256") == row["source_sha256"]
                ) and review.get("reviewed_at"):
                    approved_ids.add(review["reviewer_id"].strip().casefold())
            if len(approved_ids) < limits["independent_reviewers"]:
                errors.append("TWO_INDEPENDENT_LABEL_REVIEWS_REQUIRED")
            pending_review_errors = {"SPLIT_UNASSIGNED", "HUMAN_REVIEW_NOT_APPROVED", "TWO_INDEPENDENT_LABEL_REVIEWS_REQUIRED"}
            if (approved_ids and row["annotation_status"] in {"DRAFT", "APPROVED"}
                    and not (set(errors) - pending_review_errors)
                    and row["semantic_family"].strip() and row["group_id"].strip()):
                first_reviewed_groups[row["semantic_family"]].add(row["group_id"])
        if errors:
            issues.append({"row": number, "sample_id": sample_id, "errors": errors})
    global_errors = []
    overlaps = sorted(group for group, values in groups.items() if len(values) > 1)
    if overlaps:
        global_errors.append("PARAPHRASE_GROUP_SPLIT_LEAKAGE")
    for split, minimum in (("train", limits["minimum_train"] if minimum_train is None else minimum_train),
                           ("val", limits["minimum_val"] if minimum_val is None else minimum_val)):
        if splits[split] < minimum:
            global_errors.append(f"INSUFFICIENT_{split.upper()}_ROWS")
        if set(limits["required_families"]) - set(families[split]):
            global_errors.append(f"MISSING_{split.upper()}_SEMANTIC_FAMILIES")
    if external_protected is None:
        global_errors.append("EXTERNAL_FROZEN_TEST_EXCLUSION_REGISTRY_MISSING")
    counts = Counter(error for issue in issues for error in issue["errors"])
    return {"scope": "DATA_SMOKE_NOT_TRAINING_OR_COMPETITION_GATE", "rows": len(rows),
            "splits": dict(splits), "families": {k: dict(v) for k, v in families.items()},
            "action_counts": {k: dict(v) for k, v in actions.items()},
            "issues": issues, "issue_counts": dict(counts), "global_errors": global_errors,
            "overlapping_groups": overlaps, "data_ready_for_tokenization": not issues and not global_errors,
            "split_coverage_diagnostics": {
                "scope": "FIRST_REVIEWED_GROUP_COUNTS_NOT_FINAL_SPLIT_OR_TRAINING_APPROVAL",
                "minimum_independent_groups_for_both_splits": 2,
                "groups_by_family": {f: sorted(first_reviewed_groups[f]) for f in limits["required_families"]},
                "families_needing_more_groups": [f for f in limits["required_families"] if len(first_reviewed_groups[f]) < 2],
                "note": "Two groups is only a coverage lower bound; review, exclusions and sample-size gates still apply."},
            "ready_for_training": False, "training_blockers": ["NO_TRAINER_IMPLEMENTED", "NO_APPROVED_TOKENIZER_MASK_AUDIT", "NO_ISOLATED_GPU_APPROVAL"]}


def chat_record(row: dict) -> dict:
    if row.get("annotation_status") != "APPROVED" or not isinstance(row.get("label"), dict):
        raise ValueError("SFT export never substitutes an AI proposal for an approved human label")
    if row.get("proposal", {}).get("contract_gap"):
        raise ValueError("known proposal contract gaps cannot be exported as training labels")
    return {"sample_id": row["sample_id"], "group_id": row["group_id"], "messages": [
        {"role": "system", "content": SFT_SYSTEM},
        {"role": "user", "content": row["source_text"]},
        {"role": "assistant", "content": json.dumps(row["label"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))},
    ], "loss_roles": ["assistant"], "image_inputs": []}
