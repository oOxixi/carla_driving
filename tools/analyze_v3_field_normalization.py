#!/usr/bin/env python3
"""Measure V3 after a transparent target-lane representation normalization.

This is a post-hoc diagnostic, not a B2 Gate decision.  It preserves the raw
predictions and frozen labels, then scores a copy in which an omitted
``target_lane`` is materialized as ``CURRENT`` only for behaviours whose
semantics do not select or change a lane.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import subprocess
import sys
from collections import Counter
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


DEFAULT_CASES = Path(
    "challenge/dataset/governance/b1_closeout_v1/"
    "independent_validation_v1/cases.jsonl"
)
DEFAULT_INPUT = Path("artifacts/b2_role_exception_v3_20261008_final")
DEFAULT_OUTPUT = Path(
    "artifacts/b2_role_exception_v3_20261008_semantic_normalized"
)
CORE_MAX_DROP = 0.015
SAFETY_MAX_DROP = 0.0

# These behaviours keep the current lane by definition or do not issue a lane
# selection.  Lane-changing, route-branch, avoidance, return, and pull-over
# behaviours are deliberately excluded.
IMPLICIT_CURRENT_BEHAVIORS = (
    "FOLLOW",
    "HOLD",
    "KEEP_LANE",
    "SET_SPEED",
    "SLOW_DOWN",
    "STOP",
    "YIELD",
)


class NormalizationDiagnosticError(RuntimeError):
    """Raised when an input binding or normalization invariant fails."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_logical_lf(path: Path) -> str:
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


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise NormalizationDiagnosticError(f"{path} must contain a JSON object")
    return value


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise NormalizationDiagnosticError(
                f"{path}:{line_number} must contain a JSON object"
            )
        rows.append(value)
    if not rows:
        raise NormalizationDiagnosticError(f"{path} is empty")
    return rows


def metric_values(evidence: Mapping[str, Any]) -> dict[str, Any]:
    return {
        name: evidence["metrics"][name]
        for name in GATE_METRICS
    }


def assert_metric_binding(
    name: str,
    actual: Mapping[str, Any],
    expected: Mapping[str, Any],
) -> None:
    for metric in GATE_METRICS:
        if actual["metrics"][metric] != expected[metric]:
            raise NormalizationDiagnosticError(
                f"{name} metric binding mismatch for {metric}"
            )


def normalize_student_records(
    records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    normalized = copy.deepcopy(records)
    counts: Counter[str] = Counter()
    adjusted_samples: set[str] = set()

    for record in normalized:
        if record.get("status") != "SUCCESS":
            continue
        prediction = record.get("prediction")
        if not isinstance(prediction, dict):
            raise NormalizationDiagnosticError("SUCCESS record lacks a prediction object")
        steps = prediction.get("steps")
        if not isinstance(steps, list):
            raise NormalizationDiagnosticError("prediction.steps must be a list")
        for step in steps:
            if not isinstance(step, dict):
                raise NormalizationDiagnosticError("prediction step must be an object")
            behavior = str(step.get("behavior", ""))
            target = step.get("target")
            if not isinstance(target, dict):
                raise NormalizationDiagnosticError("prediction step.target must be an object")
            if (
                behavior in IMPLICIT_CURRENT_BEHAVIORS
                and target.get("target_lane") is None
            ):
                target["target_lane"] = "CURRENT"
                counts[behavior] += 1
                adjusted_samples.add(str(record.get("sample_id", "")))

    return normalized, {
        "adjusted_step_count": sum(counts.values()),
        "adjusted_sample_count": len(adjusted_samples),
        "adjustments_by_behavior": dict(sorted(counts.items())),
    }


def threshold_projection(
    teacher: Mapping[str, Any],
    student: Mapping[str, Any],
) -> tuple[dict[str, Any], bool]:
    result: dict[str, Any] = {}
    passed = True
    for name in GATE_METRICS:
        teacher_value = teacher["metrics"][name]["value"]
        student_value = student["metrics"][name]["value"]
        limit = (
            SAFETY_MAX_DROP
            if name == "safety_critical_behavior_recall"
            else CORE_MAX_DROP
        )
        drop = (
            None
            if teacher_value is None or student_value is None
            else teacher_value - student_value
        )
        metric_pass = drop is not None and drop <= limit + 1e-12
        passed = passed and metric_pass
        result[name] = {
            "teacher": teacher_value,
            "student": student_value,
            "absolute_drop": drop,
            "maximum_drop": limit,
            "threshold_projection_pass": metric_pass,
            "numerator": student["metrics"][name]["numerator"],
            "denominator": student["metrics"][name]["denominator"],
        }
    return result, passed


def git_sha(repo: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        text=True,
        encoding="utf-8",
    ).strip()


def build_report(
    repo: Path,
    cases_path: Path,
    input_directory: Path,
) -> dict[str, Any]:
    report_path = input_directory / "diagnostic_report.json"
    student_path = input_directory / "student_fp32_predictions.jsonl"
    teacher_path = input_directory / "teacher_reference_predictions.jsonl"
    diagnostic = load_json(report_path)
    cases = load_jsonl(cases_path)
    student = load_jsonl(student_path)
    teacher = load_jsonl(teacher_path)

    expected_student_sha = diagnostic["prediction_bindings"][
        "student_fp32_predictions_sha256"
    ]
    expected_teacher_sha = diagnostic["prediction_bindings"][
        "teacher_reference_predictions_sha256"
    ]
    if sha256_file(student_path) != expected_student_sha:
        raise NormalizationDiagnosticError("Student prediction SHA256 mismatch")
    if sha256_file(teacher_path) != expected_teacher_sha:
        raise NormalizationDiagnosticError("Teacher prediction SHA256 mismatch")

    cases_binding = diagnostic["dataset"]["verified_files"][
        "independent_validation_v1/cases.jsonl"
    ]["logical_lf_sha256"]
    if sha256_logical_lf(cases_path) != cases_binding:
        raise NormalizationDiagnosticError("frozen cases logical-LF SHA256 mismatch")

    case_ids = [str(row.get("sample_id", "")) for row in cases]
    student_ids = [str(row.get("sample_id", "")) for row in student]
    teacher_ids = [str(row.get("sample_id", "")) for row in teacher]
    if not case_ids or case_ids != student_ids or case_ids != teacher_ids:
        raise NormalizationDiagnosticError(
            "case, Student, and Teacher sample identities/order do not match"
        )

    teacher_evidence = aggregate_gate_metric_evidence(cases, teacher)
    strict_student_evidence = aggregate_gate_metric_evidence(cases, student)
    assert_metric_binding(
        "Teacher",
        teacher_evidence,
        diagnostic["teacher_evidence"]["metrics"],
    )
    assert_metric_binding(
        "strict Student",
        strict_student_evidence,
        diagnostic["student_evidence"]["metrics"],
    )

    normalized_student, adjustment = normalize_student_records(student)
    normalized_student_evidence = aggregate_gate_metric_evidence(
        cases,
        normalized_student,
    )
    if adjustment["adjusted_step_count"] <= 0:
        raise NormalizationDiagnosticError("normalization adjusted no prediction steps")
    unchanged_metrics = set(GATE_METRICS) - {
        "target_lane_accuracy",
        "plan_sequence_accuracy",
    }
    for name in unchanged_metrics:
        if (
            strict_student_evidence["metrics"][name]
            != normalized_student_evidence["metrics"][name]
        ):
            raise NormalizationDiagnosticError(
                f"normalization unexpectedly changed {name}"
            )
    for name in ("target_lane_accuracy", "plan_sequence_accuracy"):
        if (
            normalized_student_evidence["metrics"][name]["numerator"]
            < strict_student_evidence["metrics"][name]["numerator"]
        ):
            raise NormalizationDiagnosticError(
                f"normalization unexpectedly reduced {name}"
            )
    normalized_projection, normalized_pass = threshold_projection(
        teacher_evidence,
        normalized_student_evidence,
    )

    metric_delta: dict[str, Any] = {}
    for name in GATE_METRICS:
        before = strict_student_evidence["metrics"][name]
        after = normalized_student_evidence["metrics"][name]
        metric_delta[name] = {
            "strict": before["value"],
            "semantic_normalized": after["value"],
            "absolute_gain": (
                None
                if before["value"] is None or after["value"] is None
                else after["value"] - before["value"]
            ),
            "strict_numerator": before["numerator"],
            "semantic_normalized_numerator": after["numerator"],
            "denominator": after["denominator"],
        }

    return {
        "schema_version": "1.0",
        "status": "POST_HOC_DIAGNOSTIC_ONLY",
        "formal_gate_eligible": False,
        "source_git_sha": git_sha(repo),
        "dataset": {
            "dataset_version": diagnostic["dataset"]["dataset_version"],
            "sample_count": len(cases),
            "case_set_digest_sha256": diagnostic["dataset"][
                "case_set_digest_sha256"
            ],
            "cases_logical_lf_sha256": cases_binding,
        },
        "candidate": diagnostic["candidate_freeze"],
        "input_bindings": {
            "normalization_runner_path": "tools/analyze_v3_field_normalization.py",
            "normalization_runner_sha256": sha256_file(Path(__file__)),
            "strict_diagnostic_report_path": report_path.relative_to(repo).as_posix(),
            "strict_diagnostic_report_sha256": sha256_file(report_path),
            "student_predictions_path": student_path.relative_to(repo).as_posix(),
            "student_predictions_sha256": expected_student_sha,
            "teacher_predictions_path": teacher_path.relative_to(repo).as_posix(),
            "teacher_predictions_sha256": expected_teacher_sha,
        },
        "normalization": {
            "name": "IMPLICIT_CURRENT_LANE_V1",
            "rule": (
                "For scoring only, materialize target.target_lane='CURRENT' when "
                "the Student emitted null and its predicted behavior is in the "
                "fixed non-lane-selecting behavior allowlist."
            ),
            "implicit_current_behaviors": list(IMPLICIT_CURRENT_BEHAVIORS),
            "lane_critical_behaviors_unchanged": [
                "AVOID_OBSTACLE",
                "CHANGE_LANE_LEFT",
                "CHANGE_LANE_RIGHT",
                "PULL_OVER",
                "RETURN_TO_LANE",
                "TURN_LEFT",
                "TURN_RIGHT",
            ],
            "other_fields_changed": False,
            **adjustment,
        },
        "strict_student_evidence": strict_student_evidence,
        "semantic_normalized_student_evidence": normalized_student_evidence,
        "metric_delta": metric_delta,
        "recovered_correct_predictions": {
            "target_lane_steps": (
                normalized_student_evidence["metrics"]["target_lane_accuracy"]["numerator"]
                - strict_student_evidence["metrics"]["target_lane_accuracy"]["numerator"]
            ),
            "complete_plans": (
                normalized_student_evidence["metrics"]["plan_sequence_accuracy"]["numerator"]
                - strict_student_evidence["metrics"]["plan_sequence_accuracy"]["numerator"]
            ),
        },
        "semantic_normalized_threshold_projection": {
            "result": "PASS" if normalized_pass else "FAIL",
            "comparison": normalized_projection,
        },
        "interpretation_limits": [
            "The raw model output and the original strict diagnostic remain unchanged.",
            "The rule is post-hoc and was evaluated after the independent labels were exposed, so it cannot issue a formal Gate decision.",
            "Only a representation-level null-versus-CURRENT convention is normalized; no lane-critical maneuver is corrected.",
            "A future formal policy must freeze this equivalence before evaluating a new unseen benchmark.",
        ],
    }


def write_output(output: Path, report: Mapping[str, Any]) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError(output)
    staging = output.with_name(output.name + ".tmp")
    if staging.exists():
        raise FileExistsError(staging)
    staging.mkdir(parents=True)
    try:
        report_path = staging / "semantic_normalization_report.json"
        report_path.write_bytes(canonical_json_bytes(report))
        comparison = report["semantic_normalized_threshold_projection"]["comparison"]
        lines = [
            "# V3 field-semantic normalization diagnostic",
            "",
            "Status: `POST_HOC_DIAGNOSTIC_ONLY`; this does not replace the strict B2 Gate.",
            "",
            "| Metric | Strict | Normalized | Gain | Normalized projection |",
            "|---|---:|---:|---:|---|",
        ]
        for name in GATE_METRICS:
            delta = report["metric_delta"][name]
            lines.append(
                f"| `{name}` | {delta['strict']:.6f} | "
                f"{delta['semantic_normalized']:.6f} | "
                f"{delta['absolute_gain']:.6f} | "
                f"{'PASS' if comparison[name]['threshold_projection_pass'] else 'FAIL'} |"
            )
        lines.extend(
            [
                "",
                f"Adjusted steps: {report['normalization']['adjusted_step_count']} across "
                f"{report['normalization']['adjusted_sample_count']} samples.",
                "",
                "Only null `target_lane` values on the fixed implicit-current behavior allowlist "
                "were materialized as `CURRENT`. Raw predictions, lane-critical maneuvers, and "
                "all other fields were unchanged.",
            ]
        )
        readme_path = staging / "README.md"
        readme_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        checksums = [
            f"{sha256_file(path)}  {path.name}"
            for path in sorted((report_path, readme_path))
        ]
        (staging / "SHA256SUMS").write_text(
            "\n".join(checksums) + "\n",
            encoding="ascii",
            newline="\n",
        )
        staging.replace(output)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return {
        "output": str(output),
        "report_sha256": sha256_file(
            output / "semantic_normalization_report.json"
        ),
        "readme_sha256": sha256_file(output / "README.md"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=str(REPOSITORY_ROOT))
    parser.add_argument("--cases", default=str(DEFAULT_CASES))
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    repo = Path(args.repo).resolve()

    def resolve(value: str) -> Path:
        path = Path(value)
        return path.resolve() if path.is_absolute() else (repo / path).resolve()

    try:
        report = build_report(
            repo,
            resolve(args.cases),
            resolve(args.input),
        )
        result = write_output(resolve(args.output), report)
    except (
        FileExistsError,
        KeyError,
        OSError,
        TypeError,
        ValueError,
        NormalizationDiagnosticError,
    ) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(json.dumps({**result, "metric_delta": report["metric_delta"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
