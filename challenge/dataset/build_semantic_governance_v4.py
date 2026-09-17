#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path



TEACHER_V4_SHA = "95e97b00def8ec36f12937da34ce8bb9082c4a04"

# Challenge SHA should be filled from current HEAD at execution time.
#
# These are the eight scenario semantics that were independently proven
# corrupted in the historical D1/D2 acquisition and fixed by Teacher v4.
DIRECTIONAL = {
    "B06_left_turn": ("TURN", "LEFT", "TURN_LEFT"),
    "B07_right_turn": ("TURN", "RIGHT", "TURN_RIGHT"),
    "B08_lane_change_left": (
        "CHANGE_LANE", "LEFT", "CHANGE_LANE_LEFT"
    ),
    "B09_lane_change_right": (
        "CHANGE_LANE", "RIGHT", "CHANGE_LANE_RIGHT"
    ),
    "REG_004_advanced_rain_left_turn": (
        "TURN", "LEFT", "TURN_LEFT"
    ),
    "REG_005_advanced_rain_right_turn": (
        "TURN", "RIGHT", "TURN_RIGHT"
    ),
    "REG_009_challenge_lane_change_left": (
        "CHANGE_LANE", "LEFT", "CHANGE_LANE_LEFT"
    ),
    "REG_010_challenge_lane_change_right": (
        "CHANGE_LANE", "RIGHT", "CHANGE_LANE_RIGHT"
    ),
}

EXPECTED = {
    "D1": 8,
    "D2": 181,
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_json_sha256(obj: dict) -> str:
    payload = json.dumps(
        obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            row["_source_line"] = lineno
            rows.append(row)
    return rows


def scenario_key(row: dict) -> str | None:
    meta = row.get("metadata") or {}

    sid = str(meta.get("scenario_id") or "")
    if sid in DIRECTIONAL:
        return sid

    p = str(meta.get("scenario_config_path") or "")
    stem = Path(p).stem
    if stem in DIRECTIONAL:
        return stem

    return None


def behaviors(row: dict) -> list[str]:
    plan = row.get("teacher_plan") or {}
    return [
        str(step.get("behavior"))
        for step in plan.get("steps", [])
        if isinstance(step, dict) and step.get("behavior") is not None
    ]


def identity(row: dict) -> dict:
    meta = row.get("metadata") or {}
    return {
        "sample_id": row.get("sample_id"),
        "run_id": meta.get("run_id"),
        "command_id": meta.get("command_id"),
        "request_id": meta.get("request_id"),
        "frame_id": meta.get("frame_id"),
        "group_key": meta.get("group_key"),
        "seed": meta.get("seed"),
    }


def classify(row: dict) -> dict | None:
    key = scenario_key(row)
    if key is None:
        return None

    expected_intent, expected_direction, expected_behavior = DIRECTIONAL[key]

    hint = ((row.get("model_request") or {}).get("command_hint") or {})
    observed_intent = hint.get("intent")
    observed_direction = hint.get("direction")
    observed_behaviors = behaviors(row)

    # Confirmed P0 corruption signature:
    # intended directional maneuver was collapsed to SET_SPEED upstream,
    # therefore Qwen was supervised with SET_SPEED instead of TURN/CHANGE_LANE.
    confirmed = (
        observed_intent == "SET_SPEED"
        and observed_direction in (None, "")
        and observed_behaviors == ["SET_SPEED"]
    )

    already_correct = (
        observed_intent == expected_intent
        and observed_direction == expected_direction
        and expected_behavior in observed_behaviors
    )

    if confirmed:
        classification = "CONFIRMED_DIRECTIONAL_SEMANTIC_CONTAMINATION"
    elif already_correct:
        classification = "DIRECTIONAL_SEMANTICS_CORRECT"
    else:
        classification = "DIRECTIONAL_UNEXPECTED_STATE"

    meta = row.get("metadata") or {}

    return {
        "governance_schema_version": "1.0",
        "classification": classification,
        "reason_code": (
            "P0_DIRECTIONAL_INTENT_COLLAPSED_TO_SET_SPEED"
            if confirmed
            else None
        ),
        "sample_identity": identity(row),
        "source": {
            "dataset_version": row.get("dataset_version"),
            "source_line": row["_source_line"],
            "scenario_id": meta.get("scenario_id"),
            "scenario_family": meta.get("scenario_family"),
            "scenario_config_path": meta.get("scenario_config_path"),
            "teacher_git_sha": meta.get("teacher_git_sha"),
            "teacher_profile": meta.get("teacher_profile"),
            "teacher_baseline_git_sha": meta.get(
                "teacher_baseline_git_sha"
            ),
        },
        "expected_semantics": {
            "intent": expected_intent,
            "direction": expected_direction,
            "required_behavior": expected_behavior,
        },
        "observed_semantics": {
            "model_request_intent": observed_intent,
            "model_request_direction": observed_direction,
            "teacher_behaviors": observed_behaviors,
            "source_text": (
                (row.get("model_request") or {}).get("source_text")
            ),
        },
        "historical_quality": {
            "valid_for_training": (
                (row.get("quality") or {}).get("valid_for_training")
            ),
            "training_role": (
                (row.get("quality") or {}).get("training_role")
            ),
            "closed_loop_available": (
                (row.get("closed_loop_quality") or {}).get("available")
            ),
            "closed_loop_run_status": (
                (row.get("closed_loop_quality") or {}).get("run_status")
            ),
            "scenario_acceptance_passed": (
                (row.get("closed_loop_quality") or {}).get(
                    "scenario_acceptance_passed"
                )
            ),
        },
        "governance_action": (
            "EXCLUDE_FROM_TRAINING_UNTIL_V4_RECOLLECTION"
            if confirmed
            else "REVIEW"
        ),
    }


def dump_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(
                json.dumps(row, ensure_ascii=False, sort_keys=True)
                + "\n"
            )


def main() -> None:
    import subprocess

    parser = argparse.ArgumentParser(
        description="Build non-destructive semantic governance views."
    )
    parser.add_argument(
        "--d1-jsonl",
        type=Path,
        required=True,
        help="Frozen D1 valid JSONL",
    )
    parser.add_argument(
        "--d2-jsonl",
        type=Path,
        required=True,
        help="Frozen D2 Wave1 valid JSONL",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        required=True,
        help="Output directory for governance artifacts",
    )
    args = parser.parse_args()

    d1 = args.d1_jsonl.resolve()
    d2 = args.d2_jsonl.resolve()
    out = args.output_root.resolve()

    out.mkdir(parents=True, exist_ok=True)

    challenge_sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        text=True,
    ).strip()

    datasets = {
        "D1": d1,
        "D2": d2,
    }

    report = {
        "governance_schema_version": "1.0",
        "policy": (
            "Non-destructive semantic governance view. "
            "Frozen source JSONL files are never modified."
        ),
        "teacher_v4_git_sha": TEACHER_V4_SHA,
        "challenge_governance_git_sha": challenge_sha,
        "sources": {},
        "counts": {},
        "scenario_counts": {},
        "unexpected_states": {},
    }

    all_quarantine = []
    all_unaffected_ids = []

    for label, path in datasets.items():
        if not path.is_file():
            raise FileNotFoundError(path)

        rows = load_jsonl(path)

        findings = []
        unaffected_ids = []

        for row in rows:
            result = classify(row)

            if result is None:
                unaffected_ids.append(row["sample_id"])
            else:
                findings.append(result)
                if result["classification"] != (
                    "CONFIRMED_DIRECTIONAL_SEMANTIC_CONTAMINATION"
                ):
                    # Do not silently classify ambiguous directional rows
                    # as unaffected.
                    pass

        contaminated = [
            x for x in findings
            if x["classification"]
            == "CONFIRMED_DIRECTIONAL_SEMANTIC_CONTAMINATION"
        ]

        correct_directional = [
            x for x in findings
            if x["classification"] == "DIRECTIONAL_SEMANTICS_CORRECT"
        ]

        unexpected = [
            x for x in findings
            if x["classification"] == "DIRECTIONAL_UNEXPECTED_STATE"
        ]

        if len(contaminated) != EXPECTED[label]:
            raise AssertionError(
                f"{label}: expected {EXPECTED[label]} confirmed "
                f"directional contaminations, got {len(contaminated)}"
            )

        if correct_directional:
            raise AssertionError(
                f"{label}: historical directional rows unexpectedly "
                f"already correct: {len(correct_directional)}"
            )

        if unexpected:
            raise AssertionError(
                f"{label}: unexpected directional states found: "
                f"{len(unexpected)}"
            )

        ids = [
            x["sample_identity"]["sample_id"]
            for x in contaminated
        ]

        if len(ids) != len(set(ids)):
            raise AssertionError(f"{label}: duplicate quarantine sample_id")

        scenario_counts = Counter(
            x["source"]["scenario_id"]
            for x in contaminated
        )

        dump_jsonl(
            out / f"{label.lower()}_directional_quarantine.jsonl",
            contaminated,
        )

        (out / f"{label.lower()}_directional_quarantine_ids.txt").write_text(
            "".join(f"{x}\n" for x in sorted(ids)),
            encoding="utf-8",
        )

        (out / f"{label.lower()}_unaffected_candidate_ids.txt").write_text(
            "".join(f"{x}\n" for x in sorted(unaffected_ids)),
            encoding="utf-8",
        )

        report["sources"][label] = {
            "path": str(path),
            "sha256": sha256_file(path),
            "dataset_version": (
                rows[0].get("dataset_version") if rows else None
            ),
            "total_rows": len(rows),
        }

        report["counts"][label] = {
            "total_rows": len(rows),
            "confirmed_directional_contamination": len(contaminated),
            "directional_correct": len(correct_directional),
            "directional_unexpected": len(unexpected),
            "non_directional_rows": len(unaffected_ids),
        }

        report["scenario_counts"][label] = dict(
            sorted(scenario_counts.items())
        )

        report["unexpected_states"][label] = unexpected

        all_quarantine.extend(
            [{"dataset": label, **x} for x in contaminated]
        )

        all_unaffected_ids.extend(
            (label, x) for x in unaffected_ids
        )

    # Cross-dataset identity checks.
    all_ids = [
        x["sample_identity"]["sample_id"]
        for x in all_quarantine
    ]

    if len(all_ids) != 189:
        raise AssertionError(
            f"expected 189 total quarantine rows, got {len(all_ids)}"
        )

    if len(all_ids) != len(set(all_ids)):
        raise AssertionError(
            "sample_id overlap exists across D1/D2 quarantine"
        )

    dump_jsonl(
        out / "directional_quarantine_all.jsonl",
        all_quarantine,
    )

    (out / "directional_quarantine_ids.txt").write_text(
        "".join(f"{x}\n" for x in sorted(all_ids)),
        encoding="utf-8",
    )

    report["counts"]["TOTAL"] = {
        "confirmed_directional_contamination": len(all_ids),
        "expected": 189,
    }

    report["report_canonical_sha256"] = canonical_json_sha256(
        {k: v for k, v in report.items()
         if k != "report_canonical_sha256"}
    )

    report_path = out / "directional_audit_report.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("D1_TOTAL =", report["counts"]["D1"]["total_rows"])
    print(
        "D1_DIRECTIONAL_QUARANTINE =",
        report["counts"]["D1"][
            "confirmed_directional_contamination"
        ],
    )
    print("D2_TOTAL =", report["counts"]["D2"]["total_rows"])
    print(
        "D2_DIRECTIONAL_QUARANTINE =",
        report["counts"]["D2"][
            "confirmed_directional_contamination"
        ],
    )
    print(
        "TOTAL_DIRECTIONAL_QUARANTINE =",
        report["counts"]["TOTAL"][
            "confirmed_directional_contamination"
        ],
    )
    print(
        "REPORT_CANONICAL_SHA256 =",
        report["report_canonical_sha256"],
    )
    print("SEMANTIC_DIRECTIONAL_GOVERNANCE=PASS")


if __name__ == "__main__":
    main()
