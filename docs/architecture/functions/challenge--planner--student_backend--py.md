# student_backend：功能记录

上级模块：[模块说明](../modules/challenge-planner.md) · 实现：[challenge/planner/student_backend.py](../../../challenge/planner/student_backend.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [Head解码、约束修复和就绪判定](student-plan-decoding.md)

## 功能职责与范围

PyTorch Student backend implementing the frozen planner boundary.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `StudentBackend`

源码位置：[challenge/planner/student_backend.py 第 24 行](../../../challenge/planner/student_backend.py#L24)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `StudentBackend.__init__`

源码位置：[challenge/planner/student_backend.py 第 27 行](../../../challenge/planner/student_backend.py#L27)。类型：`FunctionDef`。

```python
StudentBackend.__init__(self, model: StudentPlannerV0 | None=None, *, weights: str | Path | None=None, weights_manifest: str | Path | None=None, registry: InterfaceRegistry | None=None) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `StudentBackend.infer`

源码位置：[challenge/planner/student_backend.py 第 66 行](../../../challenge/planner/student_backend.py#L66)。类型：`FunctionDef`。

```python
StudentBackend.infer(self, request: Mapping[str, Any]) -> Mapping[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `StudentBackend.health`

源码位置：[challenge/planner/student_backend.py 第 81 行](../../../challenge/planner/student_backend.py#L81)。类型：`FunctionDef`。

```python
StudentBackend.health(self) -> tuple[bool, str]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `validate_weight_manifest`

源码位置：[challenge/planner/student_backend.py 第 87 行](../../../challenge/planner/student_backend.py#L87)。类型：`FunctionDef`。

```python
validate_weight_manifest(weights: str | Path, manifest_path: str | Path, *, expected_model_id: str, expected_config_id: str=StudentModelConfig().config_id) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `validate_weight_manifest` 调用：`Path`, `Path(manifest_path).read_text`, `StudentModelConfig`, `ValueError`, `hashlib.sha256`, `hashlib.sha256(path.read_bytes()).hexdigest`, `isinstance`, `json.loads`, `manifest.get`, `manifest[key].strip`, `path.read_bytes`, `re.fullmatch`, `required.difference`, `sorted`.
- `__init__` 调用：`InterfaceRegistry`, `Path`, `PlanValidator`, `StudentPlanAdapter`, `StudentPlannerV0`, `StudentPreprocessor`, `ValueError`, `assert_frozen_contracts`, `getattr`, `self.model.eval`, `self.model.load_state_dict`, `str`, `torch.load`, `validate_weight_manifest`.
- `infer` 调用：`self._adapter.decode`, `self._preprocess`, `self._registry.validate`, `self._validator.validate`, `self.model`, `tensorized.as_tuple`, `torch.inference_mode`, `validation_scene`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__init__`，第 40 行：`ValueError('weights_manifest requires weights')`。
- `validate_weight_manifest`，第 97 行：`ValueError('weight manifest must be a JSON object')`。
- `validate_weight_manifest`，第 104 行：`ValueError(f'weight manifest missing candidate identity fields: {missing}')`。
- `validate_weight_manifest`，第 107 行：`ValueError(f'weight manifest {key} must be a non-empty string')`。
- `validate_weight_manifest`，第 109 行：`ValueError('weight manifest git_sha must be a full 40-character Git SHA')`。
- `validate_weight_manifest`，第 111 行：`ValueError('weight manifest model_id does not match Student structure')`。
- `validate_weight_manifest`，第 113 行：`ValueError('weight manifest config_id does not match Student configuration')`。
- `validate_weight_manifest`，第 115 行：`ValueError('weight manifest has not passed the A3 FP32 Gate')`。
- `validate_weight_manifest`，第 118 行：`ValueError('weight manifest SHA256 does not match weights')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [challenge/planner/common.py](../../../challenge/planner/common.py)
- [challenge/planner/frozen_contracts.py](../../../challenge/planner/frozen_contracts.py)
- [challenge/planner/student_adapter.py](../../../challenge/planner/student_adapter.py)
- [challenge/student/model.py](../../../challenge/student/model.py)
- [challenge/student/preprocess.py](../../../challenge/student/preprocess.py)
- [runtime/interface_registry.py](../../../runtime/interface_registry.py)
- [runtime/plan_validator.py](../../../runtime/plan_validator.py)

静态 import 消费者（含测试）：

- [challenge/planner/__init__.py](../../../challenge/planner/__init__.py)
- [challenge/tests/test_a1_student.py](../../../challenge/tests/test_a1_student.py)
- [challenge/tests/test_delivery.py](../../../challenge/tests/test_delivery.py)

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-planner.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/planner/student_backend.py`

来源 SHA256：`1596dc7354fe9444c50fff99a3db08d00574fb3829764d52ff6b8dee19b3b572`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `StudentBackend.__init__` / 40 | `weights_manifest is not None and weights is None` | `raise ValueError('weights_manifest requires weights')` |
| `validate_weight_manifest` / 97 | `not isinstance(manifest, dict)` | `raise ValueError('weight manifest must be a JSON object')` |
| `validate_weight_manifest` / 104 | `missing` | `raise ValueError(f'weight manifest missing candidate identity fields: {missing}')` |
| `validate_weight_manifest` / 107 | `not isinstance(manifest[key], str) or not manifest[key].strip()` | `raise ValueError(f'weight manifest {key} must be a non-empty string')` |
| `validate_weight_manifest` / 109 | `not re.fullmatch('[0-9a-fA-F]{40}', manifest['git_sha'])` | `raise ValueError('weight manifest git_sha must be a full 40-character Git SHA')` |
| `validate_weight_manifest` / 111 | `manifest.get('model_id') != expected_model_id` | `raise ValueError('weight manifest model_id does not match Student structure')` |
| `validate_weight_manifest` / 113 | `manifest['config_id'] != expected_config_id` | `raise ValueError('weight manifest config_id does not match Student configuration')` |
| `validate_weight_manifest` / 115 | `manifest.get('gate_status') != 'A3_FP32_GATE_PASSED'` | `raise ValueError('weight manifest has not passed the A3 FP32 Gate')` |
| `validate_weight_manifest` / 118 | `manifest.get('weights_sha256') != actual` | `raise ValueError('weight manifest SHA256 does not match weights')` |
