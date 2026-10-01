"""Command-line entry points for the A2 workflow."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shlex
import sys

from .calibration import build_development_calibration, load_formal_calibration_v1
from .config import DEFAULT_QUANT_CONFIG
from .consistency import verify_export_consistency
from .drift import analyze_drift
from .openexplorer import prepare_openexplorer_bundle
from .ptq import quantize_qdq
from .sensitivity import analyze_sensitive_nodes
from .manifest import bind_b2_gate_result
from .governance import B1_CLOSEOUT_RELATIVE, audit_a3_candidate


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m challenge.quantization.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    calibration = subparsers.add_parser("build-calibration")
    calibration.add_argument("--repo", default=".")
    calibration.add_argument("--source", default="challenge/dataset/releases/d2_v1_1/train.jsonl")
    calibration.add_argument("--out", default="artifacts/a2/dev_calibration_400")
    calibration.add_argument("--count", type=int, default=400)
    calibration.add_argument("--seed", type=int, default=20260923)

    validate_calibration = subparsers.add_parser("validate-calibration-v1")
    validate_calibration.add_argument("--repo", default=".")
    validate_calibration.add_argument(
        "--release-dir", default="challenge/dataset/releases/calibration_v1",
    )
    validate_calibration.add_argument("--check-tensors", action="store_true")

    validate_upstream = subparsers.add_parser("validate-upstream")
    validate_upstream.add_argument("--repo", default=".")
    validate_upstream.add_argument("--weights", required=True)
    validate_upstream.add_argument("--weights-manifest", required=True)
    validate_upstream.add_argument(
        "--b1-closeout-dir", default=B1_CLOSEOUT_RELATIVE.as_posix(),
    )
    validate_upstream.add_argument("--output")

    ptq = subparsers.add_parser("ptq")
    ptq.add_argument("--repo", default=".")
    ptq.add_argument("--source-onnx", default="challenge/student_v0_fp32.onnx")
    ptq.add_argument("--calibration-jsonl", required=True)
    ptq.add_argument("--calibration-manifest", required=True)
    ptq.add_argument("--quant-config", default=str(DEFAULT_QUANT_CONFIG))
    ptq.add_argument("--output", required=True)
    ptq.add_argument(
        "--exclude-node",
        action="append",
        default=[],
        help="repeatable ONNX node name to keep in FP32 for a mixed-precision candidate",
    )
    ptq.add_argument("--allow-smoke", action="store_true")
    ptq.add_argument("--allow-candidate", action="store_true")

    drift = subparsers.add_parser("drift")
    drift.add_argument("--repo", default=".")
    drift.add_argument("--baseline-onnx", required=True)
    drift.add_argument("--candidate-onnx", required=True)
    drift.add_argument("--jsonl", required=True)
    drift.add_argument("--output", required=True)
    drift.add_argument("--limit", type=int, default=100)

    openexplorer = subparsers.add_parser("prepare-openexplorer")
    openexplorer.add_argument("--repo", default=".")
    openexplorer.add_argument("--source-onnx", required=True)
    openexplorer.add_argument("--calibration-jsonl", required=True)
    openexplorer.add_argument("--calibration-manifest", required=True)
    openexplorer.add_argument("--output", required=True)
    openexplorer.add_argument("--limit", type=int)
    openexplorer.add_argument("--allow-smoke", action="store_true")
    openexplorer.add_argument("--allow-candidate", action="store_true")

    consistency = subparsers.add_parser("export-consistency")
    consistency.add_argument("--repo", default=".")
    consistency.add_argument("--weights", required=True)
    consistency.add_argument("--weights-manifest", required=True)
    consistency.add_argument("--onnx", required=True)
    consistency.add_argument("--jsonl", required=True)
    consistency.add_argument("--output", required=True)
    consistency.add_argument("--limit", type=int, default=20)
    consistency.add_argument("--allow-pending-candidate", action="store_true")

    sensitivity = subparsers.add_parser("sensitive-layers")
    sensitivity.add_argument("--repo", default=".")
    sensitivity.add_argument("--source-onnx", required=True)
    sensitivity.add_argument("--calibration-jsonl", required=True)
    sensitivity.add_argument("--calibration-manifest", required=True)
    sensitivity.add_argument("--quant-config", default=str(DEFAULT_QUANT_CONFIG))
    sensitivity.add_argument("--output", required=True)
    sensitivity.add_argument("--limit", type=int)
    sensitivity.add_argument("--max-groups", type=int)
    sensitivity.add_argument("--allow-smoke", action="store_true")
    sensitivity.add_argument("--allow-candidate", action="store_true")

    bind_b2 = subparsers.add_parser("bind-b2-result")
    bind_b2.add_argument("--repo", default=".")
    bind_b2.add_argument("--int8-manifest", required=True)
    bind_b2.add_argument("--int8-artifact", required=True)
    bind_b2.add_argument("--b2-decision", required=True)

    args = parser.parse_args()
    repo_path = Path(args.repo).resolve()
    exit_code = 0

    def output_path(value: str) -> Path:
        path = Path(value)
        return path.resolve() if path.is_absolute() else (repo_path / path).resolve()

    if args.command == "build-calibration":
        result = build_development_calibration(
            args.repo, source_jsonl=args.source, output_directory=args.out,
            count=args.count, seed=args.seed,
        )
    elif args.command == "validate-calibration-v1":
        release = load_formal_calibration_v1(
            args.repo, release_directory=args.release_dir,
        )
        result = dict(release.identity)
        if args.check_tensors:
            result["tensor_contract"] = release.validate_tensor_contract()
    elif args.command == "validate-upstream":
        result = audit_a3_candidate(
            args.repo,
            weights=args.weights,
            weights_manifest=args.weights_manifest,
            closeout_directory=args.b1_closeout_dir,
        )
        if args.output:
            output = output_path(args.output)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(
                json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        if result["formal_eligible"] is not True:
            exit_code = 2
    elif args.command == "ptq":
        result = quantize_qdq(
            args.repo, source_onnx=args.source_onnx,
            calibration_jsonl=args.calibration_jsonl,
            calibration_manifest=args.calibration_manifest,
            quant_config=args.quant_config, output_onnx=args.output,
            excluded_nodes=args.exclude_node,
            allow_smoke=args.allow_smoke,
            allow_candidate=args.allow_candidate,
        )
        command = shlex.join([sys.executable, "-m", "challenge.quantization.cli", *sys.argv[1:]])
        output_path(args.output).parent.joinpath("commands.txt").write_text(
            command + "\n", encoding="utf-8",
        )
    elif args.command == "drift":
        result = analyze_drift(
            args.repo, baseline_onnx=args.baseline_onnx,
            candidate_onnx=args.candidate_onnx, jsonl_path=args.jsonl,
            output_json=args.output, limit=args.limit,
        )
    elif args.command == "prepare-openexplorer":
        result = prepare_openexplorer_bundle(
            args.repo, source_onnx=args.source_onnx,
            calibration_jsonl=args.calibration_jsonl,
            calibration_manifest=args.calibration_manifest,
            output_directory=args.output, limit=args.limit,
            allow_smoke=args.allow_smoke, allow_candidate=args.allow_candidate,
        )
    elif args.command == "export-consistency":
        result = verify_export_consistency(
            args.repo, weights=args.weights, weights_manifest=args.weights_manifest,
            onnx_model=args.onnx, jsonl_path=args.jsonl, output_json=args.output,
            limit=args.limit, allow_pending_candidate=args.allow_pending_candidate,
        )
    elif args.command == "sensitive-layers":
        result = analyze_sensitive_nodes(
            args.repo, source_onnx=args.source_onnx,
            calibration_jsonl=args.calibration_jsonl,
            calibration_manifest=args.calibration_manifest,
            quant_config=args.quant_config, output_directory=args.output,
            limit=args.limit, max_groups=args.max_groups,
            allow_smoke=args.allow_smoke, allow_candidate=args.allow_candidate,
        )
        command = shlex.join([sys.executable, "-m", "challenge.quantization.cli", *sys.argv[1:]])
        output_path(args.output).joinpath("commands.txt").write_text(
            command + "\n", encoding="utf-8",
        )
    else:
        result = bind_b2_gate_result(
            int8_manifest=output_path(args.int8_manifest),
            int8_artifact=output_path(args.int8_artifact),
            b2_decision=output_path(args.b2_decision),
        )
    display = result
    if args.command == "prepare-openexplorer":
        display = {key: value for key, value in result.items() if key != "samples"}
        display["sample_file_groups"] = len(result["samples"])
        display["manifest"] = str(Path(args.output) / "openexplorer_input_manifest.json")
    elif args.command == "sensitive-layers":
        display = {
            "status": result["status"],
            "experiment_count": result["experiment_count"],
            "baseline_quantization_id": result["baseline_quantization_id"],
            "report": str(Path(args.output) / "sensitive_layer_report.json"),
        }
    print(json.dumps(display, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
