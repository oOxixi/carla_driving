# student_adapter：功能记录

上级模块：[模块说明](../modules/challenge-planner.md) · 实现：[challenge/planner/student_adapter.py](../../../challenge/planner/student_adapter.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [Head解码、约束修复和就绪判定](student-plan-decoding.md)

## 功能职责与范围

Decode Student tensors into a strict, grounded ManeuverPlan V2.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `StudentPlanAdapter`

源码位置：[challenge/planner/student_adapter.py 第 23 行](../../../challenge/planner/student_adapter.py#L23)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `StudentPlanAdapter.__init__`

源码位置：[challenge/planner/student_adapter.py 第 24 行](../../../challenge/planner/student_adapter.py#L24)。类型：`FunctionDef`。

```python
StudentPlanAdapter.__init__(self, *, model_id: str='student-v0-r3-fp32') -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `StudentPlanAdapter.decode`

源码位置：[challenge/planner/student_adapter.py 第 27 行](../../../challenge/planner/student_adapter.py#L27)。类型：`FunctionDef`。

```python
StudentPlanAdapter.decode(self, request: Mapping[str, Any], outputs: Mapping[str, Tensor]) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_best_allowed`

源码位置：[challenge/planner/student_adapter.py 第 121 行](../../../challenge/planner/student_adapter.py#L121)。类型：`FunctionDef`。

```python
_best_allowed(logits: Tensor, names: Sequence[str], allowed: set[str]) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_feasible_behaviors`

源码位置：[challenge/planner/student_adapter.py 第 129 行](../../../challenge/planner/student_adapter.py#L129)。类型：`FunctionDef`。

```python
_feasible_behaviors(request: Mapping[str, Any], allowed: set[str]) -> set[str]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_plan_id`

源码位置：[challenge/planner/student_adapter.py 第 154 行](../../../challenge/planner/student_adapter.py#L154)。类型：`FunctionDef`。

```python
_plan_id(request_id: str) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_bounded_speed`

源码位置：[challenge/planner/student_adapter.py 第 159 行](../../../challenge/planner/student_adapter.py#L159)。类型：`FunctionDef`。

```python
_bounded_speed(predicted: float, request: Mapping[str, Any]) -> float
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_compatible_completion`

源码位置：[challenge/planner/student_adapter.py 第 169 行](../../../challenge/planner/student_adapter.py#L169)。类型：`FunctionDef`。

```python
_compatible_completion(behavior: str, predicted: str) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_step`

源码位置：[challenge/planner/student_adapter.py 第 192 行](../../../challenge/planner/student_adapter.py#L192)。类型：`FunctionDef`。

```python
_step(*, index: int, behavior: str, target: Mapping[str, Any] | None, predicted_lane: str, speed: float, completion: str, on_failure: str) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `_best_allowed` 调用：`torch.argsort`, `torch.argsort(logits, descending=True).tolist`.
- `_feasible_behaviors` 调用：`bool`, `capabilities.get`, `feasible.difference_update`, `feasible.discard`, `request.get`, `set`, `str`, `str(item).upper`.
- `_plan_id` 调用：`hashlib.sha256`, `hashlib.sha256(request_id.encode('utf-8')).hexdigest`, `request_id.encode`.
- `_bounded_speed` 调用：`constraints.get`, `float`, `limits.append`, `max`, `min`.
- `_step` 调用：`behavior.startswith`, `preconditions.append`, `preconditions.extend`.
- `decode` 调用：`ValueError`, `_best_allowed`, `_bounded_speed`, `_compatible_completion`, `_expanded_allowed_behaviors`, `_feasible_behaviors`, `_plan_id`, `_step`, `bool`, `completion_logits[0, index].argmax`, `completion_logits[0, index].argmax().item`, `confidence_value[0, 0].item`, `confirmation_logits[0, 0].item`, `failure_logits[0, index].argmax`, `failure_logits[0, index].argmax().item`, `float`, `int`, `len`, `logit.item`, `max`, `min`, `plan_length_logits[0].argmax`, `plan_length_logits[0].argmax().item`, `pointer_scores.argmax`, `pointer_scores.argmax().item`, `pointer_scores[:min(len(request['targets']), 8)].argmax`, `pointer_scores[:min(len(request['targets']), 8)].argmax().item`, `range`, `set`, `set(outputs).difference`, `sorted`, `steps.append`, `str`, `target_lane_logits[0, index].argmax`, `target_lane_logits[0, index].argmax().item`, `target_speed_mps[0, index].item`, `zip`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `decode`，第 35 行：`ValueError(f'Student V0 output dict mismatch: missing={missing}, extra={extra}')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [challenge/student/contract.py](../../../challenge/student/contract.py)
- [challenge/student/preprocess.py](../../../challenge/student/preprocess.py)

静态 import 消费者（含测试）：

- [challenge/planner/student_backend.py](../../../challenge/planner/student_backend.py)
- [challenge/tests/test_a1_student.py](../../../challenge/tests/test_a1_student.py)

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-planner.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/planner/student_adapter.py`

来源 SHA256：`63b0bf00f8c5335c94c498eaa662f971fe0b66f395573dad8da6b3748973ca19`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `StudentPlanAdapter.decode` / 35 | `missing or extra` | `raise ValueError(f'Student V0 output dict mismatch: missing={missing}, extra={extra}')` |
