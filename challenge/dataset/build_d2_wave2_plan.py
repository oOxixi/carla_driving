#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from challenge.dataset import collect_d1_200 as base


PLAN_VERSION = "b1_d2_expansion_wave2_v1"

EXPECTED_REGISTRY_SHA256 = (
    "263b878582c6bf3a041646b9859014696601694748a90e8156ca4481c69a866e"
)
EXPECTED_PRIOR_D1_PLAN_SHA256 = (
    "c4ea670c224376e6bd69f69be22e07d4e3f89ccf3978277ae028b13edcf1e166"
)

EXPECTED_TEACHER_PROFILE = "b1-pinned-teacher-v4"
EXPECTED_TEACHER_GIT_SHA = (
    "95e97b00def8ec36f12937da34ce8bb9082c4a04"
)

EXPECTED_WAVE1_PLAN_VERSION = "b1_d2_expansion_wave1_v2"

SEED_START = 2_100_000

QUOTAS = {
    "DIRECTIONAL_RECOLLECTION": 240,
    "QWEN_CHAIN_ROUTING": 128,
    "SAFETY_COMPLEX": 240,
    "VARIANT": 358,
    "BALANCED_SEEN": 1034,
    "NON_TOWN03": 0,
}

PLANNED_RUNS = sum(QUOTAS.values())

if PLANNED_RUNS != 2000:
    raise RuntimeError(f"Wave2 must contain exactly 2000 runs, got {PLANNED_RUNS}")


DIRECTIONAL_RECOLLECTION = {
    "B06_left_turn",
    "B07_right_turn",
    "B08_lane_change_left",
    "B09_lane_change_right",
    "REG_004_advanced_rain_left_turn",
    "REG_005_advanced_rain_right_turn",
    "REG_009_challenge_lane_change_left",
    "REG_010_challenge_lane_change_right",
}

if len(DIRECTIONAL_RECOLLECTION) != 8:
    raise AssertionError("directional recollection source count must be 8")


PROCESS_FAILED_EXCLUDE = {
    "DEV_S2_BICYCLE_FOLLOW_TARGETED",
    "DEV_S2_P3_PEDESTRIAN_OVERTAKE_TARGETED",
    "DEV_S2_SPECIFIC_EVENTS_COMPACT",
    "ROUTE_GEN_TOWN03_DESTINATION",
}


# Preserve Wave1's conservative treatment. These are not the v4 directional
# semantic quarantine. They are historical acquisition-quality concerns.
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
    "D01_red_light_stop",
    "D07_low_ttc_emergency_brake",
    "D08_command_conflict_red_light_continue",
    "REG_006_advanced_red_light",
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
    "VAR_A02_low_ttc_stationary_lead",
    "VAR_A03_occluded_pedestrian",
    "VAR_A05_adjacent_lane_blocked",
    "VAR_A06_red_light_wet_weather",
    "VAR_C03_multi_target_partial_occlusion",
}


ACTION_TAGS = {
    sid: ["DIRECTIONAL_RECOLLECTION_V4"]
    for sid in DIRECTIONAL_RECOLLECTION
}


def canonical_json_sha256(value: object) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def scenario_file_path(repo: Path, row: dict[str, str]) -> Path:
    rel = Path(row["scenario_path"])
    if rel.parts and rel.parts[0] == "scenarios":
        return repo / rel
    return repo / "scenarios" / rel


def scenario_exists(repo: Path, rel: str) -> bool:
    p = Path(rel)
    return (repo / p).is_file() or (repo / "scenarios" / p).is_file()


def seed_expansion_policy(
    repo: Path,
    row: dict[str, str],
) -> tuple[bool, str]:
    path = scenario_file_path(repo, row)
    payload = json.loads(path.read_text(encoding="utf-8"))

    raw_tags = payload.get("tags") or []
    tags = {
        str(tag).strip()
        for tag in raw_tags
        if str(tag).strip()
    }

    route = payload.get("route") or {}
    planning_mode = str(route.get("planning_mode", "")).strip()

    if (
        "route_generalization" in tags
        and planning_mode == "destination"
    ):
        return (
            False,
            "ROUTE_GENERALIZATION_DESTINATION_FIXED_FIXTURE",
        )

    return True, "SEED_EXPANSION_ELIGIBLE"


def read_registry(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    required = {
        "scenario_path",
        "scenario_id",
        "family",
        "source_bucket",
        "policy_class",
        "command_count",
        "map",
        "seed",
    }

    if not rows or not required.issubset(rows[0]):
        raise RuntimeError(
            f"registry schema mismatch: {sorted(rows[0] if rows else [])}"
        )

    return rows


def load_plan_seed_values(path: Path) -> set[int]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    plan = payload.get("plan")

    if not isinstance(plan, list):
        raise RuntimeError(f"plan[] missing: {path}")

    seeds = set()

    for row in plan:
        seed = row.get("extension_seed")
        if isinstance(seed, int):
            seeds.add(seed)

    return seeds


def validate_wave1_plan(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))

    if payload.get("plan_version") != EXPECTED_WAVE1_PLAN_VERSION:
        raise RuntimeError(
            "unexpected Wave1 plan version: "
            f"{payload.get('plan_version')!r}"
        )

    plan = payload.get("plan")
    if not isinstance(plan, list) or len(plan) != 1000:
        raise RuntimeError(
            f"Wave1 plan must contain 1000 rows, got "
            f"{len(plan) if isinstance(plan, list) else '<invalid>'}"
        )

    seeds = [
        row.get("extension_seed")
        for row in plan
    ]

    if any(type(seed) is not int for seed in seeds):
        raise RuntimeError("Wave1 contains invalid extension_seed")

    if len(seeds) != len(set(seeds)):
        raise RuntimeError("Wave1 contains duplicate extension_seed")

    if min(seeds) != 2_000_000 or max(seeds) != 2_000_999:
        raise RuntimeError(
            "Wave1 seed namespace mismatch: "
            f"{min(seeds)}..{max(seeds)}"
        )

    embedded_sha = payload.get("plan_canonical_sha256")

    if not isinstance(embedded_sha, str):
        raise RuntimeError("Wave1 missing plan_canonical_sha256")

    clone = dict(payload)
    clone.pop("plan_canonical_sha256", None)

    # Wave1 computed the canonical hash before adding the field.
    actual = canonical_json_sha256(clone)

    if actual != embedded_sha:
        raise RuntimeError(
            "Wave1 canonical hash mismatch "
            f"embedded={embedded_sha} actual={actual}"
        )

    return payload


def validate_teacher_manifest(path: Path) -> dict[str, Any]:
    x = json.loads(path.read_text(encoding="utf-8"))

    if x.get("teacher_profile") != EXPECTED_TEACHER_PROFILE:
        raise RuntimeError(
            f"unexpected teacher_profile: {x.get('teacher_profile')!r}"
        )

    if x.get("teacher_git_sha") != EXPECTED_TEACHER_GIT_SHA:
        raise RuntimeError(
            f"unexpected teacher_git_sha: {x.get('teacher_git_sha')!r}"
        )

    verification = x.get("verification") or {}

    if verification.get("directional_semantic_gate") != "8/8 PASS":
        raise RuntimeError(
            "Teacher v4 directional semantic gate not frozen PASS"
        )

    if verification.get("directional_closed_loop_gate") != "8/8 SUCCEEDED":
        raise RuntimeError(
            "Teacher v4 directional closed-loop gate not frozen PASS"
        )

    return x


def validate_semantic_report(path: Path) -> dict[str, Any]:
    x = json.loads(path.read_text(encoding="utf-8"))

    counts = x.get("counts") or {}

    try:
        d1 = counts["D1"]["confirmed_directional_contamination"]
        d2 = counts["D2"]["confirmed_directional_contamination"]
        total = counts["TOTAL"]["confirmed_directional_contamination"]
    except Exception as exc:
        raise RuntimeError(
            "semantic governance report schema mismatch"
        ) from exc

    if (d1, d2, total) != (8, 181, 189):
        raise RuntimeError(
            "unexpected semantic quarantine counts: "
            f"D1={d1} D2={d2} TOTAL={total}"
        )

    return x


def validate_eligibility_report(path: Path) -> dict[str, Any]:
    x = json.loads(path.read_text(encoding="utf-8"))
    counts = x.get("counts") or {}

    try:
        d1 = counts["d1"]["positive_eligible"]
        d2 = counts["d2"]["positive_eligible"]
        hn = counts["d2"]["hard_negative_eligible"]
        cumulative = counts["cumulative"]["positive_eligible"]
    except Exception as exc:
        raise RuntimeError(
            "training eligibility report schema mismatch"
        ) from exc

    if (d1, d2, hn, cumulative) != (122, 953, 64, 1075):
        raise RuntimeError(
            "unexpected eligibility counts: "
            f"D1={d1} D2={d2} HN={hn} cumulative={cumulative}"
        )

    return x


def cap_for(row: dict[str, str], bucket: str) -> int:
    sid = row["scenario_id"]

    if sid in PROCESS_FAILED_EXCLUDE:
        return 0

    if bucket == "DIRECTIONAL_RECOLLECTION":
        return 30 if sid in DIRECTIONAL_RECOLLECTION else 0

    # The directional repair scenarios are isolated to recollection.
    # Do not let general expansion silently oversample them again.
    if sid in DIRECTIONAL_RECOLLECTION:
        return 0

    if sid in HISTORICAL_QUARANTINE_CAP4:
        return 4

    if row.get("family") in {"qwen_fullchain", "qwen_routing"}:
        return 40

    if row.get("source_bucket") == "VARIANT":
        return 32

    if sid in SAFETY_COMPLEX_HINTS:
        return 24

    return 24


def historical_status(sid: str) -> str:
    if sid in PROCESS_FAILED_EXCLUDE:
        return "PROCESS_FAILED_EXCLUDED"

    if sid in DIRECTIONAL_RECOLLECTION:
        return "V4_DIRECTIONAL_RECOLLECTION"

    if sid in HISTORICAL_QUARANTINE_CAP4:
        return "HISTORICAL_ACQUISITION_LIMITED"

    return "ELIGIBLE_OR_UNOBSERVED"


def tags_for(row: dict[str, str], bucket: str) -> list[str]:
    sid = row["scenario_id"]
    tags = list(ACTION_TAGS.get(sid, []))

    if row.get("source_bucket") == "VARIANT":
        tags.append("VARIANT")

    if row.get("family") == "qwen_fullchain":
        tags.append("QWEN_FULLCHAIN")

    if row.get("family") == "qwen_routing":
        tags.append("QWEN_ROUTING")

    if row.get("map") != "Town03":
        tags.append("NON_TOWN03")

    if sid in SAFETY_COMPLEX_HINTS:
        tags.append("SAFETY_OR_COMPLEX")

    if bucket == "DIRECTIONAL_RECOLLECTION":
        tags.extend([
            "SEMANTIC_REPAIR_RECOLLECTION",
            "TEACHER_V4_REQUIRED",
        ])

    return sorted(set(tags))


def base_allowed(
    repo: Path,
    rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    return [
        row
        for row in rows
        if row["policy_class"] == "TRAIN_POSITIVE"
        and row["source_bucket"] in {"SEEN", "VARIANT"}
        and row["scenario_id"] not in PROCESS_FAILED_EXCLUDE
        and seed_expansion_policy(repo, row)[0]
    ]


def candidate_pool(
    repo: Path,
    rows: list[dict[str, str]],
    bucket: str,
) -> list[dict[str, str]]:
    allowed = base_allowed(repo, rows)

    if bucket == "DIRECTIONAL_RECOLLECTION":
        return [
            row for row in allowed
            if row["scenario_id"] in DIRECTIONAL_RECOLLECTION
        ]

    # General expansion explicitly excludes the semantic-repair scenarios.
    allowed = [
        row for row in allowed
        if row["scenario_id"] not in DIRECTIONAL_RECOLLECTION
    ]

    if bucket == "QWEN_CHAIN_ROUTING":
        return [
            row for row in allowed
            if row["family"] in {"qwen_fullchain", "qwen_routing"}
        ]

    if bucket == "SAFETY_COMPLEX":
        return [
            row for row in allowed
            if row["scenario_id"] in SAFETY_COMPLEX_HINTS
        ]

    if bucket == "VARIANT":
        return [
            row for row in allowed
            if row["source_bucket"] == "VARIANT"
        ]

    if bucket == "BALANCED_SEEN":
        return [
            row for row in allowed
            if row["source_bucket"] == "SEEN"
        ]

    if bucket == "NON_TOWN03":
        return [
            row for row in allowed
            if row.get("map") != "Town03"
        ]

    raise RuntimeError(f"unknown quota bucket {bucket}")


def build_plan(
    repo: Path,
    rows: list[dict[str, str]],
    prior_seeds: set[int],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    wave2_namespace = set(
        range(SEED_START, SEED_START + PLANNED_RUNS)
    )

    collision = wave2_namespace & prior_seeds

    if collision:
        raise RuntimeError(
            "Wave2 reserved seed namespace overlaps prior acquisition: "
            f"{sorted(collision)[:20]}"
        )

    raw_capacity = {}

    for bucket, target in QUOTAS.items():
        pool = candidate_pool(repo, rows, bucket)

        capacity = sum(
            cap_for(row, bucket)
            for row in pool
        )

        raw_capacity[bucket] = {
            "candidate_scenarios": len(pool),
            "capacity": capacity,
            "target": target,
        }

        if capacity < target:
            raise RuntimeError(
                f"raw capacity insufficient for {bucket}: "
                f"target={target} capacity={capacity} "
                f"scenarios={len(pool)}"
            )

    print(
        "RAW_QUOTA_CAPACITY="
        + json.dumps(raw_capacity, sort_keys=True)
    )

    counts: Counter[str] = Counter()
    plan: list[dict[str, Any]] = []
    next_seed = SEED_START

    def allocate(bucket: str, target: int) -> None:
        nonlocal next_seed

        if target == 0:
            return

        pool = sorted(
            candidate_pool(repo, rows, bucket),
            key=lambda row: (
                counts[row["scenario_id"]],
                row.get("family", ""),
                row["scenario_id"],
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
                    key=lambda row: (
                        counts[row["scenario_id"]],
                        row.get("family", ""),
                        row["scenario_id"],
                    ),
                )

                stalled_rounds += 1

                if stalled_rounds > len(pool) + 2:
                    raise RuntimeError(
                        f"cannot satisfy quota {bucket}: "
                        f"target={target} made={made}"
                    )

            row = pool[cursor]
            cursor += 1

            sid = row["scenario_id"]

            # Total scenario count is global across Wave2. The cap depends on
            # the bucket in which the row is currently being allocated.
            if counts[sid] >= cap_for(row, bucket):
                continue

            if next_seed >= SEED_START + PLANNED_RUNS:
                raise RuntimeError("Wave2 seed namespace exhausted")

            if next_seed in prior_seeds:
                raise RuntimeError(
                    f"unexpected prior seed collision: {next_seed}"
                )

            extension_id = f"D2W2_{sid}__seed_{next_seed}"

            item = {
                "extension_id": extension_id,
                "scenario_id": sid,
                "scenario_path": row["scenario_path"],
                "family": row["family"],
                "source_bucket": row["source_bucket"],
                "policy_class": row["policy_class"],
                "map": row["map"],
                "base_seed": (
                    int(row["seed"])
                    if str(row["seed"]).strip()
                    else None
                ),
                "extension_seed": next_seed,
                "command_count": int(row["command_count"]),
                "quota_bucket": bucket,
                "priority_tags": tags_for(row, bucket),
                "historical_status": historical_status(sid),
                "scenario_cap": cap_for(row, bucket),
                "teacher_profile": EXPECTED_TEACHER_PROFILE,
                "teacher_git_sha": EXPECTED_TEACHER_GIT_SHA,
            }

            plan.append(item)
            counts[sid] += 1
            next_seed += 1
            made += 1
            stalled_rounds = 0

    # Scarce / purpose-specific pools first.
    allocation_order = (
        "DIRECTIONAL_RECOLLECTION",
        "QWEN_CHAIN_ROUTING",
        "SAFETY_COMPLEX",
        "VARIANT",
        "BALANCED_SEEN",
        "NON_TOWN03",
    )

    for bucket in allocation_order:
        allocate(bucket, QUOTAS[bucket])

    if len(plan) != PLANNED_RUNS:
        raise RuntimeError(
            f"planned run count mismatch: {len(plan)}"
        )

    seeds = [row["extension_seed"] for row in plan]
    ids = [row["extension_id"] for row in plan]

    if len(seeds) != len(set(seeds)):
        raise RuntimeError("duplicate extension_seed")

    if len(ids) != len(set(ids)):
        raise RuntimeError("duplicate extension_id")

    if set(seeds) & prior_seeds:
        raise RuntimeError("Wave2 seed overlaps prior acquisition")

    if seeds != list(range(SEED_START, SEED_START + PLANNED_RUNS)):
        raise RuntimeError(
            "Wave2 seeds must exactly occupy reserved namespace "
            f"{SEED_START}..{SEED_START + PLANNED_RUNS - 1}"
        )

    recollection = [
        row for row in plan
        if row["quota_bucket"] == "DIRECTIONAL_RECOLLECTION"
    ]

    recollection_counts = Counter(
        row["scenario_id"]
        for row in recollection
    )

    expected_recollection = {
        sid: 30 for sid in DIRECTIONAL_RECOLLECTION
    }

    if dict(recollection_counts) != expected_recollection:
        raise RuntimeError(
            "directional recollection must be exactly balanced 30/scenario: "
            f"{dict(sorted(recollection_counts.items()))}"
        )

    return plan, raw_capacity


def main() -> int:
    ap = argparse.ArgumentParser()

    ap.add_argument("--registry", required=True)
    ap.add_argument("--prior-d1-plan", required=True)
    ap.add_argument("--prior-wave1-plan", required=True)
    ap.add_argument("--teacher-manifest-v4", required=True)
    ap.add_argument("--semantic-report-v4", required=True)
    ap.add_argument("--eligibility-report-v4", required=True)
    ap.add_argument("--output-dir", required=True)

    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--allow-uncommitted-code", action="store_true")

    args = ap.parse_args()

    repo = Path(__file__).resolve().parents[2]

    def resolve_arg(raw: str) -> Path:
        p = Path(raw).expanduser()
        if not p.is_absolute():
            p = repo / p
        return p.resolve()

    registry_path = resolve_arg(args.registry)
    prior_d1_path = resolve_arg(args.prior_d1_plan)
    wave1_path = resolve_arg(args.prior_wave1_plan)
    teacher_manifest_path = resolve_arg(args.teacher_manifest_v4)
    semantic_report_path = resolve_arg(args.semantic_report_v4)
    eligibility_report_path = resolve_arg(args.eligibility_report_v4)
    output_dir = resolve_arg(args.output_dir)

    required_files = (
        registry_path,
        prior_d1_path,
        wave1_path,
        teacher_manifest_path,
        semantic_report_path,
        eligibility_report_path,
    )

    for path in required_files:
        if not path.is_file():
            raise RuntimeError(f"required file missing: {path}")

    registry_sha = sha256_file(registry_path)

    if registry_sha != EXPECTED_REGISTRY_SHA256:
        raise RuntimeError(
            "registry SHA mismatch "
            f"expected={EXPECTED_REGISTRY_SHA256} "
            f"actual={registry_sha}"
        )

    prior_d1_sha = sha256_file(prior_d1_path)

    if prior_d1_sha != EXPECTED_PRIOR_D1_PLAN_SHA256:
        raise RuntimeError(
            "prior D1 plan SHA mismatch "
            f"expected={EXPECTED_PRIOR_D1_PLAN_SHA256} "
            f"actual={prior_d1_sha}"
        )

    wave1_payload = validate_wave1_plan(wave1_path)
    teacher_manifest = validate_teacher_manifest(
        teacher_manifest_path
    )
    semantic_report = validate_semantic_report(
        semantic_report_path
    )
    eligibility_report = validate_eligibility_report(
        eligibility_report_path
    )

    rel = Path("challenge/dataset/build_d2_wave2_plan.py")

    if args.allow_uncommitted_code:
        builder_identity = {
            "path": str(rel),
            "git_sha": base.current_head(repo),
            "sha256": sha256_file(repo / rel),
            "tracked_matches_head": False,
        }
        formal_gate = False
        print("FORMAL_CODE_GATE=BYPASSED_FOR_DEVELOPMENT")
    else:
        builder_identity = base.verify_tracked_file_matches_head(
            repo,
            rel,
        )
        formal_gate = True
        print("FORMAL_CODE_GATE=PASS")

    rows = read_registry(registry_path)

    train_positive = [
        row
        for row in rows
        if row["policy_class"] == "TRAIN_POSITIVE"
    ]

    if any(
        row["source_bucket"] == "UNSEEN"
        for row in train_positive
    ):
        raise RuntimeError(
            "UNSEEN appears inside TRAIN_POSITIVE registry rows"
        )

    if any(
        "RESERVED_TEST" in row.get("policy_class", "")
        for row in train_positive
    ):
        raise RuntimeError(
            "reserved Test row leaked into TRAIN_POSITIVE"
        )

    missing_files = [
        row["scenario_id"]
        for row in train_positive
        if not scenario_exists(repo, row["scenario_path"])
    ]

    if missing_files:
        raise RuntimeError(
            f"scenario files missing: {missing_files[:20]}"
        )

    registry_ids = {
        row["scenario_id"]
        for row in train_positive
    }

    missing_directional = (
        DIRECTIONAL_RECOLLECTION - registry_ids
    )

    if missing_directional:
        raise RuntimeError(
            "directional recollection sources missing from "
            f"TRAIN_POSITIVE registry: {sorted(missing_directional)}"
        )

    policy_counts = Counter(
        seed_expansion_policy(repo, row)[1]
        for row in train_positive
    )

    prior_d1_seeds = load_plan_seed_values(prior_d1_path)
    wave1_seeds = load_plan_seed_values(wave1_path)

    if prior_d1_seeds & wave1_seeds:
        raise RuntimeError(
            "historical D1/Wave1 seed collision detected"
        )

    prior_seeds = prior_d1_seeds | wave1_seeds

    plan, raw_capacity = build_plan(
        repo,
        train_positive,
        prior_seeds,
    )

    bucket_counts = Counter(
        row["quota_bucket"] for row in plan
    )
    source_counts = Counter(
        row["source_bucket"] for row in plan
    )
    family_counts = Counter(
        row["family"] for row in plan
    )
    map_counts = Counter(
        row["map"] for row in plan
    )
    scenario_counts = Counter(
        row["scenario_id"] for row in plan
    )
    history_counts = Counter(
        row["historical_status"] for row in plan
    )

    normalized_bucket_counts = {
        bucket: bucket_counts.get(bucket, 0)
        for bucket in QUOTAS
    }

    if normalized_bucket_counts != QUOTAS:
        raise RuntimeError(
            "quota mismatch "
            f"expected={QUOTAS} "
            f"actual={normalized_bucket_counts}"
        )

    recollection_counts = Counter(
        row["scenario_id"]
        for row in plan
        if row["quota_bucket"] == "DIRECTIONAL_RECOLLECTION"
    )

    payload = {
        "schema_version": "1.0",
        "plan_version": PLAN_VERSION,
        "status": "D2_WAVE2_PLANNED",
        "repo_git_sha": base.current_head(repo),
        "branch": base.current_branch(repo),
        "formal_code_gate": formal_gate,
        "builder_identity": builder_identity,

        "registry": {
            "path": str(registry_path),
            "sha256": registry_sha,
            "train_positive_scenarios": len(train_positive),
        },

        "prior_acquisition": {
            "d1_extension_plan": {
                "path": str(prior_d1_path),
                "sha256": prior_d1_sha,
                "known_extension_seeds": len(prior_d1_seeds),
            },
            "wave1_plan": {
                "path": str(wave1_path),
                "sha256": sha256_file(wave1_path),
                "plan_version": wave1_payload["plan_version"],
                "plan_canonical_sha256":
                    wave1_payload["plan_canonical_sha256"],
                "known_extension_seeds": len(wave1_seeds),
            },
        },

        "teacher_identity": {
            "teacher_profile":
                teacher_manifest["teacher_profile"],
            "teacher_baseline_git_sha":
                teacher_manifest["teacher_git_sha"],
            "teacher_tag":
                teacher_manifest.get("teacher_tag"),
            "teacher_model_id":
                teacher_manifest["model_id"],
            "teacher_model_revision":
                teacher_manifest["model_revision"],
            "teacher_model_artifact_sha256":
                teacher_manifest["model_artifact_sha256"],
            "teacher_manifest_path":
                str(teacher_manifest_path),
            "teacher_manifest_sha256":
                sha256_file(teacher_manifest_path),
        },

        "governance_inputs": {
            "semantic_report": {
                "path": str(semantic_report_path),
                "sha256": sha256_file(semantic_report_path),
                "confirmed_directional_contamination": 189,
                "report_canonical_sha256":
                    semantic_report.get(
                        "report_canonical_sha256"
                    ),
            },
            "training_eligibility_report": {
                "path": str(eligibility_report_path),
                "sha256": sha256_file(eligibility_report_path),
                "current_positive_eligible": 1075,
                "current_hard_negative_eligible": 64,
                "report_canonical_sha256":
                    eligibility_report.get(
                        "report_canonical_sha256"
                    ),
            },
        },

        "policy": {
            "allowed_source_buckets": ["SEEN", "VARIANT"],
            "required_policy_class": "TRAIN_POSITIVE",
            "protected_unseen": "FORBIDDEN",
            "reserved_test_candidate": "FORBIDDEN",
            "seed_namespace": {
                "start": SEED_START,
                "end": SEED_START + PLANNED_RUNS - 1,
            },
            "prior_seed_overlap": "FORBIDDEN",
            "route_generalization_destination":
                "FIXED_FIXTURE_EXCLUDED",
            "process_failed_sources": "EXCLUDED",
            "historical_acquisition_quarantine":
                "CAP_4_PER_SCENARIO",
            "directional_recollection": {
                "teacher_required":
                    EXPECTED_TEACHER_PROFILE,
                "source_scenarios":
                    sorted(DIRECTIONAL_RECOLLECTION),
                "runs_per_scenario": 30,
                "total_runs": 240,
                "old_samples_replaced": False,
                "old_samples_policy":
                    "KEEP_IMMUTABLE_AND_QUARANTINED",
                "general_expansion_reuse":
                    "EXCLUDED",
            },
            "target": {
                "wave2_runs": 2000,
                "current_positive_eligible": 1075,
                "program_target":
                    "CUMULATIVE_VALID_TEACHER_AT_LEAST_3000_TO_5000",
            },
        },

        "quotas": QUOTAS,

        "counts": {
            "planned_runs": len(plan),
            "quota_buckets":
                dict(sorted(normalized_bucket_counts.items())),
            "raw_quota_capacity": raw_capacity,
            "seed_expansion_policy":
                dict(sorted(policy_counts.items())),
            "source_buckets":
                dict(sorted(source_counts.items())),
            "families":
                dict(sorted(family_counts.items())),
            "maps":
                dict(sorted(map_counts.items())),
            "historical_status":
                dict(sorted(history_counts.items())),
            "unique_scenarios": len(scenario_counts),
            "max_runs_per_scenario":
                max(scenario_counts.values()),
            "directional_recollection":
                dict(sorted(recollection_counts.items())),
        },

        "plan": plan,
    }

    payload["plan_canonical_sha256"] = (
        canonical_json_sha256(payload)
    )

    print("PLAN_VERSION=" + PLAN_VERSION)
    print("REPO_HEAD=" + base.current_head(repo))
    print(
        "BUILDER_SHA256="
        + builder_identity["sha256"]
    )
    print("REGISTRY_SHA256=" + registry_sha)
    print("PRIOR_D1_PLAN_SHA256=" + prior_d1_sha)
    print(
        "PRIOR_WAVE1_PLAN_SHA256="
        + sha256_file(wave1_path)
    )
    print(
        "TEACHER_MANIFEST_SHA256="
        + sha256_file(teacher_manifest_path)
    )
    print(
        "SEMANTIC_REPORT_SHA256="
        + sha256_file(semantic_report_path)
    )
    print(
        "ELIGIBILITY_REPORT_SHA256="
        + sha256_file(eligibility_report_path)
    )
    print("PLANNED_RUNS=" + str(len(plan)))
    print(
        "QUOTAS="
        + json.dumps(
            dict(sorted(normalized_bucket_counts.items())),
            sort_keys=True,
        )
    )
    print(
        "RAW_QUOTA_CAPACITY="
        + json.dumps(raw_capacity, sort_keys=True)
    )
    print(
        "SOURCE_BUCKETS="
        + json.dumps(
            dict(sorted(source_counts.items())),
            sort_keys=True,
        )
    )
    print(
        "FAMILIES="
        + json.dumps(
            dict(sorted(family_counts.items())),
            sort_keys=True,
        )
    )
    print(
        "MAPS="
        + json.dumps(
            dict(sorted(map_counts.items())),
            sort_keys=True,
        )
    )
    print(
        "DIRECTIONAL_RECOLLECTION="
        + json.dumps(
            dict(sorted(recollection_counts.items())),
            sort_keys=True,
        )
    )
    print(
        "UNIQUE_SCENARIOS="
        + str(len(scenario_counts))
    )
    print(
        "MAX_RUNS_PER_SCENARIO="
        + str(max(scenario_counts.values()))
    )
    print(
        "PLAN_CANONICAL_SHA256="
        + payload["plan_canonical_sha256"]
    )

    if args.dry_run:
        print("B1_D2_WAVE2_PLAN_DRY_RUN=PASS")
        return 0

    output_dir.mkdir(parents=True, exist_ok=True)

    plan_json = (
        output_dir / "d2_expansion_plan_wave2.json"
    )
    plan_csv = (
        output_dir / "d2_expansion_plan_wave2.csv"
    )
    manifest = (
        output_dir / "d2_expansion_plan_wave2_manifest.json"
    )
    report = (
        output_dir / "d2_expansion_plan_wave2_quality_report.md"
    )

    base.write_json(plan_json, payload)

    fieldnames = [
        "extension_id",
        "scenario_id",
        "scenario_path",
        "family",
        "source_bucket",
        "policy_class",
        "map",
        "base_seed",
        "extension_seed",
        "command_count",
        "quota_bucket",
        "priority_tags",
        "historical_status",
        "scenario_cap",
        "teacher_profile",
        "teacher_git_sha",
    ]

    with plan_csv.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
        )
        writer.writeheader()

        for row in plan:
            out = dict(row)
            out["priority_tags"] = "|".join(
                row["priority_tags"]
            )
            writer.writerow(out)

    manifest_obj = {
        "schema_version": "1.0",
        "plan_version": PLAN_VERSION,
        "repo_git_sha": base.current_head(repo),
        "formal_code_gate": formal_gate,
        "builder_identity": builder_identity,
        "plan_canonical_sha256":
            payload["plan_canonical_sha256"],
        "artifacts_sha256": {
            plan_json.name: sha256_file(plan_json),
            plan_csv.name: sha256_file(plan_csv),
        },
        "teacher_identity":
            payload["teacher_identity"],
        "governance_inputs":
            payload["governance_inputs"],
        "counts": payload["counts"],
        "quotas": QUOTAS,
    }

    base.write_json(
        manifest,
        manifest_obj,
    )

    report.write_text(
        "# B1 D2 Expansion Plan Wave 2 Quality Report\n\n"
        f"- Planned runs: {len(plan)}\n"
        f"- Seed namespace: {SEED_START}.."
        f"{SEED_START + PLANNED_RUNS - 1}\n"
        f"- Unique scenarios: {len(scenario_counts)}\n"
        f"- Source buckets: "
        f"{dict(sorted(source_counts.items()))}\n"
        f"- Families: "
        f"{dict(sorted(family_counts.items()))}\n"
        f"- Maps: "
        f"{dict(sorted(map_counts.items()))}\n"
        f"- Quotas: "
        f"{dict(sorted(bucket_counts.items()))}\n"
        f"- Directional recollection: "
        f"{dict(sorted(recollection_counts.items()))}\n"
        "- Directional recollection uses Teacher v4 only.\n"
        "- Historical 189 contaminated samples remain immutable "
        "and quarantined; Wave2 does not relabel them.\n"
        "- Protected UNSEEN/RESERVED_TEST_CANDIDATE: forbidden.\n"
        "- Route-generalization destination fixed fixtures: "
        "excluded from arbitrary seed expansion.\n"
        "- Wave2 seeds are disjoint from prior D1 and Wave1 seeds.\n",
        encoding="utf-8",
    )

    print(
        "PLAN_JSON_SHA256="
        + sha256_file(plan_json)
    )
    print(
        "PLAN_CSV_SHA256="
        + sha256_file(plan_csv)
    )
    print(
        "MANIFEST_SHA256="
        + sha256_file(manifest)
    )
    print(
        "QUALITY_REPORT_SHA256="
        + sha256_file(report)
    )
    print("B1_D2_WAVE2_PLAN_BUILD=PASS")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
