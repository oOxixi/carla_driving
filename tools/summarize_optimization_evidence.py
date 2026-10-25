"""Produce a scoped audit alongside existing CARLA evidence without altering it."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from integration.evidence_reporting import scoped_command_statistics, safety_override_category


def audit_evidence(path: Path) -> dict:
    commands, terminals, safety = {}, {}, {}
    start, summary, previous_reason = {}, {}, None
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for line in stream:
            digest.update(line)
            if not line.strip():
                continue
            row = json.loads(line)
            kind = row.get("record_type")
            if kind == "run_start":
                start = row
            elif kind == "command":
                commands[row["command_id"]] = row
            elif kind == "feedback":
                feedback = row["feedback"]
                terminals[feedback["command_id"]] = feedback["status"]
            elif kind == "frame":
                override = row.get("safety", {})
                reason = str(override.get("reason", "UNKNOWN")) if override.get("override") else None
                if reason is not None:
                    counts = safety.setdefault(reason, {"frames": 0, "episodes": 0, "category": safety_override_category(reason)})
                    counts["frames"] += 1
                    counts["episodes"] += int(reason != previous_reason)
                previous_reason = reason
            elif kind in {"run_complete", "run_failed"}:
                summary = row.get("summary", {})
    config = start.get("config", {})
    metrics = summary.get("acceptance", {}).get("metrics", {})
    statistics = scoped_command_statistics(commands, terminals)
    return {
        "schema_version": "1.0", "source_jsonl": str(path), "source_sha256": digest.hexdigest(),
        "run_id": start.get("run_id"), "run_status": summary.get("status", "INCOMPLETE"),
        "scenario_id": start.get("scenario_id"), "code_version_recorded": config.get("code_version"),
        "provenance": config.get("provenance", {"status": "LEGACY_NOT_RECORDED"}),
        "command_statistics": statistics, "safety_overrides_by_reason": safety,
        "route_finished": metrics.get("route_finished"),
        "collision_count": summary.get("collision_count"),
        "lane_invasion_count": summary.get("lane_invasion_count"),
        "red_light_violation_count": summary.get("red_light_violation_count"),
        "latency": summary.get("latency", {}),
        "score": summary.get("score"),
        "note": "Original JSONL and acceptance results are unchanged. Per-reason episodes split when the reason changes; their sum can exceed continuous override episodes.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("jsonl", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output already exists; choose a fresh audit path")
    report = audit_evidence(args.jsonl)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "run_status": report["run_status"],
                      "command_counts": {key: item["status_counts"] for key, item in report["command_statistics"].items()}}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
