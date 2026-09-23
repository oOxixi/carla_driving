# preflight：功能记录

上级模块：[模块说明](../modules/challenge-training.md) · 实现：[challenge/distillation/preflight.py](../../../challenge/distillation/preflight.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [各Head损失、mask与加权](distillation-objective.md)
- [恢复、纯权重候选与晋级身份](checkpoint-and-promotion.md)

## 功能职责与范围

Fail-closed dataset checks before A3 reads production supervision.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `is_protected_split`

源码位置：[challenge/distillation/preflight.py 第 24 行](../../../challenge/distillation/preflight.py#L24)。类型：`FunctionDef`。

```python
is_protected_split(value: object) -> bool
```

`is_protected_split` 定义蒸馏训练使用的模型、Dataset、标签器、loss或错误类型；字段和Head顺序受Student contract约束，修改后必须重训并更新身份。

### `preflight_datasets`

源码位置：[challenge/distillation/preflight.py 第 29 行](../../../challenge/distillation/preflight.py#L29)。类型：`FunctionDef`。

```python
preflight_datasets(train_path: str | Path, val_path: str | Path, *, max_steps: int=4, max_targets: int=8, expected_version: str | None=None, expected_teacher_git_sha: str | None=None, expected_teacher_model_id: str | None=None, expected_teacher_model_revision: str | None=None, expected_teacher_artifact_fingerprint_sha256: str | None=None, asset_root: str | Path | None=None, require_rgb: bool=False, max_errors: int=100) -> dict[str, Any]
```

Return an auditable report; callers must reject ``valid == False``.

### `write_preflight_report`

源码位置：[challenge/distillation/preflight.py 第 101 行](../../../challenge/distillation/preflight.py#L101)。类型：`FunctionDef`。

```python
write_preflight_report(path: str | Path, report: Mapping[str, Any]) -> Path
```

`write_preflight_report` 写出训练报告、checkpoint、hard-case或纯权重候选；写盘成功不代表候选可部署，仍需SHA、manifest和独立Gate绑定。

### `_scan_path`

源码位置：[challenge/distillation/preflight.py 第 113 行](../../../challenge/distillation/preflight.py#L113)。类型：`FunctionDef`。

```python
_scan_path(path: Path, split: str, encoder: DistillationLabelEncoder, expected_version: str | None, max_errors: int, expected_teacher_git_sha: str | None, expected_teacher_model_id: str | None, asset_root: Path | None, require_rgb: bool, expected_teacher_model_revision: str | None, expected_teacher_artifact_fingerprint_sha256: str | None) -> dict[str, Any]
```

`_scan_path` 实现本文件对应的蒸馏、评测或候选处理子步骤；具体输入、mask、拒绝条件和副作用见本页签名/异常/调用表。

### `_inspect_record`

源码位置：[challenge/distillation/preflight.py 第 213 行](../../../challenge/distillation/preflight.py#L213)。类型：`FunctionDef`。

```python
_inspect_record(record: Mapping[str, Any], split: str, encoder: DistillationLabelEncoder, expected_version: str | None, expected_teacher_git_sha: str | None, expected_teacher_model_id: str | None, asset_root: Path | None, require_rgb: bool, expected_teacher_model_revision: str | None, expected_teacher_artifact_fingerprint_sha256: str | None) -> dict[str, Any]
```

`_inspect_record` 实现本文件对应的蒸馏、评测或候选处理子步骤；具体输入、mask、拒绝条件和副作用见本页签名/异常/调用表。

### `_split_matches`

源码位置：[challenge/distillation/preflight.py 第 346 行](../../../challenge/distillation/preflight.py#L346)。类型：`FunctionDef`。

```python
_split_matches(declared: str, expected: str) -> bool
```

`_split_matches` 实现本文件对应的蒸馏、评测或候选处理子步骤；具体输入、mask、拒绝条件和副作用见本页签名/异常/调用表。

### `_public_stats`

源码位置：[challenge/distillation/preflight.py 第 353 行](../../../challenge/distillation/preflight.py#L353)。类型：`FunctionDef`。

```python
_public_stats(value: Mapping[str, Any]) -> dict[str, Any]
```

`_public_stats` 实现本文件对应的蒸馏、评测或候选处理子步骤；具体输入、mask、拒绝条件和副作用见本页签名/异常/调用表。

### `_validate_rgb`

源码位置：[challenge/distillation/preflight.py 第 361 行](../../../challenge/distillation/preflight.py#L361)。类型：`FunctionDef`。

```python
_validate_rgb(record: Mapping[str, Any], asset_root: Path | None, require_rgb: bool) -> None
```

`_validate_rgb` 核对训练输入、冻结身份或候选证据；只覆盖显式检查项，不能用通过结果替代Student权重、样本清单和Teacher provenance的完整绑定。

### `_validate_recorded_pointers`

源码位置：[challenge/distillation/preflight.py 第 376 行](../../../challenge/distillation/preflight.py#L376)。类型：`FunctionDef`。

```python
_validate_recorded_pointers(record: Mapping[str, Any], labels: Mapping[str, Any]) -> None
```

`_validate_recorded_pointers` 核对训练输入、冻结身份或候选证据；只覆盖显式检查项，不能用通过结果替代Student权重、样本清单和Teacher provenance的完整绑定。

### `main`

源码位置：[challenge/distillation/preflight.py 第 397 行](../../../challenge/distillation/preflight.py#L397)。类型：`FunctionDef`。

```python
main(argv: Sequence[str] | None=None) -> int
```

解析训练、评测或晋级命令行参数，调用对应门禁并用退出码表达成功/拒绝；生成报告或候选不自动等于通过独立Validation或Frozen Test。

## 内部调用与异常路径

- `is_protected_split` 调用：`any`, `str`, `str(value or '').strip`, `str(value or '').strip().lower`.
- `preflight_datasets` 调用：`DistillationLabelEncoder`, `Path`, `Path(asset_root).resolve`, `Path(train_path).resolve`, `Path(val_path).resolve`, `ValueError`, `_public_stats`, `_scan_path`, `errors.append`, `len`, `set`, `set(train[field]).intersection`, `sorted`, `str`, `train.pop`, `validation.pop`.
- `write_preflight_report` 调用：`Path`, `destination.parent.mkdir`, `destination.with_name`, `dict`, `json.dumps`, `temporary.replace`, `temporary.write_text`.
- `_scan_path` 调用：`Counter`, `ValueError`, `_inspect_record`, `enumerate`, `is_protected_split`, `isinstance`, `json.loads`, `len`, `path.is_file`, `path.open`, `raw.strip`, `result['errors'].append`, `result['group_keys'].append`, `result['warnings'].extend`, `result[field].append`, `result[name].update`, `seen.add`, `set`, `str`.
- `_inspect_record` 调用：`Counter`, `ValueError`, `_split_matches`, `_validate_recorded_pointers`, `_validate_rgb`, `declared_class.get`, `dict`, `encoder.encode`, `hashlib.sha256`, `hashlib.sha256(canonical).hexdigest`, `is_protected_split`, `isinstance`, `json.dumps`, `json.dumps(dict(record), ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode`, `len`, `metadata.get`, `plan.get`, `policy.get`, `provenance.get`, `quality.get`, `record.get`, `request.get`, `sample_class.strip`, `sample_class.strip().lower`, `str`, `str(metadata.get('group_key', '')).strip`, `str(metadata.get('split', '')).strip`, `str(record.get('sample_id', '')).strip`, `sum`, `teacher.get`, `warnings.append`, `zip`.
- `_split_matches` 调用：`declared.strip`, `declared.strip().lower`.
- `_public_stats` 调用：`dict`, `isinstance`, `item.items`, `sorted`, `value.items`.
- `_validate_rgb` 调用：`ValueError`, `isinstance`, `record.get`, `resolve_packaged_rgb`, `visual.get`.
- `_validate_recorded_pointers` 调用：`ValueError`, `int`, `isinstance`, `record.get`, `targets.get`, `zip`.
- `main` 调用：`argparse.ArgumentParser`, `json.dumps`, `parser.add_argument`, `parser.parse_args`, `preflight_datasets`, `print`, `write_preflight_report`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `_inspect_record`，第 227 行：`ValueError('sample_id is required for traceability')`。
- `_inspect_record`，第 230 行：`ValueError('metadata must be an object')`。
- `_inspect_record`，第 233 行：`ValueError('record metadata identifies frozen Test data')`。
- `_inspect_record`，第 238 行：`ValueError(f'metadata.split={declared_split!r} does not match {split!r} manifest')`。
- `_inspect_record`，第 243 行：`ValueError(f'dataset_version={version!r} does not match expected {expected_version!r}')`。
- `_inspect_record`，第 248 行：`ValueError('record.input must contain ModelRequest V1')`。
- `_inspect_record`，第 256 行：`ValueError('record.teacher.maneuver_plan must contain ManeuverPlan V2')`。
- `_inspect_record`，第 269 行：`ValueError('teacher_provenance must be an object when present')`。
- `_inspect_record`，第 285 行：`ValueError(f'teacher_git_sha={teacher_sha!r} does not match expected')`。
- `_inspect_record`，第 287 行：`ValueError(f'teacher_model_id={teacher_model!r} does not match expected')`。
- `_inspect_record`，第 289 行：`ValueError(f'teacher_model_revision={teacher_revision!r} does not match expected')`。
- `_inspect_record`，第 296 行：`ValueError('teacher_artifact_fingerprint_sha256 does not match expected')`。
- `_inspect_record`，第 301 行：`ValueError('quality.schema_valid is false')`。
- `_inspect_record`，第 303 行：`ValueError('quality.valid_for_training is false')`。
- `_inspect_record`，第 306 行：`ValueError('training_policy.train_eligible must be true')`。
- `_inspect_record`，第 322 行：`ValueError(f'unsupported sample_class: {sample_class!r}')`。
- `_scan_path`，第 166 行：`ValueError('record must be a JSON object')`。
- `_validate_recorded_pointers`，第 383 行：`ValueError('B1 target pointer contract does not match A1 max_targets=8')`。
- `_validate_recorded_pointers`，第 386 行：`ValueError('student_targets.steps must be a list')`。
- `_validate_recorded_pointers`，第 392 行：`ValueError(f'recorded target pointers {actual} do not match encoded {expected}')`。
- `_validate_recorded_pointers`，第 394 行：`ValueError('invalid or outside-TopK target cannot enter ordinary supervision')`。
- `_validate_rgb`，第 367 行：`ValueError('visual_input.rgb_sha256 is required')`。
- `_validate_rgb`，第 371 行：`ValueError('asset_root is required for packaged RGB')`。
- `preflight_datasets`，第 46 行：`ValueError('max_errors must be positive')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 399 行：`parser.add_argument('--train', required=True)`。
- 第 400 行：`parser.add_argument('--val', required=True)`。
- 第 401 行：`parser.add_argument('--dataset-version')`。
- 第 402 行：`parser.add_argument('--teacher-git-sha')`。
- 第 403 行：`parser.add_argument('--teacher-model-id')`。
- 第 404 行：`parser.add_argument('--teacher-model-revision')`。
- 第 405 行：`parser.add_argument('--teacher-artifact-fingerprint-sha256')`。
- 第 406 行：`parser.add_argument('--asset-root')`。
- 第 407 行：`parser.add_argument('--require-rgb', action='store_true')`。
- 第 408 行：`parser.add_argument('--max-steps', type=int, default=4)`。
- 第 409 行：`parser.add_argument('--max-targets', type=int, default=8)`。
- 第 410 行：`parser.add_argument('--max-errors', type=int, default=100)`。
- 第 411 行：`parser.add_argument('--output')`。

## 上下游与关联验证

静态导入的项目内实现：

- [challenge/distillation/dataset.py](../../../challenge/distillation/dataset.py)
- [challenge/distillation/label_encoder.py](../../../challenge/distillation/label_encoder.py)

静态 import 消费者（含测试）：

- [challenge/distillation/artifacts.py](../../../challenge/distillation/artifacts.py)
- [challenge/distillation/tests/test_b1_smoke_integration.py](../../../challenge/distillation/tests/test_b1_smoke_integration.py)
- [challenge/distillation/tests/test_preflight.py](../../../challenge/distillation/tests/test_preflight.py)
- [challenge/distillation/train.py](../../../challenge/distillation/train.py)

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-training.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/distillation/preflight.py`

来源 SHA256：`f4e90110a514ece237560865c15c500de7c25f94446412d0447b79b2031e5d09`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 399 | `'--train'` | `required=True` |
| 400 | `'--val'` | `required=True` |
| 401 | `'--dataset-version'` | `` |
| 402 | `'--teacher-git-sha'` | `` |
| 403 | `'--teacher-model-id'` | `` |
| 404 | `'--teacher-model-revision'` | `` |
| 405 | `'--teacher-artifact-fingerprint-sha256'` | `` |
| 406 | `'--asset-root'` | `` |
| 407 | `'--require-rgb'` | `action='store_true'` |
| 408 | `'--max-steps'` | `type=int; default=4` |
| 409 | `'--max-targets'` | `type=int; default=8` |
| 410 | `'--max-errors'` | `type=int; default=100` |
| 411 | `'--output'` | `` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `preflight_datasets` / 46 | `max_errors < 1` | `raise ValueError('max_errors must be positive')` |
| `_scan_path` / 166 | `not isinstance(record, dict)` | `raise ValueError('record must be a JSON object')` |
| `_inspect_record` / 227 | `not sample_id` | `raise ValueError('sample_id is required for traceability')` |
| `_inspect_record` / 230 | `not isinstance(metadata, Mapping)` | `raise ValueError('metadata must be an object')` |
| `_inspect_record` / 233 | `is_protected_split(declared_split)` | `raise ValueError('record metadata identifies frozen Test data')` |
| `_inspect_record` / 238 | `NOT (not declared_split) AND not _split_matches(declared_split, split)` | `raise ValueError(f'metadata.split={declared_split!r} does not match {split!r} manifest')` |
| `_inspect_record` / 243 | `expected_version and version != expected_version` | `raise ValueError(f'dataset_version={version!r} does not match expected {expected_version!r}')` |
| `_inspect_record` / 248 | `not isinstance(request, Mapping)` | `raise ValueError('record.input must contain ModelRequest V1')` |
| `_inspect_record` / 256 | `not isinstance(plan, Mapping)` | `raise ValueError('record.teacher.maneuver_plan must contain ManeuverPlan V2')` |
| `_inspect_record` / 269 | `not isinstance(provenance, Mapping)` | `raise ValueError('teacher_provenance must be an object when present')` |
| `_inspect_record` / 285 | `expected_teacher_git_sha and teacher_sha != expected_teacher_git_sha` | `raise ValueError(f'teacher_git_sha={teacher_sha!r} does not match expected')` |
| `_inspect_record` / 287 | `expected_teacher_model_id and teacher_model != expected_teacher_model_id` | `raise ValueError(f'teacher_model_id={teacher_model!r} does not match expected')` |
| `_inspect_record` / 289 | `expected_teacher_model_revision and teacher_revision != expected_teacher_model_revision` | `raise ValueError(f'teacher_model_revision={teacher_revision!r} does not match expected')` |
| `_inspect_record` / 296 | `expected_teacher_artifact_fingerprint_sha256 and teacher_fingerprint != expected_teacher_artifact_fingerprint_sha256` | `raise ValueError('teacher_artifact_fingerprint_sha256 does not match expected')` |
| `_inspect_record` / 301 | `isinstance(quality, Mapping) and quality.get('schema_valid') is False` | `raise ValueError('quality.schema_valid is false')` |
| `_inspect_record` / 303 | `isinstance(quality, Mapping) and quality.get('valid_for_training') is False` | `raise ValueError('quality.valid_for_training is false')` |
| `_inspect_record` / 306 | `isinstance(policy, Mapping) and policy and (policy.get('train_eligible') is not True)` | `raise ValueError('training_policy.train_eligible must be true')` |
| `_inspect_record` / 322 | `sample_class not in {'normal', 'complex', 'safety_critical'}` | `raise ValueError(f'unsupported sample_class: {sample_class!r}')` |
| `_validate_rgb` / 367 | `not isinstance(visual, Mapping) or not visual.get('rgb_sha256') AND require_rgb` | `raise ValueError('visual_input.rgb_sha256 is required')` |
| `_validate_rgb` / 371 | `asset_root is None AND require_rgb` | `raise ValueError('asset_root is required for packaged RGB')` |
| `_validate_recorded_pointers` / 383 | `int(targets.get('target_top_k', 8)) != 8 or int(targets.get('no_target_index', 8)) != 8` | `raise ValueError('B1 target pointer contract does not match A1 max_targets=8')` |
| `_validate_recorded_pointers` / 386 | `not isinstance(recorded, list)` | `raise ValueError('student_targets.steps must be a list')` |
| `_validate_recorded_pointers` / 392 | `actual != expected` | `raise ValueError(f'recorded target pointers {actual} do not match encoded {expected}')` |
| `_validate_recorded_pointers` / 394 | `targets.get('target_outside_topk') is True or targets.get('invalid_target_id') is True` | `raise ValueError('invalid or outside-TopK target cannot enter ordinary supervision')` |
