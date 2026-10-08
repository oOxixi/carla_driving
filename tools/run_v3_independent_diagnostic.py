#!/usr/bin/env python3
"""Run a one-shot, non-formal V3 replay on B1 Independent Validation v1.

This utility deliberately does not publish a B2 Gate decision.  It exists to
produce auditable diagnostic evidence when the historical benchmark cannot be
promoted through the repository's fail-closed formal path (for example because
authoritative template identities are unavailable).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import subprocess
import sys
import time
from collections import defaultdict
from collections.abc import Iterable, Mapping
from importlib import metadata
from pathlib import Path
from typing import Any

# Direct ``python tools/...`` execution does not automatically expose the
# repository root on sys.path.
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

import torch

from challenge.benchmark.metric_evidence import (
    GATE_METRICS,
    aggregate_gate_metric_evidence,
)
from challenge.benchmark.raw_predictions import write_prediction_records
from challenge.planner.student_adapter import StudentPlanAdapter
from challenge.runtime.student_x86 import OnnxModel
from challenge.student.preprocess import StudentPreprocessor
from runtime.interface_registry import InterfaceRegistry, InterfaceValidationError


DEFAULT_CASES = Path(
    "challenge/dataset/governance/b1_closeout_v1/"
    "independent_validation_v1/cases.jsonl"
)
DEFAULT_IDENTITY = DEFAULT_CASES.with_name("dataset_identity.json")
DEFAULT_CASE_MANIFEST = DEFAULT_CASES.with_name("case_manifest.json")
DEFAULT_CASE_SET_DIGEST = DEFAULT_CASES.with_name("case_set_digest.json")
DEFAULT_LEDGER = DEFAULT_CASES.parents[1] / "SHA256SUMS"
DEFAULT_ONNX = Path(
    "artifacts/a2/a3_robust_fp32_candidate_v3_11823750/"
    "student_v0_fp32_candidate.onnx"
)
DEFAULT_EXPORT_EVIDENCE = DEFAULT_ONNX.with_name("export_consistency.json")
DEFAULT_HANDOFF = Path(
    "challenge/distillation/releases/"
    "a3_b1_closeout_robust_fp32_candidate_v3/handoff_manifest.json"
)
DEFAULT_TEMPLATE_ATTESTATION = Path(
    "challenge/dataset/attestations/"
    "b1_legacy_template_identity_recovery_v1/recovery_attestation.json"
)
EXPECTED_ONNX_SHA256 = (
    "681a5d4bf16ba61741ef0e559649c43c041de649eef3e8e6f0b6285beaab4286"
)
EXPECTED_WEIGHTS_SHA256 = (
    "7f379c78c170228713e3d91b8e2eabd04172010ae0ed0b8cf71afe291fe6e805"
)
CORE_MAX_DROP = 0.015
SAFETY_MAX_DROP = 0.0


class DiagnosticError(RuntimeError):
    """Raised when diagnostic inputs cannot be verified safely."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_logical_lf(path: Path) -> str:
    """Hash tracked text using repository LF bytes on CRLF Windows checkouts."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(
            dict(value),
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def write_json(path: Path, value: Mapping[str, Any]) -> str:
    payload = canonical_json_bytes(value)
    path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise DiagnosticError(f"{path} must contain a JSON object")
    return value


def load_cases(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise DiagnosticError(f"{path}:{line_number} must be an object")
        rows.append(value)
    if not rows:
        raise DiagnosticError("independent validation case set is empty")
    return rows


def load_sha256_ledger(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, name = line.split(None, 1)
        result[name.strip().replace("\\", "/")] = digest.lower()
    return result


def verify_frozen_inputs(
    repo_root: Path,
    cases_path: Path,
    identity_path: Path,
    case_manifest_path: Path,
    case_set_digest_path: Path,
    ledger_path: Path,
    cases: list[dict[str, Any]],
) -> dict[str, Any]:
    identity = load_json(identity_path)
    manifest = load_json(case_manifest_path)
    digest_manifest = load_json(case_set_digest_path)
    ledger = load_sha256_ledger(ledger_path)
    base = cases_path.parent.relative_to(ledger_path.parent).as_posix()

    verified_files: dict[str, dict[str, Any]] = {}
    for path in (cases_path, identity_path, case_manifest_path, case_set_digest_path):
        key = f"{base}/{path.name}"
        expected = ledger.get(key)
        if expected is None:
            raise DiagnosticError(f"B1 SHA256SUMS has no entry for {key}")
        actual = sha256_logical_lf(path)
        if actual != expected:
            raise DiagnosticError(
                f"B1 logical-LF hash mismatch for {path}: expected {expected}, got {actual}"
            )
        verified_files[key] = {
            "logical_lf_sha256": actual,
            "checkout_bytes_sha256": sha256_file(path),
        }

    if identity.get("status") != "FROZEN":
        raise DiagnosticError("independent validation identity is not FROZEN")
    if identity.get("dataset_version") != "b1_independent_validation_v1":
        raise DiagnosticError("unexpected independent validation dataset_version")
    if identity.get("counts", {}).get("samples") != len(cases):
        raise DiagnosticError("dataset identity sample count does not match cases")
    if manifest.get("case_count") != len(cases):
        raise DiagnosticError("case manifest count does not match cases")
    if digest_manifest.get("case_count") != len(cases):
        raise DiagnosticError("case-set digest count does not match cases")

    case_ids = [str(row.get("sample_id", "")) for row in cases]
    manifest_ids = [str(row.get("sample_id", "")) for row in manifest.get("cases", [])]
    if not all(case_ids) or len(set(case_ids)) != len(case_ids):
        raise DiagnosticError("cases contain blank or duplicate sample_id")
    if case_ids != manifest_ids:
        raise DiagnosticError("case manifest order does not exactly match cases.jsonl")

    image_count = 0
    image_bytes = 0
    for case in cases:
        visual = case.get("visual_input")
        request = case.get("model_request")
        if not isinstance(visual, Mapping) or not isinstance(request, Mapping):
            raise DiagnosticError(f"case {case.get('sample_id')} lacks visual/model request")
        reference = request.get("rgb_ref")
        if not isinstance(reference, str) or not reference.strip():
            raise DiagnosticError(f"case {case.get('sample_id')} lacks rgb_ref")
        image_path = (repo_root / reference).resolve()
        if not image_path.is_relative_to(repo_root) or not image_path.is_file():
            raise DiagnosticError(f"case image is missing or escapes repository: {reference}")
        expected_image_sha = str(visual.get("rgb_sha256", "")).lower()
        if sha256_file(image_path) != expected_image_sha:
            raise DiagnosticError(f"case image SHA256 mismatch: {reference}")
        expected_size = int(visual.get("size_bytes", -1))
        if image_path.stat().st_size != expected_size:
            raise DiagnosticError(f"case image size mismatch: {reference}")
        image_count += 1
        image_bytes += expected_size

    return {
        "dataset_version": identity["dataset_version"],
        "sample_count": len(cases),
        "group_count": identity["counts"]["groups"],
        "case_set_digest_sha256": digest_manifest["sha256"],
        "verified_files": verified_files,
        "verified_rgb": {
            "count": image_count,
            "total_size_bytes": image_bytes,
            "all_sha256_and_size_verified": True,
        },
        "leakage_checks": identity.get("leakage_checks", {}),
    }


def teacher_records(cases: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    registry = InterfaceRegistry()
    registry.warm(("maneuver_plan",))
    records: list[dict[str, Any]] = []
    for case in cases:
        sample_id = str(case["sample_id"])
        plan = case.get("teacher_plan")
        try:
            validated = registry.validate("maneuver_plan", plan)
        except (InterfaceValidationError, TypeError, ValueError) as error:
            records.append(
                {
                    "record_type": "role_exception_stored_teacher_reference",
                    "sample_id": sample_id,
                    "status": "INVALID_OUTPUT",
                    "prediction": plan,
                    "error": {
                        "code": "INVALID_STORED_TEACHER_PLAN",
                        "type": type(error).__name__,
                        "message": str(error),
                    },
                }
            )
            continue
        records.append(
            {
                "record_type": "role_exception_stored_teacher_reference",
                "sample_id": sample_id,
                "request_id": validated["request_id"],
                "command_id": validated["command_id"],
                "status": "SUCCESS",
                "prediction": validated,
                "error": None,
            }
        )
    return records


def student_records(
    repo_root: Path,
    cases: Iterable[Mapping[str, Any]],
    runtime: OnnxModel,
    *,
    model_id: str,
) -> tuple[list[dict[str, Any]], list[float]]:
    preprocessor = StudentPreprocessor()
    adapter = StudentPlanAdapter(model_id=model_id)
    registry = InterfaceRegistry()
    registry.warm(("model_request", "maneuver_plan"))
    output_names = [item.name for item in runtime.outputs]
    records: list[dict[str, Any]] = []
    inference_ms: list[float] = []

    for case in cases:
        sample_id = str(case["sample_id"])
        request = dict(case["model_request"])
        rgb_ref = request.get("rgb_ref")
        if isinstance(rgb_ref, str):
            request["rgb_ref"] = str((repo_root / rgb_ref).resolve())
        request_id = str(request.get("request_id", ""))
        command_id = str(request.get("command_id", ""))
        try:
            validated_request = registry.validate("model_request", request)
            tensors = preprocessor(validated_request)
            inputs = {
                name: tensor.numpy()
                for name, tensor in zip(
                    ("rgb", "text_tokens", "targets", "state"),
                    tensors.as_tuple(),
                    strict=True,
                )
            }
            started = time.perf_counter_ns()
            raw_outputs = runtime.run(inputs)
            elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000.0
            inference_ms.append(elapsed_ms)
            outputs = {
                name: torch.from_numpy(value)
                for name, value in zip(output_names, raw_outputs, strict=True)
            }
            plan = adapter.decode(validated_request, outputs)
            validated_plan = registry.validate("maneuver_plan", plan)
            if validated_plan["request_id"] != request_id:
                raise DiagnosticError("Student request_id mismatch")
            if validated_plan["command_id"] != command_id:
                raise DiagnosticError("Student command_id mismatch")
        except (Exception,) as error:  # Evidence must retain every failed case.
            records.append(
                {
                    "record_type": "role_exception_student_prediction",
                    "sample_id": sample_id,
                    "request_id": request_id,
                    "command_id": command_id,
                    "status": "INFERENCE_ERROR",
                    "prediction": None,
                    "error": {
                        "code": "STUDENT_REPLAY_ERROR",
                        "type": type(error).__name__,
                        "message": str(error),
                    },
                }
            )
            continue
        records.append(
            {
                "record_type": "role_exception_student_prediction",
                "sample_id": sample_id,
                "request_id": request_id,
                "command_id": command_id,
                "status": "SUCCESS",
                "prediction": validated_plan,
                "error": None,
            }
        )
    return records, inference_ms


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * fraction))))
    return ordered[index]


def metric_comparison(
    teacher: Mapping[str, Any],
    student: Mapping[str, Any],
) -> tuple[dict[str, Any], bool]:
    result: dict[str, Any] = {}
    passed = True
    for name in GATE_METRICS:
        teacher_value = teacher["metrics"][name]["value"]
        student_value = student["metrics"][name]["value"]
        maximum_drop = SAFETY_MAX_DROP if name == "safety_critical_behavior_recall" else CORE_MAX_DROP
        drop = None if teacher_value is None or student_value is None else teacher_value - student_value
        metric_pass = drop is not None and drop <= maximum_drop + 1e-12
        passed = passed and metric_pass
        result[name] = {
            "teacher": teacher_value,
            "student": student_value,
            "absolute_drop": drop,
            "maximum_drop": maximum_drop,
            "threshold_projection_pass": metric_pass,
            "numerator": student["metrics"][name]["numerator"],
            "denominator": student["metrics"][name]["denominator"],
        }
    return result, passed


def slices(
    cases: list[dict[str, Any]],
    teacher: list[dict[str, Any]],
    student: list[dict[str, Any]],
) -> dict[str, Any]:
    indexes: dict[str, list[int]] = defaultdict(list)
    for index, case in enumerate(cases):
        sample_class = case.get("sample_class", {})
        primary = str(sample_class.get("primary", "normal")).lower()
        family = str(case.get("metadata", {}).get("scenario_family", "UNKNOWN"))
        indexes[f"sample_class:{primary}"].append(index)
        indexes[f"scenario_family:{family}"].append(index)

    result: dict[str, Any] = {}
    for name, positions in sorted(indexes.items()):
        slice_cases = [cases[index] for index in positions]
        teacher_evidence = aggregate_gate_metric_evidence(
            slice_cases, [teacher[index] for index in positions]
        )
        student_evidence = aggregate_gate_metric_evidence(
            slice_cases, [student[index] for index in positions]
        )
        comparison, _ = metric_comparison(teacher_evidence, student_evidence)
        result[name] = {
            "sample_count": len(positions),
            "comparison": comparison,
        }
    return result


def git_sha(repo_root: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def package_versions() -> dict[str, str]:
    result: dict[str, str] = {}
    for name in ("numpy", "onnxruntime", "Pillow", "torch"):
        try:
            result[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            result[name] = "NOT_INSTALLED"
    return result


def build_readme(report: Mapping[str, Any]) -> str:
    comparison = report["metric_comparison"]
    rows = [
        "| Metric | Teacher | Student | Drop | Limit | Projection |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for name in GATE_METRICS:
        item = comparison[name]
        rows.append(
            f"| `{name}` | {item['teacher']:.6f} | {item['student']:.6f} | "
            f"{item['absolute_drop']:.6f} | {item['maximum_drop']:.6f} | "
            f"{'PASS' if item['threshold_projection_pass'] else 'FAIL'} |"
        )
    return "\n".join(
        [
            "# V3 Independent Validation role-exception diagnostic",
            "",
            "This package is a one-shot A2-executed diagnostic. It is **not** a B2 "
            "Independent Validation signature and cannot promote the candidate to FINAL.",
            "",
            f"- Candidate freeze: `{report['candidate_freeze']['status']}`",
            f"- Formal release status: `{report['formal_release_status']}`",
            f"- Samples: `{report['dataset']['sample_count']}`",
            f"- Student replay coverage: `{report['student_evidence']['coverage']['success_count']}`/"
            f"`{report['student_evidence']['coverage']['sample_count']}`",
            f"- Threshold projection: `{report['threshold_projection']['status']}`",
            "",
            *rows,
            "",
            "The Teacher column is the frozen stored Teacher plan scored against its own "
            "reference label. It is not a fresh Teacher-service replay.",
            "",
            "Formal B2 publication remains fail-closed because authoritative historical "
            "template identities are unrecoverable, the formal policy is not frozen, and "
            "this run was executed under an A2 role exception rather than by B2.",
            "",
        ]
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo_root).resolve()
    destination = Path(args.output).resolve()
    staging = destination.with_name(destination.name + ".tmp")
    if destination.exists() or staging.exists():
        raise DiagnosticError("output or staging directory already exists")

    def resolved(value: str | Path) -> Path:
        path = Path(value)
        return path.resolve() if path.is_absolute() else (repo_root / path).resolve()

    cases_path = resolved(args.cases)
    identity_path = resolved(args.identity)
    case_manifest_path = resolved(args.case_manifest)
    case_set_digest_path = resolved(args.case_set_digest)
    ledger_path = resolved(args.ledger)
    onnx_path = resolved(args.onnx)
    export_evidence_path = resolved(args.export_evidence)
    handoff_path = resolved(args.handoff)
    template_attestation_path = resolved(args.template_attestation)

    cases = load_cases(cases_path)
    dataset = verify_frozen_inputs(
        repo_root,
        cases_path,
        identity_path,
        case_manifest_path,
        case_set_digest_path,
        ledger_path,
        cases,
    )

    actual_onnx_sha256 = sha256_file(onnx_path)
    if actual_onnx_sha256 != args.expected_onnx_sha256:
        raise DiagnosticError("FP32 ONNX SHA256 does not match the frozen candidate")
    export_evidence = load_json(export_evidence_path)
    if export_evidence.get("status") != "PASS":
        raise DiagnosticError("FP32 export consistency evidence is not PASS")
    if export_evidence.get("onnx_sha256") != actual_onnx_sha256:
        raise DiagnosticError("export evidence does not bind the selected ONNX")
    if export_evidence.get("weights_sha256") != args.expected_weights_sha256:
        raise DiagnosticError("export evidence does not bind the selected weights")
    handoff = load_json(handoff_path)
    candidate_identity = handoff.get("candidate_identity", {})
    if candidate_identity.get("weights_sha256") != args.expected_weights_sha256:
        raise DiagnosticError("A3 handoff does not bind the selected weights")

    runtime = OnnxModel(str(onnx_path))
    teacher = teacher_records(cases)
    student, inference_ms = student_records(
        repo_root,
        cases,
        runtime,
        model_id=str(candidate_identity.get("model_id", "student-v0-r3-fp32")),
    )
    teacher_evidence = aggregate_gate_metric_evidence(cases, teacher)
    student_evidence = aggregate_gate_metric_evidence(cases, student)
    comparison, metrics_pass = metric_comparison(teacher_evidence, student_evidence)
    schema_validity = (
        student_evidence["coverage"]["success_count"]
        / student_evidence["coverage"]["sample_count"]
    )
    projected_pass = metrics_pass and schema_validity == 1.0

    template_attestation = load_json(template_attestation_path)
    report: dict[str, Any] = {
        "schema_version": "1.0",
        "evidence_role": "A2_ROLE_EXCEPTION_DIAGNOSTIC",
        "formal_gate_eligible": False,
        "formal_release_status": "BLOCKED_NOT_FINAL",
        "candidate_freeze": {
            "status": "V3_FROZEN_AS_SOLE_RELEASE_CANDIDATE",
            "scope": "candidate selection only; no B2 Gate signature",
            "model_id": candidate_identity.get("model_id"),
            "config_id": candidate_identity.get("config_id"),
            "training_dataset_version": candidate_identity.get("dataset_version"),
            "weights_sha256": args.expected_weights_sha256,
            "fp32_onnx_sha256": actual_onnx_sha256,
        },
        "dataset": dataset,
        "teacher_reference": {
            "kind": "FROZEN_STORED_TEACHER_PLAN",
            "fresh_teacher_service_replay": False,
            "teacher_profile": "b1-pinned-teacher-v4",
            "teacher_git_sha": "95e97b00def8ec36f12937da34ce8bb9082c4a04",
            "teacher_model_id": "Qwen/Qwen3.5-2B",
        },
        "teacher_evidence": teacher_evidence,
        "student_evidence": student_evidence,
        "metric_comparison": comparison,
        "threshold_projection": {
            "status": "PASS" if projected_pass else "FAIL",
            "formal_decision": False,
            "schema_validity": schema_validity,
            "schema_validity_required": 1.0,
            "core_max_drop": CORE_MAX_DROP,
            "safety_max_drop": SAFETY_MAX_DROP,
        },
        "slice_diagnostics": slices(cases, teacher, student),
        "runtime": {
            "platform": platform.platform(),
            "python": sys.version.split()[0],
            "packages": package_versions(),
            "execution_provider": runtime.providers[0],
            "model_only_inference_ms": {
                "count": len(inference_ms),
                "mean": sum(inference_ms) / len(inference_ms) if inference_ms else None,
                "p50": percentile(inference_ms, 0.50),
                "p95": percentile(inference_ms, 0.95),
                "max": max(inference_ms) if inference_ms else None,
                "scope": "diagnostic local CPU timing; not B3 formal latency evidence",
            },
        },
        "source_bindings": {
            "evaluation_git_sha": git_sha(repo_root),
            "diagnostic_runner_path": Path(__file__).resolve().relative_to(repo_root).as_posix(),
            "diagnostic_runner_checkout_sha256": sha256_file(Path(__file__).resolve()),
            "handoff_manifest_path": handoff_path.relative_to(repo_root).as_posix(),
            "handoff_manifest_checkout_sha256": sha256_file(handoff_path),
            "handoff_manifest_logical_lf_sha256": sha256_logical_lf(handoff_path),
            "export_consistency_path": export_evidence_path.relative_to(repo_root).as_posix(),
            "export_consistency_checkout_sha256": sha256_file(export_evidence_path),
            "template_identity_attestation_path": template_attestation_path.relative_to(repo_root).as_posix(),
            "template_identity_attestation_checkout_sha256": sha256_file(
                template_attestation_path
            ),
            "template_identity_attestation_logical_lf_sha256": sha256_logical_lf(
                template_attestation_path
            ),
            "template_identity_status": template_attestation.get("status"),
        },
        "formal_blockers": [
            "RUN_EXECUTED_BY_A2_ROLE_EXCEPTION_NOT_INDEPENDENT_B2",
            "HISTORICAL_TEMPLATE_LINEAGE_UNRECOVERABLE",
            "FORMAL_B2_POLICY_NOT_FROZEN",
            "A3_HANDOFF_REMAINS_PENDING_A3_FP32_GATE",
        ],
        "use_restrictions": [
            "Do not use these 240 labels for training, calibration, threshold selection, or error-driven iteration.",
            "Do not rename this package to A3_FP32_GATE_PASSED or A2_INT8_GATE_PASSED.",
            "A B2 owner must issue any formal Gate decision from independently controlled evidence.",
        ],
    }

    staging.mkdir(parents=True)
    try:
        teacher_sha256 = write_prediction_records(
            staging / "teacher_reference_predictions.jsonl", teacher
        )
        student_sha256 = write_prediction_records(
            staging / "student_fp32_predictions.jsonl", student
        )
        report["prediction_bindings"] = {
            "teacher_reference_predictions_sha256": teacher_sha256,
            "student_fp32_predictions_sha256": student_sha256,
        }
        report_sha256 = write_json(staging / "diagnostic_report.json", report)
        (staging / "README.md").write_text(build_readme(report), encoding="utf-8", newline="\n")
        output_files = [
            "README.md",
            "diagnostic_report.json",
            "student_fp32_predictions.jsonl",
            "teacher_reference_predictions.jsonl",
        ]
        checksum_lines = [
            f"{sha256_file(staging / name)}  {name}" for name in sorted(output_files)
        ]
        (staging / "SHA256SUMS").write_text(
            "\n".join(checksum_lines) + "\n", encoding="ascii", newline="\n"
        )
        staging.replace(destination)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    return {
        "output": str(destination),
        "diagnostic_report_sha256": report_sha256,
        "threshold_projection": report["threshold_projection"],
        "student_coverage": student_evidence["coverage"],
        "candidate_freeze": report["candidate_freeze"],
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--repo-root", default=".")
    result.add_argument("--cases", default=str(DEFAULT_CASES))
    result.add_argument("--identity", default=str(DEFAULT_IDENTITY))
    result.add_argument("--case-manifest", default=str(DEFAULT_CASE_MANIFEST))
    result.add_argument("--case-set-digest", default=str(DEFAULT_CASE_SET_DIGEST))
    result.add_argument("--ledger", default=str(DEFAULT_LEDGER))
    result.add_argument("--onnx", default=str(DEFAULT_ONNX))
    result.add_argument("--export-evidence", default=str(DEFAULT_EXPORT_EVIDENCE))
    result.add_argument("--handoff", default=str(DEFAULT_HANDOFF))
    result.add_argument("--template-attestation", default=str(DEFAULT_TEMPLATE_ATTESTATION))
    result.add_argument("--expected-onnx-sha256", default=EXPECTED_ONNX_SHA256)
    result.add_argument("--expected-weights-sha256", default=EXPECTED_WEIGHTS_SHA256)
    result.add_argument("--output", required=True)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        result = run(args)
    except (DiagnosticError, OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
