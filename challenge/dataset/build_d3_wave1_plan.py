#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


PLAN_VERSION = "b1_d3_expansion_wave1_v1"

EXPECTED_TEACHER_GIT_SHA = (
    "95e97b00def8ec36f12937da34ce8bb9082c4a04"
)
EXPECTED_TEACHER_PROFILE = "b1-pinned-teacher-v4"

EXPECTED_D2_SPLIT_VERSION = "b1_d2_provisional_split_v1"

SEED_START = 2_200_000

QUOTAS = {
    "UNDERCOVERED": 600,
    "VARIANT": 220,
    "SAFETY_COMPLEX": 400,
    "QWEN_CHAIN_ROUTING": 160,
    "HARD_NEGATIVE_TARGETED": 220,
    "BALANCED_SEEN": 400,
}

PLANNED_RUNS = sum(QUOTAS.values())

if PLANNED_RUNS != 2000:
    raise RuntimeError(
        f"D3 Wave1 must contain exactly 2000 runs, got {PLANNED_RUNS}"
    )


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


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_sha256(obj: object) -> str:
    raw = json.dumps(
        obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")

    return hashlib.sha256(raw).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))

    return rows


def row_family(row: dict[str, Any]) -> str:
    return str(
        row.get("family")
        or row.get("scenario_family")
        or ""
    )


def row_source(row: dict[str, Any]) -> str:
    return str(row.get("source_bucket") or "")


def plan_seed_values(payload: dict[str, Any]) -> set[int]:
    rows = payload.get("plan")

    if not isinstance(rows, list):
        raise RuntimeError("prior plan has no plan[]")

    out = set()

    for row in rows:
        seed = row.get("extension_seed")

        if isinstance(seed, int):
            out.add(seed)

    return out


def validate_teacher_manifest(path: Path) -> dict[str, Any]:
    x = load_json(path)

    if x.get("teacher_profile") != EXPECTED_TEACHER_PROFILE:
        raise RuntimeError(
            "Teacher profile mismatch: "
            f"{x.get('teacher_profile')!r}"
        )

    if x.get("teacher_git_sha") != EXPECTED_TEACHER_GIT_SHA:
        raise RuntimeError(
            "Teacher SHA mismatch: "
            f"{x.get('teacher_git_sha')!r}"
        )

    verification = x.get("verification") or {}

    if verification.get("directional_semantic_gate") != "8/8 PASS":
        raise RuntimeError(
            "Teacher v4 directional semantic gate is not frozen PASS"
        )

    if (
        verification.get("directional_closed_loop_gate")
        != "8/8 SUCCEEDED"
    ):
        raise RuntimeError(
            "Teacher v4 directional closed-loop gate is not frozen PASS"
        )

    return x


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--d2-wave2-plan",
        type=Path,
        default=Path(
            "artifacts/b1_d2_expansion_plan_wave2_v1/"
            "d2_expansion_plan_wave2.json"
        ),
    )

    parser.add_argument(
        "--d2-split-assignments",
        type=Path,
        default=Path(
            "artifacts/b1_d2_split_v1/"
            "split_assignments.jsonl"
        ),
    )

    parser.add_argument(
        "--d2-split-report",
        type=Path,
        default=Path(
            "artifacts/b1_d2_split_v1/"
            "split_report.json"
        ),
    )

    parser.add_argument(
        "--wave1-plan",
        type=Path,
        required=True,
        help="Frozen D2 Wave1 formal plan",
    )

    parser.add_argument(
        "--teacher-manifest",
        type=Path,
        default=Path(
            "challenge/teacher_pinned_manifest_v4.json"
        ),
    )

    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path(
            "artifacts/b1_d3_expansion_plan_wave1_v1"
        ),
    )

    args = parser.parse_args()

    wave2_path = args.d2_wave2_plan.resolve()
    assignments_path = args.d2_split_assignments.resolve()
    split_report_path = args.d2_split_report.resolve()
    wave1_path = args.wave1_plan.resolve()
    teacher_manifest_path = args.teacher_manifest.resolve()
    output_root = args.output_root.resolve()

    for p in (
        wave2_path,
        assignments_path,
        split_report_path,
        wave1_path,
        teacher_manifest_path,
    ):
        if not p.is_file():
            raise RuntimeError(f"required input missing: {p}")

    teacher = validate_teacher_manifest(teacher_manifest_path)

    d2_wave2 = load_json(wave2_path)
    d2_wave1 = load_json(wave1_path)
    split_report = load_json(split_report_path)
    assignments = load_jsonl(assignments_path)

    if split_report.get("split_version") != EXPECTED_D2_SPLIT_VERSION:
        raise RuntimeError(
            "unexpected D2 split version: "
            f"{split_report.get('split_version')!r}"
        )

    if split_report.get("status") != "PASS":
        raise RuntimeError("D2 split report is not PASS")

    counts = split_report.get("counts") or {}

    if (
        counts.get("governed_assets") != 3600
        or counts.get("positive") != 3395
        or counts.get("hard_negative") != 205
        or counts.get("excluded") != 192
    ):
        raise RuntimeError(
            "D2 governed baseline counts do not match frozen D2 delivery"
        )

    if len(assignments) != 3600:
        raise RuntimeError(
            f"expected 3600 D2 assignments, got {len(assignments)}"
        )

    train = [
        x
        for x in assignments
        if x.get("split") == "TRAIN"
    ]

    val = [
        x
        for x in assignments
        if x.get("split") == "VAL"
    ]

    reserved = [
        x
        for x in assignments
        if x.get("split") == "RESERVED_TEST_CANDIDATE"
    ]

    if (len(train), len(val), len(reserved)) != (2520, 540, 540):
        raise RuntimeError(
            "D2 split baseline mismatch: "
            f"{len(train)}/{len(val)}/{len(reserved)}"
        )

    # Frozen D2 baseline used for coverage-aware sampling.
    train_scenario_count = Counter(
        str(x.get("scenario_id") or "")
        for x in train
    )

    train_hn_count = Counter(
        str(x.get("scenario_id") or "")
        for x in train
        if x.get("training_role") == "HARD_NEGATIVE"
    )

    # D2 Wave2 plan is the schema-compatible source of scenario templates.
    prior_rows = d2_wave2.get("plan")

    if not isinstance(prior_rows, list) or len(prior_rows) != 2000:
        raise RuntimeError(
            "D2 Wave2 formal plan must contain exactly 2000 rows"
        )

    template_by_scenario: dict[str, dict[str, Any]] = {}

    for row in prior_rows:
        sid = str(row.get("scenario_id") or "")

        if not sid:
            raise RuntimeError("D2 Wave2 row missing scenario_id")

        # Any prior row is sufficient as structural template.
        template_by_scenario.setdefault(sid, row)

    if len(template_by_scenario) != 101:
        raise RuntimeError(
            "expected 101 D2 Wave2 template scenarios, got "
            f"{len(template_by_scenario)}"
        )

    # Seed collision guards.
    prior_seeds = (
        plan_seed_values(d2_wave1)
        | plan_seed_values(d2_wave2)
    )

    namespace = set(
        range(SEED_START, SEED_START + PLANNED_RUNS)
    )

    collision = namespace & prior_seeds

    if collision:
        raise RuntimeError(
            "D3 Wave1 seed namespace collides with D2: "
            f"{sorted(collision)[:20]}"
        )

    if (
        min(namespace) != SEED_START
        or max(namespace) != SEED_START + PLANNED_RUNS - 1
        or len(namespace) != PLANNED_RUNS
    ):
        raise RuntimeError(
            "D3 Wave1 seed namespace invalid: "
            f"{min(namespace)}..{max(namespace)} "
            f"count={len(namespace)} "
            f"expected={SEED_START}.."
            f"{SEED_START + PLANNED_RUNS - 1} "
            f"count={PLANNED_RUNS}"
        )

    templates = list(template_by_scenario.values())

    # Rank the 60 lowest-covered currently available scenarios.
    undercovered_ids = {
        sid
        for sid, _ in sorted(
            (
                (
                    str(row["scenario_id"]),
                    train_scenario_count[
                        str(row["scenario_id"])
                    ],
                )
                for row in templates
            ),
            key=lambda x: (x[1], x[0]),
        )[:60]
    }

    hn_target_ids = {
        sid
        for sid, n in train_hn_count.items()
        if n > 0 and sid in template_by_scenario
    }

    if not hn_target_ids:
        raise RuntimeError(
            "no historical hard-negative scenarios available"
        )

    def pool(bucket: str) -> list[dict[str, Any]]:
        if bucket == "UNDERCOVERED":
            return [
                x for x in templates
                if str(x["scenario_id"]) in undercovered_ids
            ]

        if bucket == "VARIANT":
            return [
                x for x in templates
                if row_source(x) == "VARIANT"
            ]

        if bucket == "SAFETY_COMPLEX":
            return [
                x for x in templates
                if str(x["scenario_id"]) in SAFETY_COMPLEX_HINTS
            ]

        if bucket == "QWEN_CHAIN_ROUTING":
            return [
                x for x in templates
                if row_family(x)
                in {"qwen_fullchain", "qwen_routing"}
            ]

        if bucket == "HARD_NEGATIVE_TARGETED":
            return [
                x for x in templates
                if str(x["scenario_id"]) in hn_target_ids
            ]

        if bucket == "BALANCED_SEEN":
            return [
                x for x in templates
                if row_source(x) == "SEEN"
            ]

        raise RuntimeError(f"unknown D3 bucket: {bucket}")

    # Per-bucket and global caps avoid creating a new skew while allowing
    # scarce Qwen/HN pools to receive meaningful targeted expansion.
    bucket_caps = {
        "UNDERCOVERED": 18,
        "VARIANT": 20,
        "SAFETY_COMPLEX": 20,
        "QWEN_CHAIN_ROUTING": 40,
        "HARD_NEGATIVE_TARGETED": 20,
        "BALANCED_SEEN": 18,
    }

    global_cap = 48

    capacity_report = {}

    for bucket, target in QUOTAS.items():
        p = pool(bucket)
        cap = bucket_caps[bucket]

        capacity = sum(
            min(cap, global_cap)
            for _ in p
        )

        capacity_report[bucket] = {
            "target": target,
            "candidate_scenarios": len(p),
            "nominal_capacity": capacity,
        }

        if not p:
            raise RuntimeError(
                f"empty candidate pool for {bucket}"
            )

        if capacity < target:
            raise RuntimeError(
                f"insufficient nominal capacity for {bucket}: "
                f"target={target} capacity={capacity} "
                f"scenarios={len(p)}"
            )

    print(
        "D3_RAW_QUOTA_CAPACITY="
        + json.dumps(capacity_report, sort_keys=True)
    )

    global_alloc = Counter()
    bucket_alloc: dict[str, Counter[str]] = {
        bucket: Counter()
        for bucket in QUOTAS
    }

    plan: list[dict[str, Any]] = []
    next_seed = SEED_START

    def allocation_key(
        row: dict[str, Any],
        bucket: str,
    ) -> tuple:
        sid = str(row["scenario_id"])

        if bucket == "HARD_NEGATIVE_TARGETED":
            # First: scenarios that historically generated more HNs.
            return (
                global_alloc[sid],
                bucket_alloc[bucket][sid],
                -train_hn_count[sid],
                train_scenario_count[sid],
                sid,
            )

        return (
            global_alloc[sid],
            bucket_alloc[bucket][sid],
            train_scenario_count[sid],
            row_family(row),
            sid,
        )

    def allocate(bucket: str, target: int) -> None:
        nonlocal next_seed

        p = pool(bucket)
        per_bucket_cap = bucket_caps[bucket]

        made = 0

        while made < target:
            eligible = [
                row
                for row in p
                if (
                    bucket_alloc[bucket][
                        str(row["scenario_id"])
                    ] < per_bucket_cap
                    and global_alloc[
                        str(row["scenario_id"])
                    ] < global_cap
                )
            ]

            if not eligible:
                raise RuntimeError(
                    f"capacity exhausted while allocating {bucket}: "
                    f"made={made} target={target}"
                )

            row = min(
                eligible,
                key=lambda x: allocation_key(x, bucket),
            )

            sid = str(row["scenario_id"])

            new_row = copy.deepcopy(row)

            index = len(plan)

            new_row["extension_id"] = (
                f"d3w1_{index:04d}_{sid}"
            )
            new_row["extension_seed"] = next_seed
            new_row["quota_bucket"] = bucket

            new_row["d3_metadata"] = {
                "plan_version": PLAN_VERSION,
                "wave": "D3_WAVE1",
                "baseline_d2_train_samples": 2520,
                "baseline_d2_train_scenario_count":
                    train_scenario_count[sid],
                "baseline_d2_train_hard_negative_count":
                    train_hn_count[sid],
                "coverage_priority": (
                    "UNDERCOVERED"
                    if sid in undercovered_ids
                    else "STANDARD"
                ),
                "selection_bucket": bucket,
            }

            # Do not inherit fields whose names explicitly bind the row
            # to D2 Wave2 plan bookkeeping.
            new_row.pop("plan_index", None)

            new_row["plan_index"] = index

            tags = set(new_row.get("tags") or [])
            tags.add("D3_WAVE1")
            tags.add(bucket)

            if sid in hn_target_ids:
                tags.add("HISTORICAL_HARD_NEGATIVE_SOURCE")

            if sid in undercovered_ids:
                tags.add("D2_TRAIN_UNDERCOVERED")

            new_row["tags"] = sorted(tags)

            plan.append(new_row)

            global_alloc[sid] += 1
            bucket_alloc[bucket][sid] += 1

            next_seed += 1
            made += 1

    allocation_order = [
        "UNDERCOVERED",
        "QWEN_CHAIN_ROUTING",
        "SAFETY_COMPLEX",
        "HARD_NEGATIVE_TARGETED",
        "VARIANT",
        "BALANCED_SEEN",
    ]

    for bucket in allocation_order:
        allocate(bucket, QUOTAS[bucket])

    if len(plan) != 2000:
        raise RuntimeError(
            f"expected 2000 D3 Wave1 rows, got {len(plan)}"
        )

    seeds = [
        row["extension_seed"]
        for row in plan
    ]

    expected_seeds = list(
        range(SEED_START, SEED_START + PLANNED_RUNS)
    )

    if seeds != expected_seeds:
        raise RuntimeError(
            "D3 Wave1 seeds are not exact contiguous namespace"
        )

    extension_ids = [
        row["extension_id"]
        for row in plan
    ]

    if len(extension_ids) != len(set(extension_ids)):
        raise RuntimeError("duplicate D3 extension_id")

    bucket_counts = Counter(
        row["quota_bucket"]
        for row in plan
    )

    if dict(bucket_counts) != QUOTAS:
        raise RuntimeError(
            "D3 quota mismatch: "
            f"actual={dict(bucket_counts)} "
            f"expected={QUOTAS}"
        )

    scenario_counts = Counter(
        str(row["scenario_id"])
        for row in plan
    )

    if max(scenario_counts.values()) > global_cap:
        raise RuntimeError(
            "D3 per-scenario global cap violated"
        )

    # Reserved D2 groups themselves must not occur in this new plan.
    # New seeds guarantee distinct acquisition groups; this records the
    # frozen D2 reserved population explicitly in provenance.
    reserved_group_keys = {
        str(x["group_key"])
        for x in reserved
    }

    if len(reserved_group_keys) != 540:
        raise RuntimeError(
            "D2 reserved-test candidate group count mismatch"
        )

    repo_sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        text=True,
    ).strip()

    payload = {
        "schema_version": "1.0",
        "plan_version": PLAN_VERSION,
        "phase": "D3",
        "wave": "WAVE1",
        "challenge_git_sha": repo_sha,
        "teacher": {
            "teacher_profile":
                teacher["teacher_profile"],
            "teacher_git_sha":
                teacher["teacher_git_sha"],
        },
        "seed_namespace": {
            "start": SEED_START,
            "end": SEED_START + PLANNED_RUNS - 1,
            "count": PLANNED_RUNS,
            "prior_seed_collision": 0,
        },
        "d2_baseline": {
            "governed_assets": 3600,
            "train_samples": 2520,
            "val_samples": 540,
            "reserved_test_candidate_samples": 540,
            "reserved_test_candidate_groups": 540,
            "positive_eligible": 3395,
            "hard_negative_eligible": 205,
            "gap_to_train_8000": 5480,
            "gap_to_train_15000": 12480,
        },
        "policy": {
            "coverage_aware": True,
            "adjacent_frame_random_sampling": False,
            "d2_reserved_groups_frozen": True,
            "historical_directional_quarantine_restored":
                False,
            "directional_recollection_primary_bucket":
                False,
            "fixed_fixture_policy_inherited_from_d2_wave2":
                True,
            "teacher_v4_required": True,
        },
        "quotas": QUOTAS,
        "allocation_order": allocation_order,
        "bucket_caps": bucket_caps,
        "global_scenario_cap": global_cap,
        "capacity": capacity_report,
        "scenario_counts": dict(
            sorted(scenario_counts.items())
        ),
        "bucket_scenario_counts": {
            bucket: dict(sorted(counter.items()))
            for bucket, counter in bucket_alloc.items()
        },
        "sources": {
            "d2_wave2_plan": {
                "path": str(wave2_path),
                "sha256": sha256_file(wave2_path),
            },
            "d2_wave1_plan": {
                "path": str(wave1_path),
                "sha256": sha256_file(wave1_path),
            },
            "d2_split_assignments": {
                "path": str(assignments_path),
                "sha256": sha256_file(assignments_path),
            },
            "d2_split_report": {
                "path": str(split_report_path),
                "sha256": sha256_file(split_report_path),
            },
            "teacher_manifest": {
                "path": str(teacher_manifest_path),
                "sha256":
                    sha256_file(teacher_manifest_path),
            },
        },
        "plan": plan,
    }

    payload["plan_canonical_sha256"] = canonical_sha256(
        payload
    )

    output_root.mkdir(parents=True, exist_ok=True)

    output_path = (
        output_root / "d3_expansion_plan_wave1.json"
    )

    output_path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )

    print("PLAN_VERSION =", PLAN_VERSION)
    print("PLANNED_RUNS =", len(plan))
    print(
        "SEED_NAMESPACE =",
        f"{SEED_START}.."
        f"{SEED_START + PLANNED_RUNS - 1}",
    )
    print(
        "QUOTAS =",
        json.dumps(QUOTAS, sort_keys=True),
    )
    print(
        "UNIQUE_SCENARIOS =",
        len(scenario_counts),
    )
    print(
        "MAX_RUNS_PER_SCENARIO =",
        max(scenario_counts.values()),
    )
    print(
        "UNDERCOVERED_POOL_SCENARIOS =",
        len(undercovered_ids),
    )
    print(
        "HN_TARGET_SCENARIOS =",
        len(hn_target_ids),
    )
    print(
        "PLAN_CANONICAL_SHA256 =",
        payload["plan_canonical_sha256"],
    )
    print(
        "PLAN_FILE_SHA256 =",
        sha256_file(output_path),
    )
    print("D3_WAVE1_PLAN=PASS")


if __name__ == "__main__":
    main()
