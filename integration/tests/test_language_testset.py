from __future__ import annotations

import json
from pathlib import Path

from tools.validate_language_testset import CATEGORIES, validate_language_testset


ROOT = Path(__file__).resolve().parents[2]
TESTSET = ROOT / "datasets" / "language_v1" / "commands.jsonl"


def test_checked_in_language_testset_covers_every_required_category() -> None:
    errors, coverage = validate_language_testset(TESTSET)
    assert errors == []
    assert set(coverage) == CATEGORIES
    assert all(count >= 2 for count in coverage.values())


def test_missing_coverage_and_unsafe_low_confidence_expectation_fail(
    tmp_path: Path,
) -> None:
    case = {
        "schema_version": "1.0",
        "case_id": "bad",
        "category": "low_asr_confidence",
        "transcript": "可能走",
        "normalized_text": "继续",
        "asr_confidence": 0.8,
        "scene": {},
        "expected": {
            "action": "START",
            "requires_confirmation": False,
            "safety_override": False,
        },
    }
    target = tmp_path / "bad.jsonl"
    target.write_text(json.dumps(case, ensure_ascii=False) + "\n", encoding="utf-8")

    errors, _ = validate_language_testset(target)

    assert any("below 0.6" in error for error in errors)
    assert any("fail closed with STOP" in error for error in errors)
    assert any("must require confirmation" in error for error in errors)
    assert any("missing category" in error for error in errors)
