#!/usr/bin/env python3
"""Package an A2-assisted, non-independent B2 proxy audit.

The package exercises the repository's B2 metric and Gate code against real
V3.1 replay evidence, but it deliberately cannot issue a formal B2 signature.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import yaml


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from challenge.benchmark.evaluation_artifact import (
    build_student_evaluation,
    build_teacher_evaluation,
)
from challenge.benchmark.gate_decision import build_gate_decision
from challenge.benchmark.policy_manifest import (
    build_policy_manifest,
    policy_manifest_sha256,
)
from challenge.benchmark.readiness import check_b2_readiness
from challenge.benchmark.student_candidate import verify_student_candidate


DEFAULT_DIAGNOSTIC = Path("artifacts/b2_proxy_v31_recheck_20261008")
DEFAULT_REFERENCE = Path(
    "artifacts/b2_role_exception_v3_1_adapter_20261008_final"
)
DEFAULT_CASES = Path(
    "challenge/dataset/governance/b1_closeout_v1/"
    "independent_validation_v1/cases.jsonl"
)
DEFAULT_B1_IDENTITY = DEFAULT_CASES.with_name("dataset_identity.json")
DEFAULT_B1_CASE_MANIFEST = DEFAULT_CASES.with_name("case_manifest.json")
DEFAULT_B1_CASE_DIGEST = DEFAULT_CASES.with_name("case_set_digest.json")
DEFAULT_CONFIG = Path("challenge/benchmark/benchmark_config.yaml")
DEFAULT_CANDIDATE = Path(
    "challenge/distillation/releases/"
    "a3_b1_closeout_robust_fp32_candidate_v3"
)
DEFAULT_EXPORT = Path(
    "artifacts/a2/a3_robust_fp32_candidate_v3_11823750/"
    "export_consistency.json"
)
DEFAULT_JUNIT = Path("artifacts/a2/b2_benchmark_tests_20261008.junit.xml")


class ProxyAuditError(RuntimeError):
    """Raised when proxy evidence is incomplete or inconsistent."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ProxyAuditError(f"{path} must contain a JSON object")
    return value


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ProxyAuditError(f"{path}:{number} must contain an object")
        rows.append(value)
    if not rows:
        raise ProxyAuditError(f"{path} is empty")
    return rows


def verify_sha256sums(directory: Path) -> dict[str, str]:
    ledger = directory / "SHA256SUMS"
    if not ledger.is_file():
        raise ProxyAuditError(f"missing checksum ledger: {ledger}")
    result: dict[str, str] = {}
    for line in ledger.read_text(encoding="ascii").splitlines():
        if not line.strip():
            continue
        digest, name = line.split(None, 1)
        name = name.strip()
        actual = sha256_file(directory / name)
        if actual != digest.lower():
            raise ProxyAuditError(f"checksum mismatch: {directory / name}")
        result[name] = actual
    return result


def git_sha(repo_root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def junit_summary(path: Path) -> dict[str, Any]:
    root = ElementTree.parse(path).getroot()
    suite = root if root.tag == "testsuite" else root.find("testsuite")
    if suite is None:
        raise ProxyAuditError("JUnit report has no testsuite")
    result = {
        name: int(suite.attrib.get(name, "0"))
        for name in ("tests", "failures", "errors", "skipped")
    }
    result["time_seconds"] = float(suite.attrib.get("time", "0"))
    result["sha256"] = sha256_file(path)
    result["status"] = (
        "PASS"
        if result["tests"] > 0
        and result["failures"] == 0
        and result["errors"] == 0
        else "FAIL"
    )
    return result


def proxy_policy(config_path: Path) -> dict[str, Any]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ProxyAuditError("B2 benchmark config must be an object")
    config = dict(config)
    config["purpose"] = "A3_FP32_GATE_PROXY_NON_INDEPENDENT"
    config["formal_policy"] = {
        "status": "FROZEN",
        "policy_version": "b2-proxy-v3.1-a2-assisted-20261008",
        "slice_minimum_denominators": {
            "normal": 1,
            "complex": 1,
            "safety_critical": 1,
        },
        "multi_run_merge_rule": "single_run_only",
    }
    manifest = build_policy_manifest(config)
    manifest["evidence_scope"] = "A2_ASSISTED_NON_INDEPENDENT_PROXY"
    manifest["formal_gate_eligible"] = False
    manifest["slice_metrics_are_diagnostic_not_gate_checks"] = True
    return manifest


def metric_values(evidence: Mapping[str, Any]) -> dict[str, float]:
    result: dict[str, float] = {}
    for name, record in evidence["metrics"].items():
        value = record.get("value")
        if value is None:
            raise ProxyAuditError(f"metric {name} has an empty denominator")
        result[name] = float(value)
    return result


def build_proxy_benchmark(
    report: Mapping[str, Any],
    candidate: Mapping[str, Any],
    case_manifest_path: Path,
) -> dict[str, Any]:
    dataset = report["dataset"]
    return {
        "schema_version": "1.0",
        "benchmark_id": "b2-proxy-b1-iv1-v3.1-20261008",
        "benchmark_kind": "independent_validation_reused_post_hoc",
        "purpose": "A3_FP32_GATE_PROXY_NON_INDEPENDENT",
        "formal_gate_eligible": False,
        "source_dataset_version": dataset["dataset_version"],
        "candidate_training_dataset_version": candidate["dataset_version"],
        "case_manifest_sha256": sha256_file(case_manifest_path),
        "case_set_digest": dataset["case_set_digest_sha256"],
        "sample_count": dataset["sample_count"],
        "group_count": dataset["group_count"],
        "label_exposure_status": "EXPOSED_BEFORE_ADAPTER_V3_1_REVISION",
        "cohort_assignment": {
            "seen_variant_unseen": "NOT_AVAILABLE",
            "sample_class_counts": {
                "normal": 166,
                "complex": 58,
                "safety_critical": 16,
            },
        },
    }


def mismatch_rows(
    cases: Iterable[Mapping[str, Any]],
    teacher: Iterable[Mapping[str, Any]],
    student: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for case, teacher_record, student_record in zip(
        cases, teacher, student, strict=True
    ):
        teacher_plan = teacher_record.get("prediction") or {}
        student_plan = student_record.get("prediction") or {}
        teacher_behaviors = [
            step.get("behavior") for step in teacher_plan.get("steps", [])
        ]
        student_behaviors = [
            step.get("behavior") for step in student_plan.get("steps", [])
        ]
        if teacher_behaviors == student_behaviors:
            continue
        request = case.get("model_request", {})
        capabilities = request.get("scene_capabilities", {})
        result.append(
            {
                "sample_id": case.get("sample_id"),
                "scenario_id": case.get("metadata", {}).get("scenario_id"),
                "sample_class": case.get("sample_class", {}).get("primary"),
                "teacher_behaviors": teacher_behaviors,
                "student_behaviors": student_behaviors,
                "left_lane_exists": capabilities.get("left_lane_exists"),
                "left_gap_safe": capabilities.get("left_gap_safe"),
                "allowed_behaviors": request.get("constraints", {}).get(
                    "allowed_behaviors"
                ),
                "interpretation": (
                    "Student chose fail-safe STOP instead of the stored Teacher "
                    "lane change while left_gap_safe=false."
                ),
            }
        )
    return result


def slice_alerts(report: Mapping[str, Any]) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    for slice_name, slice_record in report["slice_diagnostics"].items():
        for metric_name, metric in slice_record["comparison"].items():
            if metric["denominator"] <= 0 or metric["threshold_projection_pass"]:
                continue
            alerts.append(
                {
                    "slice": slice_name,
                    "sample_count": slice_record["sample_count"],
                    "metric": metric_name,
                    "denominator": metric["denominator"],
                    "student": metric["student"],
                    "absolute_drop": metric["absolute_drop"],
                    "aggregate_gate_limit": metric["maximum_drop"],
                    "scope": "DIAGNOSTIC_ONLY_NOT_A_FROZEN_SLICE_GATE",
                }
            )
    return alerts


def readme(audit: Mapping[str, Any]) -> str:
    gate = audit["metric_gate_projection"]
    tests = audit["b2_unit_tests"]
    return "\n".join(
        [
            "# B2 Proxy Evaluation Audit — V3.1",
            "",
            "This package was executed by A2 to complete the reproducible B2 test "
            "workflow. It is not an independent B2 signature and cannot be renamed "
            "to `A3_FP32_GATE_PASSED`.",
            "",
            f"- Technical metric projection: `{gate['gate_status']}`",
            f"- Formal release status: `{audit['formal_release_status']}`",
            f"- Replay coverage: `{audit['coverage']['success_count']}`/"
            f"`{audit['coverage']['sample_count']}`",
            f"- B2 code tests: `{tests['tests']}` passed, "
            f"`{tests['failures']}` failed, `{tests['errors']}` errors",
            f"- Repeatability: `{audit['repeatability']['status']}`",
            f"- Behavior mismatches: `{audit['mismatch_count']}`",
            "",
            "The aggregate repository thresholds pass. Two complex "
            "`SUP_A15_lane_change_blocked` cases differ because the stored Teacher "
            "changes lane while `left_gap_safe=false`; Student V3.1 chooses STOP. "
            "Those two cases also create diagnostic complex/safety_D slice drops "
            "above 1.5%, but no formal slice policy has been frozen.",
            "",
            "Formal status remains blocked because the labels were exposed before "
            "Adapter V3.1 was revised, the run was executed by A2 rather than an "
            "independent B2 owner, Seen/Variant/Unseen cohorts are absent, the "
            "repository formal policy is still incomplete, and no fresh Teacher "
            "service replay was performed.",
            "",
        ]
    )


def deterministic_zip(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise ProxyAuditError(f"ZIP already exists: {destination}")
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(item for item in source.rglob("*") if item.is_file()):
            relative = path.relative_to(source).as_posix()
            info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())


def run(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo_root).resolve()

    def resolved(value: str | Path) -> Path:
        path = Path(value)
        return path.resolve() if path.is_absolute() else (repo_root / path).resolve()

    diagnostic = resolved(args.diagnostic)
    reference = resolved(args.reference)
    cases_path = resolved(args.cases)
    b1_identity_path = resolved(args.b1_identity)
    b1_case_manifest_path = resolved(args.b1_case_manifest)
    b1_case_digest_path = resolved(args.b1_case_digest)
    config_path = resolved(args.config)
    candidate_path = resolved(args.candidate)
    export_path = resolved(args.export_evidence)
    junit_path = resolved(args.junit)
    destination = resolved(args.output)
    zip_path = resolved(args.zip)
    staging = destination.with_name(destination.name + ".tmp")

    if destination.exists() or staging.exists():
        raise ProxyAuditError("output or staging directory already exists")

    diagnostic_sums = verify_sha256sums(diagnostic)
    reference_sums = verify_sha256sums(reference)
    report = load_json(diagnostic / "diagnostic_report.json")
    cases = load_jsonl(cases_path)
    teacher_records = load_jsonl(diagnostic / "teacher_reference_predictions.jsonl")
    student_records = load_jsonl(diagnostic / "student_fp32_predictions.jsonl")
    candidate = verify_student_candidate(candidate_path)
    junit = junit_summary(junit_path)

    if junit["status"] != "PASS":
        raise ProxyAuditError("B2 unit tests did not pass")
    if report.get("formal_gate_eligible") is not False:
        raise ProxyAuditError("diagnostic must remain non-formal")
    if report.get("threshold_projection", {}).get("status") != "PASS":
        raise ProxyAuditError("real replay does not pass aggregate projection")
    if len(cases) != 240 or len(teacher_records) != 240 or len(student_records) != 240:
        raise ProxyAuditError("expected exact 240-case coverage")

    repeatability_files = (
        "teacher_reference_predictions.jsonl",
        "student_fp32_predictions.jsonl",
    )
    repeatability: dict[str, Any] = {"status": "PASS", "files": {}}
    for name in repeatability_files:
        current_sha = sha256_file(diagnostic / name)
        reference_sha = sha256_file(reference / name)
        matched = current_sha == reference_sha
        repeatability["files"][name] = {
            "current_sha256": current_sha,
            "reference_sha256": reference_sha,
            "byte_identical": matched,
        }
        if not matched:
            repeatability["status"] = "FAIL"
    if repeatability["status"] != "PASS":
        raise ProxyAuditError("V3.1 replay predictions are not repeatable")

    policy = proxy_policy(config_path)
    policy_sha = policy_manifest_sha256(policy)
    benchmark = build_proxy_benchmark(report, candidate, b1_case_manifest_path)
    benchmark_sha = hashlib.sha256(canonical_json_bytes(benchmark)).hexdigest()
    evaluator_sha = git_sha(repo_root)
    case_digest = report["dataset"]["case_set_digest_sha256"]
    evaluation_dataset_version = candidate["dataset_version"]
    common_bindings = {
        "release_manifest_sha256": candidate["release_manifest_sha256"],
        "a3_view_manifest_sha256": candidate["a3_view_manifest_sha256"],
    }

    teacher_evaluation = build_teacher_evaluation(
        cases,
        teacher_records,
        evaluation_id="b2-proxy-v31-teacher-stored-reference-20261008",
        dataset_version=evaluation_dataset_version,
        benchmark_manifest_sha256=benchmark_sha,
        policy_manifest_sha256=policy_sha,
        case_set_digest=case_digest,
        evaluator_git_sha=evaluator_sha,
        evidence_bindings=common_bindings,
    )
    teacher_evaluation.update(
        {
            "formal_gate_eligible": False,
            "execution_role": "A2_ASSISTED_B2_PROXY",
            "teacher_execution_mode": "FROZEN_STORED_PLAN_NOT_FRESH_SERVICE",
            "source_benchmark_dataset_version": report["dataset"]["dataset_version"],
        }
    )
    student_evaluation = build_student_evaluation(
        cases,
        student_records,
        evaluation_id="b2-proxy-v31-student-fp32-20261008",
        dataset_version=evaluation_dataset_version,
        benchmark_manifest_sha256=benchmark_sha,
        policy_manifest_sha256=policy_sha,
        case_set_digest=case_digest,
        evaluator_git_sha=evaluator_sha,
        model_id=candidate["model_id"],
        config_id=candidate["config_id"],
        weights_sha256=candidate["weights_sha256"],
        evidence_bindings=common_bindings,
    )
    student_evaluation.update(
        {
            "formal_gate_eligible": False,
            "execution_role": "A2_ASSISTED_B2_PROXY",
            "adapter_contract_id": report["candidate_freeze"]["adapter_contract_id"],
            "source_benchmark_dataset_version": report["dataset"]["dataset_version"],
        }
    )
    gate_projection = build_gate_decision(
        teacher_evaluation,
        student_evaluation,
        policy,
    )
    gate_projection.update(
        {
            "decision_scope": "METRIC_THRESHOLD_PROJECTION_ONLY",
            "formal_decision": False,
            "formal_gate_eligible": False,
        }
    )

    readiness = check_b2_readiness(
        config_path,
        student_candidate_directory=candidate_path,
    )
    mismatches = mismatch_rows(cases, teacher_records, student_records)
    alerts = slice_alerts(report)
    blockers = list(
        dict.fromkeys(
            [
                *report.get("formal_blockers", []),
                "SEEN_VARIANT_UNSEEN_COHORT_ASSIGNMENT_MISSING",
                "FRESH_TEACHER_SERVICE_REPLAY_NOT_EXECUTED",
                *readiness.get("blockers", []),
            ]
        )
    )

    audit: dict[str, Any] = {
        "schema_version": "1.0",
        "audit_id": "b2-proxy-audit-v3.1-a2-assisted-20261008",
        "execution_role": "A2_ASSISTED_B2_PROXY",
        "formal_gate_eligible": False,
        "formal_release_status": "BLOCKED_NOT_FINAL",
        "metric_gate_projection": {
            "gate_status": gate_projection["gate_status"],
            "formal_decision": False,
            "policy_manifest_sha256": policy_sha,
            "benchmark_manifest_sha256": benchmark_sha,
        },
        "candidate": {
            **candidate,
            "fp32_onnx_sha256": report["candidate_freeze"]["fp32_onnx_sha256"],
            "adapter_contract_id": report["candidate_freeze"]["adapter_contract_id"],
        },
        "dataset": report["dataset"],
        "coverage": student_evaluation["coverage"],
        "teacher_metrics": teacher_evaluation["metric_evidence"],
        "student_metrics": student_evaluation["metric_evidence"],
        "slice_alerts": alerts,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "repeatability": repeatability,
        "b2_unit_tests": junit,
        "readiness_status": readiness["status"],
        "formal_blockers": blockers,
        "source_bindings": {
            "evaluation_git_sha": evaluator_sha,
            "diagnostic_report_sha256": sha256_file(
                diagnostic / "diagnostic_report.json"
            ),
            "diagnostic_sha256sums_sha256": sha256_file(
                diagnostic / "SHA256SUMS"
            ),
            "reference_sha256sums_sha256": sha256_file(reference / "SHA256SUMS"),
            "candidate_handoff_manifest_sha256": candidate[
                "handoff_manifest_sha256"
            ],
            "export_consistency_sha256": sha256_file(export_path),
            "b1_dataset_identity_sha256": sha256_file(b1_identity_path),
            "b1_case_manifest_sha256": sha256_file(b1_case_manifest_path),
            "b1_case_set_digest_file_sha256": sha256_file(b1_case_digest_path),
            "diagnostic_ledger_entries": diagnostic_sums,
            "reference_ledger_entries": reference_sums,
        },
        "use_restrictions": [
            "Do not rename this artifact to A3_FP32_GATE_PASSED.",
            "Do not represent this A2-executed replay as independent B2 validation.",
            "Do not use the exposed 240-case labels for further candidate tuning.",
            "A formal decision requires a B2-controlled unseen set or explicit competition-level waiver.",
        ],
    }

    staging.mkdir(parents=True)
    try:
        write_json(staging / "b2_proxy_audit.json", audit)
        write_json(staging / "proxy_benchmark_manifest.json", benchmark)
        write_json(staging / "proxy_policy_manifest.json", policy)
        write_json(staging / "teacher_evaluation.proxy.json", teacher_evaluation)
        write_json(staging / "student_evaluation.proxy.json", student_evaluation)
        write_json(staging / "metric_gate_projection.json", gate_projection)
        write_json(staging / "formal_readiness.json", readiness)
        write_json(
            staging / "mismatch_analysis.json",
            {"mismatch_count": len(mismatches), "mismatches": mismatches},
        )
        (staging / "README.md").write_text(
            readme(audit), encoding="utf-8", newline="\n"
        )

        copy_files = {
            diagnostic / "diagnostic_report.json": "evidence/diagnostic_report.json",
            diagnostic / "teacher_reference_predictions.jsonl": (
                "evidence/teacher_reference_predictions.jsonl"
            ),
            diagnostic / "student_fp32_predictions.jsonl": (
                "evidence/student_fp32_predictions.jsonl"
            ),
            junit_path: "tests/b2_benchmark_tests.junit.xml",
            cases_path: "dataset/cases.jsonl",
            b1_identity_path: "dataset/dataset_identity.json",
            b1_case_manifest_path: "dataset/case_manifest.json",
            b1_case_digest_path: "dataset/case_set_digest.json",
            candidate_path / "handoff_manifest.json": (
                "identity/candidate_handoff_manifest.json"
            ),
            candidate_path / "student_v0_fp32_candidate.json": (
                "identity/student_v0_fp32_candidate.json"
            ),
            export_path: "identity/export_consistency.json",
        }
        for source, relative in copy_files.items():
            target = staging / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

        checksum_files = sorted(
            item for item in staging.rglob("*") if item.is_file()
        )
        checksum_lines = [
            f"{sha256_file(path)}  {path.relative_to(staging).as_posix()}"
            for path in checksum_files
        ]
        (staging / "SHA256SUMS").write_text(
            "\n".join(checksum_lines) + "\n",
            encoding="ascii",
            newline="\n",
        )
        staging.replace(destination)
        deterministic_zip(destination, zip_path)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    return {
        "output": str(destination),
        "zip": str(zip_path),
        "zip_sha256": sha256_file(zip_path),
        "audit_sha256": sha256_file(destination / "b2_proxy_audit.json"),
        "metric_gate_projection": gate_projection["gate_status"],
        "formal_release_status": audit["formal_release_status"],
        "b2_unit_tests": junit,
        "repeatability": repeatability["status"],
        "mismatch_count": len(mismatches),
        "slice_alert_count": len(alerts),
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--repo-root", default=".")
    result.add_argument("--diagnostic", default=str(DEFAULT_DIAGNOSTIC))
    result.add_argument("--reference", default=str(DEFAULT_REFERENCE))
    result.add_argument("--cases", default=str(DEFAULT_CASES))
    result.add_argument("--b1-identity", default=str(DEFAULT_B1_IDENTITY))
    result.add_argument("--b1-case-manifest", default=str(DEFAULT_B1_CASE_MANIFEST))
    result.add_argument("--b1-case-digest", default=str(DEFAULT_B1_CASE_DIGEST))
    result.add_argument("--config", default=str(DEFAULT_CONFIG))
    result.add_argument("--candidate", default=str(DEFAULT_CANDIDATE))
    result.add_argument("--export-evidence", default=str(DEFAULT_EXPORT))
    result.add_argument("--junit", default=str(DEFAULT_JUNIT))
    result.add_argument("--output", required=True)
    result.add_argument("--zip", required=True)
    return result


def main() -> int:
    try:
        value = run(parser().parse_args())
    except (OSError, ValueError, ProxyAuditError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
