#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []

    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            if not line.strip():
                continue

            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"{path}:{line_no}: invalid JSON: {exc}"
                ) from exc

            if not isinstance(obj, dict):
                raise ValueError(
                    f"{path}:{line_no}: non-object row"
                )

            rows.append(obj)

    return rows


def validate_sample(sample: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if sample.get("dataset_schema_version") != "1.0":
        errors.append("DATASET_SCHEMA_VERSION")

    if not isinstance(sample.get("sample_id"), str):
        errors.append("SAMPLE_ID")

    metadata = sample.get("metadata")
    if not isinstance(metadata, dict):
        errors.append("METADATA")
        return errors

    model_request = sample.get("model_request")
    teacher_plan = sample.get("teacher_plan")

    if not isinstance(model_request, dict):
        errors.append("MODEL_REQUEST")
    else:
        if model_request.get("schema_version") != "1.0":
            errors.append("MODEL_REQUEST_SCHEMA_VERSION")

    if not isinstance(teacher_plan, dict):
        errors.append("TEACHER_PLAN")
    else:
        if teacher_plan.get("schema_version") != "2.0":
            errors.append("TEACHER_PLAN_SCHEMA_VERSION")

        if teacher_plan.get("plan_type") != "MANEUVER_SEQUENCE":
            errors.append("TEACHER_PLAN_TYPE")

        steps = teacher_plan.get("steps")
        if not isinstance(steps, list) or not (1 <= len(steps) <= 4):
            errors.append("TEACHER_PLAN_STEPS")

    if isinstance(model_request, dict) and isinstance(teacher_plan, dict):
        if model_request.get("request_id") != teacher_plan.get("request_id"):
            errors.append("REQUEST_ID_MISMATCH")

        if model_request.get("command_id") != teacher_plan.get("command_id"):
            errors.append("COMMAND_ID_MISMATCH")

    visual = sample.get("visual_input")
    if not isinstance(visual, dict):
        errors.append("VISUAL_INPUT")
    else:
        if visual.get("available") is not True:
            errors.append("RGB_UNAVAILABLE")

        digest = visual.get("rgb_sha256")
        if not isinstance(digest, str) or len(digest) != 64:
            errors.append("RGB_SHA256")

    grounding = sample.get("target_grounding")
    if not isinstance(grounding, dict):
        errors.append("TARGET_GROUNDING")
    elif grounding.get("valid") is not True:
        errors.append("TARGET_GROUNDING_INVALID")

    quality = sample.get("quality")
    if not isinstance(quality, dict):
        errors.append("QUALITY")
    elif quality.get("valid_for_training") is not True:
        errors.append("NOT_VALID_FOR_TRAINING")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset")
    args = parser.parse_args()

    path = Path(args.dataset)
    rows = read_jsonl(path)

    all_errors = []
    seen_ids = set()
    duplicate_ids = []

    classes = Counter()
    model_ids = Counter()
    scenarios = Counter()

    for index, sample in enumerate(rows):
        sid = sample.get("sample_id")

        if sid in seen_ids:
            duplicate_ids.append(sid)
        else:
            seen_ids.add(sid)

        errors = validate_sample(sample)
        if errors:
            all_errors.append(
                {
                    "index": index,
                    "sample_id": sid,
                    "errors": errors,
                }
            )

        sample_class = sample.get("sample_class", {})
        if isinstance(sample_class, dict):
            classes[str(sample_class.get("primary"))] += 1

        metadata = sample.get("metadata", {})
        if isinstance(metadata, dict):
            model_ids[str(metadata.get("teacher_model_id"))] += 1
            scenarios[str(metadata.get("scenario_id"))] += 1

    print(f"SAMPLES={len(rows)}")
    print(f"UNIQUE_SAMPLE_IDS={len(seen_ids)}")
    print(f"DUPLICATE_SAMPLE_IDS={len(duplicate_ids)}")
    print(f"INVALID_SAMPLES={len(all_errors)}")

    print("\nCLASSES")
    for k, v in classes.items():
        print(k, v)

    print("\nTEACHER_MODELS")
    for k, v in model_ids.items():
        print(k, v)

    print("\nSCENARIOS")
    for k, v in scenarios.items():
        print(k, v)

    if all_errors:
        print("\nERRORS")
        for item in all_errors[:50]:
            print(json.dumps(item, ensure_ascii=False))

        raise SystemExit(1)

    if duplicate_ids:
        print("\nDUPLICATES")
        for sid in duplicate_ids[:50]:
            print(sid)

        raise SystemExit(1)

    print("\nDATASET_VALIDATION=PASS")


if __name__ == "__main__":
    main()
