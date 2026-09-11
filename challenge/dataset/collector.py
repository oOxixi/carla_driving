#!/usr/bin/env python3
"""
Build B1 Teacher-distillation samples from ScenarioEvidenceRecorder JSONL.

Source-of-truth mapping:
  input:
    canonical_routing / SUBMIT
      -> payload.orchestration.model_request

  teacher label:
    canonical_routing / RESOLVE
      -> payload.orchestration.decision_plan

  closed-loop outcome:
    canonical_routing / MANEUVER_EVENT
    + run_complete

The collector is offline/read-only:
- does not modify CARLA
- does not modify Planner
- does not modify A/B/C/D
- does not modify SafetySupervisor
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any


DATASET_SCHEMA_VERSION = "1.0"
DEFAULT_DATASET_VERSION = "teacher_distill_v0.1_smoke"


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def stable_route_hash(route: Any) -> str | None:
    if route is None:
        return None

    return hashlib.sha256(
        canonical_json(route).encode("utf-8")
    ).hexdigest()[:16]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            if not line.strip():
                continue

            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"{path}:{line_no}: invalid JSON: {exc}"
                ) from exc

            if not isinstance(row, dict):
                raise ValueError(
                    f"{path}:{line_no}: row is not a JSON object"
                )

            rows.append(row)

    return rows


def load_scenario(
    repo_root: Path,
    config_path: str | None,
) -> dict[str, Any] | None:
    if not config_path:
        return None

    p = Path(config_path)

    if not p.is_absolute():
        p = repo_root / p

    if not p.is_file():
        return None

    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    return data if isinstance(data, dict) else None


def index_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    run_start = next(
        (
            r
            for r in rows
            if r.get("record_type") == "run_start"
        ),
        None,
    )

    run_complete = next(
        (
            r
            for r in reversed(rows)
            if r.get("record_type") == "run_complete"
        ),
        None,
    )

    submits: dict[str, list[dict[str, Any]]] = {}
    resolves: dict[str, list[dict[str, Any]]] = {}
    maneuver_events: dict[str, list[dict[str, Any]]] = {}

    for row in rows:
        if row.get("record_type") != "canonical_routing":
            continue

        phase = str(row.get("phase", "")).upper()
        command_id = row.get("command_id")

        if not isinstance(command_id, str) or not command_id:
            continue

        if phase == "SUBMIT":
            submits.setdefault(command_id, []).append(row)

        elif phase == "RESOLVE":
            resolves.setdefault(command_id, []).append(row)

        elif phase == "MANEUVER_EVENT":
            maneuver_events.setdefault(command_id, []).append(row)

    return {
        "run_start": run_start,
        "run_complete": run_complete,
        "submits": submits,
        "resolves": resolves,
        "maneuver_events": maneuver_events,
    }


def extract_model_request(
    row: dict[str, Any],
) -> dict[str, Any] | None:
    payload = row.get("payload")

    if not isinstance(payload, dict):
        return None

    orchestration = payload.get("orchestration")

    if not isinstance(orchestration, dict):
        return None

    req = orchestration.get("model_request")

    return req if isinstance(req, dict) else None


def extract_teacher_plan(
    row: dict[str, Any],
) -> dict[str, Any] | None:
    payload = row.get("payload")

    if not isinstance(payload, dict):
        return None

    orchestration = payload.get("orchestration")

    if not isinstance(orchestration, dict):
        return None

    plan = orchestration.get("decision_plan")

    return plan if isinstance(plan, dict) else None


def extract_model_timing(
    row: dict[str, Any],
) -> dict[str, Any] | None:
    payload = row.get("payload")

    if not isinstance(payload, dict):
        return None

    orchestration = payload.get("orchestration")

    if not isinstance(orchestration, dict):
        return None

    timing = orchestration.get("model_timing")

    return timing if isinstance(timing, dict) else None


def get_disposition(
    row: dict[str, Any],
) -> str | None:
    payload = row.get("payload")

    if isinstance(payload, dict):
        value = payload.get("disposition")

        if isinstance(value, str):
            return value

    return None


def find_rgb(
    repo_root: Path,
    rgb_ref: Any,
) -> tuple[Path | None, bool]:
    if not isinstance(rgb_ref, str) or not rgb_ref:
        return None, False

    p = Path(rgb_ref)

    if not p.is_absolute():
        p = repo_root / p

    p = p.resolve()

    return p, p.is_file()


def classify_sample(
    model_request: dict[str, Any],
    teacher_plan: dict[str, Any],
    closed_loop: dict[str, Any],
) -> dict[str, Any]:
    scene_summary = model_request.get("scene_summary")

    risk = None

    if isinstance(scene_summary, dict):
        risk = scene_summary.get("risk_level")

    steps = teacher_plan.get("steps")

    if not isinstance(steps, list):
        steps = []

    behaviors = [
        str(step.get("behavior"))
        for step in steps
        if isinstance(step, dict)
        and step.get("behavior") is not None
    ]

    safety_critical = (
        risk in {"HIGH", "EMERGENCY"}
        or bool(
            closed_loop.get(
                "safety_override_observed"
            )
        )
        or bool(
            closed_loop.get(
                "collision_count"
            )
        )
    )

    complex_behaviors = {
        "AVOID_OBSTACLE",
        "RETURN_TO_LANE",
        "YIELD",
        "FOLLOW",
        "CHANGE_LANE_LEFT",
        "CHANGE_LANE_RIGHT",
    }

    if safety_critical:
        primary = "SAFETY_CRITICAL"

    elif (
        len(steps) > 1
        or any(
            behavior in complex_behaviors
            for behavior in behaviors
        )
    ):
        primary = "COMPLEX"

    else:
        primary = "NORMAL"

    return {
        "primary": primary,
        "safety_critical": safety_critical,
    }


def extract_closed_loop(
    run_complete: dict[str, Any] | None,
    command_id: str,
    maneuver_events: list[dict[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "available": run_complete is not None,
        "run_status": None,
        "scenario_acceptance_passed": None,
        "command_terminal_status": None,
        "plan_terminal_state": None,
        "plan_terminal_reason": None,
        "collision_count": None,
        "lane_invasion_count": None,
        "route_deviation_count": None,
        "red_light_violation_count": None,
        "safety_override_frames": None,
        "safety_override_observed": None,
        "min_gap_m": None,
        "min_ttc_s": None,
    }

    for row in maneuver_events:
        payload = row.get("payload")

        if not isinstance(payload, dict):
            continue

        if payload.get("event_type") == "qwen_terminal":
            result["plan_terminal_state"] = payload.get(
                "state"
            )
            result["plan_terminal_reason"] = payload.get(
                "reason_code"
            )

    if run_complete is None:
        return result

    summary = run_complete.get("summary")

    if not isinstance(summary, dict):
        return result

    result["run_status"] = summary.get(
        "status"
    )

    result["collision_count"] = summary.get(
        "collision_count"
    )

    result["lane_invasion_count"] = summary.get(
        "lane_invasion_count"
    )

    result["route_deviation_count"] = summary.get(
        "route_deviation_count"
    )

    result["red_light_violation_count"] = summary.get(
        "red_light_violation_count"
    )

    result["safety_override_frames"] = summary.get(
        "safety_override_frames"
    )

    result["min_gap_m"] = summary.get(
        "min_gap_m"
    )

    result["min_ttc_s"] = summary.get(
        "min_ttc_s"
    )

    result["safety_override_observed"] = bool(
        (
            summary.get(
                "safety_override_frames"
            )
            or 0
        )
        > 0
    )

    acceptance = summary.get(
        "acceptance"
    )

    if isinstance(acceptance, dict):
        result["scenario_acceptance_passed"] = (
            acceptance.get("passed")
        )

    statuses = summary.get(
        "command_terminal_statuses"
    )

    if isinstance(statuses, dict):
        result["command_terminal_status"] = (
            statuses.get(command_id)
        )

    return result


def validate_pair(
    model_request: dict[str, Any] | None,
    teacher_plan: dict[str, Any] | None,
    rgb_exists: bool,
    resolve_disposition: str | None,
) -> tuple[bool, list[str]]:
    reasons: list[str] = []

    if model_request is None:
        reasons.append(
            "MODEL_REQUEST_MISSING"
        )

    if teacher_plan is None:
        reasons.append(
            "MANEUVER_PLAN_MISSING"
        )

    if model_request is not None:
        if (
            model_request.get(
                "schema_version"
            )
            != "1.0"
        ):
            reasons.append(
                "MODEL_REQUEST_SCHEMA_VERSION_INVALID"
            )

        if not isinstance(
            model_request.get(
                "request_id"
            ),
            str,
        ):
            reasons.append(
                "MODEL_REQUEST_REQUEST_ID_MISSING"
            )

        if not isinstance(
            model_request.get(
                "command_id"
            ),
            str,
        ):
            reasons.append(
                "MODEL_REQUEST_COMMAND_ID_MISSING"
            )

        if not rgb_exists:
            reasons.append(
                "RGB_MISSING"
            )

    if teacher_plan is not None:
        if (
            teacher_plan.get(
                "schema_version"
            )
            != "2.0"
        ):
            reasons.append(
                "MANEUVER_PLAN_SCHEMA_VERSION_INVALID"
            )

        if (
            teacher_plan.get(
                "plan_type"
            )
            != "MANEUVER_SEQUENCE"
        ):
            reasons.append(
                "MANEUVER_PLAN_TYPE_INVALID"
            )

        steps = teacher_plan.get(
            "steps"
        )

        if (
            not isinstance(
                steps,
                list,
            )
            or not (
                1
                <= len(steps)
                <= 4
            )
        ):
            reasons.append(
                "MANEUVER_PLAN_STEPS_INVALID"
            )

    if (
        model_request is not None
        and teacher_plan is not None
    ):
        if (
            model_request.get(
                "request_id"
            )
            != teacher_plan.get(
                "request_id"
            )
        ):
            reasons.append(
                "REQUEST_ID_MISMATCH"
            )

        if (
            model_request.get(
                "command_id"
            )
            != teacher_plan.get(
                "command_id"
            )
        ):
            reasons.append(
                "COMMAND_ID_MISMATCH"
            )

    if resolve_disposition != "SLOW_READY":
        reasons.append(
            "RESOLVE_NOT_READY:"
            + (
                resolve_disposition
                or "NONE"
            )
        )

    return (
        len(reasons) == 0,
        reasons,
    )


def target_grounding(
    model_request: dict[str, Any],
    teacher_plan: dict[str, Any],
) -> dict[str, Any]:
    targets = model_request.get(
        "targets"
    )

    if not isinstance(
        targets,
        list,
    ):
        targets = []

    target_ids = [
        target.get(
            "target_id"
        )
        for target in targets
        if isinstance(
            target,
            dict,
        )
        and isinstance(
            target.get(
                "target_id"
            ),
            str,
        )
    ]

    referenced: list[str] = []

    steps = teacher_plan.get(
        "steps"
    )

    if isinstance(
        steps,
        list,
    ):
        for step in steps:
            if not isinstance(
                step,
                dict,
            ):
                continue

            target = step.get(
                "target"
            )

            if not isinstance(
                target,
                dict,
            ):
                continue

            target_id = target.get(
                "target_id"
            )

            if isinstance(
                target_id,
                str,
            ):
                referenced.append(
                    target_id
                )

    missing = [
        target_id
        for target_id in referenced
        if target_id not in target_ids
    ]

    return {
        "candidate_target_ids": target_ids,
        "teacher_referenced_target_ids": referenced,
        "valid": len(missing) == 0,
        "missing_target_ids": missing,
        "ordering_policy": (
            "PRESERVE_MODEL_REQUEST_ORDER"
        ),
    }


def build_sample(
    *,
    repo_root: Path,
    log_path: Path,
    run_start: dict[str, Any] | None,
    run_complete: dict[str, Any] | None,
    submit: dict[str, Any],
    resolve: dict[str, Any],
    maneuver_events: list[dict[str, Any]],
    scenario_data: dict[str, Any] | None,
    dataset_version: str,
) -> dict[str, Any]:
    model_request = extract_model_request(
        submit
    )

    teacher_plan = extract_teacher_plan(
        resolve
    )

    resolve_disposition = get_disposition(
        resolve
    )

    rgb_path: Path | None = None
    rgb_exists = False

    if model_request is not None:
        rgb_path, rgb_exists = find_rgb(
            repo_root,
            model_request.get(
                "rgb_ref"
            ),
        )

    valid, rejection_reasons = validate_pair(
        model_request,
        teacher_plan,
        rgb_exists,
        resolve_disposition,
    )

    command_id = str(
        submit.get(
            "command_id"
        )
    )

    run_config: dict[str, Any] = {}

    if isinstance(
        run_start,
        dict,
    ):
        cfg = run_start.get(
            "config"
        )

        if isinstance(
            cfg,
            dict,
        ):
            run_config = cfg

    route = None
    scenario_family = None
    weather = None

    if isinstance(
        scenario_data,
        dict,
    ):
        route = scenario_data.get(
            "route"
        )

        scenario_family = scenario_data.get(
            "category"
        )

        weather = scenario_data.get(
            "weather"
        )

    route_hash = stable_route_hash(
        route
    )

    frame_id = None
    sim_time_s = None
    request_id = None
    model_id = None
    plan_id = None

    if model_request is not None:
        request_id = model_request.get(
            "request_id"
        )

        scene_summary = model_request.get(
            "scene_summary"
        )

        if isinstance(
            scene_summary,
            dict,
        ):
            frame_id = scene_summary.get(
                "frame_id"
            )

            sim_time_s = scene_summary.get(
                "sim_time_s"
            )

    if teacher_plan is not None:
        model_id = teacher_plan.get(
            "model_id"
        )

        plan_id = teacher_plan.get(
            "plan_id"
        )

    run_id = None
    scenario_id = None
    difficulty = None
    recorded_at_utc = None

    if isinstance(
        run_start,
        dict,
    ):
        run_id = run_start.get(
            "run_id"
        )

        scenario_id = run_start.get(
            "scenario_id"
        )

        difficulty = run_start.get(
            "difficulty"
        )

        recorded_at_utc = run_start.get(
            "recorded_at_utc"
        )

    sample_seed = run_config.get(
        "seed"
    )

    sample_map = run_config.get(
        "map"
    )

    code_version = run_config.get(
        "code_version"
    )

    group_payload = {
        "scenario_family": scenario_family,
        "map": sample_map,
        "route_hash": route_hash,
        "seed": sample_seed,
    }

    group_key = sha256_bytes(
        canonical_json(
            group_payload
        ).encode(
            "utf-8"
        )
    )[:20]

    sample_identity = {
        "run_id": run_id,
        "command_id": command_id,
        "request_id": request_id,
        "frame_id": frame_id,
    }

    sample_id = (
        "td_"
        + sha256_bytes(
            canonical_json(
                sample_identity
            ).encode(
                "utf-8"
            )
        )[:24]
    )

    closed_loop = extract_closed_loop(
        run_complete,
        command_id,
        maneuver_events,
    )

    if (
        model_request is not None
        and teacher_plan is not None
    ):
        grounding = target_grounding(
            model_request,
            teacher_plan,
        )
    else:
        grounding = {
            "candidate_target_ids": [],
            "teacher_referenced_target_ids": [],
            "valid": False,
            "missing_target_ids": [],
            "ordering_policy": (
                "PRESERVE_MODEL_REQUEST_ORDER"
            ),
        }

    if (
        valid
        and not grounding["valid"]
    ):
        valid = False

        rejection_reasons.append(
            "TARGET_GROUNDING_INVALID"
        )

    if (
        model_request is not None
        and teacher_plan is not None
    ):
        sample_class = classify_sample(
            model_request,
            teacher_plan,
            closed_loop,
        )
    else:
        sample_class = {
            "primary": "UNKNOWN",
            "safety_critical": False,
        }

    rgb_sha256 = None
    rgb_size_bytes = None
    rgb_rel = None

    if rgb_path is not None:
        try:
            rgb_rel = (
                rgb_path
                .relative_to(
                    repo_root
                )
                .as_posix()
            )
        except ValueError:
            rgb_rel = str(
                rgb_path
            )

    if (
        rgb_exists
        and rgb_path is not None
    ):
        rgb_sha256 = sha256_file(
            rgb_path
        )

        rgb_size_bytes = (
            rgb_path
            .stat()
            .st_size
        )

    quality = {
        "model_request_schema_version_valid": (
            model_request is not None
            and model_request.get(
                "schema_version"
            )
            == "1.0"
        ),
        "maneuver_plan_schema_version_valid": (
            teacher_plan is not None
            and teacher_plan.get(
                "schema_version"
            )
            == "2.0"
        ),
        "request_id_match": (
            model_request is not None
            and teacher_plan is not None
            and model_request.get(
                "request_id"
            )
            == teacher_plan.get(
                "request_id"
            )
        ),
        "command_id_match": (
            model_request is not None
            and teacher_plan is not None
            and model_request.get(
                "command_id"
            )
            == teacher_plan.get(
                "command_id"
            )
        ),
        "rgb_exists": rgb_exists,
        "target_grounding_valid": grounding[
            "valid"
        ],
        "resolve_ready": (
            resolve_disposition
            == "SLOW_READY"
        ),
        "valid_for_training": valid,
        "rejection_reasons": (
            rejection_reasons
        ),
    }

    return {
        "dataset_schema_version": (
            DATASET_SCHEMA_VERSION
        ),
        "dataset_version": (
            dataset_version
        ),
        "sample_id": sample_id,

        "metadata": {
            "run_id": run_id,
            "recorded_at_utc": (
                recorded_at_utc
            ),

            "scenario_id": (
                scenario_id
            ),
            "scenario_family": (
                scenario_family
            ),
            "difficulty": (
                difficulty
            ),
            "map": (
                sample_map
            ),
            "weather": (
                weather
            ),
            "seed": (
                sample_seed
            ),

            "route_hash": (
                route_hash
            ),
            "group_key": (
                group_key
            ),

            "frame_id": (
                frame_id
            ),
            "sim_time_s": (
                sim_time_s
            ),

            "teacher_git_sha": (
                code_version
            ),
            "teacher_model_id": (
                model_id
            ),
            "teacher_mode": (
                run_config.get(
                    "qwen_mode"
                )
            ),
            "teacher_service_url": (
                run_config.get(
                    "qwen_service_url"
                )
            ),

            "request_id": (
                request_id
            ),
            "command_id": (
                command_id
            ),
            "plan_id": (
                plan_id
            ),

            "source_log": (
                str(
                    log_path
                )
            ),
            "scenario_config_path": (
                run_config.get(
                    "config_path"
                )
            ),
        },

        "model_request": copy.deepcopy(
            model_request
        ),

        "teacher_plan": copy.deepcopy(
            teacher_plan
        ),

        "visual_input": {
            "rgb_ref": (
                model_request.get(
                    "rgb_ref"
                )
                if model_request
                is not None
                else None
            ),
            "resolved_path": (
                rgb_rel
            ),
            "rgb_sha256": (
                rgb_sha256
            ),
            "size_bytes": (
                rgb_size_bytes
            ),
            "available": (
                rgb_exists
            ),
        },

        "target_grounding": (
            grounding
        ),

        "teacher_runtime": {
            "resolve_disposition": (
                resolve_disposition
            ),
            "model_timing": (
                extract_model_timing(
                    resolve
                )
            ),
        },

        "sample_class": (
            sample_class
        ),

        "closed_loop_quality": (
            closed_loop
        ),

        "quality": (
            quality
        ),
    }


def build_run_level_rejection(
    *,
    log_path: Path,
    dataset_version: str,
    run_start: dict[str, Any] | None,
    failure: dict[str, Any] | None,
    reason: str,
) -> dict[str, Any]:
    run_id = None
    scenario_id = None
    config = {}

    if isinstance(
        run_start,
        dict,
    ):
        run_id = run_start.get(
            "run_id"
        )

        scenario_id = run_start.get(
            "scenario_id"
        )

        cfg = run_start.get(
            "config"
        )

        if isinstance(
            cfg,
            dict,
        ):
            config = cfg

    return {
        "dataset_schema_version": (
            DATASET_SCHEMA_VERSION
        ),
        "dataset_version": (
            dataset_version
        ),

        "source_log": str(
            log_path
        ),

        "run_id": (
            run_id
        ),
        "scenario_id": (
            scenario_id
        ),

        "teacher_git_sha": (
            config.get(
                "code_version"
            )
        ),
        "teacher_model_id": (
            config.get(
                "qwen_model"
            )
        ),
        "teacher_mode": (
            config.get(
                "qwen_mode"
            )
        ),

        "command_id": None,
        "request_id": None,

        "valid_for_training": False,

        "rejection_reasons": [
            reason
        ],

        "runtime_failure": (
            copy.deepcopy(
                failure
            )
            if failure is not None
            else None
        ),
    }


def collect_file(
    *,
    repo_root: Path,
    log_path: Path,
    dataset_version: str,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    rows = read_jsonl(
        log_path
    )

    indexed = index_rows(
        rows
    )

    run_start = indexed[
        "run_start"
    ]

    run_complete = indexed[
        "run_complete"
    ]

    run_config = {}

    if isinstance(
        run_start,
        dict,
    ):
        cfg = run_start.get(
            "config"
        )

        if isinstance(
            cfg,
            dict,
        ):
            run_config = cfg

    scenario_data = load_scenario(
        repo_root,
        run_config.get(
            "config_path"
        ),
    )

    accepted: list[
        dict[str, Any]
    ] = []

    rejected: list[
        dict[str, Any]
    ] = []

    submits = indexed[
        "submits"
    ]

    resolves = indexed[
        "resolves"
    ]

    maneuver_events = indexed[
        "maneuver_events"
    ]

    # ---------------------------------------------------------
    # Run-level failure governance.
    #
    # Some failures happen before a canonical SUBMIT exists,
    # e.g.:
    # - unsupported Qwen backend/profile
    # - runtime initialization failure
    # - service construction failure
    #
    # These runs are not training samples, but they must remain
    # auditable rather than disappearing silently.
    # ---------------------------------------------------------
    if not submits:
        runtime_failures = [
            row
            for row in rows
            if row.get(
                "record_type"
            )
            == "runtime_failure_diagnosis"
        ]

        if runtime_failures:
            for failure in (
                runtime_failures
            ):
                rejected.append(
                    build_run_level_rejection(
                        log_path=log_path,
                        dataset_version=dataset_version,
                        run_start=run_start,
                        failure=failure,
                        reason=(
                            "RUNTIME_FAILURE_BEFORE_SUBMIT"
                        ),
                    )
                )

        else:
            rejected.append(
                build_run_level_rejection(
                    log_path=log_path,
                    dataset_version=dataset_version,
                    run_start=run_start,
                    failure=None,
                    reason=(
                        "NO_CANONICAL_SUBMIT"
                    ),
                )
            )

        return (
            accepted,
            rejected,
        )

    # ---------------------------------------------------------
    # Normal command-level Teacher sample assembly.
    # ---------------------------------------------------------
    for (
        command_id,
        submit_rows,
    ) in submits.items():

        for submit in submit_rows:
            submit_req = (
                extract_model_request(
                    submit
                )
            )

            submit_request_id = (
                submit_req.get(
                    "request_id"
                )
                if isinstance(
                    submit_req,
                    dict,
                )
                else None
            )

            candidates = resolves.get(
                command_id,
                [],
            )

            chosen = None

            for resolve in candidates:
                resolve_req = (
                    extract_model_request(
                        resolve
                    )
                )

                if not isinstance(
                    resolve_req,
                    dict,
                ):
                    continue

                if (
                    resolve_req.get(
                        "request_id"
                    )
                    == submit_request_id
                ):
                    chosen = resolve
                    break

            if chosen is None:
                rejected.append({
                    "dataset_schema_version": (
                        DATASET_SCHEMA_VERSION
                    ),
                    "dataset_version": (
                        dataset_version
                    ),
                    "source_log": (
                        str(
                            log_path
                        )
                    ),
                    "run_id": (
                        run_start.get(
                            "run_id"
                        )
                        if isinstance(
                            run_start,
                            dict,
                        )
                        else None
                    ),
                    "scenario_id": (
                        run_start.get(
                            "scenario_id"
                        )
                        if isinstance(
                            run_start,
                            dict,
                        )
                        else None
                    ),
                    "command_id": (
                        command_id
                    ),
                    "request_id": (
                        submit_request_id
                    ),
                    "valid_for_training": (
                        False
                    ),
                    "rejection_reasons": [
                        "MATCHING_RESOLVE_NOT_FOUND"
                    ],
                })

                continue

            sample = build_sample(
                repo_root=repo_root,
                log_path=log_path,
                run_start=run_start,
                run_complete=run_complete,
                submit=submit,
                resolve=chosen,
                maneuver_events=(
                    maneuver_events.get(
                        command_id,
                        [],
                    )
                ),
                scenario_data=scenario_data,
                dataset_version=dataset_version,
            )

            if sample[
                "quality"
            ][
                "valid_for_training"
            ]:
                accepted.append(
                    sample
                )

            else:
                rejected.append(
                    sample
                )

    return (
        accepted,
        rejected,
    )


def write_jsonl(
    path: Path,
    rows: list[dict[str, Any]],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        encoding="utf-8",
    ) as f:
        for row in rows:
            f.write(
                json.dumps(
                    row,
                    ensure_ascii=False,
                    separators=(
                        ",",
                        ":",
                    ),
                )
                + "\n"
            )


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--repo-root",
        default=".",
    )

    parser.add_argument(
        "--input-log",
        action="append",
        required=True,
        help=(
            "ScenarioEvidenceRecorder JSONL; "
            "repeat for multiple files"
        ),
    )

    parser.add_argument(
        "--output",
        required=True,
    )

    parser.add_argument(
        "--rejected-output",
        required=True,
    )

    parser.add_argument(
        "--dataset-version",
        default=(
            DEFAULT_DATASET_VERSION
        ),
    )

    args = parser.parse_args()

    repo_root = (
        Path(
            args.repo_root
        )
        .expanduser()
        .resolve()
    )

    accepted_all: list[
        dict[str, Any]
    ] = []

    rejected_all: list[
        dict[str, Any]
    ] = []

    for item in args.input_log:
        log_path = (
            Path(
                item
            )
            .expanduser()
        )

        if not log_path.is_absolute():
            log_path = (
                repo_root
                / log_path
            ).resolve()

        accepted, rejected = collect_file(
            repo_root=repo_root,
            log_path=log_path,
            dataset_version=(
                args.dataset_version
            ),
        )

        accepted_all.extend(
            accepted
        )

        rejected_all.extend(
            rejected
        )

    sample_ids: set[str] = set()

    duplicate_ids: list[
        str
    ] = []

    deduped: list[
        dict[str, Any]
    ] = []

    for sample in accepted_all:
        sid = sample[
            "sample_id"
        ]

        if sid in sample_ids:
            duplicate_ids.append(
                sid
            )
            continue

        sample_ids.add(
            sid
        )

        deduped.append(
            sample
        )

    write_jsonl(
        Path(
            args.output
        ),
        deduped,
    )

    write_jsonl(
        Path(
            args.rejected_output
        ),
        rejected_all,
    )

    print(
        f"COLLECTED_ACCEPTED={len(deduped)}"
    )

    print(
        f"COLLECTED_REJECTED={len(rejected_all)}"
    )

    print(
        "DUPLICATE_SAMPLE_IDS="
        f"{len(duplicate_ids)}"
    )

    if duplicate_ids:
        print(
            "DUPLICATES:"
        )

        for sid in duplicate_ids:
            print(
                sid
            )


if __name__ == "__main__":
    main()
