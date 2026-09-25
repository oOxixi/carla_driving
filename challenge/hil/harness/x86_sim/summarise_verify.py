"""Summarise a batch of hb_verifier logs into per-tensor cosine statistics.

Usage: python3 summarise_verify.py <log_dir> <out_json>
"""
import glob
import json
import os
import re
import statistics
import sys

ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

HEADS = (
    "plan_length_logits", "behavior_logits", "target_pointer_logits", "target_lane_logits",
    "target_speed_mps", "completion_type_logits", "on_failure_logits", "confidence",
    "requires_confirmation_logits", "replan_condition_logits",
)


def percentile(values, q):
    ordered = sorted(values)
    if not ordered:
        return None
    index = min(len(ordered) - 1, max(0, int(round(q * (len(ordered) - 1)))))
    return ordered[index]


def main() -> int:
    log_dir, out_json = sys.argv[1], sys.argv[2]
    per_case: dict[str, dict[str, float]] = {}
    for path in sorted(glob.glob(os.path.join(log_dir, "*.log"))):
        case = os.path.basename(path)[:-4]
        values: dict[str, float] = {}
        with open(path, encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                line = ANSI.sub("", line).rstrip()
                if "|" not in line:
                    continue
                parts = [p.strip() for p in line.split("|")]
                if len(parts) < 4:
                    continue
                tensor, cosine = parts[2], parts[3]
                try:
                    values[tensor] = float(cosine)
                except ValueError:
                    continue
        if values:
            per_case[case] = values

    tensors = [t for t in HEADS if any(t in v for v in per_case.values())]
    backbone = sorted({t for v in per_case.values() for t in v} - set(tensors))

    stats = {}
    for tensor in list(tensors) + backbone:
        series = [v[tensor] for v in per_case.values() if tensor in v]
        if not series:
            continue
        stats[tensor] = {
            "n": len(series),
            "min": round(min(series), 6),
            "p05": round(percentile(series, 0.05), 6),
            "p50": round(percentile(series, 0.50), 6),
            "mean": round(statistics.fmean(series), 6),
            "max": round(max(series), 6),
            "below_0_99": sum(1 for s in series if s < 0.99),
            "below_0_999": sum(1 for s in series if s < 0.999),
        }

    report = {"cases": len(per_case), "log_dir": log_dir,
              "head_stats": {t: stats[t] for t in tensors if t in stats},
              "backbone_stats": {t: stats[t] for t in backbone if t in stats},
              "per_case": per_case}
    os.makedirs(os.path.dirname(os.path.abspath(out_json)), exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)

    print(f"cases: {len(per_case)}")
    print(f"{'tensor':<32}{'n':>4}{'min':>10}{'p05':>10}{'p50':>10}{'mean':>10}{'max':>10}"
          f"{'<0.99':>7}{'<0.999':>8}")
    for tensor in tensors:
        s = stats.get(tensor)
        if s:
            print(f"{tensor:<32}{s['n']:>4}{s['min']:>10.4f}{s['p05']:>10.4f}{s['p50']:>10.4f}"
                  f"{s['mean']:>10.4f}{s['max']:>10.4f}{s['below_0_99']:>7}{s['below_0_999']:>8}")
    if backbone:
        worst = min((stats[t]["min"], t) for t in backbone if t in stats)
        print(f"\nbackbone tensors: {len(backbone)}, worst min cosine {worst[0]:.4f} ({worst[1]})")
    print(f"wrote {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
