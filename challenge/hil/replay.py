"""Replay of frozen B1 request sets through the planner under test."""

from __future__ import annotations

from dataclasses import dataclass, field
import copy
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .identity import sha256_file
from .run_io import read_json, read_jsonl
from .runtime_adapter import PlannerRuntime
from .stages import StageTrace


REQUEST_SOURCE_PREFERENCE: tuple[str, ...] = (
    "data/smoke_valid.jsonl",
    "data/smoke_train_eligible.jsonl",
    # B1 D2 release layout (challenge/dataset/releases/*): val is preferred over
    # train because it is not the split the Student was fitted on, and the
    # reserved test candidates are deliberately NOT auto-selected: they belong
    # to B2's frozen benchmark, not to a B3 tooling replay.
    "val.jsonl",
    "data/train.jsonl",
    "data/val.jsonl",
    "train.jsonl",
)

FORBIDDEN_PLAN_KEYS: tuple[str, ...] = ("steer", "throttle", "brake", "waypoints")
REQUIRED_PLAN_KEYS: tuple[str, ...] = (
    "schema_version",
    "plan_type",
    "request_id",
    "command_id",
    "steps",
    "confidence",
    "reason_code",
)


@dataclass(frozen=True, slots=True)
class ReplayCase:
    case_id: str
    sample_id: str
    scenario_id: str
    request: dict[str, Any]
    teacher_plan: dict[str, Any] | None
    rgb_path: str | None
    rgb_sha256: str | None
    rgb_resolved: bool
    rgb_source: str
    source_file: str


@dataclass(slots=True)
class ReplayResult:
    rows: list[dict[str, Any]] = field(default_factory=list)
    traces: list[StageTrace] = field(default_factory=list)
    plans: list[dict[str, Any]] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)


def _rgb_index(delivery_root: Path | None) -> dict[str, dict[str, Any]]:
    if delivery_root is None:
        return {}
    path = delivery_root / "manifests" / "rgb_manifest.json"
    if path.is_file():
        payload = read_json(path)
        return {
            str(entry.get("sample_id")): entry
            for entry in payload.get("entries", ())
            if isinstance(entry, Mapping)
        }
    # B1 D2 release layout: a flat {sample_id: {release_rgb_ref, ...}} mapping.
    release_path = delivery_root / "rgb_mapping.json"
    if release_path.is_file():
        payload = read_json(release_path)
        index: dict[str, dict[str, Any]] = {}
        for sample_id, value in payload.items():
            if not isinstance(value, Mapping):
                continue
            index[str(sample_id)] = {
                "sample_id": str(sample_id),
                "packaged_rgb_path": value.get("release_rgb_ref"),
                "original_rgb_ref": value.get("original_rgb_ref"),
                "rgb_sha256": value.get("rgb_sha256"),
            }
        return index
    return {}


def _resolve_rgb(
    request: Mapping[str, Any],
    *,
    sample_id: str,
    manifest_entry: Mapping[str, Any] | None,
    delivery_root: Path | None,
    repo_root: Path | None,
) -> tuple[str | None, str | None, bool, str]:
    """Return (path, sha256, resolved, source)."""
    reference = request.get("rgb_ref")
    if manifest_entry is not None and delivery_root is not None:
        packaged = manifest_entry.get("packaged_rgb_path")
        if isinstance(packaged, str) and packaged:
            # The smoke layout stores a delivery-relative path; the D2 release
            # layout stores a repository-relative one, so try both roots.
            for root in (delivery_root, repo_root):
                if root is None:
                    continue
                candidate = (root / packaged).resolve()
                if candidate.is_file():
                    digest = manifest_entry.get("rgb_sha256")
                    actual = sha256_file(candidate)
                    if isinstance(digest, str) and digest and digest.lower() != actual.lower():
                        return str(candidate), actual, False, "sha256_mismatch"
                    return str(candidate), actual, True, "delivery_rgb_manifest"
    if isinstance(reference, str) and reference.strip():
        for root in (delivery_root, repo_root):
            if root is None:
                continue
            candidate = (root / reference).resolve()
            if candidate.is_file():
                return str(candidate), sha256_file(candidate), True, f"raw_ref_under_{root.name}"
        return str(reference), None, False, "raw_ref_missing_on_disk"
    return None, None, False, "no_rgb_reference"


def load_replay_cases(
    *,
    delivery_root: str | Path | None,
    requests_path: str | Path | None = None,
    repo_root: str | Path | None = None,
    limit: int | None = None,
) -> tuple[list[ReplayCase], dict[str, Any]]:
    delivery = Path(delivery_root).resolve() if delivery_root else None
    repo = Path(repo_root).resolve() if repo_root else None
    source = Path(requests_path).resolve() if requests_path else None
    if source is None:
        if delivery is None:
            raise ValueError("either requests_path or delivery_root is required")
        for relative in REQUEST_SOURCE_PREFERENCE:
            candidate = delivery / relative
            if candidate.is_file():
                source = candidate
                break
        if source is None:
            raise FileNotFoundError(
                f"no request JSONL found under {delivery}; tried {REQUEST_SOURCE_PREFERENCE}"
            )
    records = read_jsonl(source)
    manifest = _rgb_index(delivery)
    cases: list[ReplayCase] = []
    unresolved = 0
    for index, record in enumerate(records):
        request = record.get("model_request")
        if not isinstance(request, Mapping):
            raise ValueError(f"{source}: record {index} has no model_request object")
        sample_id = str(record.get("sample_id", f"sample_{index:04d}"))
        metadata = record.get("metadata") if isinstance(record.get("metadata"), Mapping) else {}
        scenario_id = str(metadata.get("scenario_id", "UNKNOWN"))
        rgb_path, rgb_sha, rgb_resolved, rgb_source = _resolve_rgb(
            request,
            sample_id=sample_id,
            manifest_entry=manifest.get(sample_id),
            delivery_root=delivery,
            repo_root=repo,
        )
        if not rgb_resolved:
            unresolved += 1
        rewritten = copy.deepcopy(dict(request))
        if rgb_resolved and rgb_path is not None:
            rewritten["rgb_ref"] = rgb_path
        teacher_plan = record.get("teacher_plan")
        cases.append(
            ReplayCase(
                case_id=f"{scenario_id}#{index:04d}",
                sample_id=sample_id,
                scenario_id=scenario_id,
                request=rewritten,
                teacher_plan=dict(teacher_plan) if isinstance(teacher_plan, Mapping) else None,
                rgb_path=rgb_path,
                rgb_sha256=rgb_sha,
                rgb_resolved=rgb_resolved,
                rgb_source=rgb_source,
                source_file=str(source),
            )
        )
        if limit is not None and len(cases) >= limit:
            break
    info = {
        "requests_path": str(source),
        "records": len(cases),
        "rgb_manifest_present": bool(manifest),
        "rgb_unresolved": unresolved,
        "source_preference": list(REQUEST_SOURCE_PREFERENCE),
    }
    return cases, info


def _behaviors(plan: Mapping[str, Any] | None) -> list[str]:
    if not isinstance(plan, Mapping):
        return []
    steps = plan.get("steps")
    if not isinstance(steps, Sequence):
        return []
    values: list[str] = []
    for step in steps:
        if isinstance(step, Mapping):
            values.append(str(step.get("behavior", "UNKNOWN")))
    return values


def _targets(plan: Mapping[str, Any] | None) -> list[str]:
    if not isinstance(plan, Mapping):
        return []
    steps = plan.get("steps")
    if not isinstance(steps, Sequence):
        return []
    values: list[str] = []
    for step in steps:
        if not isinstance(step, Mapping):
            continue
        target = step.get("target")
        if isinstance(target, Mapping) and target.get("target_id") is not None:
            values.append(str(target["target_id"]))
        else:
            values.append("NONE")
    return values


def _match_ratio(left: Sequence[str], right: Sequence[str]) -> float:
    if not left and not right:
        return 1.0
    width = max(len(left), len(right))
    if width == 0:
        return 1.0
    hits = sum(1 for index in range(min(len(left), len(right))) if left[index] == right[index])
    return hits / width


def structural_checks(
    request: Mapping[str, Any],
    plan: Mapping[str, Any] | None,
) -> tuple[str, ...]:
    failures: list[str] = []
    if plan is None:
        return ("no_plan_returned",)
    missing = [key for key in REQUIRED_PLAN_KEYS if key not in plan]
    if missing:
        failures.append("missing_keys:" + "|".join(missing))
    for key in FORBIDDEN_PLAN_KEYS:
        if key in plan:
            failures.append(f"forbidden_output:{key}")
    steps = plan.get("steps")
    if not isinstance(steps, Sequence) or isinstance(steps, (str, bytes)):
        failures.append("steps_not_a_sequence")
        steps = []
    if not 1 <= len(steps) <= 4:
        failures.append(f"step_count_out_of_range:{len(steps)}")
    for index, step in enumerate(steps):
        if not isinstance(step, Mapping):
            failures.append(f"step_{index}_not_object")
            continue
        for key in FORBIDDEN_PLAN_KEYS:
            if key in step:
                failures.append(f"step_{index}_forbidden_output:{key}")
    if "request_id" in plan and request.get("request_id") != plan.get("request_id"):
        failures.append("request_id_echo_mismatch")
    if "command_id" in plan and request.get("command_id") != plan.get("command_id"):
        failures.append("command_id_echo_mismatch")
    if bool(request.get("constraints", {}).get("must_stop")):
        behaviors = _behaviors(plan)
        if behaviors and behaviors[0] not in {"STOP", "HOLD"}:
            failures.append("must_stop_violated")
    return tuple(failures)


def run_replay(
    runtime: PlannerRuntime,
    cases: Iterable[ReplayCase],
    *,
    run_id: str,
    round_index: int,
    phase: str = "measured",
) -> ReplayResult:
    identity = runtime.identity.to_dict()
    rows: list[dict[str, Any]] = []
    traces: list[StageTrace] = []
    plans: list[dict[str, Any]] = []
    ready = 0
    rgb_ok = 0
    structural_ok = 0
    for case in cases:
        plan, trace = runtime.infer(
            case.request,
            case_id=case.case_id,
            round_index=round_index,
            phase=phase,
        )
        failures = structural_checks(case.request, plan)
        teacher_behaviors = _behaviors(case.teacher_plan)
        student_behaviors = _behaviors(plan)
        teacher_targets = _targets(case.teacher_plan)
        student_targets = _targets(plan)
        if trace.outcome == "READY":
            ready += 1
        if case.rgb_resolved:
            rgb_ok += 1
        if not failures:
            structural_ok += 1
        traces.append(trace)
        plans.append(
            {
                "run_id": run_id,
                "round": round_index,
                "case_id": case.case_id,
                "sample_id": case.sample_id,
                "request_id": case.request.get("request_id", ""),
                "outcome": trace.outcome,
                "structural_failures": list(failures),
                "student_plan": plan,
                "teacher_plan": case.teacher_plan,
            }
        )
        rows.append(
            {
                "run_id": run_id,
                "round": round_index,
                "case_id": case.case_id,
                "sample_id": case.sample_id,
                "scenario_id": case.scenario_id,
                "request_id": case.request.get("request_id", ""),
                "outcome": trace.outcome or "UNKNOWN",
                "rgb_resolved": case.rgb_resolved,
                "rgb_sha256": case.rgb_sha256 or "",
                "teacher_behavior_sequence": "|".join(teacher_behaviors),
                "student_behavior_sequence": "|".join(student_behaviors),
                "behavior_match_ratio": _match_ratio(teacher_behaviors, student_behaviors),
                "teacher_target_sequence": "|".join(teacher_targets),
                "student_target_sequence": "|".join(student_targets),
                "target_match_ratio": _match_ratio(teacher_targets, student_targets),
                "plan_step_count": len(student_behaviors),
                "structural_failures": "|".join(failures),
                "diagnostic_only": True,
                **{key: identity.get(key, "") for key in
                   ("model_id", "model_sha256", "config_id", "dataset_version", "git_sha")},
            }
        )
    total = len(rows)
    summary = {
        "round": round_index,
        "case_count": total,
        "ready": ready,
        "rgb_resolved": rgb_ok,
        "structural_pass": structural_ok,
        "ready_rate": (ready / total) if total else None,
        "rgb_resolution_rate": (rgb_ok / total) if total else None,
        "structural_pass_rate": (structural_ok / total) if total else None,
        "teacher_comparison": "DIAGNOSTIC_ONLY",
        "teacher_comparison_reason": (
            "Student weights are not A3-gated in this run; behaviour match is recorded "
            "for toolchain validation and must not be read as accuracy."
        ),
    }
    return ReplayResult(rows=rows, traces=traces, plans=plans, summary=summary)


def failure_row_detail(trace: StageTrace) -> dict[str, Any]:
    return {
        "outcome": trace.outcome,
        "reason_code": trace.reason_code,
        "detail": trace.outcome_detail,
        "missing_stages": list(trace.missing_stages()),
        "model_only_ms": trace.durations_ms().get("model_only_ms"),
        "planner_e2e_ms": trace.durations_ms().get("planner_e2e_ms"),
    }


__all__ = [
    "ReplayCase",
    "ReplayResult",
    "load_replay_cases",
    "run_replay",
    "structural_checks",
    "failure_row_detail",
    "REQUEST_SOURCE_PREFERENCE",
]
