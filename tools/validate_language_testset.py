"""Validate the frozen Chinese driving-language proxy test set."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1.0"
CATEGORIES = {
    "ordinary_synonym",
    "negation",
    "compound",
    "ambiguous_target",
    "missing_target",
    "dangerous_conflict",
    "low_asr_confidence",
}
ACTIONS = {"START", "STOP", "SLOW_DOWN", "SET_SPEED", "EMERGENCY_STOP"}
CONFIRMATION_CATEGORIES = {
    "ambiguous_target",
    "missing_target",
    "low_asr_confidence",
}


def validate_case(case: Any, line_number: int) -> list[str]:
    prefix = f"line {line_number}"
    if not isinstance(case, dict):
        return [f"{prefix}: case must be an object"]
    errors: list[str] = []
    required = {
        "schema_version",
        "case_id",
        "category",
        "transcript",
        "normalized_text",
        "asr_confidence",
        "scene",
        "expected",
    }
    missing = sorted(required - case.keys())
    if missing:
        errors.append(f"{prefix}: missing fields: {', '.join(missing)}")
    if case.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"{prefix}: schema_version must be {SCHEMA_VERSION}")
    if not isinstance(case.get("case_id"), str) or not case.get("case_id"):
        errors.append(f"{prefix}: case_id must be a non-empty string")
    category = case.get("category")
    if category not in CATEGORIES:
        errors.append(f"{prefix}: unsupported category {category!r}")
    for name in ("transcript", "normalized_text"):
        if not isinstance(case.get(name), str) or not case.get(name).strip():
            errors.append(f"{prefix}: {name} must be non-empty text")
    confidence = case.get("asr_confidence")
    if (
        type(confidence) not in (int, float)
        or isinstance(confidence, bool)
        or not 0.0 <= float(confidence) <= 1.0
    ):
        errors.append(f"{prefix}: asr_confidence must be in [0, 1]")
    if not isinstance(case.get("scene"), dict):
        errors.append(f"{prefix}: scene must be an object")

    expected = case.get("expected")
    if not isinstance(expected, dict):
        errors.append(f"{prefix}: expected must be an object")
        return errors
    action = expected.get("action")
    if action not in ACTIONS:
        errors.append(f"{prefix}: unsupported expected.action {action!r}")
    confirmation = expected.get("requires_confirmation")
    if type(confirmation) is not bool:
        errors.append(f"{prefix}: expected.requires_confirmation must be bool")
    safety_override = expected.get("safety_override")
    if type(safety_override) is not bool:
        errors.append(f"{prefix}: expected.safety_override must be bool")

    if category in CONFIRMATION_CATEGORIES and confirmation is not True:
        errors.append(f"{prefix}: {category} must require confirmation")
    if category == "low_asr_confidence":
        if type(confidence) in (int, float) and float(confidence) >= 0.6:
            errors.append(f"{prefix}: low_asr_confidence must be below 0.6")
        if action != "STOP":
            errors.append(f"{prefix}: low_asr_confidence must fail closed with STOP")
    if category == "dangerous_conflict":
        if safety_override is not True:
            errors.append(f"{prefix}: dangerous_conflict must require safety override")
        if action not in {"STOP", "EMERGENCY_STOP"}:
            errors.append(f"{prefix}: dangerous_conflict must stop")
    return errors


def validate_language_testset(path: Path) -> tuple[list[str], dict[str, int]]:
    errors: list[str] = []
    counts: Counter[str] = Counter()
    case_ids: set[str] = set()
    with path.open("r", encoding="utf-8") as stream:
        for line_number, raw in enumerate(stream, start=1):
            if not raw.strip():
                continue
            try:
                case = json.loads(raw)
            except json.JSONDecodeError as error:
                errors.append(f"line {line_number}: invalid JSON: {error.msg}")
                continue
            errors.extend(validate_case(case, line_number))
            if not isinstance(case, dict):
                continue
            case_id = case.get("case_id")
            if isinstance(case_id, str):
                if case_id in case_ids:
                    errors.append(f"line {line_number}: duplicate case_id {case_id!r}")
                case_ids.add(case_id)
            category = case.get("category")
            if category in CATEGORIES:
                counts[category] += 1
    for category in sorted(CATEGORIES):
        if counts[category] == 0:
            errors.append(f"coverage: missing category {category}")
    return errors, dict(sorted(counts.items()))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("jsonl", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    errors, coverage = validate_language_testset(args.jsonl)
    report = {
        "schema_version": SCHEMA_VERSION,
        "path": str(args.jsonl),
        "passed": not errors,
        "case_count": sum(coverage.values()),
        "coverage": coverage,
        "errors": errors,
    }
    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
