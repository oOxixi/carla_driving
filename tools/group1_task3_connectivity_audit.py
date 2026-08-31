from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

DATA_PATH = (
    ROOT
    / "CARLA-Language-Benchmark"
    / "datasets"
    / "final_benchmark"
    / "CARLA_language_benchmark_v1_normalized.json"
)

OUTPUT_PATH = (
    ROOT
    / "artifacts"
    / "group1_task3"
    / "connectivity_audit.json"
)

# 这些通常是运行时生成的实例编号，不适合作为“场景类型”的核心标识。
VOLATILE_SCENE_KEYS = {
    "id",
    "track_id",
}


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

        # 列表顺序可能只是生成顺序，因此排序后再参与场景签名。
        return sorted(
            normalized_items,
            key=lambda item: json.dumps(
                item,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ),
        )

    return value


def make_scene_key(record: dict[str, Any], index: int) -> str:
    """为一条数据生成稳定的场景签名。"""

    payload = {
        "scene_generator": record.get("scene_generator"),
        "scene_constraints": normalize_scene_value(
            record.get("scene_constraints", {})
        ),
    }

    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )

    # 场景信息完全为空时，不能把所有空场景误认为同一个场景。
    if not payload["scene_generator"] and not payload["scene_constraints"]:
        return f"missing_scene:{index}"

    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def make_template_key(record: dict[str, Any], index: int) -> str:
    template = record.get("template")

    if isinstance(template, str) and template.strip():
        return template.strip()

    return f"missing_template:{index}"


def find_seed_paths(value: Any, prefix: str = "") -> Counter[str]:
    """检查 JSON 中是否存在名称包含 seed 的字段。"""

    found: Counter[str] = Counter()

    if isinstance(value, dict):
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else key

            if "seed" in key.lower():
                found[path] += 1

            found.update(find_seed_paths(item, path))

    elif isinstance(value, list):
        for item in value:
            found.update(find_seed_paths(item, f"{prefix}[]"))

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


def main() -> None:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"找不到数据文件：{DATA_PATH}")

    with DATA_PATH.open("r", encoding="utf-8") as file:
        records = json.load(file)

    if not isinstance(records, list):
        raise TypeError("数据文件顶层必须是 JSON 列表")

    record_count = len(records)
    union_find = UnionFind(record_count)

    first_template_record: dict[str, int] = {}
    first_scene_record: dict[str, int] = {}

    template_counts: Counter[str] = Counter()
    scene_counts: Counter[str] = Counter()
    seed_paths: Counter[str] = Counter()

    template_keys: list[str] = []
    scene_keys: list[str] = []

    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise TypeError(f"第 {index} 条数据不是 JSON 对象")

        template_key = make_template_key(record, index)
        scene_key = make_scene_key(record, index)

        template_keys.append(template_key)
        scene_keys.append(scene_key)

        template_counts[template_key] += 1
        scene_counts[scene_key] += 1
        seed_paths.update(find_seed_paths(record))

        if template_key in first_template_record:
            union_find.union(index, first_template_record[template_key])
        else:
            first_template_record[template_key] = index

        if scene_key in first_scene_record:
            union_find.union(index, first_scene_record[scene_key])
        else:
            first_scene_record[scene_key] = index

    components: dict[int, list[int]] = defaultdict(list)

    for index in range(record_count):
        components[union_find.find(index)].append(index)

    component_summaries = []

    for component_indices in components.values():
        component_templates = {
            template_keys[index] for index in component_indices
        }
        component_scenes = {
            scene_keys[index] for index in component_indices
        }

        component_summaries.append(
            {
                "size": len(component_indices),
                "template_count": len(component_templates),
                "scene_count": len(component_scenes),
                "first_record_id": records[component_indices[0]].get("id"),
            }
        )

    component_summaries.sort(key=lambda item: item["size"], reverse=True)

    largest_size = component_summaries[0]["size"] if component_summaries else 0
    largest_ratio = largest_size / record_count if record_count else 0.0

    report = {
        "dataset_path": str(DATA_PATH),
        "record_count": record_count,
        "template_group_count": len(template_counts),
        "largest_template_group": max(template_counts.values(), default=0),
        "scene_group_count": len(scene_counts),
        "largest_scene_group": max(scene_counts.values(), default=0),
        "explicit_seed_paths": dict(seed_paths),
        "connected_component_count": len(component_summaries),
        "largest_component_size": largest_size,
        "largest_component_ratio": largest_ratio,
        "largest_components": component_summaries[:20],
        "scene_signature_rules": {
            "uses_scene_generator": True,
            "uses_scene_constraints": True,
            "ignored_keys": sorted(VOLATILE_SCENE_KEYS),
        },
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)

    print("=" * 70)
    print("GROUP 1 TASK 3 — CONNECTIVITY AUDIT")
    print("=" * 70)
    print(f"Dataset records:             {record_count}")
    print(f"Template groups:             {len(template_counts)}")
    print(f"Largest template group:      {max(template_counts.values(), default=0)}")
    print(f"Scene groups:                {len(scene_counts)}")
    print(f"Largest scene group:         {max(scene_counts.values(), default=0)}")
    print(f"Connected components:        {len(component_summaries)}")
    print(f"Largest component:           {largest_size}")
    print(f"Largest component ratio:     {largest_ratio:.2%}")

    print()
    print("Explicit seed fields:")

    if seed_paths:
        for path, count in seed_paths.most_common():
            print(f"  {path}: {count}")
    else:
        print("  NONE FOUND")

    print()
    print("Top connected components:")

    for number, component in enumerate(component_summaries[:15], start=1):
        print(
            f"  {number:02d}. size={component['size']:4d}, "
            f"templates={component['template_count']:4d}, "
            f"scenes={component['scene_count']:4d}, "
            f"first_id={component['first_record_id']}"
        )

    print()
    print(f"Report written to: {OUTPUT_PATH}")
    print("=" * 70)


if __name__ == "__main__":
    main()
