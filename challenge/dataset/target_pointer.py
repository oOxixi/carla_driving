#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


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
                    f"{path}:{line_no}: row is not object"
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

    with path.open(
        "w",
        encoding="utf-8",
    ) as f:
        for row in rows:
            f.write(
                json.dumps(
                    row,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                + "\n"
            )


def build_target_index(
    targets: Any,
    top_k: int,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    if not isinstance(targets, list):
        targets = []

    selected = []

    for item in targets[:top_k]:
        if isinstance(item, dict):
            selected.append(item)

    mapping: dict[str, int] = {}

    for index, target in enumerate(selected):
        target_id = target.get("target_id")

        if isinstance(target_id, str):
            mapping[target_id] = index

    return selected, mapping


def encode_step(
    step: dict[str, Any],
    target_map: dict[str, int],
    no_target_index: int,
) -> dict[str, Any]:
    target = step.get("target")

    target_id = None

    if isinstance(target, dict):
        target_id = target.get("target_id")

    if target_id is None:
        return {
            "step_id": step.get("step_id"),
            "behavior": step.get("behavior"),
            "target_id": None,
            "target_pointer": no_target_index,
            "target_pointer_status": "NO_TARGET",
        }

    if not isinstance(target_id, str):
        return {
            "step_id": step.get("step_id"),
            "behavior": step.get("behavior"),
            "target_id": target_id,
            "target_pointer": None,
            "target_pointer_status": "INVALID_TARGET_ID",
        }

    if target_id in target_map:
        return {
            "step_id": step.get("step_id"),
            "behavior": step.get("behavior"),
            "target_id": target_id,
            "target_pointer": target_map[target_id],
            "target_pointer_status": "MAPPED",
        }

    return {
        "step_id": step.get("step_id"),
        "behavior": step.get("behavior"),
        "target_id": target_id,
        "target_pointer": None,
        "target_pointer_status": "TARGET_OUTSIDE_TOPK",
    }


def process_sample(
    sample: dict[str, Any],
    top_k: int,
) -> dict[str, Any]:
    model_request = sample.get("model_request") or {}
    teacher_plan = sample.get("teacher_plan") or {}

    targets = model_request.get("targets")

    selected_targets, target_map = build_target_index(
        targets,
        top_k,
    )

    no_target_index = top_k

    steps = teacher_plan.get("steps")

    if not isinstance(steps, list):
        steps = []

    encoded_steps = []

    outside_topk = False
    invalid_target = False

    for step in steps:
        if not isinstance(step, dict):
            continue

        encoded = encode_step(
            step,
            target_map,
            no_target_index,
        )

        if (
            encoded["target_pointer_status"]
            == "TARGET_OUTSIDE_TOPK"
        ):
            outside_topk = True

        if (
            encoded["target_pointer_status"]
            == "INVALID_TARGET_ID"
        ):
            invalid_target = True

        encoded_steps.append(encoded)

    sample["student_targets"] = {
        "target_top_k": top_k,
        "no_target_index": no_target_index,
        "num_pointer_classes": top_k + 1,
        "candidate_order_policy": (
            "PRESERVE_MODEL_REQUEST_ORDER"
        ),
        "selected_candidate_target_ids": [
            item.get("target_id")
            for item in selected_targets
        ],
        "steps": encoded_steps,
        "target_outside_topk": outside_topk,
        "invalid_target_id": invalid_target,
    }

    return sample


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input",
        required=True,
    )

    parser.add_argument(
        "--output",
        required=True,
    )

    parser.add_argument(
        "--top-k",
        type=int,
        default=8,
    )

    args = parser.parse_args()

    if args.top_k <= 0:
        raise SystemExit(
            "--top-k must be > 0"
        )

    rows = read_jsonl(
        Path(args.input)
    )

    output = []

    outside_topk = 0
    no_target_steps = 0
    mapped_steps = 0

    for sample in rows:
        sample = process_sample(
            sample,
            args.top_k,
        )

        for step in (
            sample.get("student_targets", {})
            .get("steps", [])
        ):
            status = step.get(
                "target_pointer_status"
            )

            if status == "TARGET_OUTSIDE_TOPK":
                outside_topk += 1

            elif status == "NO_TARGET":
                no_target_steps += 1

            elif status == "MAPPED":
                mapped_steps += 1

        output.append(sample)

    write_jsonl(
        Path(args.output),
        output,
    )

    print(f"SAMPLES={len(output)}")
    print(f"TOP_K={args.top_k}")
    print(
        f"NO_TARGET_INDEX={args.top_k}"
    )
    print(
        f"MAPPED_TARGET_STEPS={mapped_steps}"
    )
    print(
        f"NO_TARGET_STEPS={no_target_steps}"
    )
    print(
        f"TARGET_OUTSIDE_TOPK_STEPS={outside_topk}"
    )

    if outside_topk > 0:
        print(
            "TARGET_POINTER_VALIDATION=FAIL"
        )
        raise SystemExit(2)

    print(
        "TARGET_POINTER_VALIDATION=PASS"
    )


if __name__ == "__main__":
    main()
