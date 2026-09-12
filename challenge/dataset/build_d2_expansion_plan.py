#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from challenge.dataset import collect_d1_200 as base

PLAN_VERSION = "b1_d2_expansion_wave1_v1"
EXPECTED_REGISTRY_SHA256 = "263b878582c6bf3a041646b9859014696601694748a90e8156ca4481c69a866e"
EXPECTED_PRIOR_D1_PLAN_SHA256 = "c4ea670c224376e6bd69f69be22e07d4e3f89ccf3978277ae028b13edcf1e166"
SEED_START = 2_000_000

QUOTAS = {
    "BALANCED_SEEN": 450,
    "VARIANT": 220,
    "UNDERCOVERED_MANEUVER": 160,
    "QWEN_CHAIN_ROUTING": 70,
    "SAFETY_COMPLEX": 80,
    "NON_TOWN03": 20,
}
PLANNED_RUNS = sum(QUOTAS.values())

PROCESS_FAILED_EXCLUDE = {
    "DEV_S2_BICYCLE_FOLLOW_TARGETED",
    "DEV_S2_P3_PEDESTRIAN_OVERTAKE_TARGETED",
    "DEV_S2_SPECIFIC_EVENTS_COMPACT",
    "ROUTE_GEN_TOWN03_DESTINATION",
}

HISTORICAL_QUARANTINE_CAP4 = {
    "ACC_A05_lane_change_left",
    "QWF_02_lane_change_then_speed",
    "QWR_07_visual_avoid_return",
    "SUP_A13_lane_change_right",
    "SUP_A14_lane_change_left_curve",
    "SUP_A15_lane_change_blocked",
    "VAR_A02_low_ttc_stationary_lead",
    "VAR_A04_lane_change_right",
}

STABLE_UNDERCOVERED = {
    "B06_left_turn",
    "B07_right_turn",
    "B08_lane_change_left",
    "B09_lane_change_right",
    "REG_004_advanced_rain_left_turn",
    "REG_005_advanced_rain_right_turn",
    "REG_009_challenge_lane_change_left",
    "REG_010_challenge_lane_change_right",
    "QWF_01_turn_then_speed",
    "QWR_05_turn_requires_qwen",
}

SAFETY_COMPLEX_HINTS = {
    "ACC_A01_lead_brake",
    "ACC_A02_red_light_conflict",
    "ACC_A03_pedestrian_crossing",
    "ACC_A04_static_obstacle_stop",
    "ACC_A06_obstacle_detour_return",
    "ACC_C04_multi_target_binding",
    "CX01_urban_intersection_conflict",
    "CX02_multi_vehicle_target_follow_brake",
    "CX03_construction_bicycle_detour",
    "CX_MAIN_01_safe_urban_mission",
    "SUP_A01_lead_brake_15m",
    "SUP_A02_lead_brake_25m_late",
    "SUP_A03_lead_brake_wet",
    "SUP_A04_red_light_close_stop_line",
    "SUP_A05_red_light_wet",
    "SUP_A06_yellow_to_red",
    "SUP_A07_pedestrian_right_to_left",
    "SUP_A08_fast_pedestrian",
    "SUP_A09_occluded_pedestrian_after_lead",
    "SUP_A10_static_vehicle_center",
    "SUP_A11_obstacle_left_offset",
    "SUP_A12_double_static_obstacle_stop",
    "SUP_A16_detour_right_static_vehicle",
    "SUP_A17_detour_left_construction",
    "SUP_A18_detour_return_original_lane",
    "SUP_C06_ignore_red_light",
    "SUP_C07_three_vehicle_binding",
    "VAR_A01_lead_brake_late",
    "VAR_A03_occluded_pedestrian",
    "VAR_A05_adjacent_lane_blocked",
    "VAR_A06_red_light_wet_weather",
    "VAR_C03_multi_target_partial_occlusion",
}

ACTION_TAGS = {
    "B06_left_turn": ["TURN_LEFT", "LOW_CURRENT_COVERAGE"],
    "REG_004_advanced_rain_left_turn": ["TURN_LEFT", "LOW_CURRENT_COVERAGE"],
    "B07_right_turn": ["TURN_RIGHT", "LOW_CURRENT_COVERAGE"],
    "REG_005_advanced_rain_right_turn": ["TURN_RIGHT", "LOW_CURRENT_COVERAGE"],
    "B08_lane_change_left": ["CHANGE_LANE_LEFT", "LOW_CURRENT_COVERAGE"],
    "REG_009_challenge_lane_change_left": ["CHANGE_LANE_LEFT", "LOW_CURRENT_COVERAGE"],
    "B09_lane_change_right": ["CHANGE_LANE_RIGHT", "LOW_CURRENT_COVERAGE"],
    "REG_010_challenge_lane_change_right": ["CHANGE_LANE_RIGHT", "LOW_CURRENT_COVERAGE"],
    "QWF_01_turn_then_speed": ["TURN_RIGHT", "QWEN_FULLCHAIN", "LOW_CURRENT_COVERAGE"],
    "QWF_02_lane_change_then_speed": ["CHANGE_LANE_LEFT", "QWEN_FULLCHAIN", "HISTORICAL_QUARANTINE"],
    "QWR_05_turn_requires_qwen": ["TURN_RIGHT", "QWEN_ROUTING", "LOW_CURRENT_COVERAGE"],
    "QWR_07_visual_avoid_return": ["AVOID_OBSTACLE", "RETURN_TO_LANE", "QWEN_ROUTING", "HISTORICAL_QUARANTINE"],
    "ACC_A05_lane_change_left": ["CHANGE_LANE_LEFT", "HISTORICAL_QUARANTINE"],
    "SUP_A13_lane_change_right": ["CHANGE_LANE_RIGHT", "HISTORICAL_QUARANTINE"],
    "SUP_A14_lane_change_left_curve": ["CHANGE_LANE_LEFT", "HISTORICAL_QUARANTINE"],
    "SUP_A15_lane_change_blocked": ["CHANGE_LANE_LEFT", "HISTORICAL_QUARANTINE"],
    "VAR_A04_lane_change_right": ["CHANGE_LANE_RIGHT", "VARIANT", "HISTORICAL_QUARANTINE"],
}


def canonical_json_sha256(value: Any) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def read_registry(path: Path) -> list[dict[str, str]]:
    # utf-8-sig intentionally strips the frozen registry BOM without mutating it.
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    required = {
        "scenario_path", "scenario_id", "family", "source_bucket",
        "policy_class", "command_count", "map", "seed",
    }
    if not rows or not required.issubset(rows[0]):
        raise RuntimeError(f"registry schema mismatch: {sorted(rows[0] if rows else [])}")
    return rows


def scenario_exists(repo: Path, rel: str) -> bool:
    p = Path(rel)
    return (repo / p).is_file() or (repo / "scenarios" / p).is_file()


def load_prior_seed_values(repo: Path, prior_plan_path: Path) -> set[int]:
    prior = json.loads(prior_plan_path.read_text(encoding="utf-8"))
    rows = prior.get("plan")
    if not isinstance(rows, list):
        raise RuntimeError("prior D1 extension plan missing plan[]")
    values = set()
    for row in rows:
        seed = row.get("extension_seed")
        if isinstance(seed, int):
            values.add(seed)
    return values


def cap_for(row: dict[str, str]) -> int:
    sid = row["scenario_id"]
    if sid in PROCESS_FAILED_EXCLUDE:
        return 0
    if sid in HISTORICAL_QUARANTINE_CAP4:
        return 4
    if sid in STABLE_UNDERCOVERED:
        return 30
    if row.get("family") in {"qwen_fullchain", "qwen_routing"}:
        return 24
    if row.get("source_bucket") == "VARIANT":
        return 24
    return 12


def historical_status(sid: str) -> str:
    if sid in PROCESS_FAILED_EXCLUDE:
        return "PROCESS_FAILED_EXCLUDED"
    if sid in HISTORICAL_QUARANTINE_CAP4:
        return "HISTORICAL_QUARANTINE_LIMITED"
    if sid in STABLE_UNDERCOVERED:
        return "ELIGIBLE_SUCCESS_UNDERCOVERED"
    return "ELIGIBLE_OR_UNOBSERVED"


def tags_for(row: dict[str, str]) -> list[str]:
    sid = row["scenario_id"]
    tags = list(ACTION_TAGS.get(sid, []))
    if row.get("source_bucket") == "VARIANT" and "VARIANT" not in tags:
        tags.append("VARIANT")
    if row.get("family") == "qwen_fullchain" and "QWEN_FULLCHAIN" not in tags:
        tags.append("QWEN_FULLCHAIN")
    if row.get("family") == "qwen_routing" and "QWEN_ROUTING" not in tags:
        tags.append("QWEN_ROUTING")
    if row.get("map") != "Town03":
        tags.append("NON_TOWN03")
    if sid in SAFETY_COMPLEX_HINTS:
        tags.append("SAFETY_OR_COMPLEX")
    return sorted(set(tags))


def candidate_pool(rows: list[dict[str, str]], bucket: str) -> list[dict[str, str]]:
    allowed = [
        r for r in rows
        if r["policy_class"] == "TRAIN_POSITIVE"
        and r["source_bucket"] in {"SEEN", "VARIANT"}
        and r["scenario_id"] not in PROCESS_FAILED_EXCLUDE
    ]
    if bucket == "BALANCED_SEEN":
        return [r for r in allowed if r["source_bucket"] == "SEEN"]
    if bucket == "VARIANT":
        return [r for r in allowed if r["source_bucket"] == "VARIANT"]
    if bucket == "UNDERCOVERED_MANEUVER":
        return [r for r in allowed if r["scenario_id"] in STABLE_UNDERCOVERED]
    if bucket == "QWEN_CHAIN_ROUTING":
        return [r for r in allowed if r["family"] in {"qwen_fullchain", "qwen_routing"}]
    if bucket == "SAFETY_COMPLEX":
        return [r for r in allowed if r["scenario_id"] in SAFETY_COMPLEX_HINTS]
    if bucket == "NON_TOWN03":
        return [r for r in allowed if r.get("map") != "Town03"]
    raise RuntimeError(f"unknown quota bucket {bucket}")


def build_plan(rows: list[dict[str, str]], prior_seeds: set[int]) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    plan: list[dict[str, Any]] = []
    next_seed = SEED_START

    # Static raw-capacity audit. This does not account for overlap between
    # quota buckets, but catches impossible quotas immediately and records
    # exactly which pool is undersized before any allocation occurs.
    raw_capacity = {}
    for bucket, target in QUOTAS.items():
        pool = candidate_pool(rows, bucket)
        capacity = sum(cap_for(r) for r in pool)
        raw_capacity[bucket] = {
            "candidate_scenarios": len(pool),
            "capacity": capacity,
            "target": target,
        }
        if capacity < target:
            raise RuntimeError(
                f"raw capacity insufficient for {bucket}: "
                f"target={target} capacity={capacity} scenarios={len(pool)}"
            )

    print("RAW_QUOTA_CAPACITY=" + json.dumps(raw_capacity, sort_keys=True))

    def allocate(bucket: str, target: int) -> None:
        nonlocal next_seed
        pool = sorted(
            candidate_pool(rows, bucket),
            key=lambda r: (
                counts[r["scenario_id"]],
                r.get("family", ""),
                r["scenario_id"],
            ),
        )
        if not pool:
            raise RuntimeError(f"empty candidate pool for {bucket}")

        made = 0
        cursor = 0
        stalled_rounds = 0

        while made < target:
            if cursor >= len(pool):
                cursor = 0
                pool = sorted(
                    pool,
                    key=lambda r: (
                        counts[r["scenario_id"]],
                        r.get("family", ""),
                        r["scenario_id"],
                    ),
                )
                stalled_rounds += 1
                if stalled_rounds > len(pool) + 2:
                    raise RuntimeError(
                        f"cannot satisfy quota {bucket}: target={target} made={made}"
                    )

            row = pool[cursor]
            cursor += 1
            sid = row["scenario_id"]
            if counts[sid] >= cap_for(row):
                continue

            while next_seed in prior_seeds:
                next_seed += 1

            if next_seed in prior_seeds:
                raise AssertionError("seed collision")

            extension_id = f"D2W1_{sid}__seed_{next_seed}"
            item = {
                "extension_id": extension_id,
                "scenario_id": sid,
                "scenario_path": row["scenario_path"],
                "family": row["family"],
                "source_bucket": row["source_bucket"],
                "policy_class": row["policy_class"],
                "map": row["map"],
                "base_seed": int(row["seed"]) if str(row["seed"]).strip() else None,
                "extension_seed": next_seed,
                "command_count": int(row["command_count"]),
                "quota_bucket": bucket,
                "priority_tags": tags_for(row),
                "historical_status": historical_status(sid),
                "scenario_cap": cap_for(row),
            }
            plan.append(item)
            counts[sid] += 1
            next_seed += 1
            made += 1
            stalled_rounds = 0

    # Order matters. QWEN_CHAIN_ROUTING is the scarcest overlapping pool,
    # so reserve its capacity before UNDERCOVERED_MANEUVER. The latter still
    # has enough non-Qwen stable maneuver scenarios to satisfy its quota.
    for bucket in (
        "QWEN_CHAIN_ROUTING",
        "UNDERCOVERED_MANEUVER",
        "NON_TOWN03",
        "SAFETY_COMPLEX",
        "VARIANT",
        "BALANCED_SEEN",
    ):
        allocate(bucket, QUOTAS[bucket])

    if len(plan) != PLANNED_RUNS:
        raise RuntimeError(f"planned run count mismatch: {len(plan)}")

    seeds = [x["extension_seed"] for x in plan]
    ids = [x["extension_id"] for x in plan]
    if len(seeds) != len(set(seeds)):
        raise RuntimeError("duplicate extension_seed")
    if len(ids) != len(set(ids)):
        raise RuntimeError("duplicate extension_id")
    if set(seeds) & prior_seeds:
        raise RuntimeError("D2 seed overlaps prior D1 extension")

    return plan


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--registry",
        default="artifacts/b1_d1_registry_final/scenario_registry_v3.csv",
    )
    ap.add_argument(
        "--prior-d1-plan",
        default="artifacts/b1_d1_extension_plan/d1_extension_plan_formal_v2.json",
    )
    ap.add_argument(
        "--output-dir",
        default="artifacts/b1_d2_expansion_plan_v1",
    )
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--allow-uncommitted-code", action="store_true")
    args = ap.parse_args()

    repo = Path(__file__).resolve().parents[2]
    registry_path = (repo / args.registry).resolve()
    prior_plan_path = (repo / args.prior_d1_plan).resolve()
    output_dir = (repo / args.output_dir).resolve()

    for p in (registry_path, prior_plan_path):
        if not p.is_file():
            raise RuntimeError(f"required file missing: {p}")

    registry_sha = base.sha256_file(registry_path)
    if registry_sha != EXPECTED_REGISTRY_SHA256:
        raise RuntimeError(
            f"registry SHA mismatch expected={EXPECTED_REGISTRY_SHA256} actual={registry_sha}"
        )

    prior_plan_sha = base.sha256_file(prior_plan_path)
    if prior_plan_sha != EXPECTED_PRIOR_D1_PLAN_SHA256:
        raise RuntimeError(
            f"prior D1 plan SHA mismatch expected={EXPECTED_PRIOR_D1_PLAN_SHA256} actual={prior_plan_sha}"
        )

    rel = "challenge/dataset/build_d2_expansion_plan.py"
    if args.allow_uncommitted_code:
        builder_identity = {
            "path": rel,
            "sha256": base.sha256_file(repo / rel),
            "matches_head": None,
            "development_override": True,
        }
        formal_gate = False
        print("FORMAL_CODE_GATE=BYPASSED_FOR_DEVELOPMENT")
    else:
        builder_identity = base.verify_tracked_file_matches_head(repo, rel)
        formal_gate = True
        print("FORMAL_CODE_GATE=PASS")

    rows = read_registry(registry_path)

    # Fail closed on protected data and registry integrity.
    train_positive = [
        r for r in rows if r["policy_class"] == "TRAIN_POSITIVE"
    ]
    if any(r["source_bucket"] == "UNSEEN" for r in train_positive):
        raise RuntimeError("UNSEEN appears inside TRAIN_POSITIVE registry rows")
    if any("RESERVED_TEST" in r.get("policy_class", "") for r in train_positive):
        raise RuntimeError("reserved Test row leaked into TRAIN_POSITIVE")

    missing_files = [
        r["scenario_id"] for r in train_positive
        if not scenario_exists(repo, r["scenario_path"])
    ]
    if missing_files:
        raise RuntimeError(f"scenario files missing: {missing_files[:20]}")

    prior_seeds = load_prior_seed_values(repo, prior_plan_path)
    plan = build_plan(train_positive, prior_seeds)

    bucket_counts = Counter(x["quota_bucket"] for x in plan)
    source_counts = Counter(x["source_bucket"] for x in plan)
    family_counts = Counter(x["family"] for x in plan)
    map_counts = Counter(x["map"] for x in plan)
    scenario_counts = Counter(x["scenario_id"] for x in plan)
    history_counts = Counter(x["historical_status"] for x in plan)

    if dict(bucket_counts) != QUOTAS:
        raise RuntimeError(
            f"quota mismatch expected={QUOTAS} actual={dict(bucket_counts)}"
        )
    for sid, count in scenario_counts.items():
        row = next(r for r in train_positive if r["scenario_id"] == sid)
        if count > cap_for(row):
            raise RuntimeError(f"scenario cap exceeded: {sid} {count}>{cap_for(row)}")

    payload = {
        "schema_version": "1.0",
        "plan_version": PLAN_VERSION,
        "status": "D2_WAVE1_PLANNED",
        "repo_git_sha": base.current_head(repo),
        "branch": base.current_branch(repo),
        "formal_code_gate": formal_gate,
        "builder_identity": builder_identity,
        "registry": {
            "path": str(registry_path.relative_to(repo)),
            "sha256": registry_sha,
            "train_positive_scenarios": len(train_positive),
        },
        "prior_d1_extension_plan": {
            "path": str(prior_plan_path.relative_to(repo)),
            "sha256": prior_plan_sha,
            "known_extension_seeds": len(prior_seeds),
        },
        "teacher_identity": {
            "teacher_baseline_git_sha": base.EXPECTED_BASELINE_GIT_SHA,
            "teacher_model_id": base.EXPECTED_MODEL_ID,
            "teacher_model_revision": base.EXPECTED_MODEL_REVISION,
            "teacher_model_artifact_sha256": base.EXPECTED_ARTIFACT_SHA256,
        },
        "policy": {
            "allowed_source_buckets": ["SEEN", "VARIANT"],
            "required_policy_class": "TRAIN_POSITIVE",
            "protected_unseen": "FORBIDDEN",
            "reserved_test_candidate": "FORBIDDEN",
            "seed_start": SEED_START,
            "process_failed_wave1_policy": "EXCLUDED",
            "historical_quarantine_policy": "CAP_4_PER_SCENARIO",
            "adaptive_strategy": (
                "Wave 1 only. Re-audit yield/coverage/failure before Wave 2; "
                "do not precommit all runs needed for 3k-5k."
            ),
        },
        "quotas": QUOTAS,
        "counts": {
            "planned_runs": len(plan),
            "quota_buckets": dict(sorted(bucket_counts.items())),
            "source_buckets": dict(sorted(source_counts.items())),
            "families": dict(sorted(family_counts.items())),
            "maps": dict(sorted(map_counts.items())),
            "historical_status": dict(sorted(history_counts.items())),
            "unique_scenarios": len(scenario_counts),
            "max_runs_per_scenario": max(scenario_counts.values()),
        },
        "plan": plan,
    }
    payload["plan_canonical_sha256"] = canonical_json_sha256(payload)

    print("PLAN_VERSION=" + PLAN_VERSION)
    print("REPO_HEAD=" + base.current_head(repo))
    print("BUILDER_SHA256=" + builder_identity["sha256"])
    print("REGISTRY_SHA256=" + registry_sha)
    print("PRIOR_D1_PLAN_SHA256=" + prior_plan_sha)
    print("PLANNED_RUNS=" + str(len(plan)))
    print("QUOTAS=" + json.dumps(dict(sorted(bucket_counts.items())), sort_keys=True))
    print("SOURCE_BUCKETS=" + json.dumps(dict(sorted(source_counts.items())), sort_keys=True))
    print("FAMILIES=" + json.dumps(dict(sorted(family_counts.items())), sort_keys=True))
    print("MAPS=" + json.dumps(dict(sorted(map_counts.items())), sort_keys=True))
    print("UNIQUE_SCENARIOS=" + str(len(scenario_counts)))
    print("MAX_RUNS_PER_SCENARIO=" + str(max(scenario_counts.values())))
    print("PLAN_CANONICAL_SHA256=" + payload["plan_canonical_sha256"])

    if args.dry_run:
        print("B1_D2_EXPANSION_PLAN_DRY_RUN=PASS")
        return 0

    output_dir.mkdir(parents=True, exist_ok=True)
    plan_json = output_dir / "d2_expansion_plan_wave1.json"
    plan_csv = output_dir / "d2_expansion_plan_wave1.csv"
    manifest = output_dir / "d2_expansion_plan_manifest.json"
    report = output_dir / "d2_expansion_plan_quality_report.md"

    base.write_json(plan_json, payload)

    fieldnames = [
        "extension_id", "scenario_id", "scenario_path", "family",
        "source_bucket", "policy_class", "map", "base_seed",
        "extension_seed", "command_count", "quota_bucket",
        "priority_tags", "historical_status", "scenario_cap",
    ]
    with plan_csv.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in plan:
            out = dict(row)
            out["priority_tags"] = "|".join(row["priority_tags"])
            w.writerow(out)

    manifest_obj = {
        "schema_version": "1.0",
        "plan_version": PLAN_VERSION,
        "repo_git_sha": base.current_head(repo),
        "formal_code_gate": formal_gate,
        "builder_identity": builder_identity,
        "plan_canonical_sha256": payload["plan_canonical_sha256"],
        "artifacts_sha256": {
            "d2_expansion_plan_wave1.json": base.sha256_file(plan_json),
            "d2_expansion_plan_wave1.csv": base.sha256_file(plan_csv),
        },
        "counts": payload["counts"],
        "quotas": QUOTAS,
    }
    base.write_json(manifest, manifest_obj)

    report.write_text(
        "# B1 D2 Expansion Plan Wave 1 Quality Report\n\n"
        f"- Planned runs: {len(plan)}\n"
        f"- Unique scenarios: {len(scenario_counts)}\n"
        f"- Source buckets: {dict(sorted(source_counts.items()))}\n"
        f"- Families: {dict(sorted(family_counts.items()))}\n"
        f"- Maps: {dict(sorted(map_counts.items()))}\n"
        f"- Quotas: {dict(sorted(bucket_counts.items()))}\n"
        "- Protected UNSEEN/RESERVED_TEST_CANDIDATE: excluded by fail-closed policy\n"
        "- Process-failed scenarios from D1 formal evidence: excluded in Wave 1\n"
        "- Historical quarantine scenarios: capped at 4 planned runs per scenario\n"
        "- Seeds: globally unique within Wave 1 and non-overlapping with prior D1 extension plan\n"
        "- Wave 2 must be generated only after Wave 1 yield/coverage/failure re-audit\n",
        encoding="utf-8",
    )

    print("PLAN_JSON_SHA256=" + base.sha256_file(plan_json))
    print("PLAN_CSV_SHA256=" + base.sha256_file(plan_csv))
    print("MANIFEST_SHA256=" + base.sha256_file(manifest))
    print("QUALITY_REPORT_SHA256=" + base.sha256_file(report))
    print("B1_D2_EXPANSION_PLAN_BUILD=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
