"""Command-line entry points for the A2 workflow."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .calibration import build_development_calibration
from .drift import analyze_drift
from .ptq import quantize_qdq


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m challenge.quantization.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    calibration = subparsers.add_parser("build-calibration")
    calibration.add_argument("--repo", default=".")
    calibration.add_argument("--source", default="challenge/dataset/releases/d2_v1_1/train.jsonl")
    calibration.add_argument("--out", default="artifacts/a2/dev_calibration_400")
    calibration.add_argument("--count", type=int, default=400)
    calibration.add_argument("--seed", type=int, default=20260923)

    ptq = subparsers.add_parser("ptq")
    ptq.add_argument("--repo", default=".")
    ptq.add_argument("--source-onnx", default="challenge/student_v0_fp32.onnx")
    ptq.add_argument("--calibration-jsonl", required=True)
    ptq.add_argument("--calibration-manifest", required=True)
    ptq.add_argument("--output", required=True)
    ptq.add_argument("--allow-smoke", action="store_true")

    drift = subparsers.add_parser("drift")
    drift.add_argument("--repo", default=".")
    drift.add_argument("--baseline-onnx", required=True)
    drift.add_argument("--candidate-onnx", required=True)
    drift.add_argument("--jsonl", required=True)
    drift.add_argument("--output", required=True)
    drift.add_argument("--limit", type=int, default=100)

    args = parser.parse_args()
    if args.command == "build-calibration":
        result = build_development_calibration(
            args.repo, source_jsonl=args.source, output_directory=args.out,
            count=args.count, seed=args.seed,
        )
    elif args.command == "ptq":
        result = quantize_qdq(
            args.repo, source_onnx=args.source_onnx,
            calibration_jsonl=args.calibration_jsonl,
            calibration_manifest=args.calibration_manifest,
            output_onnx=args.output, allow_smoke=args.allow_smoke,
        )
    else:
        result = analyze_drift(
            args.repo, baseline_onnx=args.baseline_onnx,
            candidate_onnx=args.candidate_onnx, jsonl_path=args.jsonl,
            output_json=args.output, limit=args.limit,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
