from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path

from voice_group.nlu_b2.parser import parse_command
from voice_group.vehicle_nlu.src.b1_service import process_asr_text


ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "voice_group" / "test_samples" / "manifest.json"
MINIMUM_ACCURACY = 0.95


def _samples() -> list[dict[str, object]]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _evaluate() -> tuple[Counter[str], dict[str, Counter[str]], list[str]]:
    overall: Counter[str] = Counter()
    by_language: dict[str, Counter[str]] = defaultdict(Counter)
    failures: list[str] = []

    for index, sample in enumerate(_samples()):
        result = parse_command(
            process_asr_text(
                request_id=f"manifest-{index:03d}",
                text=str(sample["text"]),
                asr_confidence=1.0,
            )
        )
        expected_intent = str(sample["intent"])
        expected_slots = dict(sample.get("slots", {}))
        intent_ok = result["intent"] == expected_intent
        slots_ok = all(
            result["slots"].get(name) == value
            for name, value in expected_slots.items()
        )
        language = str(sample["lang"])
        for stats in (overall, by_language[language]):
            stats["total"] += 1
            stats["intent_ok"] += int(intent_ok)
            stats["slots_ok"] += int(slots_ok)
        if not intent_ok or not slots_ok:
            failures.append(
                f"{language}:{sample['text']!r} expected "
                f"{expected_intent}/{expected_slots}, got "
                f"{result['intent']}/{result['slots']}"
            )

    return overall, by_language, failures


def _accuracy(stats: Counter[str], name: str) -> float:
    return stats[name] / stats["total"]


def test_all_250_manifest_transcripts_meet_official_baseline() -> None:
    overall, by_language, failures = _evaluate()

    assert overall["total"] == 250
    assert _accuracy(overall, "intent_ok") >= MINIMUM_ACCURACY, failures[:20]
    assert _accuracy(overall, "slots_ok") >= MINIMUM_ACCURACY, failures[:20]
    for language, stats in by_language.items():
        assert stats["total"] == 50, language
        assert _accuracy(stats, "intent_ok") >= MINIMUM_ACCURACY, (
            language,
            failures[:20],
        )
        assert _accuracy(stats, "slots_ok") >= MINIMUM_ACCURACY, (
            language,
            failures[:20],
        )


def test_every_manifest_audio_file_exists() -> None:
    missing = [
        str(sample["audio"])
        for sample in _samples()
        if not (MANIFEST_PATH.parent / str(sample["audio"])).is_file()
    ]
    assert not missing
