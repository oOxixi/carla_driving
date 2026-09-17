#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from pathlib import Path


RATIOS = {
    "TRAIN": 0.70,
    "VAL": 0.15,
    "RESERVED_TEST_CANDIDATE": 0.15,
}

EXPECTED = {
    "raw": 3792,
    "positive": 3395,
    "hard_negative": 205,
    "governed": 3600,
    "excluded": 192,
}


def load_jsonl(path: Path) -> list[dict]:
    out = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                out.append(json.loads(line))
    return out


def read_ids(path: Path) -> set[str]:
    return {
        x.strip()
        for x in path.read_text(encoding="utf-8").splitlines()
        if x.strip()
    }


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_sha(obj: object) -> str:
    payload = json.dumps(
        obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def stable_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sample_role(row: dict) -> str:
    return str(
        (row.get("quality") or {}).get("training_role")
        or "POSITIVE"
    )


def group_key(row: dict) -> str:
    meta = row.get("metadata") or {}
    value = meta.get("group_key")

    if value not in (None, ""):
        return str(value)

    # Conservative fallback: keep scenario/map/route/seed atomic.
    scenario = meta.get("scenario_id")
    map_name = meta.get("map") or meta.get("town")
    route = (
        meta.get("route_id")
        or meta.get("route")
        or meta.get("route_name")
    )
    seed = meta.get("seed")

    assert scenario not in (None, "")
    assert seed is not None

    return json.dumps(
        {
            "scenario_id": scenario,
            "map": map_name,
            "route": route,
            "seed": seed,
        },
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def scenario_family(row: dict) -> str:
    meta = row.get("metadata") or {}
    return str(meta.get("scenario_family") or "UNKNOWN")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(
                json.dumps(
                    row,
                    ensure_ascii=False,
                    sort_keys=True,
                )
                + "\n"
            )


def choose_split(
    group_rows: list[dict],
    current_total: Counter,
    current_roles: dict[str, Counter],
    targets_total: dict[str, float],
    targets_roles: dict[str, dict[str, float]],
) -> str:
    """
    Deterministic group-aware allocation.

    Primary objective:
        minimize GLOBAL split-size error after placing the group.

    Secondary objective:
        minimize training-role imbalance.

    The previous implementation compared only the candidate split's
    own normalized error. That systematically overfilled the smaller
    VAL / RESERVED_TEST_CANDIDATE targets.
    """
    g_total = len(group_rows)
    g_roles = Counter(sample_role(x) for x in group_rows)

    best = None

    for candidate in RATIOS:
        prospective_total = {
            split: current_total[split]
            + (g_total if split == candidate else 0)
            for split in RATIOS
        }

        prospective_roles = {
            split: {
                role: (
                    current_roles[split][role]
                    + (
                        g_roles.get(role, 0)
                        if split == candidate
                        else 0
                    )
                )
                for role in ("POSITIVE", "HARD_NEGATIVE")
            }
            for split in RATIOS
        }

        # Absolute squared count error makes the largest remaining
        # deficit receive groups first and converges toward 70/15/15.
        count_error = sum(
            (
                prospective_total[split]
                - targets_total[split]
            ) ** 2
            for split in RATIOS
        )

        # Strongly discourage unnecessary target overshoot.
        overshoot_error = sum(
            max(
                0.0,
                prospective_total[split]
                - targets_total[split],
            ) ** 2
            for split in RATIOS
        )

        # Role balance is secondary to group/sample split balance.
        role_error = 0.0

        for split in RATIOS:
            for role in ("POSITIVE", "HARD_NEGATIVE"):
                target = max(
                    targets_roles[split][role],
                    1.0,
                )
                role_error += (
                    (
                        prospective_roles[split][role]
                        - targets_roles[split][role]
                    )
                    / target
                ) ** 2

        remaining_deficit = (
            targets_total[candidate]
            - current_total[candidate]
        )

        key = (
            count_error + 4.0 * overshoot_error,
            role_error,
            -remaining_deficit,
            candidate,
        )

        if best is None or key < best[0]:
            best = (key, candidate)

    assert best is not None
    return best[1]


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument("--d1-jsonl", type=Path, required=True)
    parser.add_argument("--wave1-jsonl", type=Path, required=True)

    parser.add_argument(
        "--wave2-jsonl",
        type=Path,
        default=Path(
            "artifacts/b1_d2_wave2_2000_teacher_v4/"
            "dataset/d2_valid.jsonl"
        ),
    )

    parser.add_argument(
        "--historical-eligibility-root",
        type=Path,
        default=Path("artifacts/b1_training_eligibility_v4"),
    )

    parser.add_argument(
        "--wave2-governance-root",
        type=Path,
        default=Path("artifacts/b1_d2_cumulative_governance_v5"),
    )

    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("artifacts/b1_d2_split_v1"),
    )

    args = parser.parse_args()

    d1_path = args.d1_jsonl.resolve()
    w1_path = args.wave1_jsonl.resolve()
    w2_path = args.wave2_jsonl.resolve()
    hist = args.historical_eligibility_root.resolve()
    v5 = args.wave2_governance_root.resolve()
    out = args.output_root.resolve()
    out.mkdir(parents=True, exist_ok=True)

    d1 = load_jsonl(d1_path)
    w1 = load_jsonl(w1_path)
    w2 = load_jsonl(w2_path)

    assert len(d1) == 133
    assert len(w1) == 1198
    assert len(w2) == 2461

    # Eligible ID sets from frozen governance.
    d1_pos = read_ids(hist / "d1_positive_eligible_ids.txt")
    w1_pos = read_ids(hist / "d2_positive_eligible_ids.txt")
    w1_hn = read_ids(hist / "d2_hard_negative_eligible_ids.txt")

    w2_pos = read_ids(v5 / "wave2_positive_eligible_ids.txt")
    w2_hn = read_ids(v5 / "wave2_hard_negative_eligible_ids.txt")
    w2_excluded = read_ids(v5 / "wave2_excluded_ids.txt")

    assert len(d1_pos) == 122
    assert len(w1_pos) == 953
    assert len(w1_hn) == 64
    assert len(w2_pos) == 2320
    assert len(w2_hn) == 141
    assert len(w2_excluded) == 0

    eligible_ids = d1_pos | w1_pos | w1_hn | w2_pos | w2_hn

    assert len(eligible_ids) == EXPECTED["governed"]

    raw_rows = d1 + w1 + w2
    assert len(raw_rows) == EXPECTED["raw"]

    by_id = {}

    for row in raw_rows:
        sid = row["sample_id"]
        assert sid not in by_id, f"duplicate sample_id across sources: {sid}"
        by_id[sid] = row

    assert eligible_ids <= set(by_id)

    governed = [by_id[sid] for sid in sorted(eligible_ids)]

    # Reassert roles from eligibility source, not blindly from D1 historical
    # row quality fields.
    forced_roles = {}

    for sid in d1_pos | w1_pos | w2_pos:
        forced_roles[sid] = "POSITIVE"

    for sid in w1_hn | w2_hn:
        forced_roles[sid] = "HARD_NEGATIVE"

    assert len(forced_roles) == EXPECTED["governed"]

    # Work on shallow copies to preserve immutable source files.
    normalized = []

    source_lookup = {}

    for row in d1:
        source_lookup[row["sample_id"]] = "D1"
    for row in w1:
        source_lookup[row["sample_id"]] = "D2_WAVE1"
    for row in w2:
        source_lookup[row["sample_id"]] = "D2_WAVE2"

    for row in governed:
        sid = row["sample_id"]
        copy = dict(row)
        copy["_d2_split_role"] = forced_roles[sid]
        copy["_d2_source"] = source_lookup[sid]
        normalized.append(copy)

    roles = Counter(x["_d2_split_role"] for x in normalized)

    assert roles["POSITIVE"] == EXPECTED["positive"]
    assert roles["HARD_NEGATIVE"] == EXPECTED["hard_negative"]

    # Group atomicity.
    groups = defaultdict(list)

    for row in normalized:
        groups[group_key(row)].append(row)

    assert groups

    # Deterministic pseudo-random order. Larger groups first prevents
    # pathological late imbalance; SHA breaks ties reproducibly.
    ordered_groups = sorted(
        groups.items(),
        key=lambda kv: (
            -len(kv[1]),
            stable_hash(kv[0]),
        ),
    )

    targets_total = {
        split: EXPECTED["governed"] * ratio
        for split, ratio in RATIOS.items()
    }

    targets_roles = {
        split: {
            role: roles[role] * ratio
            for role in ("POSITIVE", "HARD_NEGATIVE")
        }
        for split, ratio in RATIOS.items()
    }

    current_total = Counter()
    current_roles = {
        split: Counter()
        for split in RATIOS
    }

    group_assignment = {}

    for gkey, rows in ordered_groups:
        split = choose_split(
            rows,
            current_total,
            current_roles,
            targets_total,
            targets_roles,
        )

        group_assignment[gkey] = split
        current_total[split] += len(rows)

        for row in rows:
            current_roles[split][row["_d2_split_role"]] += 1

    split_rows = {
        split: []
        for split in RATIOS
    }

    assignments = []

    for row in normalized:
        sid = row["sample_id"]
        gkey = group_key(row)
        split = group_assignment[gkey]

        clean_row = dict(row)
        clean_row.pop("_d2_split_role", None)
        clean_row.pop("_d2_source", None)

        split_rows[split].append(clean_row)

        assignments.append({
            "sample_id": sid,
            "group_key": gkey,
            "split": split,
            "training_role": forced_roles[sid],
            "source": source_lookup[sid],
            "scenario_family": scenario_family(row),
            "scenario_id": (
                (row.get("metadata") or {}).get("scenario_id")
            ),
            "seed": (
                (row.get("metadata") or {}).get("seed")
            ),
        })

    # ===== HARD GATES =====

    assigned_ids = {
        x["sample_id"]
        for x in assignments
    }

    assert assigned_ids == eligible_ids
    assert len(assignments) == EXPECTED["governed"]

    ids_by_split = {
        split: {
            row["sample_id"]
            for row in rows
        }
        for split, rows in split_rows.items()
    }

    split_names = list(RATIOS)

    for i, a in enumerate(split_names):
        for b in split_names[i + 1:]:
            assert ids_by_split[a].isdisjoint(ids_by_split[b])

    groups_by_split = {
        split: {
            x["group_key"]
            for x in assignments
            if x["split"] == split
        }
        for split in RATIOS
    }

    for i, a in enumerate(split_names):
        for b in split_names[i + 1:]:
            assert groups_by_split[a].isdisjoint(groups_by_split[b])

    assert sum(len(x) for x in split_rows.values()) == 3600

    # Split-ratio hard gate. Group atomicity allows a small deviation,
    # but a pathological allocation must never print PASS.
    actual_ratios = {
        split: len(split_rows[split]) / EXPECTED["governed"]
        for split in RATIOS
    }

    ratio_deviation = {
        split: abs(actual_ratios[split] - RATIOS[split])
        for split in RATIOS
    }

    MAX_RATIO_DEVIATION = 0.02

    assert all(
        deviation <= MAX_RATIO_DEVIATION
        for deviation in ratio_deviation.values()
    ), (
        "split ratio outside tolerance: "
        f"actual={actual_ratios}, "
        f"deviation={ratio_deviation}"
    )

    # Historical exclusions must never enter a split.
    all_raw_ids = set(by_id)
    excluded_ids = all_raw_ids - eligible_ids

    assert len(excluded_ids) == EXPECTED["excluded"]
    assert not (excluded_ids & assigned_ids)

    # Role preservation.
    assigned_roles = Counter(
        x["training_role"]
        for x in assignments
    )

    assert assigned_roles == {
        "POSITIVE": 3395,
        "HARD_NEGATIVE": 205,
    }

    # Write full JSONLs.
    for split, rows in split_rows.items():
        filename = {
            "TRAIN": "train.jsonl",
            "VAL": "val.jsonl",
            "RESERVED_TEST_CANDIDATE":
                "reserved_test_candidates.jsonl",
        }[split]

        write_jsonl(out / filename, rows)

        (out / filename.replace(".jsonl", "_sample_ids.txt")).write_text(
            "".join(
                f"{x['sample_id']}\n"
                for x in sorted(rows, key=lambda r: r["sample_id"])
            ),
            encoding="utf-8",
        )

    write_jsonl(
        out / "split_assignments.jsonl",
        sorted(
            assignments,
            key=lambda x: x["sample_id"],
        ),
    )

    per_split = {}

    for split in RATIOS:
        rows = [
            x
            for x in assignments
            if x["split"] == split
        ]

        per_split[split] = {
            "samples": len(rows),
            "groups": len({x["group_key"] for x in rows}),
            "positive": sum(
                x["training_role"] == "POSITIVE"
                for x in rows
            ),
            "hard_negative": sum(
                x["training_role"] == "HARD_NEGATIVE"
                for x in rows
            ),
            "sources": dict(sorted(Counter(
                x["source"] for x in rows
            ).items())),
            "scenario_families": dict(sorted(Counter(
                x["scenario_family"] for x in rows
            ).items())),
        }

    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        text=True,
    ).strip()

    report = {
        "schema_version": "1.0",
        "split_version": "b1_d2_provisional_split_v1",
        "status": "PASS",
        "policy": {
            "split_unit": "group_key",
            "group_atomicity": True,
            "adjacent_frame_random_split": False,
            "ratios": RATIOS,
            "role_preservation": True,
            "historical_exclusions_preserved": True,
            "note": (
                "D2 provisional group-aware split. "
                "D3 later freezes final Train/Val/Test/Calibration/"
                "official-like assets."
            ),
        },
        "challenge_git_sha": head,
        "sources": {
            "d1": {
                "path": str(d1_path),
                "sha256": sha256_file(d1_path),
                "rows": len(d1),
            },
            "wave1": {
                "path": str(w1_path),
                "sha256": sha256_file(w1_path),
                "rows": len(w1),
            },
            "wave2": {
                "path": str(w2_path),
                "sha256": sha256_file(w2_path),
                "rows": len(w2),
            },
            "historical_eligibility_report": {
                "path": str(
                    hist / "training_eligibility_report.json"
                ),
                "sha256": sha256_file(
                    hist / "training_eligibility_report.json"
                ),
            },
            "cumulative_governance_report": {
                "path": str(
                    v5 / "d2_cumulative_governance_report.json"
                ),
                "sha256": sha256_file(
                    v5 / "d2_cumulative_governance_report.json"
                ),
            },
        },
        "counts": {
            "raw": 3792,
            "governed_assets": 3600,
            "positive": 3395,
            "hard_negative": 205,
            "excluded": 192,
            "unique_groups": len(groups),
            "target_ratios": RATIOS,
            "actual_ratios": actual_ratios,
            "ratio_deviation": ratio_deviation,
            "splits": per_split,
        },
        "gates": {
            "raw_size_3000_5000": "PASS",
            "all_eligible_assigned_once": "PASS",
            "sample_overlap_zero": "PASS",
            "group_overlap_zero": "PASS",
            "split_ratio_within_2pct": "PASS",
            "historical_exclusion_leakage_zero": "PASS",
            "training_role_preserved": "PASS",
        },
    }

    report["report_canonical_sha256"] = canonical_sha(report)

    report_path = out / "split_report.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    artifact_files = [
        out / "train.jsonl",
        out / "val.jsonl",
        out / "reserved_test_candidates.jsonl",
        out / "split_assignments.jsonl",
        out / "split_report.json",
    ]

    manifest = {
        "schema_version": "1.0",
        "split_version": "b1_d2_provisional_split_v1",
        "status": "PASS",
        "challenge_git_sha": head,
        "governed_assets": 3600,
        "files": {
            p.name: {
                "sha256": sha256_file(p),
                "bytes": p.stat().st_size,
            }
            for p in artifact_files
        },
        "report_canonical_sha256":
            report["report_canonical_sha256"],
    }

    manifest["manifest_canonical_sha256"] = canonical_sha(manifest)

    manifest_path = out / "split_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("D2_RAW = 3792")
    print("D2_GOVERNED_ASSETS = 3600")
    print("D2_POSITIVE = 3395")
    print("D2_HARD_NEGATIVE = 205")
    print("D2_EXCLUDED = 192")
    print("UNIQUE_GROUPS =", len(groups))

    for split in RATIOS:
        x = per_split[split]
        print(
            split,
            "samples=", x["samples"],
            "groups=", x["groups"],
            "positive=", x["positive"],
            "hard_negative=", x["hard_negative"],
        )

    print("SAMPLE_OVERLAP = 0")
    print("GROUP_OVERLAP = 0")
    print(
        "ACTUAL_RATIOS =",
        {
            k: round(v, 6)
            for k, v in actual_ratios.items()
        },
    )
    print(
        "RATIO_DEVIATION =",
        {
            k: round(v, 6)
            for k, v in ratio_deviation.items()
        },
    )
    print("SPLIT_RATIO_GATE_2PCT=PASS")
    print("EXCLUSION_LEAKAGE = 0")
    print(
        "SPLIT_REPORT_CANONICAL_SHA256 =",
        report["report_canonical_sha256"],
    )
    print(
        "SPLIT_MANIFEST_CANONICAL_SHA256 =",
        manifest["manifest_canonical_sha256"],
    )
    print("D2_PROVISIONAL_SPLIT=PASS")
    print("D2_FINAL_DATA_GATE=PASS")


if __name__ == "__main__":
    main()
