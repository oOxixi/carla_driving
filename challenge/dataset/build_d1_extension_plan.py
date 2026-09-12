#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, hashlib, json
from collections import Counter
from pathlib import Path

ALLOWED_BUCKETS = {"SEEN", "VARIANT"}
ALLOWED_POLICY = "TRAIN_POSITIVE"

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def canonical_json_sha256(value) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def read_jsonl(path: Path):
    rows = []
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        x = json.loads(raw)
        if not isinstance(x, dict):
            raise RuntimeError(f"{path}:{n}: expected object")
        rows.append(x)
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", default="artifacts/b1_d1_registry_final/scenario_registry_v3.csv")
    ap.add_argument("--base-dataset", default="artifacts/b1_d1_pinned_formal/dataset/d1_valid.jsonl")
    ap.add_argument("--base-provenance", default="artifacts/b1_d1_pinned_formal/provenance_manifest.json")
    ap.add_argument("--output", default="artifacts/b1_d1_extension_plan/d1_extension_plan_formal.json")
    ap.add_argument("--minimum-total", type=int, default=200)
    ap.add_argument("--target-total", type=int, default=220)
    ap.add_argument("--seed-start", type=int, default=1000000)
    args = ap.parse_args()

    repo = Path(__file__).resolve().parents[2]
    reg = (repo / args.registry).resolve()
    base_ds = (repo / args.base_dataset).resolve()
    base_prov = (repo / args.base_provenance).resolve()
    out = (repo / args.output).resolve()

    if args.minimum_total < 200:
        raise RuntimeError("--minimum-total must be >= 200")
    if args.target_total < args.minimum_total:
        raise RuntimeError("--target-total must be >= --minimum-total")
    if args.seed_start < 0:
        raise RuntimeError("--seed-start must be non-negative")

    with reg.open("r", encoding="utf-8-sig", newline="") as f:
        registry = list(csv.DictReader(f))
    base_rows = read_jsonl(base_ds)
    prov = json.loads(base_prov.read_text(encoding="utf-8"))
    if prov.get("formal_code_gate") is not True:
        raise RuntimeError("base provenance is not formal")

    eligible = []
    for r in registry:
        policy = str(r.get("policy_class") or "")
        bucket = str(r.get("source_bucket") or "").upper()
        if policy != ALLOWED_POLICY or bucket not in ALLOWED_BUCKETS:
            continue
        sid = str(r.get("scenario_id") or "")
        sp = str(r.get("scenario_path") or "")
        if not sid or not sp:
            continue
        eligible.append({
            "scenario_id": sid,
            "scenario_path": sp,
            "source_bucket": bucket,
            "policy_class": policy,
            "base_seed": int(r.get("seed") or 0),
            "command_count": int(r.get("command_count") or 0),
        })

    needed = max(0, args.target_total - len(base_rows))

    # A split group is governed by scenario_family + map + route + seed.
    # Therefore extension seeds are globally unique, rather than applying
    # the same offset to every scenario.  We also avoid every seed already
    # present in the formal base dataset.
    base_seed_values = {
        int((row.get("metadata") or {}).get("seed"))
        for row in base_rows
        if (row.get("metadata") or {}).get("seed") is not None
    }

    plan = []
    used_extension_seeds = set()
    candidate_seed = args.seed_start

    for r in eligible:
        if len(plan) >= needed:
            break

        while (
            candidate_seed in base_seed_values
            or candidate_seed in used_extension_seeds
        ):
            candidate_seed += 1

        seed = candidate_seed
        used_extension_seeds.add(seed)
        candidate_seed += 1

        eid = f'{r["scenario_id"]}__seed_{seed}'
        plan.append({
            "extension_id": eid,
            **r,
            "extension_seed": seed,
            "extension_type": "SEED_VARIANT",
        })

    if len(plan) < needed:
        raise RuntimeError(
            f"insufficient legal extension capacity: "
            f"needed={needed}, planned={len(plan)}"
        )

    if len(used_extension_seeds) != len(plan):
        raise RuntimeError("extension seeds are not globally unique")

    if base_seed_values & used_extension_seeds:
        raise RuntimeError("extension seed overlaps formal base seed")

    payload = {
        "schema_version": "1.0",
        "plan_type": "B1_D1_SEED_VARIANT_EXTENSION",
        "base_dataset_path": str(base_ds.relative_to(repo)),
        "base_dataset_file_sha256": sha256_file(base_ds),
        "base_dataset_count": len(base_rows),
        "base_provenance_path": str(base_prov.relative_to(repo)),
        "base_collection_repo_git_sha": prov.get("collection_repo_git_sha"),
        "base_config_id": prov.get("config_id"),
        "registry_path": str(reg.relative_to(repo)),
        "registry_file_sha256": sha256_file(reg),
        "minimum_total": args.minimum_total,
        "target_total": args.target_total,
        "needed": needed,
        "planned_extensions": len(plan),
        "seed_strategy": "GLOBAL_UNIQUE_HIGH_RANGE",
        "seed_start": args.seed_start,
        "allowed_source_buckets": sorted(ALLOWED_BUCKETS),
        "allowed_policy_class": ALLOWED_POLICY,
        "protected_policy_classes": [
            "EXCLUDED_OFFICIAL","RESERVED_TEST_CANDIDATE","HARD_CASE",
            "SYSTEM_FAILURE","DEFERRED_LONG_RUN","NON_RUNNABLE_METADATA"
        ],
        "plan": plan,
    }
    payload["plan_canonical_sha256"] = canonical_json_sha256(payload)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("BASE_DATASET_COUNT=" + str(len(base_rows)))
    print("MINIMUM_TOTAL=" + str(args.minimum_total))
    print("TARGET_TOTAL=" + str(args.target_total))
    print("NEEDED=" + str(needed))
    print("PLANNED_EXTENSIONS=" + str(len(plan)))
    print("SEED_STRATEGY=GLOBAL_UNIQUE_HIGH_RANGE")
    print("SEED_START=" + str(args.seed_start))
    print("PLAN_CANONICAL_SHA256=" + payload["plan_canonical_sha256"])
    print("PLAN_FILE_SHA256=" + sha256_file(out))
    print("BUCKETS=" + json.dumps(dict(Counter(x["source_bucket"] for x in plan)), sort_keys=True))
    print("B1_D1_EXTENSION_PLAN=PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
