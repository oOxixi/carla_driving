from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


DATA_PATH = Path(
    "CARLA-Language-Benchmark"
    "/datasets"
    "/final_benchmark"
    "/CARLA_language_benchmark_v1_normalized.json"
)

INTERESTING_KEYWORDS = (
    "seed",
    "scene",
    "scenario",
    "town",
    "map",
    "route",
    "weather",
)


def canonical_json(value: Any) -> str:
    """Convert a value to a stable JSON string for counting."""
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def walk_values(value: Any, path: str = ""):
    """
    Recursively yield normalized field paths and scalar values.

    List indices are represented by [] so that:
    actors[0].class
    actors[1].class

    are both counted as:
    actors[].class
    """
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            yield from walk_values(child, child_path)

    elif isinstance(value, list):
        list_path = f"{path}[]"
        for child in value:
            yield from walk_values(child, list_path)

    else:
        yield path, value


def describe_field(records: list[dict[str, Any]], field: str) -> None:
    values = [
        canonical_json(record.get(field))
        for record in records
        if field in record
    ]

    counts = Counter(values)

    print(f"\nField: {field}")
    print(f"  Present: {len(values)}/{len(records)}")
    print(f"  Unique values: {len(counts)}")

    if counts:
        print(f"  Largest group: {counts.most_common(1)[0][1]}")
        print("  Most common values:")

        for value, count in counts.most_common(5):
            preview = value
            if len(preview) > 120:
                preview = preview[:117] + "..."

            print(f"    count={count:4d} value={preview}")


def main() -> None:
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATA_PATH.resolve()}"
        )

    with DATA_PATH.open("r", encoding="utf-8") as file:
        records = json.load(file)

    if not isinstance(records, list):
        raise TypeError(
            f"Expected a JSON list, got {type(records).__name__}"
        )

    if not all(isinstance(record, dict) for record in records):
        raise TypeError("Every dataset item must be a JSON object.")

    print("=" * 72)
    print("TASK 3 DATASET AUDIT")
    print("=" * 72)
    print(f"Dataset path: {DATA_PATH.resolve()}")
    print(f"Dataset records: {len(records)}")

    # ---------------------------------------------------------
    # 1. Check top-level field coverage
    # ---------------------------------------------------------
    top_level_presence: Counter[str] = Counter()

    for record in records:
        top_level_presence.update(record.keys())

    print("\n" + "=" * 72)
    print("TOP-LEVEL FIELD COVERAGE")
    print("=" * 72)

    for field, count in sorted(top_level_presence.items()):
        missing = len(records) - count
        print(
            f"{field:24s} present={count:5d} missing={missing:5d}"
        )

    # ---------------------------------------------------------
    # 2. Inspect likely grouping and label fields
    # ---------------------------------------------------------
    print("\n" + "=" * 72)
    print("IMPORTANT FIELD STATISTICS")
    print("=" * 72)

    fields_to_check = [
        "id",
        "category",
        "template",
        "semantic_intent",
        "scene_generator",
        "scene_constraints",
        "expected_action",
        "expected_parameters",
        "safety_policy",
    ]

    for field in fields_to_check:
        describe_field(records, field)

    # ---------------------------------------------------------
    # 3. Search recursively for seed/scene-related fields
    # ---------------------------------------------------------
    interesting_paths: dict[str, list[Any]] = defaultdict(list)
    seed_text_matches: list[tuple[str, str, str]] = []

    seed_pattern = re.compile(
        r"(?i)(?:^|[_\-\s])seed[_\-\s]*(\d+)"
    )

    for record_index, record in enumerate(records):
        record_id = str(record.get("id", record_index))

        for path, value in walk_values(record):
            path_lower = path.lower()

            if any(
                keyword in path_lower
                for keyword in INTERESTING_KEYWORDS
            ):
                interesting_paths[path].append(value)

            if isinstance(value, str):
                match = seed_pattern.search(value)

                if match:
                    seed_text_matches.append(
                        (record_id, path, match.group(1))
                    )

    print("\n" + "=" * 72)
    print("SEED / SCENE / ROUTE RELATED PATHS")
    print("=" * 72)

    if not interesting_paths:
        print("No related field paths were found.")
    else:
        for path in sorted(interesting_paths):
            values = interesting_paths[path]
            normalized_values = Counter(
                canonical_json(value) for value in values
            )

            print(
                f"{path:45s} "
                f"present={len(values):5d} "
                f"unique={len(normalized_values):5d}"
            )

    print("\n" + "=" * 72)
    print("SEED-LIKE VALUES FOUND INSIDE STRINGS")
    print("=" * 72)
    print(f"Number of matches: {len(seed_text_matches)}")

    for record_id, path, seed in seed_text_matches[:20]:
        print(
            f"record={record_id} path={path} seed={seed}"
        )

    if len(seed_text_matches) > 20:
        print(
            f"... {len(seed_text_matches) - 20} more matches omitted"
        )

    # ---------------------------------------------------------
    # 4. Examine candidate template and scene group sizes
    # ---------------------------------------------------------
    template_groups: Counter[str] = Counter()
    scene_generator_groups: Counter[str] = Counter()
    scene_signature_groups: Counter[str] = Counter()

    for record in records:
        template_key = canonical_json(record.get("template"))
        scene_generator_key = canonical_json(
            record.get("scene_generator")
        )

        # Candidate scene signature:
        # generator + complete scene constraints.
        scene_signature = canonical_json(
            {
                "scene_generator": record.get("scene_generator"),
                "scene_constraints": record.get("scene_constraints"),
            }
        )

        template_groups[template_key] += 1
        scene_generator_groups[scene_generator_key] += 1
        scene_signature_groups[scene_signature] += 1

    print("\n" + "=" * 72)
    print("CANDIDATE GROUP SIZES")
    print("=" * 72)

    print(
        "Template groups:"
        f" unique={len(template_groups)},"
        f" largest={template_groups.most_common(1)[0][1]}"
    )

    print(
        "Scene-generator groups:"
        f" unique={len(scene_generator_groups)},"
        f" largest={scene_generator_groups.most_common(1)[0][1]}"
    )

    print(
        "Scene-signature groups:"
        f" unique={len(scene_signature_groups)},"
        f" largest={scene_signature_groups.most_common(1)[0][1]}"
    )

    print("\nAudit completed successfully.")


if __name__ == "__main__":
    main()
