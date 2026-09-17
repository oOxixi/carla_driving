#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path


TEACHER_V4_SHA = "95e97b00def8ec36f12937da34ce8bb9082c4a04"

DIRECTIONAL = {
    "B06_left_turn": ("TURN", "LEFT", "TURN_LEFT"),
    "B07_right_turn": ("TURN", "RIGHT", "TURN_RIGHT"),
    "B08_lane_change_left": ("CHANGE_LANE", "LEFT", "CHANGE_LANE_LEFT"),
    "B09_lane_change_right": ("CHANGE_LANE", "RIGHT", "CHANGE_LANE_RIGHT"),
    "REG_004_advanced_rain_left_turn": ("TURN", "LEFT", "TURN_LEFT"),
    "REG_005_advanced_rain_right_turn": ("TURN", "RIGHT", "TURN_RIGHT"),
    "REG_009_challenge_lane_change_left":
        ("CHANGE_LANE", "LEFT", "CHANGE_LANE_LEFT"),
    "REG_010_challenge_lane_change_right":
        ("CHANGE_LANE", "RIGHT", "CHANGE_LANE_RIGHT"),
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_sha256(obj: object) -> str:
    data = json.dumps(
        obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_ids(path: Path, ids: set[str]) -> None:
    path.write_text(
        "".join(f"{x}\n" for x in sorted(ids)),
        encoding="utf-8",
    )


def behaviors(row: dict) -> list[str]:
    return [
        str(step.get("behavior"))
        for step in (row.get("teacher_plan") or {}).get("steps", [])
        if isinstance(step, dict) and step.get("behavior") is not None
    ]


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--previous-eligibility-root",
        type=Path,
        default=Path("artifacts/b1_training_eligibility_v4"),
    )
    parser.add_argument(
        "--wave2-jsonl",
        type=Path,
        default=Path(
            "artifacts/b1_d2_wave2_2000_teacher_v4/"
            "dataset/d2_valid.jsonl"
        ),
    )
    parser.add_argument(
        "--wave2-freeze",
        type=Path,
        default=Path(
            "artifacts/b1_d2_wave2_2000_teacher_v4/"
            "freeze_manifest.json"
        ),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("artifacts/b1_d2_cumulative_governance_v5"),
    )

    args = parser.parse_args()

    prev_root = args.previous_eligibility_root.resolve()
    wave2_path = args.wave2_jsonl.resolve()
    freeze_path = args.wave2_freeze.resolve()
    out = args.output_root.resolve()
    out.mkdir(parents=True, exist_ok=True)

    prev_report_path = prev_root / "training_eligibility_report.json"
    assert prev_report_path.is_file()
    assert wave2_path.is_file()
    assert freeze_path.is_file()

    prev = json.loads(prev_report_path.read_text(encoding="utf-8"))
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    wave2 = load_jsonl(wave2_path)

    # Historical v4 governance contract.
    assert prev["counts"]["d1"]["positive_eligible"] == 122
    assert prev["counts"]["d2"]["positive_eligible"] == 953
    assert prev["counts"]["d2"]["hard_negative_eligible"] == 64
    assert prev["counts"]["cumulative"]["positive_eligible"] == 1075
    assert prev["counts"]["cumulative"]["hard_negative_eligible"] == 64

    # Wave2 acquisition freeze contract.
    assert freeze["freeze_status"] == "PASS"
    assert freeze["valid_samples"] == 2461
    assert freeze["positive_samples"] == 2320
    assert freeze["hard_negative_samples"] == 141
    assert freeze["rejected_samples"] == 0
    assert freeze["teacher_git_sha"] == TEACHER_V4_SHA

    ids = [row["sample_id"] for row in wave2]
    assert len(wave2) == 2461
    assert len(ids) == len(set(ids))

    roles = Counter(
        (row.get("quality") or {}).get("training_role")
        for row in wave2
    )
    assert roles == {
        "POSITIVE": 2320,
        "HARD_NEGATIVE": 141,
    }

    # Exact Teacher v4 provenance on every Wave2 sample.
    teacher_shas = {
        (row.get("metadata") or {}).get("teacher_git_sha")
        for row in wave2
    }
    assert teacher_shas == {TEACHER_V4_SHA}

    positive_ids = {
        row["sample_id"]
        for row in wave2
        if (row.get("quality") or {}).get("training_role") == "POSITIVE"
    }

    hn_ids = {
        row["sample_id"]
        for row in wave2
        if (row.get("quality") or {}).get("training_role")
        == "HARD_NEGATIVE"
    }

    assert positive_ids.isdisjoint(hn_ids)
    assert positive_ids | hn_ids == set(ids)

    # Teacher-v4 directional semantic gate.
    directional_counts = Counter()
    directional_unexpected = []

    for row in wave2:
        meta = row.get("metadata") or {}
        scenario = str(meta.get("scenario_id") or "")

        if scenario not in DIRECTIONAL:
            continue

        directional_counts[scenario] += 1

        expected_intent, expected_direction, expected_behavior = (
            DIRECTIONAL[scenario]
        )

        hint = (row.get("model_request") or {}).get("command_hint") or {}

        intent = hint.get("intent")
        direction = hint.get("direction")
        observed_behaviors = behaviors(row)

        good = (
            intent == expected_intent
            and direction == expected_direction
            and expected_behavior in observed_behaviors
        )

        if not good:
            directional_unexpected.append({
                "sample_id": row["sample_id"],
                "scenario_id": scenario,
                "observed_intent": intent,
                "observed_direction": direction,
                "teacher_behaviors": observed_behaviors,
                "expected_intent": expected_intent,
                "expected_direction": expected_direction,
                "expected_behavior": expected_behavior,
            })

    assert set(directional_counts) == set(DIRECTIONAL)
    assert all(directional_counts[x] > 0 for x in DIRECTIONAL)
    assert not directional_unexpected

    # Wave2 has no semantic quarantine: it is the corrected v4 recollection.
    wave2_positive_eligible = positive_ids
    wave2_hn_eligible = hn_ids
    wave2_excluded = set()

    cumulative_positive = 1075 + len(wave2_positive_eligible)
    cumulative_hn = 64 + len(wave2_hn_eligible)
    cumulative_assets = cumulative_positive + cumulative_hn

    assert cumulative_positive == 3395
    assert cumulative_hn == 205
    assert cumulative_assets == 3600

    # Raw total: D1 133 + Wave1 1198 + Wave2 2461.
    raw_total = 133 + 1198 + 2461
    assert raw_total == 3792

    # Historical exclusions = 189 directional + 3 D1 legacy holds.
    historical_excluded = raw_total - cumulative_assets
    assert historical_excluded == 192

    write_ids(
        out / "wave2_positive_eligible_ids.txt",
        wave2_positive_eligible,
    )
    write_ids(
        out / "wave2_hard_negative_eligible_ids.txt",
        wave2_hn_eligible,
    )
    write_ids(
        out / "wave2_excluded_ids.txt",
        wave2_excluded,
    )

    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        text=True,
    ).strip()

    report = {
        "schema_version": "1.0",
        "policy": (
            "Cumulative D2 governance. Historical D1/Wave1 exclusions "
            "remain immutable; Teacher-v4 Wave2 corrected recollection "
            "is semantically audited before eligibility."
        ),
        "challenge_git_sha": head,
        "teacher_v4_git_sha": TEACHER_V4_SHA,
        "sources": {
            "previous_training_eligibility_report": {
                "path": str(prev_report_path),
                "sha256": sha256_file(prev_report_path),
            },
            "wave2_valid_jsonl": {
                "path": str(wave2_path),
                "sha256": sha256_file(wave2_path),
                "rows": len(wave2),
            },
            "wave2_freeze_manifest": {
                "path": str(freeze_path),
                "sha256": sha256_file(freeze_path),
            },
        },
        "wave2_semantic_gate": {
            "directional_scenario_sample_counts":
                dict(sorted(directional_counts.items())),
            "directional_unexpected_states": 0,
            "directional_semantics_status": "PASS",
            "teacher_v4_provenance_status": "PASS",
        },
        "counts": {
            "historical": {
                "d1_raw": 133,
                "wave1_raw": 1198,
                "historical_raw": 1331,
                "historical_positive_eligible": 1075,
                "historical_hard_negative_eligible": 64,
                "historical_excluded": 192,
            },
            "wave2": {
                "raw": 2461,
                "positive_raw": 2320,
                "hard_negative_raw": 141,
                "semantic_excluded": 0,
                "positive_eligible": 2320,
                "hard_negative_eligible": 141,
            },
            "cumulative": {
                "raw": raw_total,
                "positive_eligible": cumulative_positive,
                "hard_negative_eligible": cumulative_hn,
                "total_governed_training_assets": cumulative_assets,
                "excluded": historical_excluded,
            },
        },
        "status": {
            "wave2_semantic_governance": "PASS",
            "wave2_training_eligibility": "PASS",
            "cumulative_d2_governance": "PASS",
            "d2_raw_size_gate_3000_5000": (
                "PASS" if 3000 <= raw_total <= 5000 else "FAIL"
            ),
        },
    }

    assert report["status"]["d2_raw_size_gate_3000_5000"] == "PASS"

    report["report_canonical_sha256"] = canonical_sha256(report)

    report_path = out / "d2_cumulative_governance_report.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("D2_RAW =", raw_total)
    print("D2_POSITIVE_ELIGIBLE =", cumulative_positive)
    print("D2_HARD_NEGATIVE_ELIGIBLE =", cumulative_hn)
    print("D2_TOTAL_GOVERNED_ASSETS =", cumulative_assets)
    print("D2_EXCLUDED =", historical_excluded)
    print("WAVE2_DIRECTIONAL_SEMANTIC_UNEXPECTED = 0")
    print(
        "REPORT_CANONICAL_SHA256 =",
        report["report_canonical_sha256"],
    )
    print("D2_RAW_SIZE_GATE_3000_5000=PASS")
    print("D2_CUMULATIVE_GOVERNANCE=PASS")


if __name__ == "__main__":
    main()
