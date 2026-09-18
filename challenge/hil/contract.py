"""Executable form of the A4 runtime contract.

A prose contract gets ignored; this one fails loudly.  Run it against the
board command before handing the Runtime over, and again after any change.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from .replay import FORBIDDEN_PLAN_KEYS, REQUIRED_PLAN_KEYS, structural_checks
from .runtime_adapter import PlannerRuntime
from .stages import STAGES


PASS = "PASS"
FAIL = "FAIL"
WARN = "WARN"


def _check(name: str, status: str, detail: str) -> dict[str, str]:
    return {"check": name, "status": status, "detail": detail}


def check_runtime_contract(
    runtime: PlannerRuntime,
    requests: Sequence[Mapping[str, Any]],
    *,
    latency_budget_ms: float = 1000.0,
) -> dict[str, Any]:
    checks: list[dict[str, str]] = []
    if not requests:
        raise ValueError("contract check needs at least one request")

    checks.append(
        _check(
            "identity_declared",
            PASS if runtime.identity.complete else WARN,
            f"complete={runtime.identity.complete} missing={list(runtime.identity.missing())}",
        )
    )

    plans: list[Mapping[str, Any] | None] = []
    traces = []
    errors: list[str] = []
    for index, request in enumerate(requests):
        try:
            plan, trace = runtime.infer(
                request, case_id=f"contract-{index:02d}", round_index=0, phase="measured"
            )
        except Exception as error:
            errors.append(f"request {index}: {type(error).__name__}: {error}")
            plans.append(None)
            traces.append(None)
            continue
        plans.append(plan)
        traces.append(trace)

    checks.append(
        _check(
            "no_exception_escaped",
            PASS if not errors else FAIL,
            "; ".join(errors[:3]) if errors else f"{len(requests)} requests executed",
        )
    )

    produced = [plan for plan in plans if isinstance(plan, Mapping)]
    checks.append(
        _check(
            "plan_is_json_object",
            PASS if len(produced) == len(requests) else FAIL,
            f"{len(produced)}/{len(requests)} returned an object",
        )
    )

    missing_keys: list[str] = []
    for plan in produced:
        missing_keys.extend(key for key in REQUIRED_PLAN_KEYS if key not in plan)
    checks.append(
        _check(
            "plan_has_required_keys",
            PASS if not missing_keys else FAIL,
            f"missing={sorted(set(missing_keys))}" if missing_keys else "all required keys present",
        )
    )

    forbidden: list[str] = []
    structural: list[str] = []
    for plan, request in zip(plans, requests):
        if not isinstance(plan, Mapping):
            continue
        forbidden.extend(key for key in FORBIDDEN_PLAN_KEYS if key in plan)
        structural.extend(structural_checks(request, plan))
    checks.append(
        _check(
            "no_forbidden_outputs",
            PASS if not forbidden else FAIL,
            f"forbidden={sorted(set(forbidden))}" if forbidden else "no steer/throttle/brake/waypoints",
        )
    )
    checks.append(
        _check(
            "plan_passes_structural_checks",
            PASS if not structural else FAIL,
            f"failures={sorted(set(structural))[:5]}" if structural else "ids echoed, 1..4 steps",
        )
    )

    instrumented = [trace for trace in traces if trace is not None and trace.stage_source == "INSTRUMENTED"]
    checks.append(
        _check(
            "trace_marks_emitted",
            PASS if len(instrumented) == len(requests) else (
                WARN if instrumented else FAIL
            ),
            (
                f"{len(instrumented)}/{len(requests)} requests carried stage marks"
                if instrumented
                else "runtime does not emit trace marks: per-stage latency is NOT_AVAILABLE"
            ),
        )
    )

    model_only = [
        trace.durations_ms().get("model_only_ms")
        for trace in traces
        if trace is not None and trace.durations_ms().get("model_only_ms") is not None
    ]
    e2e = [
        trace.durations_ms().get("planner_e2e_ms")
        for trace in traces
        if trace is not None and trace.durations_ms().get("planner_e2e_ms") is not None
    ]
    checks.append(
        _check(
            "model_only_latency_available",
            PASS if len(model_only) == len(requests) else FAIL,
            f"{len(model_only)}/{len(requests)} requests reported model_inference_ms",
        )
    )
    checks.append(
        _check(
            "planner_e2e_latency_available",
            PASS if len(e2e) == len(requests) else FAIL,
            f"{len(e2e)}/{len(requests)} requests reached plan_ready",
        )
    )

    unknown_stages: list[str] = []
    for trace in traces:
        if trace is None:
            continue
        unknown_stages.extend(name for name in trace.timestamps_ns if name not in STAGES)
    checks.append(
        _check(
            "trace_stage_names_known",
            PASS if not unknown_stages else FAIL,
            f"unknown={sorted(set(unknown_stages))}" if unknown_stages else f"subset of {list(STAGES)}",
        )
    )

    over_budget = [value for value in e2e if value > latency_budget_ms]
    checks.append(
        _check(
            "latency_within_budget",
            PASS if not over_budget else FAIL,
            f"{len(over_budget)} requests over {latency_budget_ms} ms" if over_budget
            else f"all <= {latency_budget_ms} ms",
        )
    )

    failures = [item for item in checks if item["status"] == FAIL]
    warnings = [item for item in checks if item["status"] == WARN]
    return {
        "schema_version": "1.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "runtime": runtime.name,
        "capabilities": runtime.capabilities.to_dict(),
        "request_count": len(requests),
        "checks": checks,
        "failed": [item["check"] for item in failures],
        "warned": [item["check"] for item in warnings],
        "passed": not failures,
    }


__all__ = ["check_runtime_contract", "PASS", "FAIL", "WARN"]
