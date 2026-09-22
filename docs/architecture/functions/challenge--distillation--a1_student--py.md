# a1_student：功能记录

上级模块：[模块说明](../modules/challenge-training.md) · 实现：[challenge/distillation/a1_student.py](../../../challenge/distillation/a1_student.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [各Head损失、mask与加权](distillation-objective.md)
- [恢复、纯权重候选与晋级身份](checkpoint-and-promotion.md)

## 功能职责与范围

A1 Student V0 construction and fixed four-modal batch packing for A3.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `A1StudentInputPacker`

源码位置：[challenge/distillation/a1_student.py 第 12 行](../../../challenge/distillation/a1_student.py#L12)。类型：`ClassDef`。

`A1StudentInputPacker` 蒸馏训练类，封装Dataset、模型、标签、loss或错误合同；Head顺序、shape与训练身份受冻结Student契约约束。

### `A1StudentInputPacker.__init__`

源码位置：[challenge/distillation/a1_student.py 第 13 行](../../../challenge/distillation/a1_student.py#L13)。类型：`FunctionDef`。

```python
A1StudentInputPacker.__init__(self, *, max_steps: int=4, max_targets: int=8) -> None
```

`__init__` 固化本对象的训练结构、配置或依赖，并执行源码中的初始一致性检查；后续批次仍必须保持shape、device、dtype和身份一致。

### `A1StudentInputPacker.__call__`

源码位置：[challenge/distillation/a1_student.py 第 18 行](../../../challenge/distillation/a1_student.py#L18)。类型：`FunctionDef`。

```python
A1StudentInputPacker.__call__(self, requests: Sequence[Mapping[str, Any]]) -> dict[str, torch.Tensor]
```

`__call__` 实现本文件对应的蒸馏、评测或候选处理子步骤；具体输入、mask、拒绝条件和副作用见本页签名/异常/调用表。

### `build_a1_input_packer`

源码位置：[challenge/distillation/a1_student.py 第 30 行](../../../challenge/distillation/a1_student.py#L30)。类型：`FunctionDef`。

```python
build_a1_input_packer(config: Mapping[str, Any] | None=None) -> A1StudentInputPacker
```

`build_a1_input_packer` 构造模型、输入打包器、mock样本或标签所需对象；mock/integration smoke只验证链路，禁止作为正式训练或晋级精度证据。

### `build_a1_student`

源码位置：[challenge/distillation/a1_student.py 第 40 行](../../../challenge/distillation/a1_student.py#L40)。类型：`FunctionDef`。

```python
build_a1_student(config: Mapping[str, Any] | None=None) -> StudentPlannerV0
```

`build_a1_student` 构造模型、输入打包器、mock样本或标签所需对象；mock/integration smoke只验证链路，禁止作为正式训练或晋级精度证据。

### `_require_frozen_shape`

源码位置：[challenge/distillation/a1_student.py 第 53 行](../../../challenge/distillation/a1_student.py#L53)。类型：`FunctionDef`。

```python
_require_frozen_shape(*, max_steps: int, max_targets: int) -> None
```

`_require_frozen_shape` 核对训练输入、冻结身份或候选证据；只覆盖显式检查项，不能用通过结果替代Student权重、样本清单和Teacher provenance的完整绑定。

## 内部调用与异常路径

- `build_a1_input_packer` 调用：`', '.join`, `A1StudentInputPacker`, `ValueError`, `dict`, `set`, `set(raw).difference`, `sorted`.
- `build_a1_student` 调用：`', '.join`, `StudentPlannerV0`, `StudentShapeContract`, `ValueError`, `_require_frozen_shape`, `dict`, `int`, `raw.get`, `set`, `set(raw).difference`, `sorted`.
- `_require_frozen_shape` 调用：`ValueError`, `int`.
- `__init__` 调用：`StudentPreprocessor`, `StudentShapeContract`, `_require_frozen_shape`.
- `__call__` 调用：`ValueError`, `self.preprocessor`, `torch.cat`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__call__`，第 20 行：`ValueError('A1 input packer requires at least one ModelRequest')`。
- `_require_frozen_shape`，第 55 行：`ValueError('A1 Student V0 is frozen at max_steps=4 and max_targets=8')`。
- `build_a1_input_packer`，第 36 行：`ValueError('unknown A1 input option(s): ' + ', '.join(sorted(unknown)))`。
- `build_a1_student`，第 44 行：`ValueError('unknown A1 Student option(s): ' + ', '.join(sorted(unknown)))`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [challenge/student/__init__.py](../../../challenge/student/__init__.py)

静态 import 消费者（含测试）：

- [challenge/distillation/ablation_eval.py](../../../challenge/distillation/ablation_eval.py)
- [challenge/distillation/tests/test_a1_integration.py](../../../challenge/distillation/tests/test_a1_integration.py)
- [challenge/distillation/tests/test_b1_smoke_integration.py](../../../challenge/distillation/tests/test_b1_smoke_integration.py)
- [challenge/distillation/tests/test_validate_a1_inputs.py](../../../challenge/distillation/tests/test_validate_a1_inputs.py)
- [challenge/distillation/validate_a1_inputs.py](../../../challenge/distillation/validate_a1_inputs.py)

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-training.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/distillation/a1_student.py`

来源 SHA256：`0b2f26c3de511ac142acde9e5713067cc132bb0f3b58c5f849c0675e1196a60c`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `A1StudentInputPacker.__call__` / 20 | `not requests` | `raise ValueError('A1 input packer requires at least one ModelRequest')` |
| `build_a1_input_packer` / 36 | `unknown` | `raise ValueError('unknown A1 input option(s): ' + ', '.join(sorted(unknown)))` |
| `build_a1_student` / 44 | `unknown` | `raise ValueError('unknown A1 Student option(s): ' + ', '.join(sorted(unknown)))` |
| `_require_frozen_shape` / 55 | `int(max_steps) != 4 or int(max_targets) != 8` | `raise ValueError('A1 Student V0 is frozen at max_steps=4 and max_targets=8')` |
