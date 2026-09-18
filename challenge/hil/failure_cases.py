"""Deterministic abnormal-input suite.

The harness records what the runtime does; it does not decide whether the
behaviour is acceptable.  Pass/fail policy belongs to B2's gate.
"""

from __future__ import annotations

from dataclasses import dataclass
import copy
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from .run_io import write_json
from .runtime_adapter import PlannerRuntime
from .replay import structural_checks


@dataclass(frozen=True, slots=True)
class FailureCase:
    case_id: str
    description: str
    expectation: str
    expectation_code: str
    request: dict[str, Any]


def _jsonable(value: Any) -> Any:
    if isinstance(value, float):
        if math.isnan(value):
            return "NaN"
        if math.isinf(value):
            return "Infinity" if value > 0 else "-Infinity"
        return value
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def build_failure_cases(base_request: Mapping[str, Any]) -> list[FailureCase]:
    base = copy.deepcopy(dict(base_request))
    cases: list[FailureCase] = []

    request = copy.deepcopy(base)
    request["rgb_ref"] = None
    cases.append(
        FailureCase(
            "missing_rgb_ref",
            "ModelRequest carries no rgb_ref",
            "contract says a missing image becomes an all-zero tensor; a plan may still be produced",
            "MAY_PLAN",
            request,
        )
    )

    request = copy.deepcopy(base)
    request["rgb_ref"] = "definitely/not/a/real/frame.jpg"
    cases.append(
        FailureCase(
            "missing_rgb_file",
            "rgb_ref points at a file that does not exist",
            "deterministic all-zero image; no exception should escape",
            "MAY_PLAN",
            request,
        )
    )

    request = copy.deepcopy(base)
    request["source_text"] = "前方车辆减速，请保持安全距离并准备向左变道避让" * 4
    cases.append(
        FailureCase(
            "source_text_over_32_chars",
            "source_text far beyond the 32-character fixed encoding",
            "deterministic truncation at the preprocessing boundary",
            "MAY_PLAN",
            request,
        )
    )

    request = copy.deepcopy(base)
    template = dict(base.get("targets", [{}])[0]) if base.get("targets") else {}
    request["targets"] = [
        {**template, "target_id": f"X-{index:03d}"} for index in range(12)
    ]
    cases.append(
        FailureCase(
            "targets_over_8",
            "12 targets supplied, contract allows 8",
            "deterministic truncation to the first 8 in original order",
            "MAY_PLAN",
            request,
        )
    )

    request = copy.deepcopy(base)
    if request.get("targets"):
        request["targets"][0]["distance_m"] = float("nan")
    cases.append(
        FailureCase(
            "nan_target_distance",
            "target distance is NaN",
            "must not crash the process; either reject or produce a bounded plan",
            "MUST_NOT_CRASH",
            request,
        )
    )

    request = copy.deepcopy(base)
    if request.get("targets"):
        request["targets"][0]["relative_speed_mps"] = float("inf")
    cases.append(
        FailureCase(
            "infinite_relative_speed",
            "target relative speed is infinite",
            "must not crash the process; either reject or produce a bounded plan",
            "MUST_NOT_CRASH",
            request,
        )
    )

    request = copy.deepcopy(base)
    request.pop("targets", None)
    cases.append(
        FailureCase(
            "missing_targets_key",
            "targets list is absent, violating ModelRequest V1",
            "must fail closed rather than plan on an unknown scene",
            "MUST_FAIL_CLOSED",
            request,
        )
    )

    request = copy.deepcopy(base)
    request["source_text"] = ""
    cases.append(
        FailureCase(
            "empty_source_text",
            "empty instruction text",
            "must not crash; an empty command should not authorise propulsion",
            "MUST_FAIL_CLOSED",
            request,
        )
    )

    request = copy.deepcopy(base)
    request["deadline_ns"] = request.get("created_at_ns", 0)
    cases.append(
        FailureCase(
            "degenerate_deadline",
            "deadline equals the creation timestamp",
            "deadline enforcement belongs to the orchestrator; the planner itself must stay bounded",
            "MUST_NOT_CRASH",
            request,
        )
    )

    request = copy.deepcopy(base)
    request.setdefault("constraints", {})
    request["constraints"] = dict(request["constraints"])
    request["constraints"]["must_stop"] = True
    request["constraints"]["allowed_behaviors"] = ["STOP"]
    cases.append(
        FailureCase(
            "must_stop_with_narrow_allowlist",
            "hard stop constraint with a single allowed behaviour",
            "plan must begin with STOP or HOLD",
            "MUST_FAIL_CLOSED",
            request,
        )
    )

    return cases


def run_failure_cases(
    runtime: PlannerRuntime,
    cases: Sequence[FailureCase],
    *,
    run_id: str,
    output_dir: str | Path,
    latency_budget_ms: float = 1000.0,
) -> dict[str, Any]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    verdicts: dict[str, int] = {}
    for case in cases:
        request = _jsonable(case.request)
        crashed = False
        plan: Mapping[str, Any] | None = None
        trace = None
        try:
            plan, trace = runtime.infer(
                case.request, case_id=case.case_id, round_index=0, phase="measured"
            )
        except Exception as error:
            crashed = True
            detail = f"{type(error).__name__}: {error}"
        else:
            detail = trace.outcome_detail
        durations = trace.durations_ms() if trace is not None else {}
        e2e = durations.get("planner_e2e_ms")
        failures = list(structural_checks(case.request, plan)) if plan is not None else []
        behaviors = []
        if isinstance(plan, Mapping):
            steps = plan.get("steps")
            if isinstance(steps, Sequence):
                behaviors = [
                    str(step.get("behavior", ""))
                    for step in steps
                    if isinstance(step, Mapping)
                ]
        fail_closed = (
            crashed
            or trace is None
            or trace.outcome != "READY"
            or (behaviors and behaviors[0] in {"STOP", "HOLD"})
        )
        latency_bounded = e2e is None or e2e <= latency_budget_ms
        if crashed:
            verdict = "OBSERVED_PROCESS_ERROR"
        elif trace is not None and trace.outcome == "READY" and not behaviors:
            verdict = "OBSERVED_EMPTY_PLAN"
        elif fail_closed:
            verdict = "OBSERVED_FAIL_CLOSED"
        elif not latency_bounded:
            verdict = "OBSERVED_UNBOUNDED_LATENCY"
        else:
            verdict = "OBSERVED_PLAN_PRODUCED"
        if case.expectation_code == "MUST_NOT_CRASH":
            matches: bool | None = not crashed and bool(latency_bounded)
        elif case.expectation_code == "MUST_FAIL_CLOSED":
            matches = bool(fail_closed)
        else:  # MAY_PLAN
            matches = plan is not None
        verdicts[verdict] = verdicts.get(verdict, 0) + 1
        record = {
            "case_id": case.case_id,
            "description": case.description,
            "harness_expectation": case.expectation,
            "expectation_code": case.expectation_code,
            "expectation_owner": "B3 harness (provisional; B2 owns the final gate policy)",
            "matches_expectation": matches,
            "outcome": None if trace is None else trace.outcome,
            "reason_code": None if trace is None else trace.reason_code,
            "detail": detail,
            "missing_stages": [] if trace is None else list(trace.missing_stages()),
            "plan_produced": plan is not None,
            "first_behavior": behaviors[0] if behaviors else None,
            "structural_failures": failures,
            "fail_closed_observed": bool(fail_closed),
            "latency_bounded": bool(latency_bounded),
            "planner_e2e_ms": e2e,
            "model_only_ms": durations.get("model_only_ms"),
            "verdict": verdict,
            "policy_owner": "B2",
            "request": request,
        }
        records.append(record)
        write_json(output / f"{case.case_id}.json", record)
    summary = {
        "case_count": len(records),
        "verdicts": verdicts,
        "expectation_match": sum(1 for item in records if item["matches_expectation"]),
        "expectation_mismatch": [
            {
                "case_id": item["case_id"],
                "expectation_code": item["expectation_code"],
                "verdict": item["verdict"],
            }
            for item in records
            if not item["matches_expectation"]
        ],
        "policy_note": (
            "The harness records runtime behaviour on abnormal input; whether each "
            "verdict passes the gate is B2's decision."
        ),
        "cases": [
            {"case_id": item["case_id"], "verdict": item["verdict"], "outcome": item["outcome"]}
            for item in records
        ],
    }
    write_json(output / "failure_summary.json", summary)
    return summary


__all__ = ["FailureCase", "build_failure_cases", "run_failure_cases"]
