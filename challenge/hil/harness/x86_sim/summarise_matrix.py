"""Summarise an X86-simulation matrix: cohorts x heads, from per-cohort summaries.

Usage: python3 summarise_matrix.py <log_dir> <out_json> <prefix> [<prefix> ...]

Each prefix matches files named ``90_matrix_<prefix>_<cohort>.json`` produced by
``run_x86_matrix.sh``; the script prints a head-by-cohort table and records the
global minimum so the coverage claim is easy to check.
"""
import glob
import json
import os
import statistics
import sys


def main() -> int:
    log_dir, out_json = sys.argv[1], sys.argv[2]
    prefixes = sys.argv[3:] or ["bpuc"]
    report: dict[str, dict] = {}
    global_min = None
    total_cases = 0
    below_099 = 0

    for prefix in prefixes:
        pattern = os.path.join(log_dir, f"90_matrix_{prefix}_*.json")
        for path in sorted(glob.glob(pattern)):
            cohort = os.path.basename(path)[len(f"90_matrix_{prefix}_"):-5]
            data = json.loads(open(path, encoding="utf-8").read())
            heads = {k: {"min": v["min"], "p50": v["p50"], "below_0_99": v["below_0_99"]}
                     for k, v in data["head_stats"].items()}
            entry = {"cases": data["cases"], "heads": heads,
                     "head_min_below_0_99": sum(v["below_0_99"] for v in data["head_stats"].values()),
                     "backbone_worst_min": min(v["min"] for v in data["backbone_stats"].items().__iter__().__next__()[1:2]) if False else None}
            worst_backbone = min((v["min"], k) for k, v in data["backbone_stats"].items())
            entry["backbone_worst"] = {"min": round(worst_backbone[0], 6), "tensor": worst_backbone[1]}
            entry["head_worst"] = {"min": round(min(v["min"] for v in heads.values()), 6),
                                   "head": min(heads.items(), key=lambda kv: kv[1]["min"])[0]}
            report.setdefault(prefix, {})[cohort] = entry
            total_cases += data["cases"]
            below_099 += entry["head_min_below_0_99"]
            global_min = entry["head_worst"]["min"] if global_min is None else min(global_min, entry["head_worst"]["min"])

    for prefix, cohorts in report.items():
        print(f"\n=== {prefix} ===")
        heads = sorted({h for c in cohorts.values() for h in c["heads"]})
        print(f"{'cohort':<20}{'cases':>6}" + "".join(f"{h[:18]:>20}" for h in heads))
        for cohort, entry in sorted(cohorts.items()):
            row = "".join(f"{entry['heads'].get(h, {}).get('min', float('nan')):>20.4f}" for h in heads)
            print(f"{cohort:<20}{entry['cases']:>6}{row}")
        for cohort, entry in sorted(cohorts.items()):
            print(f"  {cohort:<18} worst head {entry['head_worst']['head']} min={entry['head_worst']['min']:.6f}"
                  f" | backbone worst {entry['backbone_worst']['min']:.6f}")

    summary = {"prefixes": prefixes, "matrix": report, "total_cases": total_cases,
               "head_case_observations_below_0_99": below_099, "global_head_min": global_min}
    with open(out_json, "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, ensure_ascii=False)
    print(f"\ncases={total_cases}  head-case observations below 0.99 = {below_099}  global head min = {global_min}")
    print(f"wrote {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
