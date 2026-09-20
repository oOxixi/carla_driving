# dataset：功能记录

上级模块：[模块说明](../modules/challenge-training.md) · 实现：[challenge/distillation/dataset.py](../../../challenge/distillation/dataset.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [各Head损失、mask与加权](distillation-objective.md)
- [恢复、纯权重候选与晋级身份](checkpoint-and-promotion.md)

## 功能职责与范围

Dataset boundary for A3 distillation experiments.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `DistillationDataset`

源码位置：[challenge/distillation/dataset.py 第 26 行](../../../challenge/distillation/dataset.py#L26)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `DistillationDataset.__init__`

源码位置：[challenge/distillation/dataset.py 第 27 行](../../../challenge/distillation/dataset.py#L27)。类型：`FunctionDef`。

```python
DistillationDataset.__init__(self, records: Sequence[Mapping[str, Any]], *, label_encoder: DistillationLabelEncoder | None=None, sample_weights: Mapping[str, float] | None=None, asset_root: str | Path | None=None, require_rgb: bool=False) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `DistillationDataset.__len__`

源码位置：[challenge/distillation/dataset.py 第 49 行](../../../challenge/distillation/dataset.py#L49)。类型：`FunctionDef`。

```python
DistillationDataset.__len__(self) -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `DistillationDataset.__getitem__`

源码位置：[challenge/distillation/dataset.py 第 52 行](../../../challenge/distillation/dataset.py#L52)。类型：`FunctionDef`。

```python
DistillationDataset.__getitem__(self, index: int) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `load_jsonl`

源码位置：[challenge/distillation/dataset.py 第 72 行](../../../challenge/distillation/dataset.py#L72)。类型：`FunctionDef`。

```python
load_jsonl(path: str | Path) -> list[dict[str, Any]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `make_collate_fn`

源码位置：[challenge/distillation/dataset.py 第 92 行](../../../challenge/distillation/dataset.py#L92)。类型：`FunctionDef`。

```python
make_collate_fn(*, feature_dim: int=32, input_packer: Callable[[Sequence[Mapping[str, Any]]], Mapping[str, Any]] | None=None) -> Callable[[Sequence[Mapping[str, Any]]], dict[str, Any]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `make_collate_fn.collate`

源码位置：[challenge/distillation/dataset.py 第 100 行](../../../challenge/distillation/dataset.py#L100)。类型：`FunctionDef`。

```python
make_collate_fn.collate(samples: Sequence[Mapping[str, Any]]) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `build_mock_records`

源码位置：[challenge/distillation/dataset.py 第 151 行](../../../challenge/distillation/dataset.py#L151)。类型：`FunctionDef`。

```python
build_mock_records(count: int=256) -> list[dict[str, Any]]
```

Create contract-valid unit-test records, never production training data.

### `_request`

源码位置：[challenge/distillation/dataset.py 第 192 行](../../../challenge/distillation/dataset.py#L192)。类型：`FunctionDef`。

```python
_request(record: Mapping[str, Any], *, asset_root: Path | None=None, require_rgb: bool=False) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `resolve_packaged_rgb`

源码位置：[challenge/distillation/dataset.py 第 212 行](../../../challenge/distillation/dataset.py#L212)。类型：`FunctionDef`。

```python
resolve_packaged_rgb(visual: Mapping[str, Any], asset_root: Path) -> Path
```

Resolve either portable release paths or historical SHA-named RGB assets.

### `_plan`

源码位置：[challenge/distillation/dataset.py 第 240 行](../../../challenge/distillation/dataset.py#L240)。类型：`FunctionDef`。

```python
_plan(record: Mapping[str, Any]) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_sample_class`

源码位置：[challenge/distillation/dataset.py 第 252 行](../../../challenge/distillation/dataset.py#L252)。类型：`FunctionDef`。

```python
_sample_class(record: Mapping[str, Any]) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_mock_request_features`

源码位置：[challenge/distillation/dataset.py 第 267 行](../../../challenge/distillation/dataset.py#L267)。类型：`FunctionDef`。

```python
_mock_request_features(request: Mapping[str, Any], feature_dim: int) -> list[float]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_mock_request`

源码位置：[challenge/distillation/dataset.py 第 290 行](../../../challenge/distillation/dataset.py#L290)。类型：`FunctionDef`。

```python
_mock_request(request_id: str, command_id: str, behavior: str, targets: list[dict[str, Any]], index: int) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_mock_plan`

源码位置：[challenge/distillation/dataset.py 第 340 行](../../../challenge/distillation/dataset.py#L340)。类型：`FunctionDef`。

```python
_mock_plan(request_id: str, command_id: str, behavior: str, targets: list[dict[str, Any]], index: int) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_torch`

源码位置：[challenge/distillation/dataset.py 第 394 行](../../../challenge/distillation/dataset.py#L394)。类型：`FunctionDef`。

```python
_torch() -> Any
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `load_jsonl` 调用：`FileNotFoundError`, `Path`, `ValueError`, `enumerate`, `isinstance`, `json.loads`, `raw.strip`, `records.append`, `source.is_file`, `source.read_text`, `source.read_text(encoding='utf-8').splitlines`.
- `make_collate_fn` 调用：`ValueError`, `_mock_request_features`, `_torch`, `dict`, `input_packer`, `str`, `torch.tensor`.
- `build_mock_records` 调用：`ValueError`, `_mock_plan`, `_mock_request`, `len`, `range`, `records.append`, `type`.
- `_request` 调用：`ValueError`, `dict`, `isinstance`, `record.get`, `resolve_packaged_rgb`, `str`, `visual.get`.
- `resolve_packaged_rgb` 调用：`(root / relative).resolve`, `Path`, `ValueError`, `any`, `asset_root.resolve`, `candidate.is_file`, `candidates.append`, `candidates.extend`, `hashlib.sha256`, `hashlib.sha256(image_path.read_bytes()).hexdigest`, `image_path.read_bytes`, `image_path.stat`, `int`, `isinstance`, `len`, `next`, `portable.is_relative_to`, `ref.strip`, `relative.is_absolute`, `str`, `str(visual['rgb_sha256']).lower`, `visual.get`.
- `_plan` 调用：`ValueError`, `dict`, `isinstance`, `record.get`, `teacher.get`.
- `_sample_class` 调用：`declared.get`, `isinstance`, `metadata.get`, `quality.get`, `record.get`, `str`, `str(declared).strip`, `str(declared).strip().lower`.
- `_mock_request_features` 调用：`BEHAVIORS.index`, `bool`, `constraints.get`, `enumerate`, `float`, `hashlib.sha256`, `hashlib.sha256(text.encode('utf-8')).digest`, `len`, `min`, `request.get`, `request.get('command_hint', {}).get`, `scene.get`, `str`, `str(request.get('command_hint', {}).get('intent', '')).upper`, `text.encode`.
- `_torch` 调用：`RuntimeError`.
- `__init__` 调用：`DistillationLabelEncoder`, `Path`, `Path(asset_root).resolve`, `ValueError`, `any`, `bool`, `dict`, `float`, `math.isfinite`, `sample_weights.items`, `str`, `tuple`, `weights.update`, `weights.values`.
- `__len__` 调用：`len`.
- `__getitem__` 调用：`ValueError`, `_plan`, `_request`, `_sample_class`, `dict`, `record.get`, `self.label_encoder.encode`, `str`.
- `collate` 调用：`_mock_request_features`, `_torch`, `dict`, `input_packer`, `str`, `torch.tensor`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__getitem__`，第 60 行：`ValueError(f'unsupported sample_class: {sample_class!r}')`。
- `__init__`，第 38 行：`ValueError('distillation dataset must not be empty')`。
- `__init__`，第 46 行：`ValueError('sample weights must be finite and positive')`。
- `_plan`，第 248 行：`ValueError('record.teacher.maneuver_plan must contain ManeuverPlan V2')`。
- `_request`，第 198 行：`ValueError('record.input must contain ModelRequest V1')`。
- `_request`，第 204 行：`ValueError('dataset asset_root is required for packaged RGB')`。
- `_request`，第 208 行：`ValueError('visual_input.rgb_sha256 is required')`。
- `_torch`，第 398 行：`RuntimeError('PyTorch is required for distillation batching; install it in the training environment')`。
- `build_mock_records`，第 154 行：`ValueError('mock record count must be an integer >= 2')`。
- `load_jsonl`，第 75 行：`FileNotFoundError(source)`。
- `load_jsonl`，第 83 行：`ValueError(f'{source}:{line_number}: invalid JSON: {error}')`。
- `load_jsonl`，第 85 行：`ValueError(f'{source}:{line_number}: record must be an object')`。
- `load_jsonl`，第 88 行：`ValueError(f'{source}: no records')`。
- `make_collate_fn`，第 98 行：`ValueError('feature_dim must be at least 16')`。
- `resolve_packaged_rgb`，第 216 行：`ValueError('visual_input.rgb_sha256 must be a SHA256 hex digest')`。
- `resolve_packaged_rgb`，第 223 行：`ValueError('portable RGB reference must be relative to asset_root')`。
- `resolve_packaged_rgb`，第 226 行：`ValueError('portable RGB reference escapes asset_root')`。
- `resolve_packaged_rgb`，第 231 行：`ValueError(f'packaged RGB is missing for sha256={digest}')`。
- `resolve_packaged_rgb`，第 233 行：`ValueError(f'packaged RGB hash mismatch for {image_path}')`。
- `resolve_packaged_rgb`，第 236 行：`ValueError(f'packaged RGB size mismatch for {image_path}')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [challenge/distillation/label_encoder.py](../../../challenge/distillation/label_encoder.py)

静态 import 消费者（含测试）：

- [challenge/distillation/ablation_eval.py](../../../challenge/distillation/ablation_eval.py)
- [challenge/distillation/audit_d2_view.py](../../../challenge/distillation/audit_d2_view.py)
- [challenge/distillation/preflight.py](../../../challenge/distillation/preflight.py)
- [challenge/distillation/shortcut_probe.py](../../../challenge/distillation/shortcut_probe.py)
- [challenge/distillation/tests/test_a1_integration.py](../../../challenge/distillation/tests/test_a1_integration.py)
- [challenge/distillation/tests/test_b1_d1_interface.py](../../../challenge/distillation/tests/test_b1_d1_interface.py)
- [challenge/distillation/tests/test_b1_smoke_integration.py](../../../challenge/distillation/tests/test_b1_smoke_integration.py)
- [challenge/distillation/tests/test_evaluate_class_metrics.py](../../../challenge/distillation/tests/test_evaluate_class_metrics.py)
- [challenge/distillation/tests/test_label_encoder.py](../../../challenge/distillation/tests/test_label_encoder.py)
- [challenge/distillation/tests/test_losses.py](../../../challenge/distillation/tests/test_losses.py)
- [challenge/distillation/tests/test_preflight.py](../../../challenge/distillation/tests/test_preflight.py)
- [challenge/distillation/tests/test_shortcut_probe.py](../../../challenge/distillation/tests/test_shortcut_probe.py)
- [challenge/distillation/tests/test_student_contract.py](../../../challenge/distillation/tests/test_student_contract.py)
- [challenge/distillation/tests/test_train_smoke.py](../../../challenge/distillation/tests/test_train_smoke.py)
- [challenge/distillation/tests/test_validate_a1_inputs.py](../../../challenge/distillation/tests/test_validate_a1_inputs.py)
- [challenge/distillation/train.py](../../../challenge/distillation/train.py)
- [challenge/distillation/validate_a1_inputs.py](../../../challenge/distillation/validate_a1_inputs.py)

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-training.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/distillation/dataset.py`

来源 SHA256：`fb680b919ad01e281576d89f8699a5ceb4bf5db3c9354a87cc71dcd36d2fdaee`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `DistillationDataset.__init__` / 38 | `not self.records` | `raise ValueError('distillation dataset must not be empty')` |
| `DistillationDataset.__init__` / 46 | `any((not math.isfinite(value) or value <= 0.0 for value in weights.values()))` | `raise ValueError('sample weights must be finite and positive')` |
| `DistillationDataset.__getitem__` / 60 | `sample_class not in self.sample_weights` | `raise ValueError(f'unsupported sample_class: {sample_class!r}')` |
| `load_jsonl` / 75 | `not source.is_file()` | `raise FileNotFoundError(source)` |
| `load_jsonl` / 83 | `except json.JSONDecodeError` | `raise ValueError(f'{source}:{line_number}: invalid JSON: {error}') from error` |
| `load_jsonl` / 85 | `not isinstance(item, dict)` | `raise ValueError(f'{source}:{line_number}: record must be an object')` |
| `load_jsonl` / 88 | `not records` | `raise ValueError(f'{source}: no records')` |
| `make_collate_fn` / 98 | `feature_dim < 16` | `raise ValueError('feature_dim must be at least 16')` |
| `build_mock_records` / 154 | `type(count) is not int or count < 2` | `raise ValueError('mock record count must be an integer >= 2')` |
| `_request` / 198 | `not isinstance(value, Mapping)` | `raise ValueError('record.input must contain ModelRequest V1')` |
| `_request` / 204 | `isinstance(visual, Mapping) and visual.get('rgb_sha256') AND asset_root is None AND require_rgb` | `raise ValueError('dataset asset_root is required for packaged RGB')` |
| `_request` / 208 | `NOT (isinstance(visual, Mapping) and visual.get('rgb_sha256')) AND require_rgb` | `raise ValueError('visual_input.rgb_sha256 is required')` |
| `resolve_packaged_rgb` / 216 | `len(digest) != 64 or any((char not in '0123456789abcdef' for char in digest))` | `raise ValueError('visual_input.rgb_sha256 must be a SHA256 hex digest')` |
| `resolve_packaged_rgb` / 223 | `isinstance(ref, str) and ref.strip() AND relative.is_absolute()` | `raise ValueError('portable RGB reference must be relative to asset_root')` |
| `resolve_packaged_rgb` / 226 | `isinstance(ref, str) and ref.strip() AND not portable.is_relative_to(root)` | `raise ValueError('portable RGB reference escapes asset_root')` |
| `resolve_packaged_rgb` / 231 | `image_path is None` | `raise ValueError(f'packaged RGB is missing for sha256={digest}')` |
| `resolve_packaged_rgb` / 233 | `hashlib.sha256(image_path.read_bytes()).hexdigest() != digest` | `raise ValueError(f'packaged RGB hash mismatch for {image_path}')` |
| `resolve_packaged_rgb` / 236 | `expected_size is not None and image_path.stat().st_size != int(expected_size)` | `raise ValueError(f'packaged RGB size mismatch for {image_path}')` |
| `_plan` / 248 | `not isinstance(value, Mapping)` | `raise ValueError('record.teacher.maneuver_plan must contain ManeuverPlan V2')` |
| `_torch` / 398 | `except ImportError` | `raise RuntimeError('PyTorch is required for distillation batching; install it in the training environment') from error` |
