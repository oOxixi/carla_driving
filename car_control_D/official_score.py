"""Scoring utilities for D. Implements baseline 25/10/5 penalties and summaries."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from statistics import mean
from typing import Any, Dict, Iterable, List, Optional


@dataclass
class ScoreBreakdown:
    scenario_id: str
    difficulty: str
    base_score: float
    deduction: float
    final_score: float
    serious_safety_events: int = 0
    serious_route_deviation: int = 0
    unfinished_tasks: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def calculate_deduction(result: Dict[str, Any]) -> float:
    serious_safety = int(result.get("serious_safety_events", 0))
    if "collision_count" in result:
        serious_safety += int(result.get("collision_count", 0))
    if "red_light_violation_count" in result:
        serious_safety += int(result.get("red_light_violation_count", 0))

    route_dev = int(result.get("serious_route_deviation", result.get("route_deviation_count", 0)))
    unfinished = int(result.get("unfinished_tasks", result.get("unfinished_task_count", 0)))
    return float(serious_safety * 25 + route_dev * 10 + unfinished * 5)


def score_scenario(result: Dict[str, Any], base_score: float = 25.0) -> ScoreBreakdown:
    deduction = calculate_deduction(result)
    final = max(float(base_score) - deduction, 0.0)
    return ScoreBreakdown(
        scenario_id=str(result.get("scenario_id", "UNKNOWN")),
        difficulty=str(result.get("difficulty", result.get("difficulty_level", "unknown"))),
        base_score=float(base_score),
        deduction=deduction,
        final_score=final,
        serious_safety_events=int(result.get("serious_safety_events", result.get("collision_count", 0) + result.get("red_light_violation_count", 0))),
        serious_route_deviation=int(result.get("serious_route_deviation", result.get("route_deviation_count", 0))),
        unfinished_tasks=int(result.get("unfinished_tasks", result.get("unfinished_task_count", 0))),
    )


def weighted_completion_score(results: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    buckets = {"basic": [], "advanced": [], "challenge": []}
    for r in results:
        diff = str(r.get("difficulty", r.get("difficulty_level", "basic"))).lower()
        if diff not in buckets:
            diff = "basic"
        success = str(r.get("status", "FAILED")).upper() == "SUCCEEDED"
        buckets[diff].append(1.0 if success else 0.0)

    rates = {k: (mean(v) if v else 0.0) for k, v in buckets.items()}
    weighted_rate = rates["basic"] * 0.30 + rates["advanced"] * 0.40 + rates["challenge"] * 0.30
    return {
        "completion_rates": rates,
        "weighted_completion_rate": weighted_rate,
        "task_completion_score_25": weighted_rate * 25.0,
    }


def latency_report(command_records: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    latencies: List[float] = []
    asr_latencies: List[float] = []
    intent_latencies: List[float] = []
    for c in command_records:
        e2e = c.get("e2e_latency_ms")
        if isinstance(e2e, (int, float)):
            latencies.append(float(e2e))
        a0, a1, a2 = c.get("t_audio_start_ns"), c.get("t_asr_end_ns"), c.get("t_intent_end_ns")
        if isinstance(a0, int) and isinstance(a1, int):
            asr_latencies.append((a1 - a0) / 1e6)
        if isinstance(a1, int) and isinstance(a2, int):
            intent_latencies.append((a2 - a1) / 1e6)
    return {
        "e2e_count": len(latencies),
        "e2e_avg_ms": mean(latencies) if latencies else None,
        "e2e_max_ms": max(latencies) if latencies else None,
        "e2e_under_150ms_rate": sum(x <= 150.0 for x in latencies) / len(latencies) if latencies else None,
        "asr_avg_ms": mean(asr_latencies) if asr_latencies else None,
        "intent_avg_ms": mean(intent_latencies) if intent_latencies else None,
    }


class OfficialScorer:
    def score_scenario(self, result: Dict[str, Any], base_score: float = 25.0) -> ScoreBreakdown:
        return score_scenario(result, base_score=base_score)

    def summarize(self, scenario_results: Iterable[Dict[str, Any]], command_records: Optional[Iterable[Dict[str, Any]]] = None) -> Dict[str, Any]:
        results = list(scenario_results)
        return {
            "scenario_scores": [score_scenario(r).to_dict() for r in results],
            "weighted_completion": weighted_completion_score(results),
            "latency": latency_report(command_records or []),
        }
