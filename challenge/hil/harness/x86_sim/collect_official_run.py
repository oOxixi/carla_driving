"""Turn one official-image run directory into a compact evidence JSON.

The measurement runs write a lot of raw files (latency_raw.csv, soak.jsonl, ...).
The materials only need the identity, the percentile table and the soak
summary, so this collector keeps exactly those and drops the raw bulk.

Usage:
    py -3.12 challenge/hil/harness/x86_sim/collect_official_run.py \
        --run <run_dir> --out <json> [--label v3]

<run_dir> is the directory that contains ``full_*/`` and ``soak_*`` (as produced
by run_official_full_and_soak.sh, e.g. /tmp/b3_official_full_<candidate>).
"""
from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

PERCENTILE_KEYS = (
    "preprocess_ms", "packing_ms", "inference_setup_ms", "model_inference_ms",
    "postprocess_ms", "adapter_ms", "plan_validation_ms", "pre_model_ms",
    "post_model_ms", "planner_e2e_ms", "model_only_ms", "planner_overhead_ms",
)


def _first(pattern: str) -> Path | None:
    hits = sorted(glob.glob(pattern))
    return Path(hits[0]) if hits else None


def collect(run_dir: Path) -> dict:
    latency = _first(str(run_dir / "full_*" / "*" / "latency_summary.json"))
    if latency is None:
        raise FileNotFoundError(f"no latency_summary.json under {run_dir}")
    summary = json.loads(latency.read_text(encoding="utf-8"))
    metrics = summary.get("metrics_ms", {})

    full_run = {
        "run_id": summary.get("run_id"),
        "snapshot": "frozen/d2_v1_1_val",
        "cases": 539,
        "rounds": len(summary.get("rounds", {})),
        "case_runs": summary.get("trace_count"),
        "measured_ready": summary.get("measured_ready_count"),
        "outcomes": summary.get("outcome_counts"),
        "percentiles_ms": {
            key: {k: metrics[key][k] for k in ("p50", "p95", "p99", "max") if k in metrics[key]}
            for key in PERCENTILE_KEYS if key in metrics
        },
    }

    soak = {}
    soak_summary = _first(str(run_dir / "soak_*" / "*" / "stability_logs" / "soak_summary.json"))
    if soak_summary is None:
        soak_summary = _first(str(run_dir / "soak_*" / "*" / "soak_summary.json"))
    if soak_summary is not None:
        raw = json.loads(soak_summary.read_text(encoding="utf-8"))
        hardware = _first(str(run_dir / "full_*" / "*" / "hardware_env.json"))
        cpu_count = None
        if hardware is not None:
            host = json.loads(hardware.read_text(encoding="utf-8")).get("host") or {}
            cpu_count = host.get("cpu_cores")
        latency_block = raw.get("latency_ms") or {}
        utilization = (raw.get("telemetry") or {}).get("utilization") or {}
        memory = (raw.get("telemetry") or {}).get("memory") or {}
        soak = {
            "run_id": raw.get("run_id") or (Path(soak_summary).parents[1].name),
            "observed_duration_s": raw.get("observed_duration_s"),
            "iterations": raw.get("iterations"),
            "error_count": raw.get("error_count"),
            "success_rate": raw.get("success_rate"),
            "memory_drift_kib": raw.get("memory_drift_kib"),
            "peak_rss_mib": memory.get("peak_rss_mib_max"),
            "cpu_percent_max": utilization.get("cpu_percent_max"),
            "bpu_percent_max": utilization.get("bpu_percent_max"),
            "recovery_probe": raw.get("recovery_probe"),
            "latency_p95_ms": latency_block.get("overall_p95"),
            "latency_max_ms": latency_block.get("overall_max"),
            "power": (raw.get("telemetry") or {}).get("power", {}).get("source", "NOT_APPLICABLE"),
            "capacity": {
                "cpu_count": cpu_count,
                "note": "cpu_percent is a process figure; compare it with 100 x cpu_count",
            },
        }
        soak.setdefault("power", "NOT_APPLICABLE")

    hardware = _first(str(run_dir / "full_*" / "*" / "hardware_env.json"))
    env = json.loads(hardware.read_text(encoding="utf-8")) if hardware else {}

    return {
        "candidate": {
            "model_id": summary.get("identity", {}).get("model_id"),
            "weights_sha256": summary.get("identity", {}).get("model_sha256"),
            "gate_status": summary.get("identity", {}).get("gate_status"),
            "verified": summary.get("identity", {}).get("verification", {}).get("verified"),
        },
        "full_run": full_run,
        "soak_30min": soak,
        "environment": env,
        "claim_scope": {
            "class": "X86_MEASURED",
            "note": (
                "official openexplorer X86 image, candidate weights with PENDING gate; "
                "no J6P board, no A4 runtime, not an accuracy result"
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--label", default="")
    args = parser.parse_args()

    payload = collect(Path(args.run))
    if args.label:
        payload["label"] = args.label
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {args.out}: candidate={payload['candidate']['model_id']} "
          f"e2e_p95={payload['full_run']['percentiles_ms'].get('planner_e2e_ms', {}).get('p95')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
