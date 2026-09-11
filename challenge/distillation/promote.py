"""CLI for the evidence-gated A3 FP32 weight manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

from .artifacts import promote_fp32_candidate


def _read(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Apply the A3 FP32 accuracy gate")
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--weights", required=True)
    parser.add_argument("--teacher-evaluation", required=True)
    parser.add_argument("--student-evaluation", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-core-drop", type=float, default=0.015)
    parser.add_argument("--max-safety-drop", type=float, default=0.0)
    args = parser.parse_args(argv)
    report = promote_fp32_candidate(
        _read(args.candidate),
        weights_path=args.weights,
        teacher_evaluation=_read(args.teacher_evaluation),
        student_evaluation=_read(args.student_evaluation),
        output_path=args.output,
        max_core_drop=args.max_core_drop,
        max_safety_drop=args.max_safety_drop,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if report["gate_status"] == "A3_FP32_GATE_PASSED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
