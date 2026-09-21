# artifacts：功能记录

上级模块：[模块说明](../modules/challenge-training.md) · 实现：[challenge/distillation/artifacts.py](../../../challenge/distillation/artifacts.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [各Head损失、mask与加权](distillation-objective.md)
- [恢复、纯权重候选与晋级身份](checkpoint-and-promotion.md)

## 功能职责与范围

A3 Student weight artifacts and fail-closed FP32 promotion gate.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `export_candidate_weights`

源码位置：[challenge/distillation/artifacts.py 第 26 行](../../../challenge/distillation/artifacts.py#L26)。类型：`FunctionDef`。

```python
export_candidate_weights(output_directory: str | Path, *, model: torch.nn.Module, identity: Mapping[str, Any], validation: Mapping[str, Any], checkpoint_sha256: str) -> dict[str, Any]
```

Write a pure state_dict plus a non-promoted provenance manifest.

### `promote_fp32_candidate`

源码位置：[challenge/distillation/artifacts.py 第 70 行](../../../challenge/distillation/artifacts.py#L70)。类型：`FunctionDef`。

```python
promote_fp32_candidate(candidate_manifest: Mapping[str, Any], *, weights_path: str | Path, teacher_evaluation: Mapping[str, Any], student_evaluation: Mapping[str, Any], output_path: str | Path, max_core_drop: float=0.015, max_safety_drop: float=0.0, core_metrics: Sequence[str]=CORE_METRICS, safety_metrics: Sequence[str]=SAFETY_METRICS) -> dict[str, Any]
```

Promote only independent Validation evidence; frozen Test is forbidden.

### `_validate_evaluation_identity`

源码位置：[challenge/distillation/artifacts.py 第 130 行](../../../challenge/distillation/artifacts.py#L130)。类型：`FunctionDef`。

```python
_validate_evaluation_identity(candidate: Mapping[str, Any], evaluation: Mapping[str, Any], label: str) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_validate_pinned_teacher_candidate`

源码位置：[challenge/distillation/artifacts.py 第 152 行](../../../challenge/distillation/artifacts.py#L152)。类型：`FunctionDef`。

```python
_validate_pinned_teacher_candidate(candidate: Mapping[str, Any]) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_metrics`

源码位置：[challenge/distillation/artifacts.py 第 165 行](../../../challenge/distillation/artifacts.py#L165)。类型：`FunctionDef`。

```python
_metrics(evaluation: Mapping[str, Any], label: str) -> Mapping[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_drop_check`

源码位置：[challenge/distillation/artifacts.py 第 172 行](../../../challenge/distillation/artifacts.py#L172)。类型：`FunctionDef`。

```python
_drop_check(name: str, teacher: Mapping[str, Any], student: Mapping[str, Any], max_drop: float, group: str) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_write_json`

源码位置：[challenge/distillation/artifacts.py 第 204 行](../../../challenge/distillation/artifacts.py#L204)。类型：`FunctionDef`。

```python
_write_json(path: Path, value: Mapping[str, Any]) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_json_safe`

源码位置：[challenge/distillation/artifacts.py 第 214 行](../../../challenge/distillation/artifacts.py#L214)。类型：`FunctionDef`。

```python
_json_safe(value: Any) -> Any
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_sha256`

源码位置：[challenge/distillation/artifacts.py 第 224 行](../../../challenge/distillation/artifacts.py#L224)。类型：`FunctionDef`。

```python
_sha256(path: Path) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `export_candidate_weights` 调用：`Path`, `_sha256`, `_write_json`, `bool`, `dict`, `identity.get`, `model.state_dict`, `root.mkdir`, `str`, `temporary.replace`, `torch.save`, `weights_path.with_name`.
- `promote_fp32_candidate` 调用：`Path`, `ValueError`, `_drop_check`, `_metrics`, `_sha256`, `_validate_evaluation_identity`, `_validate_pinned_teacher_candidate`, `_write_json`, `all`, `bool`, `candidate_manifest.get`, `checks.append`, `dict`, `float`, `student_evaluation.get`, `teacher_evaluation.get`.
- `_validate_evaluation_identity` 调用：`ValueError`, `candidate.get`, `evaluation.get`, `is_protected_split`, `split.strip`, `split.strip().lower`, `str`, `str(evaluation.get('evaluation_id', '')).strip`.
- `_validate_pinned_teacher_candidate` 调用：`ValueError`, `any`, `candidate.get`, `fingerprint.lower`, `len`, `revision.lower`, `str`.
- `_metrics` 调用：`ValueError`, `evaluation.get`, `isinstance`.
- `_drop_check` 调用：`ValueError`, `float`, `math.isfinite`.
- `_write_json` 调用：`_json_safe`, `dict`, `json.dumps`, `path.parent.mkdir`, `path.with_name`, `temporary.replace`, `temporary.write_text`.
- `_json_safe` 调用：`_json_safe`, `isinstance`, `math.isfinite`, `str`, `value.items`.
- `_sha256` 调用：`digest.hexdigest`, `digest.update`, `hashlib.sha256`, `iter`, `path.open`, `stream.read`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `_drop_check`，第 180 行：`ValueError(f'gate metric {name!r} is required for Teacher and Student')`。
- `_drop_check`，第 184 行：`ValueError(f'gate metric {name!r} must be numeric')`。
- `_drop_check`，第 191 行：`ValueError(f'gate metric {name!r} must be in [0,1]')`。
- `_metrics`，第 168 行：`ValueError(f'{label} evaluation.metrics must be an object')`。
- `_validate_evaluation_identity`，第 139 行：`ValueError(f'{label} gate evidence must use Validation, never frozen Test')`。
- `_validate_evaluation_identity`，第 141 行：`ValueError(f'{label} evaluation dataset_version does not match candidate')`。
- `_validate_evaluation_identity`，第 143 行：`ValueError(f'{label} evaluation_id is required')`。
- `_validate_evaluation_identity`，第 149 行：`ValueError(f'{label} evaluation {field} does not match candidate')`。
- `_validate_pinned_teacher_candidate`，第 154 行：`ValueError('production candidate requires the pinned Teacher identity')`。
- `_validate_pinned_teacher_candidate`，第 158 行：`ValueError('production candidate requires a full Teacher model revision')`。
- `_validate_pinned_teacher_candidate`，第 162 行：`ValueError('production candidate requires a valid Teacher artifact fingerprint')`。
- `promote_fp32_candidate`，第 84 行：`ValueError('only a production candidate pending the A3 gate can be promoted')`。
- `promote_fp32_candidate`，第 86 行：`ValueError('candidate must come from a clean committed challenge worktree')`。
- `promote_fp32_candidate`，第 90 行：`ValueError('candidate weight SHA256 does not match the manifest')`。
- `promote_fp32_candidate`，第 92 行：`ValueError('gate drops must be in [0,1]')`。
- `promote_fp32_candidate`，第 105 行：`ValueError('Student schema_validity must be numeric')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [challenge/distillation/preflight.py](../../../challenge/distillation/preflight.py)

静态 import 消费者（含测试）：

- [challenge/distillation/promote.py](../../../challenge/distillation/promote.py)
- [challenge/distillation/tests/test_artifacts.py](../../../challenge/distillation/tests/test_artifacts.py)
- [challenge/distillation/train.py](../../../challenge/distillation/train.py)

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-training.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/distillation/artifacts.py`

来源 SHA256：`4984eb81fffecee7895121a3319daea8a921a0d7c168887a60c418f7b5c56cd4`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `promote_fp32_candidate` / 84 | `candidate_manifest.get('gate_status') != 'PENDING_A3_FP32_GATE'` | `raise ValueError('only a production candidate pending the A3 gate can be promoted')` |
| `promote_fp32_candidate` / 86 | `candidate_manifest.get('source_worktree_dirty') is not False` | `raise ValueError('candidate must come from a clean committed challenge worktree')` |
| `promote_fp32_candidate` / 90 | `actual_weights_sha != candidate_manifest.get('weights_sha256')` | `raise ValueError('candidate weight SHA256 does not match the manifest')` |
| `promote_fp32_candidate` / 92 | `not 0.0 <= max_core_drop <= 1.0 or not 0.0 <= max_safety_drop <= 1.0` | `raise ValueError('gate drops must be in [0,1]')` |
| `promote_fp32_candidate` / 105 | `except (TypeError, ValueError)` | `raise ValueError('Student schema_validity must be numeric') from error` |
| `_validate_evaluation_identity` / 139 | `is_protected_split(split) or split.strip().lower() not in {'val', 'valid', 'validation', 'dev'}` | `raise ValueError(f'{label} gate evidence must use Validation, never frozen Test')` |
| `_validate_evaluation_identity` / 141 | `str(evaluation.get('dataset_version')) != str(candidate.get('dataset_version'))` | `raise ValueError(f'{label} evaluation dataset_version does not match candidate')` |
| `_validate_evaluation_identity` / 143 | `not str(evaluation.get('evaluation_id', '')).strip()` | `raise ValueError(f'{label} evaluation_id is required')` |
| `_validate_evaluation_identity` / 149 | `evaluation.get(field) != candidate.get(field)` | `raise ValueError(f'{label} evaluation {field} does not match candidate')` |
| `_validate_pinned_teacher_candidate` / 154 | `candidate.get('teacher_identity_policy') != 'frozen_manifest'` | `raise ValueError('production candidate requires the pinned Teacher identity')` |
| `_validate_pinned_teacher_candidate` / 158 | `len(revision) != 40 or any((char not in '0123456789abcdef' for char in revision.lower()))` | `raise ValueError('production candidate requires a full Teacher model revision')` |
| `_validate_pinned_teacher_candidate` / 162 | `len(fingerprint) != 64 or any((char not in '0123456789abcdef' for char in fingerprint.lower()))` | `raise ValueError('production candidate requires a valid Teacher artifact fingerprint')` |
| `_metrics` / 168 | `not isinstance(value, Mapping)` | `raise ValueError(f'{label} evaluation.metrics must be an object')` |
| `_drop_check` / 180 | `name not in teacher or name not in student` | `raise ValueError(f'gate metric {name!r} is required for Teacher and Student')` |
| `_drop_check` / 184 | `except (TypeError, ValueError)` | `raise ValueError(f'gate metric {name!r} must be numeric') from error` |
| `_drop_check` / 191 | `not math.isfinite(teacher_value) or not math.isfinite(student_value) or (not 0.0 <= teacher_value <= 1.0) or (not 0.0 <= student_value <= 1.0)` | `raise ValueError(f'gate metric {name!r} must be in [0,1]')` |
