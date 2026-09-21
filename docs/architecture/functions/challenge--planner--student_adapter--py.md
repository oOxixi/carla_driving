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

将 batch1 十个 Student Head 解码并约束修复为 ManeuverPlan V2。它会覆盖部分模型预测（可行行为、completion、速度上限、STOP截断），因此原始 Head 精度与最终计划通过率必须分别评估。

### `StudentPlanAdapter.__init__`

源码位置：[challenge/planner/student_adapter.py 第 24 行](../../../challenge/planner/student_adapter.py#L24)。类型：`FunctionDef`。

```python
StudentPlanAdapter.__init__(self, *, model_id: str='student-v0-r3-fp32') -> None
```

只保存写入最终计划的 `model_id`，默认 `student-v0-r3-fp32`；不加载模型、权重或配置，也不验证该 ID 与 outputs 来源一致，身份绑定由 Backend manifest 承担。

### `StudentPlanAdapter.decode`

源码位置：[challenge/planner/student_adapter.py 第 27 行](../../../challenge/planner/student_adapter.py#L27)。类型：`FunctionDef`。

```python
StudentPlanAdapter.decode(self, request: Mapping[str, Any], outputs: Mapping[str, Tensor]) -> dict[str, Any]
```

先要求 outputs 的键与 `OUTPUT_NAMES` 完全一致，再仅解码 batch索引0。plan length argmax+1并夹到Head步数；must_stop强制单步STOP。每步按允许行为/能力筛选、恢复目标指针、限制速度、替换相容completion并组装前置条件；STOP/HOLD/PULL_OVER立即截断。confidence夹[0,1]，无可行动作、确认logit≥0或confidence<0.8触发确认；replan取非负logit前8项。deadline不晚于created时仅补1 ns。

### `_best_allowed`

源码位置：[challenge/planner/student_adapter.py 第 121 行](../../../challenge/planner/student_adapter.py#L121)。类型：`FunctionDef`。

```python
_best_allowed(logits: Tensor, names: Sequence[str], allowed: set[str]) -> str
```

按 logits 降序返回第一个在 allowed 集合中的枚举；没有交集时回退 HOLD。调用方需据此设置 forced confirmation，否则 HOLD 可能并非请求原允许项。

### `_feasible_behaviors`

源码位置：[challenge/planner/student_adapter.py 第 129 行](../../../challenge/planner/student_adapter.py#L129)。类型：`FunctionDef`。

```python
_feasible_behaviors(request: Mapping[str, Any], allowed: set[str]) -> set[str]
```

从已展开允许行为开始：无 targets 删除 FOLLOW/AVOID；缺相邻车道或 gap-safe 删除对应换道；无路线删除转弯/回原道；无路口删除转弯；available_lanes 不含 SHOULDER 删除 PULL_OVER。缺可选 capability 默认按不可行处理，属于保守降级。

### `_plan_id`

源码位置：[challenge/planner/student_adapter.py 第 154 行](../../../challenge/planner/student_adapter.py#L154)。类型：`FunctionDef`。

```python
_plan_id(request_id: str) -> str
```

用完整 request_id 的 SHA256 前12位构造稳定后缀，并只保留 request_id 前80字符，生成 `student-<prefix>-<digest>`，使最大输入仍满足 plan_id 长度约束且降低前缀截断碰撞。

### `_bounded_speed`

源码位置：[challenge/planner/student_adapter.py 第 159 行](../../../challenge/planner/student_adapter.py#L159)。类型：`FunctionDef`。

```python
_bounded_speed(predicted: float, request: Mapping[str, Any]) -> float
```

把预测速度夹在0与代码上限50 m/s、request `speed_limit_mps`、`max_target_speed_mps` 的最小值之间；空值不加入限制。最终 `PlanValidator` 还应用独立默认13.888... m/s上限。

### `_compatible_completion`

源码位置：[challenge/planner/student_adapter.py 第 169 行](../../../challenge/planner/student_adapter.py#L169)。类型：`FunctionDef`。

```python
_compatible_completion(behavior: str, predicted: str) -> str
```

对有明确完成语义的行为强制返回固定 completion：转弯/换道/停车/跟车/让行/靠边/保持/避障，以及速度类和回原道。只有未覆盖行为保留模型预测，防止不相容 Head 组合进入 Validator。

### `_step`

源码位置：[challenge/planner/student_adapter.py 第 192 行](../../../challenge/planner/student_adapter.py#L192)。类型：`FunctionDef`。

```python
_step(*, index: int, behavior: str, target: Mapping[str, Any] | None, predicted_lane: str, speed: float, completion: str, on_failure: str) -> dict[str, Any]
```

组装单步 target、preconditions、completion、timeout 和 on_failure。换道/转弯/回原道强制车道与可观测前置条件；FOLLOW/AVOID才保留 target_id；速度仅给速度类/FOLLOW；PULL_OVER 只有模型预测 SHOULDER 时写车道，否则写 null（M11-01）。timeout按转弯30s、避障/回道20s、换道12s、其他10s。

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
