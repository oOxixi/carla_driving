#!/usr/bin/env python3
"""Run the pre-frozen 308-case candidate-unexposed Seen stress diagnostic."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from challenge.benchmark.metric_evidence import (  # noqa: E402
    aggregate_gate_metric_evidence,
)
from challenge.benchmark.raw_predictions import (  # noqa: E402
    write_prediction_records,
)
from challenge.runtime.student_x86 import OnnxModel  # noqa: E402
from runtime.interface_registry import (  # noqa: E402
    InterfaceRegistry,
    InterfaceValidationError,
)
from tools.prepare_b2_proxy_unseen_v1 import (  # noqa: E402
    _build_exposure,
    _identity_sets,
    _read_json,
    _set_digest,
    _verify_candidate,
)
from tools.run_v3_independent_diagnostic import (  # noqa: E402
    CORE_MAX_DROP,
    SAFETY_MAX_DROP,
    git_sha,
    git_tracked_worktree_clean,
    load_cases,
    load_json,
    load_sha256_ledger,
    metric_comparison,
    package_versions,
    percentile,
    sha256_file,
    sha256_logical_lf,
    slices,
    student_records,
    teacher_records,
    write_json,
)


DEFAULT_POLICY = Path(
    "challenge/benchmark/b2_proxy_unseen_v1/"
    "candidate_unexposed_seen_stress_policy.json"
)


class StressDiagnosticError(RuntimeError):
    """Raised when the fixed stress diagnostic cannot be executed safely."""


def _resolve(repo: Path, value: str | Path) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (repo / path).resolve()


def _canonical_json(value: Mapping[str, Any]) -> bytes:
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


def load_frozen_policy(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    value = load_json(path)
    if raw != _canonical_json(value):
        raise StressDiagnosticError("stress policy is not canonical JSON")
    if value.get("policy_status") != "FROZEN_PRE_INFERENCE":
        raise StressDiagnosticError("stress policy is not frozen pre-inference")
    if value.get("formal_gate_eligible") is not False:
        raise StressDiagnosticError("stress diagnostic must remain non-formal")
    return value, hashlib.sha256(raw).hexdigest()


def verify_source_release(
    repo: Path,
    policy: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    selection = policy["input_selection"]
    source = _resolve(repo, selection["source_file"])
    manifest_path = _resolve(repo, selection["release_manifest_path"])
    lock_path = _resolve(repo, selection["release_lock_path"])
    signed_path = _resolve(repo, selection["signed_pass_path"])
    manifest = load_json(manifest_path)
    signed = load_json(signed_path)
    ledger = load_sha256_ledger(lock_path)

    source_sha = sha256_logical_lf(source)
    expected_source_sha = selection["source_file_logical_lf_sha256"]
    if source_sha != expected_source_sha:
        raise StressDiagnosticError("locked stress source SHA256 mismatch")
    manifest_source = manifest.get("files", {}).get(source.name, {})
    if manifest_source.get("sha256") != source_sha:
        raise StressDiagnosticError("release manifest does not bind stress source")
    if ledger.get(source.name) != source_sha:
        raise StressDiagnosticError("B1 release lock does not bind stress source")

    manifest_sha = sha256_logical_lf(manifest_path)
    lock_sha = sha256_logical_lf(lock_path)
    if signed.get("status") != "PASS" or signed.get("gate") != "B1_SIGNED_PASS":
        raise StressDiagnosticError("source release lacks B1_SIGNED_PASS")
    if signed.get("release_manifest_sha256") != manifest_sha:
        raise StressDiagnosticError("B1 signed pass does not bind release manifest")
    if signed.get("release_lock_sha256") != lock_sha:
        raise StressDiagnosticError("B1 signed pass does not bind release lock")

    for name, expected in ledger.items():
        member = (source.parent / name).resolve()
        if not member.is_relative_to(source.parent) or not member.is_file():
            raise StressDiagnosticError(f"release-lock member missing or unsafe: {name}")
        if sha256_logical_lf(member) != expected:
            raise StressDiagnosticError(f"release-lock SHA256 mismatch: {name}")

    cases = load_cases(source)
    expected_count = int(selection["expected_sample_count"])
    if len(cases) != expected_count:
        raise StressDiagnosticError("stress source sample count mismatch")
    if manifest.get("counts", {}).get("hard_negative_addition") != expected_count:
        raise StressDiagnosticError("release manifest stress count mismatch")

    registry = InterfaceRegistry()
    registry.warm(("model_request", "maneuver_plan"))
    primary_counts: Counter[str] = Counter()
    sample_ids: set[str] = set()
    group_keys: set[str] = set()
    rgb_hashes: set[str] = set()
    image_bytes = 0
    for case in cases:
        sample_id = str(case.get("sample_id", "")).strip()
        metadata = case.get("metadata")
        visual = case.get("visual_input")
        request = case.get("model_request")
        if not sample_id or not isinstance(metadata, Mapping):
            raise StressDiagnosticError("case lacks sample_id or metadata")
        if not isinstance(visual, Mapping) or not isinstance(request, Mapping):
            raise StressDiagnosticError(f"{sample_id}: missing visual/model_request")
        if metadata.get("teacher_git_sha") != selection["teacher_git_sha"]:
            raise StressDiagnosticError(f"{sample_id}: Teacher Git SHA mismatch")
        if metadata.get("teacher_model_id") != selection["teacher_model_id"]:
            raise StressDiagnosticError(f"{sample_id}: Teacher model mismatch")

        rgb_ref = str(request.get("rgb_ref", ""))
        image = _resolve(repo, rgb_ref)
        if not image.is_relative_to(repo) or not image.is_file():
            raise StressDiagnosticError(f"{sample_id}: RGB path missing or unsafe")
        rgb_sha = sha256_file(image)
        if rgb_sha != visual.get("rgb_sha256"):
            raise StressDiagnosticError(f"{sample_id}: RGB SHA256 mismatch")
        if image.stat().st_size != int(visual.get("size_bytes", -1)):
            raise StressDiagnosticError(f"{sample_id}: RGB size mismatch")

        validated_request = dict(request)
        validated_request["rgb_ref"] = str(image)
        try:
            registry.validate("model_request", validated_request)
            registry.validate("maneuver_plan", case.get("teacher_plan"))
        except (InterfaceValidationError, TypeError, ValueError) as error:
            raise StressDiagnosticError(
                f"{sample_id}: schema validation failed: {error}"
            ) from error

        sample_class = case.get("sample_class")
        if not isinstance(sample_class, Mapping):
            raise StressDiagnosticError(f"{sample_id}: sample_class missing")
        primary_counts[str(sample_class.get("primary", "")).lower()] += 1
        sample_ids.add(sample_id)
        group_keys.add(str(metadata.get("group_key", "")))
        rgb_hashes.add(rgb_sha)
        image_bytes += image.stat().st_size

    if len(sample_ids) != expected_count:
        raise StressDiagnosticError("blank or duplicate sample_id in stress source")
    if len(group_keys) != expected_count or "" in group_keys:
        raise StressDiagnosticError("blank or duplicate group_key in stress source")
    if len(rgb_hashes) != expected_count:
        raise StressDiagnosticError("duplicate RGB content in stress source")
    if dict(sorted(primary_counts.items())) != selection["expected_primary_counts"]:
        raise StressDiagnosticError("stress source class counts mismatch")

    return cases, {
        "dataset_version": manifest.get("dataset_version"),
        "sample_count": len(cases),
        "primary_counts": dict(sorted(primary_counts.items())),
        "source_file": selection["source_file"],
        "source_file_logical_lf_sha256": source_sha,
        "release_manifest_logical_lf_sha256": manifest_sha,
        "release_lock_logical_lf_sha256": lock_sha,
        "b1_signed_pass_checkout_sha256": sha256_file(signed_path),
        "release_lock_entries_verified": len(ledger),
        "rgb": {
            "count": len(rgb_hashes),
            "total_size_bytes": image_bytes,
            "all_sha256_and_size_verified": True,
        },
        "all_model_requests_and_teacher_plans_schema_valid": True,
        "teacher": signed.get("teacher"),
    }


def audit_exposure(
    repo: Path,
    cases: list[dict[str, Any]],
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    boundary = policy["exposure_boundary"]
    design = _read_json(_resolve(repo, boundary["governed_sources_design_path"]))
    inventory, exposed = _build_exposure(repo, design)
    current = _identity_sets(cases)
    overlaps = {
        name: len(values & exposed[name])
        for name, values in current.items()
    }
    for name in boundary["required_zero_overlap_fields"]:
        if overlaps[name] != 0:
            raise StressDiagnosticError(
                f"stress source overlaps governed exposure on {name}"
            )
    return {
        "classification": "CANDIDATE_UNEXPOSED_SEEN_STRESS",
        "governed_row_count": inventory["combined_row_count"],
        "required_zero_overlap_fields": boundary["required_zero_overlap_fields"],
        "allowed_seen_overlap_fields": boundary["allowed_seen_overlap_fields"],
        "stress_unique_counts": {
            name: len(values) for name, values in current.items()
        },
        "stress_set_digests": {
            name: _set_digest(values) for name, values in current.items()
        },
        "overlap_counts": overlaps,
        "required_zero_overlap_pass": True,
        "interpretation": (
            "Samples, groups, RGB content and seeds are candidate-unexposed; "
            "scenario/text/request-template overlap is expected and makes this a Seen test."
        ),
    }


def _verify_policy_candidate(
    actual: Mapping[str, Any],
    policy: Mapping[str, Any],
) -> None:
    expected = policy["candidate"]
    mapping = {
        "model_id": "model_id",
        "config_id": "config_id",
        "training_dataset_version": "training_dataset_version",
        "weights_sha256": "weights_sha256",
        "fp32_onnx_sha256": "onnx_sha256",
        "adapter_contract_id": "adapter_contract_id",
        "adapter_sha256": "adapter_sha256",
    }
    for policy_key, actual_key in mapping.items():
        if expected[policy_key] != actual[actual_key]:
            raise StressDiagnosticError(f"candidate mismatch: {policy_key}")


def build_readme(report: Mapping[str, Any]) -> str:
    rows = [
        "| Metric | Teacher | Student | Drop | Limit | Projection |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for name, item in report["metric_comparison"].items():
        rows.append(
            f"| `{name}` | {item['teacher']:.6f} | {item['student']:.6f} | "
            f"{item['absolute_drop']:.6f} | {item['maximum_drop']:.6f} | "
            f"{'PASS' if item['threshold_projection_pass'] else 'FAIL'} |"
        )
    return "\n".join(
        [
            "# Candidate-unexposed Seen stress diagnostic v1",
            "",
            "This is an A2-executed B2 proxy diagnostic over all 308 locked D3 Wave1 "
            "hard-negative rows. It is not a formal Frozen Benchmark Gate.",
            "",
            f"- Candidate: `{report['candidate']['weights_sha256']}`",
            f"- Samples: `{report['source_audit']['sample_count']}`",
            f"- Student coverage: `{report['student_evidence']['coverage']['success_count']}`/"
            f"`{report['student_evidence']['coverage']['sample_count']}`",
            f"- Threshold projection: `{report['threshold_projection']['status']}`",
            "",
            *rows,
            "",
            "The sample/group/RGB/seed identities do not overlap governed Train, Dev, "
            "Calibration or prior IV, but scenario and text templates do overlap. The "
            "Teacher column uses stored plans, not a fresh service replay.",
            "",
            "Formal promotion remains blocked until the separately frozen 240-slot "
            "Seen/Variant/Unseen acquisition is collected with CARLA and exact Teacher v4.",
            "",
        ]
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    repo = Path(args.repo_root).resolve()
    output = _resolve(repo, args.output)
    staging = output.with_name(output.name + ".tmp")
    if output.exists() or staging.exists():
        raise StressDiagnosticError("output or staging directory already exists")
    if not git_tracked_worktree_clean(repo):
        raise StressDiagnosticError("tracked worktree must be clean before inference")

    policy_path = _resolve(repo, args.policy)
    policy, policy_sha = load_frozen_policy(policy_path)
    if policy["threshold_projection"] != {
        "core_max_drop": CORE_MAX_DROP,
        "safety_max_drop": SAFETY_MAX_DROP,
        "schema_validity_required": 1.0,
    }:
        raise StressDiagnosticError("runner thresholds do not match frozen stress policy")

    design = _read_json(
        _resolve(repo, policy["exposure_boundary"]["governed_sources_design_path"])
    )
    candidate = _verify_candidate(repo, design)
    _verify_policy_candidate(candidate, policy)
    cases, source_audit = verify_source_release(repo, policy)
    exposure_audit = audit_exposure(repo, cases, policy)

    onnx_path = _resolve(repo, design["candidate"]["onnx_path"])
    runtime = OnnxModel(str(onnx_path))
    teacher = teacher_records(cases)
    student, inference_ms = student_records(
        repo,
        cases,
        runtime,
        model_id=candidate["model_id"],
    )
    teacher_evidence = aggregate_gate_metric_evidence(cases, teacher)
    student_evidence = aggregate_gate_metric_evidence(cases, student)
    comparison, metric_pass = metric_comparison(teacher_evidence, student_evidence)
    coverage = student_evidence["coverage"]
    schema_validity = coverage["success_count"] / coverage["sample_count"]
    projected_pass = metric_pass and schema_validity == 1.0

    report: dict[str, Any] = {
        "schema_version": "1.0",
        "diagnostic_id": policy["diagnostic_id"],
        "evidence_role": policy["evidence_role"],
        "formal_gate_eligible": False,
        "formal_gate_decision": False,
        "formal_release_status": "BLOCKED_NOT_FINAL",
        "policy": {
            "path": policy_path.relative_to(repo).as_posix(),
            "sha256": policy_sha,
            "status": policy["policy_status"],
        },
        "candidate": candidate,
        "source_audit": source_audit,
        "exposure_audit": exposure_audit,
        "teacher_reference": {
            "kind": "LOCKED_STORED_TEACHER_PLAN",
            "fresh_teacher_service_replay": False,
            "teacher_profile": policy["input_selection"]["teacher_profile"],
            "teacher_git_sha": policy["input_selection"]["teacher_git_sha"],
            "teacher_model_id": policy["input_selection"]["teacher_model_id"],
        },
        "teacher_evidence": teacher_evidence,
        "student_evidence": student_evidence,
        "metric_comparison": comparison,
        "threshold_projection": {
            "status": "PASS" if projected_pass else "FAIL",
            "formal_decision": False,
            "schema_validity": schema_validity,
            **policy["threshold_projection"],
        },
        "slice_diagnostics": slices(cases, teacher, student),
        "runtime": {
            "packages": package_versions(),
            "execution_provider": runtime.providers[0],
            "model_only_inference_ms": {
                "count": len(inference_ms),
                "mean": sum(inference_ms) / len(inference_ms) if inference_ms else None,
                "p50": percentile(inference_ms, 0.50),
                "p95": percentile(inference_ms, 0.95),
                "max": max(inference_ms) if inference_ms else None,
                "scope": "local CPU diagnostic only; not B3 formal latency evidence",
            },
        },
        "source_bindings": {
            "evaluation_git_sha": git_sha(repo),
            "evaluation_tracked_worktree_clean": True,
            "runner_path": Path(__file__).resolve().relative_to(repo).as_posix(),
            "runner_checkout_sha256": sha256_file(Path(__file__).resolve()),
        },
        "formal_blockers": [
            "SEEN_ONLY_NOT_THREE_COHORT_FROZEN_BENCHMARK",
            "STORED_TEACHER_PLAN_NOT_FRESH_TEACHER_REPLAY",
            "REPOSITORY_VISIBLE_LABELS_NOT_SECRET_B2_HOLDOUT",
            "A2_PROXY_EXECUTION_NOT_INDEPENDENT_B2_SIGNATURE",
            "FRESH_240_CASE_PROSPECTIVE_ACQUISITION_NOT_COLLECTED",
        ],
        "use_restrictions": policy["use_restrictions"],
    }

    staging.mkdir(parents=True)
    try:
        teacher_sha = write_prediction_records(
            staging / "teacher_reference_predictions.jsonl", teacher
        )
        student_sha = write_prediction_records(
            staging / "student_fp32_predictions.jsonl", student
        )
        report["prediction_bindings"] = {
            "teacher_reference_predictions_sha256": teacher_sha,
            "student_fp32_predictions_sha256": student_sha,
        }
        report_sha = write_json(staging / "stress_report.json", report)
        (staging / "README.md").write_text(
            build_readme(report), encoding="utf-8", newline="\n"
        )
        names = [
            "README.md",
            "stress_report.json",
            "student_fp32_predictions.jsonl",
            "teacher_reference_predictions.jsonl",
        ]
        (staging / "SHA256SUMS").write_text(
            "\n".join(
                f"{sha256_file(staging / name)}  {name}" for name in sorted(names)
            )
            + "\n",
            encoding="ascii",
            newline="\n",
        )
        staging.replace(output)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    return {
        "output": str(output),
        "stress_report_sha256": report_sha,
        "sample_count": len(cases),
        "student_coverage": coverage,
        "threshold_projection": report["threshold_projection"],
        "formal_gate_decision": False,
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--repo-root", default=".")
    result.add_argument("--policy", default=str(DEFAULT_POLICY))
    result.add_argument("--output", required=True)
    return result


def main() -> int:
    try:
        result = run(parser().parse_args())
    except (
        StressDiagnosticError,
        InterfaceValidationError,
        OSError,
        ValueError,
        KeyError,
    ) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
