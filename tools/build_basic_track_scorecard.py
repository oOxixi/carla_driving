#!/usr/bin/env python3
"""Merge CARLA/Qwen and real-audio reports into the four promotion gates."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"report must be a JSON object: {path}")
    return value


def build_scorecard(carla: dict[str, Any], voice: dict[str, Any]) -> dict[str, Any]:
    overall = voice.get("overall", {})
    latency = overall.get("latency", {}) if isinstance(overall, dict) else {}
    nlu = latency.get("nlu_ms", {}) if isinstance(latency, dict) else {}
    official = carla.get("official_first_50_sensor_to_trajectory_ms", {})
    alignment = carla.get("multimodal_semantic_alignment", {})
    task = carla.get("scenario_accuracy_percent")
    scenario_count = carla.get("scenario_count_finished")
    expected_scenarios = carla.get("scenario_count_expected")
    asr = overall.get("asr_character_accuracy") if isinstance(overall, dict) else None
    align = alignment.get("accuracy_percent") if isinstance(alignment, dict) else None
    e2e = official.get("p95") if isinstance(official, dict) else None
    e2e_count = official.get("count") if isinstance(official, dict) else None
    alignment_count = alignment.get("count") if isinstance(alignment, dict) else None
    parse = nlu.get("p95_ms") if isinstance(nlu, dict) else None

    def gate(value: Any, threshold: float, *, maximum: bool = False) -> bool:
        return isinstance(value, (int, float)) and (
            float(value) <= threshold if maximum else float(value) >= threshold
        )

    gates = {
        "scenario_task_completion_ge_90": (
            gate(task, 90.0)
            and scenario_count == expected_scenarios == 84
        ),
        "asr_character_accuracy_ge_95": gate(
            None if asr is None else float(asr) * 100.0, 95.0,
        ),
        "multimodal_alignment_ge_98": (
            gate(align, 98.0) and alignment_count == expected_scenarios == 84
        ),
        "sensor_to_trajectory_p95_le_150_ms": (
            gate(e2e, 150.0, maximum=True) and e2e_count == 50
        ),
        "instruction_parse_p95_le_50_ms": gate(parse, 50.0, maximum=True),
    }
    return {
        "schema_version": "1.0",
        "evidence_policy": {
            "carla_input": "provided transcript; not ASR evidence",
            "asr_input": "real audio report",
            "decision_latency_boundary": "all sensors ready to valid trajectory",
            "decision_latency_statistic": "first 50 successful post-warmup samples, P95",
        },
        "metrics": {
            "scenario_task_completion_percent": task,
            "scenario_count": scenario_count,
            "asr_character_accuracy_percent": None if asr is None else float(asr) * 100.0,
            "multimodal_semantic_alignment_percent": align,
            "multimodal_alignment_scenario_count": alignment_count,
            "sensor_to_trajectory_p95_ms": e2e,
            "sensor_to_trajectory_sample_count": e2e_count,
            "instruction_parse_p95_ms": parse,
        },
        "gates": gates,
        "promotion_ready": all(gates.values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--carla-report", type=Path, required=True)
    parser.add_argument("--voice-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build_scorecard(_load(args.carla_report), _load(args.voice_report))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["promotion_ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
