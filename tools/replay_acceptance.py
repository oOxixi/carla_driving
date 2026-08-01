"""Run RGB/LiDAR/Qwen records through the offline A/B/C/D acceptance chain."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from integration.offline_replay import run_replay_manifest, write_replay_report
from integration.rgb_detector import OnnxYoloDetector


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", help="UTF-8 JSONL replay manifest")
    parser.add_argument("--output", help="optional JSON acceptance report path")
    parser.add_argument("--rgb-detector-model", help="optional YOLO ONNX model")
    parser.add_argument("--confidence", type=float, default=0.35)
    parser.add_argument("--iou", type=float, default=0.45)
    parser.add_argument("--input-size", type=int, default=640)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        detector = None
        if args.rgb_detector_model:
            detector = OnnxYoloDetector(
                args.rgb_detector_model,
                confidence_threshold=args.confidence,
                iou_threshold=args.iou,
                input_size=args.input_size,
            )
        report = run_replay_manifest(args.manifest, detector=detector)
        if args.output:
            write_replay_report(report, args.output)
        print(
            "replay result="
            + json.dumps(
                {
                    "passed": report.passed,
                    "frame_count": report.frame_count,
                    "passed_frames": report.passed_frames,
                    "failed_frames": report.failed_frames,
                    "output": args.output,
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            flush=True,
        )
        for result in report.results:
            if not result.passed:
                print(
                    f"replay frame={result.frame} failures={list(result.failures)}",
                    flush=True,
                )
        return 0 if report.passed else 1
    except Exception as error:
        print(
            "replay error="
            + json.dumps(
                {"type": type(error).__name__, "message": str(error)},
                ensure_ascii=False,
                sort_keys=True,
            ),
            flush=True,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
