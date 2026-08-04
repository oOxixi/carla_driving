from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


EXPECTED_RECORDS = 6192
VALID_ACTIONS = {
    "START",
    "KEEP_LANE",
    "TURN_LEFT",
    "TURN_RIGHT",
    "CHANGE_LANE_LEFT",
    "CHANGE_LANE_RIGHT",
    "SET_SPEED",
    "STOP",
    "EMERGENCY_STOP",
    "AVOID_OBJECT",
    "REQUEST_CONFIRMATION",
}
REQUIRED_FIELDS = [
    "id",
    "category",
    "template",
    "variables",
    "semantic_intent",
    "scene_generator",
    "scene_constraints",
    "expected_action",
    "expected_parameters",
    "safety_policy",
]


def audit_dataset(path: Path) -> dict[str, object]:
    data_path = Path(path)
    raw_data = data_path.read_bytes()
    data = json.loads(raw_data)
    errors: list[dict[str, object]] = []
    ids: set[object] = set()
    category: Counter[object] = Counter()
    actions: Counter[object] = Counter()

    for item in data:
        identifier = item.get("id")
        if identifier in ids:
            errors.append({"id": identifier, "error": "duplicate_id"})
        ids.add(identifier)

        for field in REQUIRED_FIELDS:
            if field not in item:
                errors.append({"id": identifier, "error": "missing_field", "field": field})

        action = item.get("expected_action")
        actions[action] += 1
        if action not in VALID_ACTIONS:
            errors.append({"id": identifier, "error": "invalid_action", "value": action})
        category[item.get("category")] += 1

    if len(data) != EXPECTED_RECORDS:
        errors.append(
            {
                "error": "record_count_mismatch",
                "expected": EXPECTED_RECORDS,
                "actual": len(data),
            }
        )

    return {
        "input": str(data_path),
        "records": len(data),
        "errors": len(errors),
        "error_examples": errors[:50],
        "category_distribution": dict(category),
        "action_distribution": dict(actions),
        "sha256": hashlib.sha256(raw_data).hexdigest(),
    }


def write_checksum(data_path: Path, output_path: Path) -> None:
    report = audit_dataset(data_path)
    payload = {
        "path": "datasets/final_benchmark/CARLA_language_benchmark_v1_normalized.json",
        "records": report["records"],
        "sha256": report["sha256"],
    }
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit the frozen CARLA language benchmark.")
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--write-checksum", type=Path)
    parser.add_argument("--checksum", type=Path)
    args = parser.parse_args()

    report = audit_dataset(args.dataset)
    if args.checksum:
        expected = json.loads(args.checksum.read_text(encoding="utf-8"))
        actual = {
            "path": "datasets/final_benchmark/CARLA_language_benchmark_v1_normalized.json",
            "records": report["records"],
            "sha256": report["sha256"],
        }
        if expected != actual:
            examples = report["error_examples"]
            assert isinstance(examples, list)
            examples.append({"error": "checksum_mismatch"})
            report["errors"] = int(report["errors"]) + 1

    if args.write_checksum:
        write_checksum(args.dataset, args.write_checksum)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
