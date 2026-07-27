"""Run a frozen proxy set through one loaded local Qwen2.5-VL checkpoint."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
from typing import Any

from integration.qwen_boundary import QwenInputContext
from integration.qwen_vl_adapter import StrictQwenVLAdapter


def _percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def _load_cases(path: Path) -> list[dict[str, Any]]:
    cases = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not cases or any(not isinstance(case, dict) for case in cases):
        raise ValueError("case file must contain JSON objects")
    return cases


def _context(case: dict[str, Any], image_name: str, index: int) -> QwenInputContext:
    return QwenInputContext(
        request_id=str(case["case_id"]),
        frame=index,
        sim_time_s=index * 0.05,
        voice_command=str(case["voice_command"]),
        rgb_ref=image_name,
        scene_state={
            "map": "Carla/Maps/Town03_Opt",
            "ego_speed_mps": case.get("ego_speed_mps", 3.0),
            **case.get("scene_state", {}),
        },
        perception={
            "traffic_light": "UNKNOWN",
            "collision": False,
            "lead_distance_m": None,
            "detected_objects": [],
            **case.get("perception", {}),
        },
        safety_state={
            "input_confidence": 1.0,
            "recommended_action": "KEEP_SPEED",
            "reason": "no_hazard",
            "visual_valid": True,
            "lidar_valid": True,
            **case.get("safety_state", {}),
        },
    )


def _evaluate(case: dict[str, Any], decision: dict[str, Any]) -> dict[str, bool]:
    expected = case["expected"]
    actions = expected.get("actions", [expected.get("action")])
    action_ok = decision["action"] in actions
    confirmation_ok = (
        "requires_confirmation" not in expected
        or decision["requires_confirmation"] is expected["requires_confirmation"]
    )
    speed_ok = True
    if "target_speed_mps" in expected:
        actual = decision.get("target_speed_mps")
        speed_ok = (
            actual is not None
            and abs(float(actual) - float(expected["target_speed_mps"]))
            <= float(expected.get("speed_tolerance_mps", 0.2))
        )
    return {
        "action": action_ok,
        "confirmation": confirmation_ok,
        "target_speed": speed_ok,
        "all": action_ok and confirmation_ok and speed_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cases", type=Path)
    parser.add_argument("--model-path", required=True, type=Path)
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--max-new-tokens", type=int, default=192)
    args = parser.parse_args()

    cases = _load_cases(args.cases)
    image = args.image.resolve()
    adapter = StrictQwenVLAdapter.from_local_checkpoint(
        args.model_path,
        image_root=image.parent,
        max_new_tokens=args.max_new_tokens,
    )
    records: list[dict[str, Any]] = []
    for index, case in enumerate(cases):
        try:
            decision = adapter(_context(case, image.name, index))
            trace = adapter.last_trace
            assert trace is not None
            checks = _evaluate(case, decision)
            record = {
                "case_id": case["case_id"],
                "category": case["category"],
                "status": "READY",
                "expected": case["expected"],
                "decision": decision,
                "checks": checks,
                "latency_ms": trace.latency_ms,
                "raw_output": trace.raw_output,
            }
        except Exception as error:
            record = {
                "case_id": case.get("case_id", f"index-{index}"),
                "category": case.get("category", "unknown"),
                "status": "ERROR",
                "expected": case.get("expected"),
                "error_type": type(error).__name__,
                "error": str(error),
                "checks": {
                    "action": False,
                    "confirmation": False,
                    "target_speed": False,
                    "all": False,
                },
            }
        records.append(record)
        print(json.dumps(record, ensure_ascii=False), flush=True)

    latencies = [
        float(record["latency_ms"])
        for record in records
        if record["status"] == "READY"
    ]
    total = len(records)
    count = lambda key: sum(record["checks"][key] for record in records)
    report = {
        "schema_version": "1.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_kind": "frozen_local_proxy_not_official",
        "rgb_source": str(image),
        "model_path": str(args.model_path.resolve()),
        "total": total,
        "ready": sum(record["status"] == "READY" for record in records),
        "metrics": {
            "strict_parse_rate": sum(record["status"] == "READY" for record in records) / total,
            "action_accuracy": count("action") / total,
            "confirmation_accuracy": count("confirmation") / total,
            "target_speed_accuracy": count("target_speed") / total,
            "all_contract_accuracy": count("all") / total,
            "target_association_accuracy": None,
            "target_association_note": "unsupported by frozen Qwen response schema",
        },
        "latency_ms": {
            "mean": statistics.fmean(latencies) if latencies else None,
            "p95": _percentile(latencies, 0.95),
            "p99": _percentile(latencies, 0.99),
            "max": max(latencies) if latencies else None,
        },
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"output": str(args.output), **report["metrics"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
