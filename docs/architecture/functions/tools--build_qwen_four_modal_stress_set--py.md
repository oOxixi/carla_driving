# build_qwen_four_modal_stress_set：功能记录

上级模块：[模块说明](../modules/support-tools.md) · 实现：[tools/build_qwen_four_modal_stress_set.py](../../../tools/build_qwen_four_modal_stress_set.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [维护工具的运行上下文和证据范围](environment-delivery.md)

## 功能职责与范围

Build an auditable four-modal Qwen stress set from real CARLA captures.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `_read_jsonl`

源码位置：[tools/build_qwen_four_modal_stress_set.py 第 34 行](../../../tools/build_qwen_four_modal_stress_set.py#L34)。类型：`FunctionDef`。

```python
_read_jsonl(path: Path) -> list[dict[str, Any]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_write_jsonl`

源码位置：[tools/build_qwen_four_modal_stress_set.py 第 45 行](../../../tools/build_qwen_four_modal_stress_set.py#L45)。类型：`FunctionDef`。

```python
_write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_sha256`

源码位置：[tools/build_qwen_four_modal_stress_set.py 第 52 行](../../../tools/build_qwen_four_modal_stress_set.py#L52)。类型：`FunctionDef`。

```python
_sha256(path: Path) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_split`

源码位置：[tools/build_qwen_four_modal_stress_set.py 第 60 行](../../../tools/build_qwen_four_modal_stress_set.py#L60)。类型：`FunctionDef`。

```python
_split(scene_id: str) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_target_bbox`

源码位置：[tools/build_qwen_four_modal_stress_set.py 第 72 行](../../../tools/build_qwen_four_modal_stress_set.py#L72)。类型：`FunctionDef`。

```python
_target_bbox(case: dict[str, Any]) -> list[float] | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_repair_legacy_target_semantics`

源码位置：[tools/build_qwen_four_modal_stress_set.py 第 86 行](../../../tools/build_qwen_four_modal_stress_set.py#L86)。类型：`FunctionDef`。

```python
_repair_legacy_target_semantics(case: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]
```

Repair the known adjacent-vs-far pedestrian label bug audibly.

Older CARLA collections fell back to a far-ahead waypoint when Town03 had
no usable adjacent lane, but still described every non-left pedestrian as
right-adjacent.  Preserve the captured target and relation, and correct the
language label instead of inventing an actor that is absent from the frame.

### `_transform_image`

源码位置：[tools/build_qwen_four_modal_stress_set.py 第 132 行](../../../tools/build_qwen_four_modal_stress_set.py#L132)。类型：`FunctionDef`。

```python
_transform_image(source: Path, destination: Path, variant: str, *, bbox: list[float] | None) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_mutate_detector`

源码位置：[tools/build_qwen_four_modal_stress_set.py 第 178 行](../../../tools/build_qwen_four_modal_stress_set.py#L178)。类型：`FunctionDef`。

```python
_mutate_detector(case: dict[str, Any], variant: str) -> tuple[dict[str, Any], dict[str, Any]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `build`

源码位置：[tools/build_qwen_four_modal_stress_set.py 第 259 行](../../../tools/build_qwen_four_modal_stress_set.py#L259)。类型：`FunctionDef`。

```python
build(collection_dir: Path, output_dir: Path) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[tools/build_qwen_four_modal_stress_set.py 第 422 行](../../../tools/build_qwen_four_modal_stress_set.py#L422)。类型：`FunctionDef`。

```python
main() -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `_read_jsonl` 调用：`ValueError`, `any`, `isinstance`, `json.loads`, `line.strip`, `path.read_text`, `path.read_text(encoding='utf-8').splitlines`.
- `_write_jsonl` 调用：`''.join`, `json.dumps`, `path.write_text`.
- `_sha256` 调用：`digest.hexdigest`, `digest.update`, `hashlib.sha256`, `iter`, `path.open`, `stream.read`.
- `_split` 调用：`hashlib.sha256`, `hashlib.sha256(scene_id.encode('utf-8')).digest`, `int.from_bytes`, `scene_id.encode`.
- `_target_bbox` 调用：`all`, `case.get`, `case.get('expected', {}).get`, `case.get('perception', {}).get`, `float`, `isinstance`, `item.get`, `len`.
- `_repair_legacy_target_semantics` 调用：`expected.get`, `isinstance`, `item.get`, `json.dumps`, `json.loads`, `next`, `relation.startswith`, `repaired.get`, `repaired.get('perception', {}).get`, `repaired.setdefault`, `str`, `target.get`.
- `_transform_image` 调用：`Image.open`, `ImageDraw.Draw`, `ImageDraw.Draw(image).rectangle`, `ImageEnhance.Brightness`, `ImageEnhance.Brightness(image).enhance`, `ImageEnhance.Contrast`, `ImageEnhance.Contrast(image).enhance`, `ImageFilter.Kernel`, `ValueError`, `_sha256`, `destination.parent.mkdir`, `image.filter`, `image.save`, `int`, `list`, `opened.convert`, `range`.
- `_mutate_detector` 调用：`ValueError`, `case.get`, `expected.get`, `float`, `isinstance`, `item.get`, `json.dumps`, `json.loads`, `len`, `max`, `min`, `next`, `objects.append`, `perception.setdefault`, `relation.startswith`, `round`, `same_explicit_target`, `str`, `target_object.get`, `target_relation.startswith`, `zip`.
- `build` 调用：`(output_dir / 'dataset_report.json').write_text`, `Counter`, `FileNotFoundError`, `ValueError`, `_mutate_detector`, `_read_jsonl`, `_repair_legacy_target_semantics`, `_sha256`, `_split`, `_target_bbox`, `_transform_image`, `_write_jsonl`, `all`, `bool`, `case.get`, `case.get('scene_state', {}).get`, `collection_dir.resolve`, `datetime.now`, `datetime.now(timezone.utc).isoformat`, `dict`, `float`, `json.dumps`, `len`, `lidar_destination.exists`, `lidar_summary.update`, `output_dir.resolve`, `output_images.mkdir`, `output_lidar.mkdir`, `perception.setdefault`, `rows.append`, `scenes_by_rgb.get`, `semantic_repairs.append`, `set`, `shutil.copy2`, `source_image.is_file`, `source_lidar.is_file`, `source_scene.get`, `str`, `variant.startswith`.
- `main` 调用：`argparse.ArgumentParser`, `build`, `json.dumps`, `parser.add_argument`, `parser.parse_args`, `print`.
- `same_explicit_target` 调用：`item.get`, `relation.startswith`, `str`, `target_relation.startswith`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `_mutate_detector`，第 202 行：`ValueError('detector_miss target is absent before mutation')`。
- `_read_jsonl`，第 41 行：`ValueError(f'{path} must contain JSON objects')`。
- `_transform_image`，第 156 行：`ValueError('partial_occlusion requires a target bbox')`。
- `build`，第 284 行：`ValueError(f"case has no matching scene: {case['case_id']}")`。
- `build`，第 288 行：`ValueError(f"scene {source_scene['scene_id']} has no raw LiDAR reference")`。
- `build`，第 293 行：`FileNotFoundError('source RGB/LiDAR file is missing')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 424 行：`parser.add_argument('--collection-dir', required=True, type=Path)`。
- 第 425 行：`parser.add_argument('--output-dir', required=True, type=Path)`。

## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [integration/tests/test_qwen_four_modal_stress_set.py](../../../integration/tests/test_qwen_four_modal_stress_set.py)
- [qwen_service/tests/test_stress_set_semantic_repair.py](../../../qwen_service/tests/test_stress_set_semantic_repair.py)
- [tools/build_detector_miss_supplement.py](../../../tools/build_detector_miss_supplement.py)
- [tools/build_four_modal_cases_v2.py](../../../tools/build_four_modal_cases_v2.py)

## 后续修改需要一起阅读

- [上级模块](../modules/support-tools.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `tools/build_qwen_four_modal_stress_set.py`

来源 SHA256：`1e6d5d6afb7ca9045bc01833c6a5ef628c32a093248d04c62917b53643e2e7ad`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 424 | `'--collection-dir'` | `required=True; type=Path` |
| 425 | `'--output-dir'` | `required=True; type=Path` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `_read_jsonl` / 41 | `not rows or any((not isinstance(row, dict) for row in rows))` | `raise ValueError(f'{path} must contain JSON objects')` |
| `_transform_image` / 156 | `NOT (variant == 'exposure_low') AND NOT (variant == 'exposure_high') AND NOT (variant == 'motion_blur') AND variant == 'partial_occlusion' AND bbox is None` | `raise ValueError('partial_occlusion requires a target bbox')` |
| `_mutate_detector` / 202 | `NOT (variant == 'detector_false_positive') AND variant == 'detector_miss' AND target_object is None` | `raise ValueError('detector_miss target is absent before mutation')` |
| `build` / 284 | `source_scene is None` | `raise ValueError(f"case has no matching scene: {case['case_id']}")` |
| `build` / 288 | `not source_lidar_ref` | `raise ValueError(f"scene {source_scene['scene_id']} has no raw LiDAR reference")` |
| `build` / 293 | `not source_image.is_file() or not source_lidar.is_file()` | `raise FileNotFoundError('source RGB/LiDAR file is missing')` |
