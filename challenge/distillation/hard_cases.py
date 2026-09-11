"""Mine validation disagreements without exposing or tuning on frozen Test."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Any, Mapping

import torch


@torch.no_grad()
def collect_hard_cases(
    batch: Mapping[str, Any],
    outputs: Mapping[str, torch.Tensor],
    *,
    split: str,
) -> list[dict[str, Any]]:
    normalized_split = split.strip().lower()
    if "test" in normalized_split or "frozen" in normalized_split:
        raise ValueError("hard-case mining is forbidden on frozen Test data")
    labels = batch["labels"]
    mask = labels["step_mask"].bool()
    predicted_behavior = outputs["behavior_logits"].argmax(-1).cpu()
    predicted_target = outputs["target_pointer_logits"].argmax(-1).cpu()
    predicted_lane = outputs["target_lane_logits"].argmax(-1).cpu()
    predicted_completion = outputs["completion_type_logits"].argmax(-1).cpu()
    predicted_failure = outputs["on_failure_logits"].argmax(-1).cpu()
    predicted_speed = outputs["target_speed_mps"].cpu()
    predicted_plan_length = outputs["plan_length_logits"].argmax(-1).cpu()
    predicted_confirmation = outputs["requires_confirmation_logits"].reshape(-1).ge(0).cpu()
    predicted_replan = outputs["replan_condition_logits"].ge(0).cpu()
    rows = []
    for index, sample_id in enumerate(batch["sample_ids"]):
        categories = []
        error_steps: dict[str, list[int]] = {}
        active = mask[index].cpu()
        comparisons = {
            "behavior": (
                predicted_behavior[index], labels["behavior"][index].cpu(),
            ),
            "target_pointer": (
                predicted_target[index], labels["target_pointer"][index].cpu(),
            ),
            "target_lane": (
                predicted_lane[index], labels["target_lane"][index].cpu(),
            ),
            "completion": (
                predicted_completion[index], labels["completion_type"][index].cpu(),
            ),
            "on_failure": (
                predicted_failure[index], labels["on_failure"][index].cpu(),
            ),
        }
        for category, (predicted, expected) in comparisons.items():
            failed = active & predicted.ne(expected)
            if failed.any():
                categories.append(category)
                error_steps[category] = failed.nonzero().flatten().tolist()
        speed_mask = labels["target_speed_mask"][index].bool().cpu() & active
        speed_error = (
            predicted_speed[index] - labels["target_speed_mps"][index].cpu()
        ).abs()
        failed_speed = speed_mask & speed_error.gt(1.0)
        if failed_speed.any():
            categories.append("target_speed")
            error_steps["target_speed"] = failed_speed.nonzero().flatten().tolist()
        if predicted_plan_length[index].item() != labels["plan_length"][index].cpu().item():
            categories.append("plan_length")
        if predicted_confirmation[index].item() != bool(
            labels["requires_confirmation"][index].cpu().item()
        ):
            categories.append("requires_confirmation")
        if not torch.equal(
            predicted_replan[index], labels["replan_conditions"][index].bool().cpu(),
        ):
            categories.append("replan_conditions")
        if not categories:
            continue
        tags = []
        if batch["sample_classes"][index] == "safety_critical":
            tags.append("safety_critical")
        if int(active.sum().item()) > 1:
            tags.append("multi_step_plan")
        rows.append({
            "sample_id": str(sample_id),
            "split": normalized_split,
            "categories": categories,
            "primary_category": categories[0],
            "error_count": len(categories),
            "error_steps": error_steps,
            "tags": tags,
            "request_id": batch["requests"][index].get("request_id"),
            "teacher_plan_id": batch["teacher_plans"][index].get("plan_id"),
            "teacher": {
                "behavior": labels["behavior"][index].cpu().tolist(),
                "target_pointer": labels["target_pointer"][index].cpu().tolist(),
                "target_lane": labels["target_lane"][index].cpu().tolist(),
                "completion": labels["completion_type"][index].cpu().tolist(),
                "on_failure": labels["on_failure"][index].cpu().tolist(),
                "plan_length": labels["plan_length"][index].cpu().item(),
            },
            "student": {
                "behavior": predicted_behavior[index].tolist(),
                "target_pointer": predicted_target[index].tolist(),
                "target_lane": predicted_lane[index].tolist(),
                "completion": predicted_completion[index].tolist(),
                "on_failure": predicted_failure[index].tolist(),
                "plan_length": predicted_plan_length[index].item(),
            },
            "metadata": batch["metadata"][index],
        })
    return rows


def write_hard_cases(path: str | Path, rows: list[Mapping[str, Any]]) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(dict(row), ensure_ascii=False, allow_nan=False) + "\n")
    return destination


def write_hard_case_bundle(
    directory: str | Path,
    rows: list[Mapping[str, Any]],
) -> dict[str, Any]:
    root = Path(directory)
    write_hard_cases(root / "validation_errors.jsonl", rows)
    category_counts = Counter(
        str(category) for row in rows for category in row.get("categories", ())
    )
    tag_counts = Counter(str(tag) for row in rows for tag in row.get("tags", ()))
    category_directory = root / "by_category"
    if category_directory.is_dir():
        for stale in category_directory.glob("*.jsonl"):
            stale.unlink()
    for category in sorted(category_counts):
        selected = [row for row in rows if category in row.get("categories", ())]
        write_hard_cases(category_directory / f"{category}.jsonl", selected)
    summary = {
        "hard_case_count": len(rows),
        "category_counts": dict(sorted(category_counts.items())),
        "tag_counts": dict(sorted(tag_counts.items())),
    }
    destination = root / "summary.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return summary


__all__ = ["collect_hard_cases", "write_hard_case_bundle", "write_hard_cases"]
