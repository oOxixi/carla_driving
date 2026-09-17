#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


D1_LEGACY_HOLD = {
    "td_5b6cdf2f648421617efb0e88",
    "td_17391f569bd1d8a5c607f1e9",
    "td_d431ad1e9ad296a0c4687551",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_sha256(obj: object) -> str:
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
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_ids(path: Path, ids: set[str]) -> None:
    path.write_text(
        "".join(f"{x}\n" for x in sorted(ids)),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--d1-jsonl", type=Path, required=True)
    parser.add_argument("--d2-jsonl", type=Path, required=True)
    parser.add_argument(
        "--directional-quarantine-ids",
        type=Path,
        required=True,
    )
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()

    d1_path = args.d1_jsonl.resolve()
    d2_path = args.d2_jsonl.resolve()
    q_path = args.directional_quarantine_ids.resolve()
    out = args.output_root.resolve()

    out.mkdir(parents=True, exist_ok=True)

    d1 = load_jsonl(d1_path)
    d2 = load_jsonl(d2_path)

    d1_by_id = {row["sample_id"]: row for row in d1}
    d2_by_id = {row["sample_id"]: row for row in d2}

    assert len(d1) == 133
    assert len(d2) == 1198
    assert len(d1_by_id) == len(d1)
    assert len(d2_by_id) == len(d2)

    d1_ids = set(d1_by_id)
    d2_ids = set(d2_by_id)

    quarantine = {
        x.strip()
        for x in q_path.read_text(encoding="utf-8").splitlines()
        if x.strip()
    }

    assert len(quarantine) == 189

    q_d1 = quarantine & d1_ids
    q_d2 = quarantine & d2_ids

    assert len(q_d1) == 8
    assert len(q_d2) == 181
    assert not (q_d1 & D1_LEGACY_HOLD)
    assert D1_LEGACY_HOLD <= d1_ids

    d2_positive = {
        row["sample_id"]
        for row in d2
        if (row.get("quality") or {}).get("training_role")
        == "POSITIVE"
    }

    d2_hn = {
        row["sample_id"]
        for row in d2
        if (row.get("quality") or {}).get("training_role")
        == "HARD_NEGATIVE"
    }

    assert len(d2_positive) == 1134
    assert len(d2_hn) == 64
    assert d2_positive.isdisjoint(d2_hn)
    assert d2_positive | d2_hn == d2_ids

    assert len(q_d2 & d2_positive) == 181
    assert len(q_d2 & d2_hn) == 0

    d1_excluded = q_d1 | D1_LEGACY_HOLD
    d1_positive_eligible = d1_ids - d1_excluded

    d2_positive_eligible = d2_positive - q_d2
    d2_hn_eligible = d2_hn - q_d2

    assert len(d1_excluded) == 11
    assert len(d1_positive_eligible) == 122
    assert len(d2_positive_eligible) == 953
    assert len(d2_hn_eligible) == 64

    cumulative_positive = (
        len(d1_positive_eligible)
        + len(d2_positive_eligible)
    )

    assert cumulative_positive == 1075

    write_ids(
        out / "d1_positive_eligible_ids.txt",
        d1_positive_eligible,
    )
    write_ids(
        out / "d1_directional_quarantine_ids.txt",
        q_d1,
    )
    write_ids(
        out / "d1_legacy_hold_ids.txt",
        D1_LEGACY_HOLD,
    )
    write_ids(
        out / "d2_positive_eligible_ids.txt",
        d2_positive_eligible,
    )
    write_ids(
        out / "d2_hard_negative_eligible_ids.txt",
        d2_hn_eligible,
    )
    write_ids(
        out / "d2_directional_quarantine_ids.txt",
        q_d2,
    )

    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        text=True,
    ).strip()

    report = {
        "schema_version": "1.0",
        "policy": (
            "Non-destructive derived training eligibility view. "
            "Historical D1/D2 JSONL assets remain immutable."
        ),
        "challenge_git_sha": head,
        "sources": {
            "d1": {
                "path": str(d1_path),
                "sha256": sha256_file(d1_path),
                "rows": len(d1),
            },
            "d2": {
                "path": str(d2_path),
                "sha256": sha256_file(d2_path),
                "rows": len(d2),
            },
            "directional_quarantine_ids": {
                "path": str(q_path),
                "sha256": sha256_file(q_path),
                "rows": len(quarantine),
            },
        },
        "counts": {
            "d1": {
                "raw": 133,
                "directional_quarantine": 8,
                "legacy_hold": 3,
                "directional_x_legacy_hold": 0,
                "excluded_union": 11,
                "positive_eligible": 122,
            },
            "d2": {
                "raw": 1198,
                "positive_raw": 1134,
                "hard_negative_raw": 64,
                "directional_quarantine": 181,
                "directional_x_positive": 181,
                "directional_x_hard_negative": 0,
                "positive_eligible": 953,
                "hard_negative_eligible": 64,
            },
            "cumulative": {
                "positive_eligible": 1075,
                "hard_negative_eligible": 64,
                "total_governed_training_assets": 1139,
            },
        },
        "status": {
            "semantic_governance": "PASS",
            "training_eligibility_set_audit": "PASS",
        },
    }

    report["report_canonical_sha256"] = canonical_sha256(report)

    (out / "training_eligibility_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("D1_POSITIVE_ELIGIBLE =", 122)
    print("D2_POSITIVE_ELIGIBLE =", 953)
    print("D2_HARD_NEGATIVE_ELIGIBLE =", 64)
    print("CUMULATIVE_POSITIVE_ELIGIBLE =", 1075)
    print("CUMULATIVE_HN_ELIGIBLE =", 64)
    print(
        "REPORT_CANONICAL_SHA256 =",
        report["report_canonical_sha256"],
    )
    print("TRAINING_ELIGIBILITY_GOVERNANCE=PASS")


if __name__ == "__main__":
    main()
