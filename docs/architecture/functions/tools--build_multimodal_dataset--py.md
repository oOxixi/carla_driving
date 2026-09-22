# build_multimodal_dataset：功能记录

上级模块：[模块说明](../modules/support-tools.md) · 实现：[tools/build_multimodal_dataset.py](../../../tools/build_multimodal_dataset.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [维护工具的运行上下文和证据范围](environment-delivery.md)

## 功能职责与范围

Build schema-v1 multimodal JSONL files from normalized capture records.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `deterministic_split`

源码位置：[tools/build_multimodal_dataset.py 第 44 行](../../../tools/build_multimodal_dataset.py#L44)。类型：`FunctionDef`。

```python
deterministic_split(sequence_id: str, scenario_id: str, seed: int, *, train_percent: int=70, val_percent: int=15) -> str
```

Assign an entire sequence/scenario/seed group without frame leakage.

### `load_capture_records`

源码位置：[tools/build_multimodal_dataset.py 第 64 行](../../../tools/build_multimodal_dataset.py#L64)。类型：`FunctionDef`。

```python
load_capture_records(path: Path) -> list[dict[str, Any]]
```

【load_capture_records】从参数、文件、环境或缓存解析维护工具的数据检查、生成、评测或证据处理所需输入；路径优先级、默认值和缺失处理以函数体为准，读取成功不自动证明内容身份正确。

### `build_dataset`

源码位置：[tools/build_multimodal_dataset.py 第 82 行](../../../tools/build_multimodal_dataset.py#L82)。类型：`FunctionDef`。

```python
build_dataset(capture_paths: Iterable[Path], *, dataset_root: Path, output_root: Path, defaults: Mapping[str, Any]) -> dict[str, Any]
```

【build_dataset】按函数体组合维护工具的数据检查、生成、评测或证据处理的中间对象或产物；输入筛选、排序、身份和失败项必须保留，生成成功不代表后续运行或评分门禁通过。

### `build_record`

源码位置：[tools/build_multimodal_dataset.py 第 158 行](../../../tools/build_multimodal_dataset.py#L158)。类型：`FunctionDef`。

```python
build_record(payload: Mapping[str, Any], *, dataset_root: Path, defaults: Mapping[str, Any]) -> dict[str, Any]
```

【build_record】生成或记录维护工具的数据检查、生成、评测或证据处理的文件/元数据；执行前要核对目标路径与覆盖行为，执行后以内容哈希、返回码和消费方复核，不能仅以文件存在判定通过。

### `_media_ref`

源码位置：[tools/build_multimodal_dataset.py 第 374 行](../../../tools/build_multimodal_dataset.py#L374)。类型：`FunctionDef`。

```python
_media_ref(value: object, dataset_root: Path) -> dict[str, Any] | None
```

【_media_ref】根据紧邻签名和函数体完成维护工具的数据检查、生成、评测或证据处理中的局部职责；返回、状态、副作用和异常以本页下方调用/raise记录为边界，名称本身不增加额外保证。

### `_objects`

源码位置：[tools/build_multimodal_dataset.py 第 401 行](../../../tools/build_multimodal_dataset.py#L401)。类型：`FunctionDef`。

```python
_objects(value: object) -> list[dict[str, Any]]
```

【_objects】根据紧邻签名和函数体完成维护工具的数据检查、生成、评测或证据处理中的局部职责；返回、状态、副作用和异常以本页下方调用/raise记录为边界，名称本身不增加额外保证。

### `_file_sha256`

源码位置：[tools/build_multimodal_dataset.py 第 427 行](../../../tools/build_multimodal_dataset.py#L427)。类型：`FunctionDef`。

```python
_file_sha256(path: Path) -> str
```

【_file_sha256】根据紧邻签名和函数体完成维护工具的数据检查、生成、评测或证据处理中的局部职责；返回、状态、副作用和异常以本页下方调用/raise记录为边界，名称本身不增加额外保证。

### `_sha_text`

源码位置：[tools/build_multimodal_dataset.py 第 435 行](../../../tools/build_multimodal_dataset.py#L435)。类型：`FunctionDef`。

```python
_sha_text(value: object, name: str) -> str
```

【_sha_text】根据紧邻签名和函数体完成维护工具的数据检查、生成、评测或证据处理中的局部职责；返回、状态、副作用和异常以本页下方调用/raise记录为边界，名称本身不增加额外保证。

### `_text`

源码位置：[tools/build_multimodal_dataset.py 第 442 行](../../../tools/build_multimodal_dataset.py#L442)。类型：`FunctionDef`。

```python
_text(value: object, name: str) -> str
```

【_text】根据紧邻签名和函数体完成维护工具的数据检查、生成、评测或证据处理中的局部职责；返回、状态、副作用和异常以本页下方调用/raise记录为边界，名称本身不增加额外保证。

### `_integer`

源码位置：[tools/build_multimodal_dataset.py 第 448 行](../../../tools/build_multimodal_dataset.py#L448)。类型：`FunctionDef`。

```python
_integer(value: object, name: str, minimum: int | None=None) -> int
```

【_integer】根据紧邻签名和函数体完成维护工具的数据检查、生成、评测或证据处理中的局部职责；返回、状态、副作用和异常以本页下方调用/raise记录为边界，名称本身不增加额外保证。

### `_number`

源码位置：[tools/build_multimodal_dataset.py 第 456 行](../../../tools/build_multimodal_dataset.py#L456)。类型：`FunctionDef`。

```python
_number(value: object, name: str, *, minimum: float | None=None, maximum: float | None=None) -> float
```

【_number】根据紧邻签名和函数体完成维护工具的数据检查、生成、评测或证据处理中的局部职责；返回、状态、副作用和异常以本页下方调用/raise记录为边界，名称本身不增加额外保证。

### `_optional_number`

源码位置：[tools/build_multimodal_dataset.py 第 473 行](../../../tools/build_multimodal_dataset.py#L473)。类型：`FunctionDef`。

```python
_optional_number(value: object, *, minimum: float | None=None) -> float | None
```

【_optional_number】根据紧邻签名和函数体完成维护工具的数据检查、生成、评测或证据处理中的局部职责；返回、状态、副作用和异常以本页下方调用/raise记录为边界，名称本身不增加额外保证。

### `_lane_id`

源码位置：[tools/build_multimodal_dataset.py 第 483 行](../../../tools/build_multimodal_dataset.py#L483)。类型：`FunctionDef`。

```python
_lane_id(value: object) -> int | None
```

【_lane_id】根据紧邻签名和函数体完成维护工具的数据检查、生成、评测或证据处理中的局部职责；返回、状态、副作用和异常以本页下方调用/raise记录为边界，名称本身不增加额外保证。

### `_action_or_none`

源码位置：[tools/build_multimodal_dataset.py 第 492 行](../../../tools/build_multimodal_dataset.py#L492)。类型：`FunctionDef`。

```python
_action_or_none(value: object) -> str | None
```

【_action_or_none】根据紧邻签名和函数体完成维护工具的数据检查、生成、评测或证据处理中的局部职责；返回、状态、副作用和异常以本页下方调用/raise记录为边界，名称本身不增加额外保证。

### `main`

源码位置：[tools/build_multimodal_dataset.py 第 501 行](../../../tools/build_multimodal_dataset.py#L501)。类型：`FunctionDef`。

```python
main() -> int
```

【main】是维护工具的数据检查、生成、评测或证据处理的执行/命令入口；参数来自紧邻签名或本页CLI表，可能读取外部资源、写产物或启动服务，应以退出码、原始日志和固定输入身份判定结果。

## 内部调用与异常路径

- `deterministic_split` 调用：`ValueError`, `f'{sequence_id}\x00{scenario_id}\x00{seed}'.encode`, `hashlib.sha256`, `hashlib.sha256(key).digest`, `int.from_bytes`.
- `load_capture_records` 调用：`TypeError`, `ValueError`, `enumerate`, `isinstance`, `json.loads`, `path.open`, `raw.strip`, `records.append`.
- `build_dataset` 调用：`''.join`, `(evidence_dir / 'quality_report.json').write_text`, `(splits_dir / f'{split}_sequences.txt').write_text`, `Counter`, `ValueError`, `build_record`, `counts.items`, `dataset_root.resolve`, `dict`, `evidence_dir.mkdir`, `json.dumps`, `len`, `load_capture_records`, `output_root.mkdir`, `output_root.resolve`, `records_by_split[split].append`, `records_dir.mkdir`, `seen_samples.add`, `sequence_splits.setdefault`, `set`, `sorted`, `splits_dir.mkdir`, `str`, `sum`, `target.write_text`.
- `build_record` 调用：`TypeError`, `ValueError`, `_action_or_none`, `_integer`, `_lane_id`, `_media_ref`, `_number`, `_objects`, `_optional_number`, `_sha_text`, `_text`, `bool`, `control.get`, `datetime.now`, `datetime.now(timezone.utc).isoformat`, `defaults.get`, `deterministic_split`, `dict`, `environment.get`, `expected.get`, `isinstance`, `language.get`, `list`, `payload.get`, `payload.get('latency_ms', {}).get`, `perception.get`, `quality.get`, `qwen.get`, `response_map.get`, `round`, `safety.get`, `str`, `str(environment.get('traffic_light_state', 'unknown')).lower`, `str(qwen.get('status', 'not_run')).lower`, `str(safety.get('risk_level', 'unknown')).lower`, `vehicle.get`.
- `_media_ref` 调用：`(dataset_root / Path(*posix.parts)).resolve`, `FileNotFoundError`, `Path`, `PurePosixPath`, `ValueError`, `_file_sha256`, `_text`, `_text(value, 'media path').replace`, `path.is_file`, `path.relative_to`, `path.suffix.lower`, `path.suffix.lower().lstrip`, `posix.is_absolute`, `{'jpg': 'jpeg', 'jpeg': 'jpeg', 'wav': 'wav-pcm16'}.get`.
- `_objects` 调用：`CLASS_MAP.get`, `TypeError`, `_number`, `_optional_number`, `enumerate`, `isinstance`, `item.get`, `list`, `objects.append`, `str`, `str(item.get('class_name', item.get('class', ''))).lower`.
- `_file_sha256` 调用：`digest.hexdigest`, `digest.update`, `hashlib.sha256`, `iter`, `path.open`, `stream.read`.
- `_sha_text` 调用：`ValueError`, `_text`, `_text(value, name).lower`, `any`, `len`.
- `_text` 调用：`ValueError`, `type`, `value.strip`.
- `_integer` 调用：`TypeError`, `ValueError`, `type`.
- `_number` 调用：`TypeError`, `ValueError`, `float`, `isinstance`, `type`.
- `_optional_number` 调用：`_number`.
- `_lane_id` 调用：`ValueError`, `int`.
- `_action_or_none` 调用：`str`, `str(value).strip`, `str(value).strip().upper`.
- `main` 调用：`argparse.ArgumentParser`, `build_dataset`, `json.dumps`, `parser.add_argument`, `parser.parse_args`, `print`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `_integer`，第 450 行：`TypeError(f'{name} must be an integer')`。
- `_integer`，第 452 行：`ValueError(f'{name} must be >= {minimum}')`。
- `_lane_id`，第 489 行：`ValueError('lane_id must be integer-compatible or null')`。
- `_media_ref`，第 382 行：`ValueError(f'unsafe media path: {relative}')`。
- `_media_ref`，第 387 行：`ValueError(f'media path escapes dataset root: {relative}')`。
- `_media_ref`，第 389 行：`FileNotFoundError(f'media file not found: {path}')`。
- `_number`，第 464 行：`TypeError(f'{name} must be numeric')`。
- `_number`，第 467 行：`ValueError(f'{name} must be >= {minimum}')`。
- `_number`，第 469 行：`ValueError(f'{name} must be <= {maximum}')`。
- `_objects`，第 403 行：`TypeError('perception.detected_objects must be an array')`。
- `_objects`，第 407 行：`TypeError('detected object must be an object')`。
- `_sha_text`，第 438 行：`ValueError(f'{name} must contain 64 lowercase hexadecimal characters')`。
- `_text`，第 444 行：`ValueError(f'{name} must be non-empty text')`。
- `build_dataset`，第 100 行：`ValueError(f'duplicate generated sample_id {sample_id!r}')`。
- `build_dataset`，第 106 行：`ValueError(f'sequence {sequence_id!r} would leak across {previous}/{split}')`。
- `build_record`，第 179 行：`ValueError(f'frame {frame_id}: {data_level} requires rgb_path')`。
- `build_record`，第 183 行：`TypeError(f'frame {frame_id}: qwen must be an object')`。
- `build_record`，第 195 行：`TypeError(f'frame {frame_id}: control must be an object')`。
- `build_record`，第 199 行：`TypeError(f'frame {frame_id}: expected must be an object')`。
- `build_record`，第 204 行：`TypeError(f'frame {frame_id}: vehicle must be an object')`。
- `build_record`，第 207 行：`TypeError(f'frame {frame_id}: language must be an object')`。
- `build_record`，第 210 行：`TypeError(f'frame {frame_id}: perception must be an object')`。
- `build_record`，第 213 行：`TypeError(f'frame {frame_id}: safety must be an object')`。
- `build_record`，第 216 行：`TypeError(f'frame {frame_id}: environment must be an object')`。
- `build_record`，第 219 行：`TypeError(f'frame {frame_id}: quality must be an object')`。
- `build_record`，第 224 行：`ValueError(f'frame {frame_id}: invalid annotation_status')`。
- `build_record`，第 231 行：`ValueError(f'frame {frame_id}: scoring requires closed_loop, synchronized and reviewed')`。
- `deterministic_split`，第 54 行：`ValueError('invalid train/val percentages')`。
- `load_capture_records`，第 73 行：`ValueError(f'{path}:{line_number}: invalid JSON: {error.msg}')`。
- `load_capture_records`，第 75 行：`TypeError(f'{path}:{line_number}: capture record must be an object')`。
- `load_capture_records`，第 78 行：`ValueError(f'{path}: capture manifest is empty')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 503 行：`parser.add_argument('capture_jsonl', nargs='+', type=Path)`。
- 第 504 行：`parser.add_argument('--dataset-root', required=True, type=Path)`。
- 第 505 行：`parser.add_argument('--output-root', required=True, type=Path)`。
- 第 506 行：`parser.add_argument('--sequence-id', required=True)`。
- 第 507 行：`parser.add_argument('--scenario-id', required=True)`。
- 第 508 行：`parser.add_argument('--seed', type=int, default=0)`。
- 第 509 行：`parser.add_argument('--difficulty', choices=('basic', 'advanced', 'challenge', 'unassigned'), default='unassigned')`。
- 第 510 行：`parser.add_argument('--map', default='Town03')`。
- 第 511 行：`parser.add_argument('--git-commit', required=True)`。
- 第 512 行：`parser.add_argument('--config-sha256', required=True)`。
- 第 513 行：`parser.add_argument('--model', default='Qwen2.5-VL')`。
- 第 514 行：`parser.add_argument('--model-version', default='local')`。

## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [integration/tests/test_multimodal_dataset_builder.py](../../../integration/tests/test_multimodal_dataset_builder.py)

## 后续修改需要一起阅读

- [上级模块](../modules/support-tools.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `tools/build_multimodal_dataset.py`

来源 SHA256：`fa8bfbcf354e8fa4a7ac4b3e799402901a781071c8b65b3b39f8ddfd007afc3f`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 503 | `'capture_jsonl'` | `nargs='+'; type=Path` |
| 504 | `'--dataset-root'` | `required=True; type=Path` |
| 505 | `'--output-root'` | `required=True; type=Path` |
| 506 | `'--sequence-id'` | `required=True` |
| 507 | `'--scenario-id'` | `required=True` |
| 508 | `'--seed'` | `type=int; default=0` |
| 509 | `'--difficulty'` | `choices=('basic', 'advanced', 'challenge', 'unassigned'); default='unassigned'` |
| 510 | `'--map'` | `default='Town03'` |
| 511 | `'--git-commit'` | `required=True` |
| 512 | `'--config-sha256'` | `required=True` |
| 513 | `'--model'` | `default='Qwen2.5-VL'` |
| 514 | `'--model-version'` | `default='local'` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `deterministic_split` / 54 | `train_percent < 0 or val_percent < 0 or train_percent + val_percent > 100` | `raise ValueError('invalid train/val percentages')` |
| `load_capture_records` / 73 | `except json.JSONDecodeError` | `raise ValueError(f'{path}:{line_number}: invalid JSON: {error.msg}') from error` |
| `load_capture_records` / 75 | `not isinstance(payload, dict)` | `raise TypeError(f'{path}:{line_number}: capture record must be an object')` |
| `load_capture_records` / 78 | `not records` | `raise ValueError(f'{path}: capture manifest is empty')` |
| `build_dataset` / 100 | `sample_id in seen_samples` | `raise ValueError(f'duplicate generated sample_id {sample_id!r}')` |
| `build_dataset` / 106 | `previous != split` | `raise ValueError(f'sequence {sequence_id!r} would leak across {previous}/{split}')` |
| `build_record` / 179 | `data_level in {'perception', 'decision', 'closed_loop'} and rgb is None` | `raise ValueError(f'frame {frame_id}: {data_level} requires rgb_path')` |
| `build_record` / 183 | `not isinstance(qwen, Mapping)` | `raise TypeError(f'frame {frame_id}: qwen must be an object')` |
| `build_record` / 195 | `not isinstance(control, Mapping)` | `raise TypeError(f'frame {frame_id}: control must be an object')` |
| `build_record` / 199 | `not isinstance(expected, Mapping)` | `raise TypeError(f'frame {frame_id}: expected must be an object')` |
| `build_record` / 204 | `not isinstance(vehicle, Mapping)` | `raise TypeError(f'frame {frame_id}: vehicle must be an object')` |
| `build_record` / 207 | `not isinstance(language, Mapping)` | `raise TypeError(f'frame {frame_id}: language must be an object')` |
| `build_record` / 210 | `not isinstance(perception, Mapping)` | `raise TypeError(f'frame {frame_id}: perception must be an object')` |
| `build_record` / 213 | `not isinstance(safety, Mapping)` | `raise TypeError(f'frame {frame_id}: safety must be an object')` |
| `build_record` / 216 | `not isinstance(environment, Mapping)` | `raise TypeError(f'frame {frame_id}: environment must be an object')` |
| `build_record` / 219 | `not isinstance(quality, Mapping)` | `raise TypeError(f'frame {frame_id}: quality must be an object')` |
| `build_record` / 224 | `annotation_status not in {'unreviewed', 'single_review', 'double_review', 'adjudicated'}` | `raise ValueError(f'frame {frame_id}: invalid annotation_status')` |
| `build_record` / 231 | `eligible_score and (data_level != 'closed_loop' or not synchronized or annotation_status not in {'double_review', 'adjudicated'})` | `raise ValueError(f'frame {frame_id}: scoring requires closed_loop, synchronized and reviewed')` |
| `_media_ref` / 382 | `posix.is_absolute() or '..' in posix.parts or (posix.parts and ':' in posix.parts[0])` | `raise ValueError(f'unsafe media path: {relative}')` |
| `_media_ref` / 387 | `except ValueError` | `raise ValueError(f'media path escapes dataset root: {relative}') from error` |
| `_media_ref` / 389 | `not path.is_file()` | `raise FileNotFoundError(f'media file not found: {path}')` |
| `_objects` / 403 | `not isinstance(value, list)` | `raise TypeError('perception.detected_objects must be an array')` |
| `_objects` / 407 | `not isinstance(item, Mapping)` | `raise TypeError('detected object must be an object')` |
| `_sha_text` / 438 | `len(text) != 64 or any((char not in '0123456789abcdef' for char in text))` | `raise ValueError(f'{name} must contain 64 lowercase hexadecimal characters')` |
| `_text` / 444 | `type(value) is not str or not value.strip()` | `raise ValueError(f'{name} must be non-empty text')` |
| `_integer` / 450 | `type(value) is not int` | `raise TypeError(f'{name} must be an integer')` |
| `_integer` / 452 | `minimum is not None and value < minimum` | `raise ValueError(f'{name} must be >= {minimum}')` |
| `_number` / 464 | `type(value) not in (int, float) or isinstance(value, bool)` | `raise TypeError(f'{name} must be numeric')` |
| `_number` / 467 | `minimum is not None and result < minimum` | `raise ValueError(f'{name} must be >= {minimum}')` |
| `_number` / 469 | `maximum is not None and result > maximum` | `raise ValueError(f'{name} must be <= {maximum}')` |
| `_lane_id` / 489 | `except (TypeError, ValueError)` | `raise ValueError('lane_id must be integer-compatible or null') from error` |

### tools/build_multimodal_dataset.py 数值检查调用

这里保留校验函数的minimum/positive等参数原文；实际可达性由调用分支决定，函数本体异常仍需看对应helper。

| 行 | 校验调用 |
|---|---|
| 165 | `_number(payload.get('sim_time_s'), 'sim_time_s', minimum=0.0)` |
| 480 | `_number(value, 'optional number', minimum=minimum)` |
| 264 | `_number(payload.get('max_sensor_skew_ms', 0.0), 'max_sensor_skew_ms', minimum=0.0)` |
| 284 | `_number(language.get('asr_confidence', 1.0), 'asr_confidence', minimum=0.0, maximum=1.0)` |
| 297 | `_number(vehicle.get('acceleration_mps2', 0.0), 'acceleration_mps2')` |
| 299 | `_number(vehicle.get('route_progress', 0.0), 'route_progress', minimum=0.0, maximum=1.0)` |
| 325 | `_number(response_map.get('confidence', 0.0), 'decision confidence', minimum=0.0, maximum=1.0)` |
| 339 | `_number(control.get('throttle', 0.0), 'throttle', minimum=0.0, maximum=1.0)` |
| 340 | `_number(control.get('brake', 0.0), 'brake', minimum=0.0, maximum=1.0)` |
| 341 | `_number(control.get('steer', 0.0), 'steer', minimum=-1.0, maximum=1.0)` |
| 415 | `_number(item.get('confidence', 0.0), 'object confidence', minimum=0.0, maximum=1.0)` |
| 296 | `_number(vehicle.get('speed_mps', 0.0), 'speed_mps', minimum=0.0)` |
| 301 | `_number(vehicle.get('x_m', 0.0), 'x_m')` |
| 302 | `_number(vehicle.get('y_m', 0.0), 'y_m')` |
| 303 | `_number(vehicle.get('yaw_deg', 0.0), 'yaw_deg')` |
