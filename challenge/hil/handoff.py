"""Export B3 runtime failures into a form A3 can actually consume.

Two very different artifacts live under ``failure_cases/`` and they must not be
conflated:

* **semantic failures** — a real ``ModelRequest`` from a frozen set produced a
  wrong or structurally invalid plan.  These carry a Teacher label, so they can
  be added to training / hard-case mining.  ``usable_for_training = true``.
* **robustness vectors** — synthetic malformed input (NaN distance, missing
  key, empty instruction).  There is no Teacher plan for them, and teaching the
  Student to answer them would be teaching it on garbage.  They stay test
  vectors: ``usable_for_training = false``.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .run_io import read_jsonl, write_json, write_jsonl


HANDOFF_SCHEMA_VERSION = "1.0"


def _canonical_sha256(payload: Any) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _failure_taxonomy(
    structural_failures: Sequence[str],
    outcome: str,
    teacher_behaviors: Sequence[str],
    student_behaviors: Sequence[str],
) -> list[str]:
    taxonomy: list[str] = []
    if outcome != "READY":
        taxonomy.append(f"RUNTIME_{outcome}")
    for item in structural_failures:
        if item.startswith("forbidden_output") or "forbidden_output" in item:
            taxonomy.append("FORBIDDEN_OUTPUT")
        elif item.startswith("step_count"):
            taxonomy.append("PLAN_LENGTH")
        elif item.startswith("missing_keys"):
            taxonomy.append("PLAN_SCHEMA")
        elif item.endswith("mismatch"):
            taxonomy.append("ID_ECHO")
        elif item == "must_stop_violated":
            taxonomy.append("SAFETY_CONSTRAINT")
        elif item.startswith("no_plan"):
            taxonomy.append("NO_PLAN")
        else:
            taxonomy.append("OTHER")
    if teacher_behaviors and student_behaviors:
        if teacher_behaviors[0] != student_behaviors[0]:
            taxonomy.append("BEHAVIOR_MISMATCH")
        if len(teacher_behaviors) != len(student_behaviors):
            taxonomy.append("LENGTH_MISMATCH")
    return sorted(set(taxonomy))


def export_handoff(
    *,
    out_dir: str | Path,
    run_id: str,
    replay_rows: Iterable[Mapping[str, Any]],
    plan_rows: Iterable[Mapping[str, Any]],
    abnormal_summary: Mapping[str, Any] | None,
    source_snapshot: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    plans_by_case = {
        (str(row.get("case_id")), int(row.get("round", 0))): row for row in plan_rows
    }
    semantic: list[dict[str, Any]] = []
    for row in replay_rows:
        failures = [item for item in str(row.get("structural_failures", "")).split("|") if item]
        outcome = str(row.get("outcome", "UNKNOWN"))
        if not failures and outcome == "READY":
            continue
        key = (str(row.get("case_id")), int(row.get("round", 0)))
        plan_row = plans_by_case.get(key)
        teacher_behaviors = [
            item for item in str(row.get("teacher_behavior_sequence", "")).split("|") if item
        ]
        student_behaviors = [
            item for item in str(row.get("student_behavior_sequence", "")).split("|") if item
        ]
        record = {
            "sample_id": row.get("sample_id"),
            "case_id": row.get("case_id"),
            "scenario_id": row.get("scenario_id"),
            "round": row.get("round"),
            "source": "hil_replay",
            "outcome": outcome,
            "structural_failures": failures,
            "failure_taxonomy": _failure_taxonomy(
                failures, outcome, teacher_behaviors, student_behaviors
            ),
            "teacher_behavior_sequence": teacher_behaviors,
            "student_behavior_sequence": student_behaviors,
            "model_request": (plan_row or {}).get("request"),
            "teacher_plan": (plan_row or {}).get("teacher_plan"),
            "student_plan": (plan_row or {}).get("student_plan"),
            "usable_for_training": bool((plan_row or {}).get("teacher_plan")),
            "training_note": (
                "has a Teacher label for the same ModelRequest"
                if (plan_row or {}).get("teacher_plan")
                else "no Teacher label available: test vector only"
            ),
        }
        record["record_sha256"] = _canonical_sha256(record)
        semantic.append(record)

    robustness: list[dict[str, Any]] = []
    if abnormal_summary:
        for item in abnormal_summary.get("cases", []):
            case_id = item.get("case_id")
            detail_path = target.parent / "failure_cases" / f"{case_id}.json"
            detail: dict[str, Any] = {}
            if detail_path.is_file():
                detail = json.loads(detail_path.read_text(encoding="utf-8"))
            record = {
                "case_id": case_id,
                "source": "abnormal_input_suite",
                "verdict": item.get("verdict"),
                "outcome": item.get("outcome"),
                "expectation_code": detail.get("expectation_code"),
                "matches_expectation": detail.get("matches_expectation"),
                "model_request": detail.get("request"),
                "usable_for_training": False,
                "training_note": (
                    "synthetic malformed input has no Teacher label; keep as a "
                    "robustness test vector, never as training data"
                ),
            }
            record["record_sha256"] = _canonical_sha256(record)
            robustness.append(record)

    handoff_path = write_jsonl(target / "handoff.jsonl", semantic + robustness)
    summary = {
        "schema_version": HANDOFF_SCHEMA_VERSION,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "counts": {
            "semantic_failures": len(semantic),
            "trainable": sum(1 for item in semantic if item["usable_for_training"]),
            "robustness_vectors": len(robustness),
        },
        "taxonomy_counts": _taxonomy_counts(semantic),
        "source_snapshot": dict(source_snapshot) if source_snapshot else None,
        "files": {"handoff.jsonl": str(handoff_path)},
        "join_key": "sample_id (falls back to case_id for synthetic vectors)",
        "consumer": "A3 distillation / hard-case mining",
        "rules": [
            "only records with usable_for_training=true may enter the training set",
            "robustness vectors validate fail-closed behaviour, not accuracy",
            "frozen Test failures must never be used for training",
        ],
    }
    write_json(target / "handoff_summary.json", summary)
    (target / "README.md").write_text(_readme(summary), encoding="utf-8")
    return summary


def _taxonomy_counts(records: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        for item in record.get("failure_taxonomy", ()):
            counts[str(item)] = counts.get(str(item), 0) + 1
    return counts


def _readme(summary: Mapping[str, Any]) -> str:
    counts = summary["counts"]
    return "\n".join(
        [
            "# B3 → A3 失败样本交接",
            "",
            f"run_id: `{summary['run_id']}`",
            "",
            f"- 语义失败（带 Teacher 标注，可训练）：{counts['trainable']} / {counts['semantic_failures']}",
            f"- 健壮性向量（合成非法输入，不可训练）：{counts['robustness_vectors']}",
            "",
            "记录格式与使用规则见 `hard_cases_handoff.md`。",
            "",
        ]
    )


def load_handoff(path: str | Path) -> list[dict[str, Any]]:
    return read_jsonl(path)


__all__ = ["export_handoff", "load_handoff", "HANDOFF_SCHEMA_VERSION"]
