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
NOT_RUN = "NOT_RUN"

#: Fields A4's `--describe` must return (a4_runtime_contract.md §4).
DESCRIBE_REQUIRED_FIELDS: tuple[str, ...] = (
    "git_sha",
    "model_id",
    "model_sha256",
    "dataset_version",
    "config_id",
    "precision",
    "batch",
    "input_shapes",
)


def _check(name: str, status: str, detail: str) -> dict[str, str]:
    return {"check": name, "status": status, "detail": detail}


def _interface_checks(
    runtime: PlannerRuntime,
    requests: Sequence[Mapping[str, Any]],
    *,
    expected_model_sha256: str | None = None,
    model_only_tensor_dir: str | None = None,
) -> list[dict[str, str]]:
    """The three entries §16 of the B3 gate document asks B3 to check itself.

    `--describe`, resident/batch mode and the model-only path all used to be
    untested prose.  Each one is driven here, and a mode that cannot be driven is
    reported as FAIL with the reason rather than quietly skipped: a runtime that
    cannot answer `--describe` cannot be bound to a model digest, and one that
    cannot serve a batch makes every end-to-end number include its start-up cost.
    """
    checks: list[dict[str, str]] = []

    try:
        described = runtime.describe()
    except Exception as error:
        checks.append(
            _check(
                "describe_endpoint",
                FAIL,
                f"cannot be driven: {type(error).__name__}: {error}",
            )
        )
        described = None
    if isinstance(described, Mapping):
        missing = [name for name in DESCRIBE_REQUIRED_FIELDS if not described.get(name)]
        checks.append(
            _check(
                "describe_endpoint",
                PASS if not missing else FAIL,
                f"missing={missing}" if missing else "all required fields present",
            )
        )
        if expected_model_sha256:
            reported = str(described.get("model_sha256") or "")
            match = reported.lower() == expected_model_sha256.lower()
            checks.append(
                _check(
                    "describe_matches_artifact",
                    PASS if match else FAIL,
                    (
                        "described model_sha256 equals the artifact on disk"
                        if match
                        else f"described={reported[:16]}… expected={expected_model_sha256[:16]}…"
                    ),
                )
            )

    batch_requests = list(requests[:2])
    try:
        plans = runtime.run_batch(batch_requests)
    except Exception as error:
        checks.append(
            _check(
                "batch_mode",
                FAIL,
                (
                    f"one process could not serve {len(batch_requests)} requests: "
                    f"{type(error).__name__}: {error}"
                ),
            )
        )
    else:
        echo_ok = len(plans) == len(batch_requests) and all(
            isinstance(plan, Mapping)
            and plan.get("request_id") == request.get("request_id")
            for plan, request in zip(plans, batch_requests, strict=True)
        )
        checks.append(
            _check(
                "batch_mode",
                PASS if echo_ok else FAIL,
                (
                    f"one process answered {len(plans)}/{len(batch_requests)} requests "
                    "with echoed request_id"
                ),
            )
        )

    if not model_only_tensor_dir:
        checks.append(
            _check(
                "model_only_mode",
                NOT_RUN,
                "no tensor dump supplied (create one with `dump-tensors`)",
            )
        )
    else:
        try:
            result = runtime.run_model_only(model_only_tensor_dir)
        except Exception as error:
            checks.append(
                _check(
                    "model_only_mode",
                    FAIL,
                    f"cannot be driven: {type(error).__name__}: {error}",
                )
            )
        else:
            outputs = result.get("outputs")
            ok = result.get("status") == "OK" and isinstance(outputs, Mapping) and outputs
            checks.append(
                _check(
                    "model_only_mode",
                    PASS if ok else FAIL,
                    (
                        f"{len(outputs)} output digests reported from {result.get('mode')}"
                        if ok
                        else f"status={result.get('status')} (no comparable output digest)"
                    ),
                )
            )
    return checks


def check_runtime_contract(
    runtime: PlannerRuntime,
    requests: Sequence[Mapping[str, Any]],
    *,
    latency_budget_ms: float = 1000.0,
    expected_model_sha256: str | None = None,
    model_only_tensor_dir: str | None = None,
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

    checks.extend(
        _interface_checks(
            runtime,
            requests,
            expected_model_sha256=expected_model_sha256,
            model_only_tensor_dir=model_only_tensor_dir,
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


__all__ = [
    "check_runtime_contract",
    "DESCRIBE_REQUIRED_FIELDS",
    "FAIL",
    "NOT_RUN",
    "PASS",
    "WARN",
]
