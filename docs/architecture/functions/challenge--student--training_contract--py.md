# training_contract：功能记录

上级模块：[模块说明](../modules/challenge-structure.md) · 实现：[challenge/student/training_contract.py](../../../challenge/student/training_contract.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [预处理真实变换与信息损失](student-preprocessing.md)

## 功能职责与范围

Executable padding and loss-mask rules for 1--4 step supervision.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `plan_length_to_class`

源码位置：[challenge/student/training_contract.py 第 30 行](../../../challenge/student/training_contract.py#L30)。类型：`FunctionDef`。

```python
plan_length_to_class(plan_length: Tensor, *, max_steps: int=4) -> Tensor
```

Map integer lengths 1..max_steps to zero-based classification labels.

### `build_step_mask`

源码位置：[challenge/student/training_contract.py 第 36 行](../../../challenge/student/training_contract.py#L36)。类型：`FunctionDef`。

```python
build_step_mask(plan_length: Tensor, *, max_steps: int=4) -> Tensor
```

Return bool[B,max_steps], true only where step index < plan_length.

### `padded_target_pointer_index`

源码位置：[challenge/student/training_contract.py 第 43 行](../../../challenge/student/training_contract.py#L43)。类型：`FunctionDef`。

```python
padded_target_pointer_index(contract: StudentShapeContract | None=None) -> int
```

The extra pointer class after target indices 0..max_targets-1 means NONE.

### `masked_step_mean`

源码位置：[challenge/student/training_contract.py 第 50 行](../../../challenge/student/training_contract.py#L50)。类型：`FunctionDef`。

```python
masked_step_mean(loss: Tensor, step_mask: Tensor) -> Tensor
```

Reduce a per-step loss without letting padded slots affect training.

### `_validate_plan_length`

源码位置：[challenge/student/training_contract.py 第 61 行](../../../challenge/student/training_contract.py#L61)。类型：`FunctionDef`。

```python
_validate_plan_length(plan_length: Tensor, *, max_steps: int) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `plan_length_to_class` 调用：`_validate_plan_length`, `plan_length.to`.
- `build_step_mask` 调用：`_validate_plan_length`, `indices.unsqueeze`, `plan_length.to`, `plan_length.to(dtype=torch.long).unsqueeze`, `torch.arange`.
- `padded_target_pointer_index` 调用：`StudentShapeContract`.
- `masked_step_mean` 调用：`(loss * expanded).sum`, `ValueError`, `expanded.sum`, `expanded.sum().clamp_min`, `mask.expand_as`, `mask.unsqueeze`, `step_mask.to`.
- `_validate_plan_length` 调用：`TypeError`, `ValueError`, `bool`, `torch.any`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `_validate_plan_length`，第 63 行：`ValueError('plan_length must be rank-1 [B]')`。
- `_validate_plan_length`，第 67 行：`TypeError('plan_length must use an integer dtype')`。
- `_validate_plan_length`，第 69 行：`ValueError(f'plan_length values must be in [1,{max_steps}]')`。
- `masked_step_mean`，第 53 行：`ValueError('loss first two dimensions must match step_mask [B,max_steps]')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [challenge/student/contract.py](../../../challenge/student/contract.py)

静态 import 消费者（含测试）：

- [challenge/tests/test_a1_student.py](../../../challenge/tests/test_a1_student.py)

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-structure.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/student/training_contract.py`

来源 SHA256：`3f9663e0d7baada4a19791bddf794f9c5b806bd7a35dd42df8efb9e54208d69c`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `masked_step_mean` / 53 | `loss.shape[:2] != step_mask.shape` | `raise ValueError('loss first two dimensions must match step_mask [B,max_steps]')` |
| `_validate_plan_length` / 63 | `plan_length.ndim != 1` | `raise ValueError('plan_length must be rank-1 [B]')` |
| `_validate_plan_length` / 67 | `plan_length.dtype not in {torch.int8, torch.int16, torch.int32, torch.int64, torch.uint8}` | `raise TypeError('plan_length must use an integer dtype')` |
| `_validate_plan_length` / 69 | `bool(torch.any(plan_length < 1)) or bool(torch.any(plan_length > max_steps))` | `raise ValueError(f'plan_length values must be in [1,{max_steps}]')` |
