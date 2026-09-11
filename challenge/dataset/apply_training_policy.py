#!/usr/bin/env python3

from __future__ import annotations

import argparse
import copy
import json
from collections import Counter
from pathlib import Path
from typing import Any


POLICY_VERSION = "b1_training_policy_v1"


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


def write_jsonl(
    path: Path,
    rows: list[dict[str, Any]],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(
                json.dumps(
                    row,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                + "\n"
            )


def get_dict(
    sample: dict[str, Any],
    key: str,
) -> dict[str, Any]:
    value = sample.get(key)

    if isinstance(value, dict):
        return value

    return {}


def evaluate_sample(
    sample: dict[str, Any],
) -> dict[str, Any]:
    quality = get_dict(
        sample,
        "quality",
    )

    closed_loop = get_dict(
        sample,
        "closed_loop_quality",
    )

    teacher_label_valid = bool(
        quality.get(
            "valid_for_training"
        )
    )

    command_status = closed_loop.get(
        "command_terminal_status"
    )

    plan_state = closed_loop.get(
        "plan_terminal_state"
    )

    plan_reason = closed_loop.get(
        "plan_terminal_reason"
    )

    run_status = closed_loop.get(
        "run_status"
    )

    scenario_acceptance = closed_loop.get(
        "scenario_acceptance_passed"
    )

    safety_override_frames = (
        closed_loop.get(
            "safety_override_frames"
        )
        or 0
    )

    closed_loop_success = (
        command_status == "SUCCEEDED"
        and plan_state == "SUCCEEDED"
    )

    safety_override_observed = (
        safety_override_frames > 0
    )

    run_status_inconsistent = (
        run_status != "SUCCEEDED"
        and closed_loop_success
        and scenario_acceptance is True
    )

    quarantine_reasons: list[str] = []

    if not teacher_label_valid:
        quarantine_reasons.append(
            "TEACHER_LABEL_INVALID"
        )

    if not closed_loop_success:
        quarantine_reasons.append(
            "CLOSED_LOOP_COMMAND_FAILED"
        )

    if command_status == "FAILED":
        quarantine_reasons.append(
            "COMMAND_TERMINAL_FAILED"
        )

    if plan_state == "FAILED":
        quarantine_reasons.append(
            "PLAN_TERMINAL_FAILED"
        )

    if plan_reason:
        if plan_state == "FAILED":
            quarantine_reasons.append(
                "PLAN_FAILURE_REASON:"
                + str(plan_reason)
            )

    train_eligible = (
        teacher_label_valid
        and closed_loop_success
    )

    if train_eligible:
        policy_class = "TRAIN_ELIGIBLE"
    else:
        policy_class = "QUARANTINED_HARD_CASE"

    return {
        "policy_version": POLICY_VERSION,

        "teacher_label_valid": (
            teacher_label_valid
        ),

        "closed_loop_success": (
            closed_loop_success
        ),

        "scenario_acceptance_passed": (
            scenario_acceptance
        ),

        "run_status": (
            run_status
        ),

        "command_terminal_status": (
            command_status
        ),

        "plan_terminal_state": (
            plan_state
        ),

        "plan_terminal_reason": (
            plan_reason
        ),

        "safety_override_observed": (
            safety_override_observed
        ),

        "safety_override_frames": (
            safety_override_frames
        ),

        "run_status_inconsistent": (
            run_status_inconsistent
        ),

        "train_eligible": (
            train_eligible
        ),

        "policy_class": (
            policy_class
        ),

        "quarantine_reasons": (
            quarantine_reasons
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input",
        required=True,
    )

    parser.add_argument(
        "--output-all",
        required=True,
    )

    parser.add_argument(
        "--output-train-eligible",
        required=True,
    )

    parser.add_argument(
        "--output-hard-cases",
        required=True,
    )

    args = parser.parse_args()

    input_path = Path(
        args.input
    )

    rows = read_jsonl(
        input_path
    )

    all_rows: list[
        dict[str, Any]
    ] = []

    train_eligible_rows: list[
        dict[str, Any]
    ] = []

    hard_case_rows: list[
        dict[str, Any]
    ] = []

    policy_counts = Counter()

    safety_override_count = 0
    inconsistent_run_count = 0

    quarantine_reason_counts = Counter()

    for original in rows:
        sample = copy.deepcopy(
            original
        )

        policy = evaluate_sample(
            sample
        )

        sample["training_policy"] = (
            policy
        )

        all_rows.append(
            sample
        )

        policy_counts[
            policy["policy_class"]
        ] += 1

        if policy[
            "safety_override_observed"
        ]:
            safety_override_count += 1

        if policy[
            "run_status_inconsistent"
        ]:
            inconsistent_run_count += 1

        if policy[
            "train_eligible"
        ]:
            train_eligible_rows.append(
                sample
            )

        else:
            hard_case_rows.append(
                sample
            )

            for reason in policy[
                "quarantine_reasons"
            ]:
                quarantine_reason_counts[
                    reason
                ] += 1

    write_jsonl(
        Path(args.output_all),
        all_rows,
    )

    write_jsonl(
        Path(
            args.output_train_eligible
        ),
        train_eligible_rows,
    )

    write_jsonl(
        Path(
            args.output_hard_cases
        ),
        hard_case_rows,
    )

    print(
        f"TOTAL_RAW_TEACHER_SAMPLES={len(rows)}"
    )

    print(
        "TRAIN_ELIGIBLE_SAMPLES="
        f"{len(train_eligible_rows)}"
    )

    print(
        "QUARANTINED_HARD_CASES="
        f"{len(hard_case_rows)}"
    )

    print(
        "SAFETY_OVERRIDE_SAMPLES="
        f"{safety_override_count}"
    )

    print(
        "RUN_STATUS_INCONSISTENT_BUT_COMMAND_SUCCESS="
        f"{inconsistent_run_count}"
    )

    print()
    print("POLICY_CLASSES")

    for key, value in sorted(
        policy_counts.items()
    ):
        print(
            f"{key}={value}"
        )

    print()
    print("QUARANTINE_REASONS")

    if quarantine_reason_counts:
        for key, value in sorted(
            quarantine_reason_counts.items()
        ):
            print(
                f"{key}={value}"
            )
    else:
        print(
            "NONE"
        )

    print()
    print("HARD_CASES")

    if hard_case_rows:
        for sample in hard_case_rows:
            metadata = (
                sample.get(
                    "metadata"
                )
                or {}
            )

            policy = (
                sample.get(
                    "training_policy"
                )
                or {}
            )

            print(
                "sample_id="
                + str(
                    sample.get(
                        "sample_id"
                    )
                )
                + " scenario="
                + str(
                    metadata.get(
                        "scenario_id"
                    )
                )
                + " command_id="
                + str(
                    metadata.get(
                        "command_id"
                    )
                )
                + " reasons="
                + ",".join(
                    policy.get(
                        "quarantine_reasons"
                    )
                    or []
                )
            )
    else:
        print(
            "NONE"
        )

    print()
    print(
        "TRAINING_POLICY_VALIDATION=PASS"
    )


if __name__ == "__main__":
    main()
