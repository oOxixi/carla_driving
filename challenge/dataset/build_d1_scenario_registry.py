#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any


FAILURE_TOKENS = (
    "timeout",
    "disconnect",
    "invalid_token",
    "stale_result",
    "rgb_blackout",
    "lidar_blackout",
    "sensor_dropout",
    "sensor_stale",
    "perception_failure",
    "steer_bias",
    "invalid_control",
    "nan",
)

HARD_TOKENS = (
    "ambiguous",
    "illegal",
    "vague",
    "asr_disagreement",
)

DEFER_TOKENS = (
    "long_run",
    "stability",
)


def load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"
    if not isinstance(value, dict):
        return None, "top-level JSON is not an object"
    return value, None


def runnable_reason(data: dict[str, Any]) -> str | None:
    sid = data.get("scenario_id")
    level = data.get("official_level")
    runtime = data.get("runtime")
    route = data.get("route")
    commands = data.get("commands")

    if not isinstance(sid, str) or not sid.strip():
        return "missing/non-string scenario_id"
    if not isinstance(level, str) or not level.strip():
        return "missing/non-string official_level"
    if not isinstance(runtime, dict):
        return "missing/non-object runtime"
    if not isinstance(route, dict):
        return "missing/non-object route"
    if not isinstance(commands, list) or not commands:
        return "missing/empty commands"
    return None


def source_bucket(rel: str) -> str:
    p = rel.lower()
    if "/variants/" in p or "/variant/" in p:
        return "VARIANT"
    if "/unseen/" in p:
        return "UNSEEN"
    return "SEEN"


def family(rel: str) -> str:
    parts = Path(rel).parts
    return parts[0] if parts else "unknown"


def classify(rel: str, data: dict[str, Any]) -> tuple[str, str]:
    p = rel.lower()
    fam = family(rel).lower()

    nonrun = runnable_reason(data)
    if nonrun is not None:
        return "NON_RUNNABLE_METADATA", nonrun

    if "official_competition" in p:
        return "EXCLUDED_OFFICIAL", "official competition scenario"

    if "generalization" in p:
        return "RESERVED_TEST_CANDIDATE", "generalization scenario reserved from training"

    if any(tok in p for tok in DEFER_TOKENS):
        return "DEFERRED_LONG_RUN", "long-run/stability scenario"

    faults = data.get("extensions", {}).get("faults")
    if isinstance(faults, list) and faults:
        return "SYSTEM_FAILURE", "extensions.faults is non-empty"

    if fam == "qwen_faults" or any(tok in p for tok in FAILURE_TOKENS):
        return "SYSTEM_FAILURE", "fault/failure semantics"

    commands = data.get("commands") or []
    for cmd in commands:
        if not isinstance(cmd, dict):
            continue
        status = str(cmd.get("status") or "").lower()
        confirm_required = cmd.get("confirm_required") is True
        text = " ".join(
            str(cmd.get(k) or "")
            for k in ("source_text", "intent", "status")
        ).lower()
        if status in {"ambiguous", "invalid", "illegal"}:
            return "HARD_CASE", f"command status={status}"
        if confirm_required:
            return "HARD_CASE", "command confirm_required=true"
        if any(tok in text for tok in HARD_TOKENS):
            return "HARD_CASE", "ambiguous/illegal/vague command semantics"

    if any(tok in p for tok in HARD_TOKENS):
        return "HARD_CASE", "ambiguous/illegal/vague filename semantics"

    return "TRAIN_POSITIVE", "ordinary runnable positive scenario"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenarios-root", default="scenarios")
    parser.add_argument(
        "--output-dir",
        default="artifacts/b1_d1_registry_v3",
    )
    args = parser.parse_args()

    root = Path(args.scenarios_root).resolve()
    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    parse_errors = 0
    total_declared_commands = 0

    for path in sorted(root.rglob("*.json")):
        rel = path.relative_to(root).as_posix()
        data, err = load_json(path)

        if data is None:
            parse_errors += 1
            rows.append(
                {
                    "scenario_path": rel,
                    "scenario_id": "",
                    "family": family(rel),
                    "source_bucket": source_bucket(rel),
                    "policy_class": "PARSE_ERROR",
                    "policy_reason": err or "unknown parse error",
                    "command_count": 0,
                    "map": "",
                    "seed": "",
                    "official_level": "",
                }
            )
            continue

        commands = data.get("commands")
        command_count = len(commands) if isinstance(commands, list) else 0
        total_declared_commands += command_count
        policy, reason = classify(rel, data)

        rows.append(
            {
                "scenario_path": rel,
                "scenario_id": str(data.get("scenario_id") or ""),
                "family": family(rel),
                "source_bucket": source_bucket(rel),
                "policy_class": policy,
                "policy_reason": reason,
                "command_count": command_count,
                "map": str(data.get("map") or ""),
                "seed": str(data.get("seed") if data.get("seed") is not None else ""),
                "official_level": str(data.get("official_level") or ""),
            }
        )

    csv_path = out_dir / "scenario_registry_v3.csv"
    json_path = out_dir / "scenario_registry_v3.json"
    summary_path = out_dir / "scenario_registry_v3_summary.json"

    fieldnames = [
        "scenario_path",
        "scenario_id",
        "family",
        "source_bucket",
        "policy_class",
        "policy_reason",
        "command_count",
        "map",
        "seed",
        "official_level",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    json_path.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    policy_counts = Counter(r["policy_class"] for r in rows)
    source_counts = Counter(r["source_bucket"] for r in rows)
    train_rows = [r for r in rows if r["policy_class"] == "TRAIN_POSITIVE"]

    summary = {
        "scenario_files": len(rows),
        "parse_errors": parse_errors,
        "total_declared_commands": total_declared_commands,
        "policy_counts": dict(sorted(policy_counts.items())),
        "source_bucket_counts": dict(sorted(source_counts.items())),
        "train_positive_scenarios": len(train_rows),
        "train_positive_declared_commands": sum(
            int(r["command_count"]) for r in train_rows
        ),
        "non_runnable_metadata": [
            {
                "scenario_path": r["scenario_path"],
                "reason": r["policy_reason"],
            }
            for r in rows
            if r["policy_class"] == "NON_RUNNABLE_METADATA"
        ],
    }
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("SCENARIO_FILES=" + str(len(rows)))
    print("PARSE_ERRORS=" + str(parse_errors))
    print("TOTAL_DECLARED_COMMANDS=" + str(total_declared_commands))
    print("TRAIN_POSITIVE_SCENARIOS=" + str(len(train_rows)))
    print(
        "TRAIN_POSITIVE_DECLARED_COMMANDS="
        + str(sum(int(r["command_count"]) for r in train_rows))
    )
    print(
        "NON_RUNNABLE_METADATA_SCENARIOS="
        + str(policy_counts.get("NON_RUNNABLE_METADATA", 0))
    )
    print(
        "POLICY_COUNTS="
        + json.dumps(dict(sorted(policy_counts.items())), ensure_ascii=False)
    )
    print(
        "SOURCE_BUCKET_COUNTS="
        + json.dumps(dict(sorted(source_counts.items())), ensure_ascii=False)
    )
    print("CSV=" + str(csv_path))
    print("SUMMARY=" + str(summary_path))
    print("B1_D1_REGISTRY_V3=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
