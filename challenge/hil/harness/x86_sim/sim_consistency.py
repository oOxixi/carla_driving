"""X86 simulation consistency: float ONNX reference vs compiled artifacts.

Runs the ONNX model with onnxruntime (CPU, full precision) and the compiled
artifact with HBRuntime (X86 instruction-level simulation), then reports the
per-output cosine similarity. No board is involved.

Usage: python3 sim_consistency.py <case_dir> <artifact> [<artifact> ...]
"""
import json
import os
import sys
import time

import numpy as np
import onnxruntime as ort
from horizon_tc_ui.hb_runtime import HBRuntime

ONNX = "/work/student/student_v0_fp32.onnx"


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=np.float64).ravel()
    b = np.asarray(b, dtype=np.float64).ravel()
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return float("nan")
    return float(np.dot(a, b) / (na * nb))


def main() -> int:
    case_dir = sys.argv[1]
    artifacts = sys.argv[2:]

    sess = ort.InferenceSession(ONNX, providers=["CPUExecutionProvider"])
    feed = {i.name: np.load(os.path.join(case_dir, f"{i.name}.npy")).astype(np.float32)
            for i in sess.get_inputs()}
    ref_names = [o.name for o in sess.get_outputs()]
    t0 = time.perf_counter_ns()
    ref = sess.run(ref_names, feed)
    ref_ms = (time.perf_counter_ns() - t0) / 1e6
    ref_map = dict(zip(ref_names, ref))
    print(f"onnxruntime reference ok: {len(ref_names)} outputs, {ref_ms:.1f} ms")

    report = {
        "case_dir": case_dir,
        "onnx": ONNX,
        "onnxruntime_ms": round(ref_ms, 3),
        "artifacts": {},
    }
    out_json = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "sim_consistency.json")
    os.makedirs(os.path.dirname(out_json), exist_ok=True)

    for path in artifacts:
        print(f"\n== {path}", flush=True)
        hr = HBRuntime(model=path)
        hr_feed = {n: np.load(os.path.join(case_dir, f"{n}.npy")).astype(np.float32)
                   for n in hr.input_names}
        out = hr.run(hr.output_names, hr_feed)
        got = dict(zip(hr.output_names, out))
        cos = {n: (cosine(got[n], ref_map[n]) if n in ref_map else float("nan"))
               for n in hr.output_names}
        # The .hbm path goes through the QEMU BPU emulator (~1 min per call), so
        # only one run is kept: it is a correctness check, not a latency source.
        timed = 1 if path.endswith(".hbm") else 20
        warmup = 0 if path.endswith(".hbm") else 2
        for _ in range(warmup):
            hr.run(hr.output_names, hr_feed)
        ts = []
        for _ in range(timed):
            t0 = time.perf_counter_ns()
            hr.run(hr.output_names, hr_feed)
            ts.append((time.perf_counter_ns() - t0) / 1e6)
        ts.sort()
        entry = {
            "cosine": {k: round(v, 6) for k, v in cos.items()},
            "min_cosine": round(float(np.nanmin(list(cos.values()))), 6),
            "mean_cosine": round(float(np.nanmean(list(cos.values()))), 6),
            "latency_ms": {
                "n": len(ts),
                "mean": round(sum(ts) / len(ts), 3),
                "p50": round(ts[len(ts) // 2], 3),
                "p95": round(ts[int(len(ts) * 0.95) - 1], 3),
                "max": round(ts[-1], 3),
            },
        }
        report["artifacts"][path] = entry
        print(f"   latency mean={entry['latency_ms']['mean']} ms "
              f"p50={entry['latency_ms']['p50']} p95={entry['latency_ms']['p95']} "
              f"(n={entry['latency_ms']['n']})", flush=True)
        for name, value in sorted(cos.items(), key=lambda kv: kv[1]):
            print(f"   cosine {name:<22} {value:.6f}")
        with open(out_json, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2, ensure_ascii=False)

    print(f"\nwrote {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
