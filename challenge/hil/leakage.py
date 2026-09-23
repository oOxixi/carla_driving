"""Independent shortcut (lookup) probe for a replay input set.

A3's `shortcut_probe.py` reported that the D2 validation split could be matched
by pure table lookup: every validation instruction text already appeared in the
training split.  B3's job is independent verification, so rather than quoting
that result this module re-derives it from the files themselves.

What it measures, without any model and without touching RGB:

1. how many validation cases have an instruction text that appears verbatim in
   the training split;
2. how many validation scenario ids appear in the training split;
3. the "lookup baseline": memorise every (scenario_id, source_text) -> Teacher
   plan pair found in training, then answer each validation case from that table
   alone and count how often the key is found, and how often the recalled plan
   is also the validation case's own Teacher plan.

The numbers are input-quality facts.  The pass/fail policy for template leakage
belongs to B2; B3 reports the counts and the file digests that produced them.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .identity import sha256_file
from .run_io import read_jsonl


def request_of(record: Mapping[str, Any]) -> Mapping[str, Any]:
    """Accept both B1 release records and frozen-snapshot records."""
    for key in ("model_request", "request"):
        value = record.get(key)
        if isinstance(value, Mapping):
            return value
    return {}


def scenario_of(record: Mapping[str, Any]) -> str:
    metadata = record.get("metadata")
    if isinstance(metadata, Mapping) and metadata.get("scenario_id") is not None:
        return str(metadata["scenario_id"])
    if record.get("scenario_id") is not None:
        return str(record["scenario_id"])
    return "UNKNOWN"


def instruction_text(record: Mapping[str, Any]) -> str:
    return str(request_of(record).get("source_text", ""))


def _plan_key(plan: Any) -> str | None:
    if not isinstance(plan, Mapping):
        return None
    steps = plan.get("steps")
    if not isinstance(steps, Sequence) or isinstance(steps, (str, bytes)):
        return None
    behaviours = []
    for step in steps:
        if isinstance(step, Mapping):
            target = step.get("target")
            target_id = target.get("target_id") if isinstance(target, Mapping) else None
            behaviours.append(f"{step.get('behavior', 'UNKNOWN')}:{target_id}")
    return "|".join(behaviours)


def teacher_plan_of(record: Mapping[str, Any]) -> Any:
    value = record.get("teacher_plan")
    if value is None:
        value = record.get("teacher")
    return value


def _share(numerator: int, denominator: int) -> float | None:
    return (numerator / denominator) if denominator else None


def lookup_probe(
    train_records: Iterable[Mapping[str, Any]],
    validation_records: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    train = [record for record in train_records]
    validation = [record for record in validation_records]

    train_texts: set[str] = set()
    train_scenarios: set[str] = set()
    lookup: dict[tuple[str, str], set[str]] = {}
    for record in train:
        text = instruction_text(record)
        scenario = scenario_of(record)
        train_texts.add(text)
        train_scenarios.add(scenario)
        key = _plan_key(teacher_plan_of(record))
        if key is not None:
            lookup.setdefault((scenario, text), set()).add(key)

    text_hits = 0
    scenario_hits = 0
    key_found = 0
    key_found_and_agree = 0
    key_found_conflicting = 0
    unknown = 0
    for record in validation:
        text = instruction_text(record)
        scenario = scenario_of(record)
        if text and text in train_texts:
            text_hits += 1
        if scenario in train_scenarios:
            scenario_hits += 1
        expected = _plan_key(teacher_plan_of(record))
        if expected is None:
            unknown += 1
            continue
        recalled = lookup.get((scenario, text))
        if not recalled:
            continue
        key_found += 1
        if len(recalled) == 1 and expected in recalled:
            key_found_and_agree += 1
        else:
            key_found_conflicting += 1

    total = len(validation)
    agreement_share = _share(key_found_and_agree, total)
    validation_texts = {
        instruction_text(record) for record in validation if instruction_text(record)
    }
    train_texts.discard("")
    verdict = "LOOKUP_SHORTCUT_PRESENT" if (agreement_share or 0.0) >= 0.5 else "NO_LOOKUP_SHORTCUT_FOUND"
    return {
        "schema_version": "1.0",
        "train_cases": len(train),
        "validation_cases": total,
        "validation_teacher_plans_missing": unknown,
        "instruction_text_in_train": text_hits,
        "instruction_text_in_train_share": _share(text_hits, total),
        "scenario_id_in_train": scenario_hits,
        "scenario_id_in_train_share": _share(scenario_hits, total),
        "lookup_key_found": key_found,
        "lookup_key_found_share": _share(key_found, total),
        "lookup_recalls_teacher_plan": key_found_and_agree,
        "lookup_recalls_teacher_plan_share": agreement_share,
        "lookup_key_ambiguous": key_found_conflicting,
        "train_distinct_instruction_texts": len(train_texts),
        "validation_distinct_instruction_texts": len(validation_texts),
        "validation_cases_per_distinct_instruction_text": (
            (total / len(validation_texts)) if validation_texts else None
        ),
        "verdict": verdict,
        "policy_note": (
            "Facts only: B3 does not own the leakage policy. A high "
            "lookup_recalls_teacher_plan_share means behaviour matching on this input "
            "set can be produced without looking at the image, so it cannot support a "
            "generalisation claim until B2 issues a template/scenario-disjoint set."
        ),
    }


def probe_files(
    train_path: str | Path,
    validation_path: str | Path,
) -> dict[str, Any]:
    train_file = Path(train_path)
    validation_file = Path(validation_path)
    report = lookup_probe(read_jsonl(train_file), read_jsonl(validation_file))
    report["train_file"] = str(train_file.resolve())
    report["train_file_sha256"] = sha256_file(train_file)
    report["validation_file"] = str(validation_file.resolve())
    report["validation_file_sha256"] = sha256_file(validation_file)
    return report


def write_probe(report: Mapping[str, Any], path: str | Path) -> Path:
    from .run_io import write_json

    return write_json(path, dict(report))


__all__ = [
    "instruction_text",
    "lookup_probe",
    "probe_files",
    "request_of",
    "scenario_of",
    "teacher_plan_of",
    "write_probe",
]
