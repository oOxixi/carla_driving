from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INPUT = (
    ROOT
    / "CARLA-Language-Benchmark"
    / "datasets"
    / "final_benchmark"
    / "CARLA_language_benchmark_v1_normalized.json"
)

DEFAULT_OUTPUT_DIR = (
    ROOT
    / "CARLA-Language-Benchmark"
    / "datasets"
    / "splits"
    / "group1_task3_v1"
)

DEFAULT_REPORT = (
    ROOT
    / "artifacts"
    / "group1_task3"
    / "split_audit.json"
)

SPLIT_NAMES = ("train", "val", "test")
DEFAULT_RATIOS = {
    "train": 0.70,
    "val": 0.15,
    "test": 0.15,
}

# 这些字段通常是运行时实例编号，不应决定“场景类型”。
VOLATILE_SCENE_KEYS = {
    "id",
    "track_id",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "按模板、场景和源 seed 的连通分组划分 CARLA 语言数据集，"
            "并自动检查重复、标签冲突和跨 split 泄漏。"
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"输入 JSON 文件，默认：{DEFAULT_INPUT}",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"train/val/test 输出目录，默认：{DEFAULT_OUTPUT_DIR}",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT,
        help=f"审计报告路径，默认：{DEFAULT_REPORT}",
    )
    parser.add_argument(
        "--split-seed",
        type=int,
        default=20260728,
        help="只用于让分配过程可复现；它不是数据来源 seed，默认：20260728",
    )
    parser.add_argument(
        "--train-ratio",
        type=float,
        default=DEFAULT_RATIOS["train"],
    )
    parser.add_argument(
        "--val-ratio",
        type=float,
        default=DEFAULT_RATIOS["val"],
    )
    parser.add_argument(
        "--test-ratio",
        type=float,
        default=DEFAULT_RATIOS["test"],
    )
    parser.add_argument(
        "--require-source-seed",
        action="store_true",
        help="若数据中不存在源 seed 字段，则以非零状态退出。",
    )
    return parser.parse_args()


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    normalized = unicodedata.normalize("NFKC", value)
    normalized = " ".join(normalized.split())
    return normalized.strip().lower()


def normalize_scene_value(value: Any) -> Any:
    """递归标准化场景数据，移除易变化的实例编号。"""

    if isinstance(value, dict):
        return {
            key: normalize_scene_value(item)
            for key, item in sorted(value.items())
            if key not in VOLATILE_SCENE_KEYS
        }

    if isinstance(value, list):
        normalized_items = [normalize_scene_value(item) for item in value]
        return sorted(normalized_items, key=canonical_json)

    return value


def make_template_key(record: dict[str, Any], index: int) -> str:
    template = normalize_text(record.get("template"))

    if template:
        return template

    # 缺失模板的数据不能全部并成同一组。
    return f"missing_template:{index}"


def make_scene_key(record: dict[str, Any], index: int) -> str:
    payload = {
        "scene_generator": record.get("scene_generator"),
        "scene_constraints": normalize_scene_value(
            record.get("scene_constraints", {})
        ),
    }

    if not payload["scene_generator"] and not payload["scene_constraints"]:
        return f"missing_scene:{index}"

    return sha256_text(canonical_json(payload))


def make_duplicate_key(record: dict[str, Any]) -> str:
    """
    检查“内容完全相同、仅 id 不同”的重复记录。
    """

    payload = {
        key: value
        for key, value in record.items()
        if key != "id"
    }
    return sha256_text(canonical_json(payload))


def make_input_key(record: dict[str, Any], index: int) -> str:
    """
    标签冲突检查的输入签名：
    同一模板、变量和场景输入，不应对应不同标签。
    """

    payload = {
        "template": make_template_key(record, index),
        "variables": record.get("variables", {}),
        "scene_generator": record.get("scene_generator"),
        "scene_constraints": normalize_scene_value(
            record.get("scene_constraints", {})
        ),
    }
    return sha256_text(canonical_json(payload))


def make_label_key(record: dict[str, Any]) -> str:
    payload = {
        "semantic_intent": record.get("semantic_intent"),
        "expected_action": record.get("expected_action"),
        "expected_parameters": record.get("expected_parameters", {}),
        "safety_policy": record.get("safety_policy"),
    }
    return canonical_json(payload)


def find_seed_entries(
    value: Any,
    prefix: str = "",
) -> list[tuple[str, str]]:
    """
    递归查找字段名中包含 seed 的字段，返回：
    (字段路径, 规范化后的字段值)
    """

    found: list[tuple[str, str]] = []

    if isinstance(value, dict):
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else key

            if "seed" in key.lower():
                found.append((path, canonical_json(item)))

            found.extend(find_seed_entries(item, path))

    elif isinstance(value, list):
        for item in value:
            found.extend(find_seed_entries(item, f"{prefix}[]"))

    return found


class UnionFind:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))
        self.component_size = [1] * size

    def find(self, item: int) -> int:
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, first: int, second: int) -> None:
        root_first = self.find(first)
        root_second = self.find(second)

        if root_first == root_second:
            return

        if self.component_size[root_first] < self.component_size[root_second]:
            root_first, root_second = root_second, root_first

        self.parent[root_second] = root_first
        self.component_size[root_first] += self.component_size[root_second]


def connect_same_key(
    union_find: UnionFind,
    key_to_indices: dict[str, list[int]],
) -> None:
    for indices in key_to_indices.values():
        if len(indices) < 2:
            continue

        first = indices[0]
        for index in indices[1:]:
            union_find.union(first, index)


def collect_components(
    union_find: UnionFind,
    record_count: int,
) -> list[list[int]]:
    components: dict[int, list[int]] = defaultdict(list)

    for index in range(record_count):
        components[union_find.find(index)].append(index)

    return list(components.values())


def assign_components(
    components: list[list[int]],
    record_count: int,
    ratios: dict[str, float],
    split_seed: int,
) -> tuple[dict[int, str], dict[str, int]]:
    """
    按连通分量整体分配，保证同模板、同场景、同源 seed 不跨 split。
    目标比例在分组约束允许的范围内尽量接近 70/15/15。
    """

    rng = random.Random(split_seed)
    shuffled = components[:]
    rng.shuffle(shuffled)
    shuffled.sort(key=len, reverse=True)

    targets = {
        split: record_count * ratios[split]
        for split in SPLIT_NAMES
    }
    counts = {split: 0 for split in SPLIT_NAMES}
    assignment: dict[int, str] = {}

    for component in shuffled:
        size = len(component)

        fitting_splits = [
            split
            for split in SPLIT_NAMES
            if counts[split] + size <= targets[split]
        ]

        if fitting_splits:
            # 优先选择“相对缺口”最大的 split。
            chosen = max(
                fitting_splits,
                key=lambda split: (
                    (targets[split] - counts[split]) / max(targets[split], 1.0),
                    targets[split] - counts[split],
                ),
            )
        else:
            # 所有 split 都会超目标时，选择相对溢出最小者。
            chosen = min(
                SPLIT_NAMES,
                key=lambda split: (
                    (counts[split] + size - targets[split])
                    / max(targets[split], 1.0),
                    counts[split],
                ),
            )

        counts[chosen] += size

        for index in component:
            assignment[index] = chosen

    return assignment, counts


def find_cross_split_leaks(
    key_to_indices: dict[str, list[int]],
    assignment: dict[int, str],
    limit: int = 20,
) -> tuple[int, list[dict[str, Any]]]:
    leak_count = 0
    examples: list[dict[str, Any]] = []

    for key, indices in key_to_indices.items():
        splits = sorted({assignment[index] for index in indices})

        if len(splits) <= 1:
            continue

        leak_count += 1

        if len(examples) < limit:
            examples.append(
                {
                    "key": key,
                    "splits": splits,
                    "record_indices": indices[:20],
                }
            )

    return leak_count, examples


def duplicate_summary(
    duplicate_to_indices: dict[str, list[int]],
    records: list[dict[str, Any]],
    limit: int = 20,
) -> dict[str, Any]:
    groups = [
        (key, indices)
        for key, indices in duplicate_to_indices.items()
        if len(indices) > 1
    ]
    groups.sort(key=lambda item: len(item[1]), reverse=True)

    return {
        "group_count": len(groups),
        "extra_record_count": sum(len(indices) - 1 for _, indices in groups),
        "examples": [
            {
                "fingerprint": key,
                "count": len(indices),
                "record_ids": [
                    records[index].get("id")
                    for index in indices[:20]
                ],
            }
            for key, indices in groups[:limit]
        ],
    }


def label_conflict_summary(
    input_to_indices: dict[str, list[int]],
    records: list[dict[str, Any]],
    limit: int = 20,
) -> dict[str, Any]:
    conflicts: list[dict[str, Any]] = []

    for input_key, indices in input_to_indices.items():
        label_to_indices: dict[str, list[int]] = defaultdict(list)

        for index in indices:
            label_to_indices[make_label_key(records[index])].append(index)

        if len(label_to_indices) <= 1:
            continue

        conflicts.append(
            {
                "input_fingerprint": input_key,
                "label_variant_count": len(label_to_indices),
                "variants": [
                    {
                        "label": json.loads(label_key),
                        "record_ids": [
                            records[index].get("id")
                            for index in variant_indices[:20]
                        ],
                    }
                    for label_key, variant_indices
                    in list(label_to_indices.items())[:10]
                ],
            }
        )

    return {
        "group_count": len(conflicts),
        "examples": conflicts[:limit],
    }


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(value, file, ensure_ascii=False, indent=2)
        file.write("\n")


def build_index(
    keys: Iterable[str],
) -> dict[str, list[int]]:
    result: dict[str, list[int]] = defaultdict(list)

    for index, key in enumerate(keys):
        result[key].append(index)

    return result


def validate_ratios(ratios: dict[str, float]) -> None:
    for split, ratio in ratios.items():
        if ratio <= 0.0:
            raise ValueError(f"{split} ratio 必须大于 0，当前为 {ratio}")

    total = sum(ratios.values())

    if abs(total - 1.0) > 1e-9:
        raise ValueError(
            f"train/val/test 比例之和必须为 1，当前为 {total}"
        )


def main() -> int:
    args = parse_args()

    ratios = {
        "train": args.train_ratio,
        "val": args.val_ratio,
        "test": args.test_ratio,
    }
    validate_ratios(ratios)

    input_path = args.input.resolve()
    output_dir = args.output_dir.resolve()
    report_path = args.report.resolve()

    if not input_path.exists():
        raise FileNotFoundError(f"找不到输入数据：{input_path}")

    with input_path.open("r", encoding="utf-8") as file:
        records = json.load(file)

    if not isinstance(records, list):
        raise TypeError("输入 JSON 顶层必须是列表")

    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise TypeError(f"第 {index} 条记录不是 JSON 对象")

    record_count = len(records)

    template_keys = [
        make_template_key(record, index)
        for index, record in enumerate(records)
    ]
    scene_keys = [
        make_scene_key(record, index)
        for index, record in enumerate(records)
    ]
    duplicate_keys = [
        make_duplicate_key(record)
        for record in records
    ]
    input_keys = [
        make_input_key(record, index)
        for index, record in enumerate(records)
    ]

    template_to_indices = build_index(template_keys)
    scene_to_indices = build_index(scene_keys)
    duplicate_to_indices = build_index(duplicate_keys)
    input_to_indices = build_index(input_keys)

    seed_to_indices: dict[str, list[int]] = defaultdict(list)
    seed_path_counts: Counter[str] = Counter()

    for index, record in enumerate(records):
        for path, value in find_seed_entries(record):
            seed_path_counts[path] += 1
            seed_to_indices[f"{path}={value}"].append(index)

    union_find = UnionFind(record_count)

    # 四类约束都整体绑定；重复记录即使存在，也不能被分到不同 split。
    connect_same_key(union_find, template_to_indices)
    connect_same_key(union_find, scene_to_indices)
    connect_same_key(union_find, seed_to_indices)
    connect_same_key(union_find, duplicate_to_indices)

    components = collect_components(union_find, record_count)

    assignment, split_counts = assign_components(
        components=components,
        record_count=record_count,
        ratios=ratios,
        split_seed=args.split_seed,
    )

    split_records = {
        split: [
            record
            for index, record in enumerate(records)
            if assignment[index] == split
        ]
        for split in SPLIT_NAMES
    }

    split_paths = {
        split: output_dir / f"{split}.json"
        for split in SPLIT_NAMES
    }

    for split in SPLIT_NAMES:
        write_json(split_paths[split], split_records[split])

    manifest_path = output_dir / "split_manifest.json"
    manifest = {
        "source_path": str(input_path),
        "source_sha256": sha256_file(input_path),
        "split_seed": args.split_seed,
        "note": (
            "split_seed 仅用于可复现分配，不等同于数据来源 seed。"
        ),
        "target_ratios": ratios,
        "record_count": record_count,
        "splits": {
            split: {
                "path": str(split_paths[split]),
                "count": split_counts[split],
                "ratio": (
                    split_counts[split] / record_count
                    if record_count
                    else 0.0
                ),
                "record_ids": [
                    record.get("id")
                    for record in split_records[split]
                ],
            }
            for split in SPLIT_NAMES
        },
    }
    write_json(manifest_path, manifest)

    template_leaks, template_leak_examples = find_cross_split_leaks(
        template_to_indices,
        assignment,
    )
    scene_leaks, scene_leak_examples = find_cross_split_leaks(
        scene_to_indices,
        assignment,
    )
    seed_leaks, seed_leak_examples = find_cross_split_leaks(
        seed_to_indices,
        assignment,
    )
    duplicate_leaks, duplicate_leak_examples = find_cross_split_leaks(
        duplicate_to_indices,
        assignment,
    )

    duplicates = duplicate_summary(
        duplicate_to_indices,
        records,
    )
    label_conflicts = label_conflict_summary(
        input_to_indices,
        records,
    )

    source_seed_status = (
        "available"
        if seed_path_counts
        else "missing"
    )

    leakage_total = (
        template_leaks
        + scene_leaks
        + seed_leaks
        + duplicate_leaks
    )

    data_quality_error_total = (
        duplicates["group_count"]
        + label_conflicts["group_count"]
    )

    if leakage_total:
        overall_status = "failed_cross_split_leakage"
    elif data_quality_error_total:
        overall_status = "failed_data_quality"
    elif not seed_path_counts and args.require_source_seed:
        overall_status = "blocked_missing_source_seed"
    elif not seed_path_counts:
        overall_status = "passed_with_documented_seed_limitation"
    else:
        overall_status = "passed"


    report = {
        "overall_status": overall_status,
        "source": {
            "path": str(input_path),
            "sha256": sha256_file(input_path),
            "record_count": record_count,
        },
        "configuration": {
            "split_seed": args.split_seed,
            "target_ratios": ratios,
            "scene_signature_ignored_keys": sorted(VOLATILE_SCENE_KEYS),
        },
        "grouping": {
            "template_group_count": len(template_to_indices),
            "scene_group_count": len(scene_to_indices),
            "source_seed_group_count": len(seed_to_indices),
            "connected_component_count": len(components),
            "largest_component_size": max(
                (len(component) for component in components),
                default=0,
            ),
        },
        "source_seed": {
            "status": source_seed_status,
            "field_paths": dict(seed_path_counts),
            "require_source_seed": args.require_source_seed,
            "explanation": (
                "未发现源 seed 字段，因此当前只能证明模板和场景隔离；"
                "split_seed 只能保证划分可复现，不能替代源 seed 隔离。"
                if not seed_path_counts
                else "已发现源 seed 字段，并纳入连通分组。"
            ),
        },
        "splits": {
            split: {
                "path": str(split_paths[split]),
                "sha256": sha256_file(split_paths[split]),
                "count": split_counts[split],
                "actual_ratio": (
                    split_counts[split] / record_count
                    if record_count
                    else 0.0
                ),
                "target_ratio": ratios[split],
            }
            for split in SPLIT_NAMES
        },
        "duplicate_check": duplicates,
        "label_conflict_check": label_conflicts,
        "cross_split_leakage": {
            "total_group_count": leakage_total,
            "template": {
                "group_count": template_leaks,
                "examples": template_leak_examples,
            },
            "scene": {
                "group_count": scene_leaks,
                "examples": scene_leak_examples,
            },
            "source_seed": {
                "group_count": seed_leaks,
                "examples": seed_leak_examples,
            },
            "duplicate_fingerprint": {
                "group_count": duplicate_leaks,
                "examples": duplicate_leak_examples,
            },
        },
        "outputs": {
            "manifest": str(manifest_path),
            "report": str(report_path),
        },
    }

    write_json(report_path, report)

    print("=" * 76)
    print("GROUP 1 TASK 3 — GROUPED TRAIN / VAL / TEST SPLIT")
    print("=" * 76)
    print(f"Source records:        {record_count}")
    print(f"Connected components:  {len(components)}")
    print(f"Source seed status:     {source_seed_status}")
    print()

    for split in SPLIT_NAMES:
        actual_ratio = (
            split_counts[split] / record_count
            if record_count
            else 0.0
        )
        print(
            f"{split:>5}: {split_counts[split]:5d} "
            f"({actual_ratio:7.2%}, target={ratios[split]:.2%})"
        )

    print()
    print(f"Duplicate groups:       {duplicates['group_count']}")
    print(f"Label conflict groups:  {label_conflicts['group_count']}")
    print(f"Cross-split leak groups:{leakage_total:5d}")
    print(f"Overall status:         {overall_status}")
    print()
    print(f"Manifest: {manifest_path}")
    print(f"Report:   {report_path}")
    print("=" * 76)

    if leakage_total:
        return 2

    if data_quality_error_total:
        return 2

    if args.require_source_seed and not seed_path_counts:
        return 3

    return 0


if __name__ == "__main__":
    sys.exit(main())
