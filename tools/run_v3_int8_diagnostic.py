#!/usr/bin/env python3
"""Compare one V3 INT8 candidate with FP32 and Teacher on the frozen replay.

This is post-hoc A2 diagnostic evidence only.  The benchmark labels were
already exposed before Adapter V3.1, so even a passing projection cannot issue
an A2/B2 Gate decision.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from challenge.benchmark.metric_evidence import (  # noqa: E402
    GATE_METRICS,
    aggregate_gate_metric_evidence,
)
from challenge.benchmark.raw_predictions import write_prediction_records  # noqa: E402
from challenge.runtime.student_x86 import OnnxModel  # noqa: E402
from tools.run_v3_independent_diagnostic import (  # noqa: E402
    ADAPTER_CONTRACT_ID,
    ADAPTER_PATH,
    DEFAULT_CASE_MANIFEST,
    DEFAULT_CASE_SET_DIGEST,
    DEFAULT_CASES,
    DEFAULT_EXPORT_EVIDENCE,
    DEFAULT_HANDOFF,
    DEFAULT_IDENTITY,
    DEFAULT_LEDGER,
    DEFAULT_ONNX,
    DEFAULT_TEMPLATE_ATTESTATION,
    DiagnosticError,
    git_sha,
    git_tracked_worktree_clean,
    load_cases,
    load_json,
    package_versions,
    percentile,
    sha256_file,
    sha256_logical_lf,
    student_records,
    teacher_records,
    verify_frozen_inputs,
)


EXPECTED_FP32_ONNX_SHA256 = (
    "681a5d4bf16ba61741ef0e559649c43c041de649eef3e8e6f0b6285beaab4286"
)
EXPECTED_WEIGHTS_SHA256 = (
    "7f379c78c170228713e3d91b8e2eabd04172010ae0ed0b8cf71afe291fe6e805"
)
TEACHER_TO_FP32_CORE_LIMIT = 0.015
TEACHER_TO_INT8_CORE_LIMIT = 0.020
FP32_TO_INT8_CORE_LIMIT = 0.010
SAFETY_LIMIT = 0.0


def canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(
            dict(value), ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def write_json(path: Path, value: Mapping[str, Any]) -> str:
    payload = canonical_json_bytes(value)
    path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


def compare_metrics(
    reference: Mapping[str, Any],
    candidate: Mapping[str, Any],
    *,
    core_limit: float,
) -> tuple[dict[str, Any], bool]:
    result: dict[str, Any] = {}
    passed = True
    for name in GATE_METRICS:
        reference_value = reference["metrics"][name]["value"]
        candidate_value = candidate["metrics"][name]["value"]
        limit = SAFETY_LIMIT if name == "safety_critical_behavior_recall" else core_limit
        drop = (
            None
            if reference_value is None or candidate_value is None
            else reference_value - candidate_value
        )
        metric_pass = drop is not None and drop <= limit + 1e-12
        passed = passed and metric_pass
        result[name] = {
            "reference": reference_value,
            "candidate": candidate_value,
            "absolute_drop": drop,
            "maximum_drop": limit,
            "pass": metric_pass,
            "numerator": candidate["metrics"][name]["numerator"],
            "denominator": candidate["metrics"][name]["denominator"],
        }
    return result, passed


def _gate_step_signature(step: Mapping[str, Any]) -> tuple[Any, ...]:
    target = step["target"]
    completion = step["completion"]
    return (
        step["behavior"],
        target.get("target_id"),
        target.get("target_lane"),
        completion.get("type"),
    )


def pairwise_decode_diagnostics(
    fp32: list[dict[str, Any]],
    int8: list[dict[str, Any]],
) -> dict[str, Any]:
    if len(fp32) != len(int8):
        raise DiagnosticError("FP32 and INT8 prediction counts differ")
    plans_equal = 0
    step_pairs = 0
    field_matches = {
        "behavior": 0,
        "target_pointer": 0,
        "target_lane": 0,
        "completion": 0,
    }
    speed_deltas: list[float] = []
    mismatched_sample_ids: list[str] = []
    for fp32_record, int8_record in zip(fp32, int8, strict=True):
        if fp32_record["sample_id"] != int8_record["sample_id"]:
            raise DiagnosticError("FP32 and INT8 sample identity/order differ")
        if fp32_record["status"] != "SUCCESS" or int8_record["status"] != "SUCCESS":
            continue
        fp32_steps = fp32_record["prediction"]["steps"]
        int8_steps = int8_record["prediction"]["steps"]
        fp32_signature = tuple(_gate_step_signature(step) for step in fp32_steps)
        int8_signature = tuple(_gate_step_signature(step) for step in int8_steps)
        if fp32_signature == int8_signature:
            plans_equal += 1
        else:
            mismatched_sample_ids.append(str(fp32_record["sample_id"]))
        for fp32_step, int8_step in zip(fp32_steps, int8_steps, strict=False):
            step_pairs += 1
            fp32_target = fp32_step["target"]
            int8_target = int8_step["target"]
            field_matches["behavior"] += int(
                fp32_step["behavior"] == int8_step["behavior"]
            )
            field_matches["target_pointer"] += int(
                fp32_target.get("target_id") == int8_target.get("target_id")
            )
            field_matches["target_lane"] += int(
                fp32_target.get("target_lane") == int8_target.get("target_lane")
            )
            field_matches["completion"] += int(
                fp32_step["completion"].get("type")
                == int8_step["completion"].get("type")
            )
            fp32_speed = fp32_target.get("target_speed_mps")
            int8_speed = int8_target.get("target_speed_mps")
            if fp32_speed is not None and int8_speed is not None:
                speed_deltas.append(abs(float(fp32_speed) - float(int8_speed)))
    return {
        "plan_gate_field_agreement": {
            "numerator": plans_equal,
            "denominator": len(fp32),
            "value": plans_equal / len(fp32),
            "mismatched_sample_ids": mismatched_sample_ids,
        },
        "step_field_agreement": {
            name: {
                "numerator": value,
                "denominator": step_pairs,
                "value": value / step_pairs if step_pairs else None,
            }
            for name, value in field_matches.items()
        },
        "target_speed_abs_delta_mps": {
            "count": len(speed_deltas),
            "mean": sum(speed_deltas) / len(speed_deltas) if speed_deltas else None,
            "p95": percentile(speed_deltas, 0.95),
            "max": max(speed_deltas) if speed_deltas else None,
        },
    }


def verify_int8_identity(
    int8_path: Path,
    manifest_path: Path,
    fp32_path: Path,
) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    int8_sha = sha256_file(int8_path)
    if manifest.get("int8_artifact_sha256") != int8_sha:
        raise DiagnosticError("INT8 manifest top-level artifact SHA256 mismatch")
    if (manifest.get("output") or {}).get("sha256") != int8_sha:
        raise DiagnosticError("INT8 manifest output SHA256 mismatch")
    if manifest.get("source_fp32_onnx_sha256") != sha256_file(fp32_path):
        raise DiagnosticError("INT8 manifest does not bind the selected FP32 ONNX")
    if manifest.get("source_fp32_weights_sha256") != EXPECTED_WEIGHTS_SHA256:
        raise DiagnosticError("INT8 manifest does not bind the selected FP32 weights")
    if manifest.get("gate_status") not in {"NOT_FORMAL", "PENDING_B2_INT8_GATE"}:
        raise DiagnosticError("unexpected INT8 diagnostic gate status")

    quant_config_path = manifest_path.with_name("quant_config.yaml")
    calibration_manifest_path = manifest_path.with_name("calibration_manifest.json")
    if sha256_file(quant_config_path) != manifest.get("quant_config_sha256"):
        raise DiagnosticError("quant config SHA256 mismatch")
    calibration = manifest.get("calibration") or {}
    if (
        sha256_logical_lf(calibration_manifest_path)
        != manifest.get("calibration_manifest_sha256")
    ):
        raise DiagnosticError("calibration manifest logical-LF SHA256 mismatch")
    expected_checkout = calibration.get("manifest_worktree_sha256")
    if expected_checkout and sha256_file(calibration_manifest_path) != expected_checkout:
        raise DiagnosticError("calibration manifest checkout SHA256 mismatch")
    return {
        "quantization_id": manifest.get("quantization_id"),
        "status": manifest.get("status"),
        "gate_status": manifest.get("gate_status"),
        "model_id": manifest.get("model_id"),
        "config_id": manifest.get("config_id"),
        "int8_sha256": int8_sha,
        "int8_size_bytes": int8_path.stat().st_size,
        "source_fp32_onnx_sha256": manifest.get("source_fp32_onnx_sha256"),
        "source_fp32_weights_sha256": manifest.get("source_fp32_weights_sha256"),
        "calibration_manifest_sha256": manifest.get("calibration_manifest_sha256"),
        "quant_config_sha256": manifest.get("quant_config_sha256"),
        "excluded_nodes": (manifest.get("quantization") or {}).get("excluded_nodes", []),
        "manifest_path": manifest_path.relative_to(REPOSITORY_ROOT).as_posix(),
        "manifest_sha256": sha256_file(manifest_path),
    }


def build_readme(report: Mapping[str, Any]) -> str:
    def rows(comparison: Mapping[str, Any]) -> list[str]:
        return [
            (
                f"| `{name}` | {comparison[name]['reference']:.6f} | "
                f"{comparison[name]['candidate']:.6f} | "
                f"{comparison[name]['absolute_drop']:.6f} | "
                f"{comparison[name]['maximum_drop']:.6f} | "
                f"{'PASS' if comparison[name]['pass'] else 'FAIL'} |"
            )
            for name in GATE_METRICS
        ]

    projection = report["threshold_projection"]
    return "\n".join(
        [
            "# V3.1 INT8 post-hoc diagnostic",
            "",
            "Status: `POST_HOC_DIAGNOSTIC_ONLY`; this is not an A2/B2 Gate signature.",
            "",
            f"- INT8 SHA256: `{report['int8_candidate']['int8_sha256']}`",
            f"- Quantization ID: `{report['int8_candidate']['quantization_id']}`",
            f"- Adapter: `{report['adapter_contract_id']}`",
            f"- Samples: `{report['dataset']['sample_count']}`",
            f"- Projection: `{'PASS' if projection['pass'] else 'FAIL'}`",
            "",
            "## Teacher to INT8",
            "",
            "| Metric | Teacher | INT8 | Drop | Limit | Result |",
            "|---|---:|---:|---:|---:|---|",
            *rows(report["comparisons"]["teacher_to_int8"]),
            "",
            "## FP32 to INT8",
            "",
            "| Metric | FP32 | INT8 | Extra drop | Limit | Result |",
            "|---|---:|---:|---:|---:|---|",
            *rows(report["comparisons"]["fp32_to_int8"]),
            "",
            "The benchmark was exposed before Adapter V3.1. These results may select a "
            "candidate for a future unseen B2 evaluation, but cannot issue a formal Gate.",
            "",
        ]
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    repo = Path(args.repo_root).resolve()
    destination = Path(args.output)
    destination = destination.resolve() if destination.is_absolute() else (repo / destination).resolve()
    staging = destination.with_name(destination.name + ".tmp")
    if destination.exists() or staging.exists():
        raise DiagnosticError("output or staging directory already exists")

    def resolved(value: str | Path) -> Path:
        path = Path(value)
        return path.resolve() if path.is_absolute() else (repo / path).resolve()

    paths = {
        "cases": resolved(args.cases),
        "identity": resolved(args.identity),
        "case_manifest": resolved(args.case_manifest),
        "case_set_digest": resolved(args.case_set_digest),
        "ledger": resolved(args.ledger),
        "fp32": resolved(args.fp32),
        "export_evidence": resolved(args.export_evidence),
        "handoff": resolved(args.handoff),
        "template_attestation": resolved(args.template_attestation),
        "int8": resolved(args.int8),
        "int8_manifest": resolved(args.int8_manifest),
    }
    cases = load_cases(paths["cases"])
    dataset = verify_frozen_inputs(
        repo,
        paths["cases"],
        paths["identity"],
        paths["case_manifest"],
        paths["case_set_digest"],
        paths["ledger"],
        cases,
    )
    if sha256_file(paths["fp32"]) != EXPECTED_FP32_ONNX_SHA256:
        raise DiagnosticError("FP32 ONNX is not the frozen V3 candidate")
    export = load_json(paths["export_evidence"])
    if export.get("status") != "PASS":
        raise DiagnosticError("FP32 export consistency is not PASS")
    if export.get("onnx_sha256") != EXPECTED_FP32_ONNX_SHA256:
        raise DiagnosticError("FP32 export evidence ONNX binding mismatch")
    if export.get("weights_sha256") != EXPECTED_WEIGHTS_SHA256:
        raise DiagnosticError("FP32 export evidence weight binding mismatch")
    handoff = load_json(paths["handoff"])
    candidate_identity = handoff.get("candidate_identity") or {}
    if candidate_identity.get("weights_sha256") != EXPECTED_WEIGHTS_SHA256:
        raise DiagnosticError("A3 handoff weight binding mismatch")
    int8_identity = verify_int8_identity(
        paths["int8"], paths["int8_manifest"], paths["fp32"],
    )

    teacher = teacher_records(cases)
    fp32_runtime = OnnxModel(str(paths["fp32"]))
    fp32, fp32_ms = student_records(
        repo, cases, fp32_runtime, model_id=str(candidate_identity.get("model_id")),
    )
    int8_runtime = OnnxModel(str(paths["int8"]))
    int8, int8_ms = student_records(
        repo, cases, int8_runtime, model_id=str(candidate_identity.get("model_id")),
    )
    teacher_evidence = aggregate_gate_metric_evidence(cases, teacher)
    fp32_evidence = aggregate_gate_metric_evidence(cases, fp32)
    int8_evidence = aggregate_gate_metric_evidence(cases, int8)
    teacher_to_fp32, fp32_pass = compare_metrics(
        teacher_evidence, fp32_evidence, core_limit=TEACHER_TO_FP32_CORE_LIMIT,
    )
    teacher_to_int8, int8_pass = compare_metrics(
        teacher_evidence, int8_evidence, core_limit=TEACHER_TO_INT8_CORE_LIMIT,
    )
    fp32_to_int8, extra_pass = compare_metrics(
        fp32_evidence, int8_evidence, core_limit=FP32_TO_INT8_CORE_LIMIT,
    )
    fp32_schema = fp32_evidence["coverage"]["success_count"] / len(cases)
    int8_schema = int8_evidence["coverage"]["success_count"] / len(cases)
    projected_pass = (
        fp32_pass and int8_pass and extra_pass
        and fp32_schema == 1.0 and int8_schema == 1.0
    )
    template_attestation = load_json(paths["template_attestation"])
    report: dict[str, Any] = {
        "schema_version": "1.0",
        "status": "POST_HOC_DIAGNOSTIC_ONLY",
        "formal_gate_eligible": False,
        "formal_release_status": "BLOCKED_NOT_FINAL",
        "adapter_contract_id": ADAPTER_CONTRACT_ID,
        "dataset": dataset,
        "fp32_candidate": {
            "model_id": candidate_identity.get("model_id"),
            "config_id": candidate_identity.get("config_id"),
            "weights_sha256": EXPECTED_WEIGHTS_SHA256,
            "onnx_sha256": EXPECTED_FP32_ONNX_SHA256,
        },
        "int8_candidate": int8_identity,
        "teacher_evidence": teacher_evidence,
        "fp32_evidence": fp32_evidence,
        "int8_evidence": int8_evidence,
        "comparisons": {
            "teacher_to_fp32": teacher_to_fp32,
            "teacher_to_int8": teacher_to_int8,
            "fp32_to_int8": fp32_to_int8,
        },
        "pairwise_fp32_to_int8": pairwise_decode_diagnostics(fp32, int8),
        "threshold_projection": {
            "pass": projected_pass,
            "formal_decision": False,
            "teacher_to_fp32_core_limit": TEACHER_TO_FP32_CORE_LIMIT,
            "teacher_to_int8_core_limit": TEACHER_TO_INT8_CORE_LIMIT,
            "fp32_to_int8_core_limit": FP32_TO_INT8_CORE_LIMIT,
            "safety_limit": SAFETY_LIMIT,
            "fp32_schema_validity": fp32_schema,
            "int8_schema_validity": int8_schema,
        },
        "runtime": {
            "packages": package_versions(),
            "fp32_execution_provider": fp32_runtime.providers[0],
            "int8_execution_provider": int8_runtime.providers[0],
            "fp32_model_only_ms": {
                "count": len(fp32_ms),
                "mean": sum(fp32_ms) / len(fp32_ms),
                "p50": percentile(fp32_ms, 0.50),
                "p95": percentile(fp32_ms, 0.95),
                "max": max(fp32_ms),
            },
            "int8_model_only_ms": {
                "count": len(int8_ms),
                "mean": sum(int8_ms) / len(int8_ms),
                "p50": percentile(int8_ms, 0.50),
                "p95": percentile(int8_ms, 0.95),
                "max": max(int8_ms),
            },
            "timing_scope": "local CPU diagnostic only; not B3 formal latency evidence",
        },
        "source_bindings": {
            "evaluation_git_sha": git_sha(repo),
            "evaluation_tracked_worktree_clean": git_tracked_worktree_clean(repo),
            "runner_path": Path(__file__).resolve().relative_to(repo).as_posix(),
            "runner_sha256": sha256_file(Path(__file__).resolve()),
            "adapter_path": ADAPTER_PATH.as_posix(),
            "adapter_sha256": sha256_file(repo / ADAPTER_PATH),
            "template_identity_status": template_attestation.get("status"),
        },
        "formal_blockers": [
            "RUN_EXECUTED_BY_A2_ROLE_EXCEPTION_NOT_INDEPENDENT_B2",
            "BENCHMARK_LABELS_EXPOSED_BEFORE_THIS_ADAPTER_REVISION",
            "FORMAL_B2_POLICY_NOT_FROZEN",
            "A3_FP32_GATE_NOT_FORMALLY_PASSED",
            "A2_CANNOT_SELF_SIGN_INT8_GATE",
        ],
        "use_restrictions": [
            "Do not use these 240 labels for calibration, tuning, or candidate repair.",
            "Do not rename this diagnostic as A2_INT8_GATE_PASSED.",
            "Use the selected candidate only as input to a new unseen B2 evaluation.",
        ],
    }

    staging.mkdir(parents=True)
    try:
        teacher_sha = write_prediction_records(
            staging / "teacher_reference_predictions.jsonl", teacher,
        )
        fp32_sha = write_prediction_records(staging / "student_fp32_predictions.jsonl", fp32)
        int8_sha = write_prediction_records(staging / "student_int8_predictions.jsonl", int8)
        report["prediction_bindings"] = {
            "teacher_reference_predictions_sha256": teacher_sha,
            "student_fp32_predictions_sha256": fp32_sha,
            "student_int8_predictions_sha256": int8_sha,
        }
        report_sha = write_json(staging / "diagnostic_report.json", report)
        (staging / "README.md").write_text(
            build_readme(report), encoding="utf-8", newline="\n",
        )
        names = (
            "README.md",
            "diagnostic_report.json",
            "student_fp32_predictions.jsonl",
            "student_int8_predictions.jsonl",
            "teacher_reference_predictions.jsonl",
        )
        (staging / "SHA256SUMS").write_text(
            "\n".join(f"{sha256_file(staging / name)}  {name}" for name in names)
            + "\n",
            encoding="ascii",
            newline="\n",
        )
        staging.replace(destination)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return {
        "output": str(destination),
        "diagnostic_report_sha256": report_sha,
        "int8_candidate": int8_identity,
        "threshold_projection": report["threshold_projection"],
        "pairwise_fp32_to_int8": report["pairwise_fp32_to_int8"],
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--repo-root", default=str(REPOSITORY_ROOT))
    result.add_argument("--cases", default=str(DEFAULT_CASES))
    result.add_argument("--identity", default=str(DEFAULT_IDENTITY))
    result.add_argument("--case-manifest", default=str(DEFAULT_CASE_MANIFEST))
    result.add_argument("--case-set-digest", default=str(DEFAULT_CASE_SET_DIGEST))
    result.add_argument("--ledger", default=str(DEFAULT_LEDGER))
    result.add_argument("--fp32", default=str(DEFAULT_ONNX))
    result.add_argument("--export-evidence", default=str(DEFAULT_EXPORT_EVIDENCE))
    result.add_argument("--handoff", default=str(DEFAULT_HANDOFF))
    result.add_argument("--template-attestation", default=str(DEFAULT_TEMPLATE_ATTESTATION))
    result.add_argument("--int8", required=True)
    result.add_argument("--int8-manifest", required=True)
    result.add_argument("--output", required=True)
    return result


def main() -> int:
    try:
        result = run(parser().parse_args())
    except (DiagnosticError, KeyError, OSError, TypeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
