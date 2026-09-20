# student_contract：功能记录

上级模块：[模块说明](../modules/challenge-training.md) · 实现：[challenge/distillation/student_contract.py](../../../challenge/distillation/student_contract.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [各Head损失、mask与加权](distillation-objective.md)
- [恢复、纯权重候选与晋级身份](checkpoint-and-promotion.md)

## 功能职责与范围

Runtime gate for the A1 Student/A3 trainer handoff.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `validate_student_outputs`

源码位置：[challenge/distillation/student_contract.py 第 19 行](../../../challenge/distillation/student_contract.py#L19)。类型：`FunctionDef`。

```python
validate_student_outputs(outputs: Mapping[str, Tensor], labels: Mapping[str, Tensor], *, max_targets: int) -> None
```

Raise a focused error before malformed Student heads reach the loss.

### `validate_finite_gradients`

源码位置：[challenge/distillation/student_contract.py 第 63 行](../../../challenge/distillation/student_contract.py#L63)。类型：`FunctionDef`。

```python
validate_finite_gradients(model: torch.nn.Module) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `forward_student`

源码位置：[challenge/distillation/student_contract.py 第 72 行](../../../challenge/distillation/student_contract.py#L72)。类型：`FunctionDef`。

```python
forward_student(model: torch.nn.Module, model_inputs: Mapping[str, Any]) -> Mapping[str, Tensor]
```

Call either the frozen A1 four-input model or the D1 mapping-style dummy.

## 内部调用与异常路径

- `validate_student_outputs` 调用：`', '.join`, `TypeError`, `ValueError`, `expected.items`, `isinstance`, `len`, `set`, `set(expected).difference`, `sorted`, `torch.is_tensor`, `torch.isfinite`, `torch.isfinite(value).all`, `tuple`, `value.is_floating_point`.
- `validate_finite_gradients` 调用：`', '.join`, `RuntimeError`, `bad.append`, `model.named_parameters`, `torch.isfinite`, `torch.isfinite(parameter.grad).all`.
- `forward_student` 调用：`all`, `model`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `validate_finite_gradients`，第 69 行：`RuntimeError('non-finite Student gradient(s): ' + ', '.join(bad[:20]))`。
- `validate_student_outputs`，第 27 行：`TypeError('Student forward must return a mapping of named heads')`。
- `validate_student_outputs`，第 43 行：`ValueError('Student output is missing head(s): ' + ', '.join(missing))`。
- `validate_student_outputs`，第 48 行：`TypeError(f'Student head {name!r} must be a torch.Tensor')`。
- `validate_student_outputs`，第 50 行：`ValueError(f'Student head {name!r} has shape {tuple(value.shape)}; expected {shape}')`。
- `validate_student_outputs`，第 54 行：`TypeError(f'Student head {name!r} must use a floating dtype')`。
- `validate_student_outputs`，第 56 行：`ValueError(f'Student head {name!r} is on {value.device}; labels are on {label_device}')`。
- `validate_student_outputs`，第 60 行：`ValueError(f'Student head {name!r} contains NaN or infinity')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [challenge/distillation/label_encoder.py](../../../challenge/distillation/label_encoder.py)

静态 import 消费者（含测试）：

- [challenge/distillation/evaluate.py](../../../challenge/distillation/evaluate.py)
- [challenge/distillation/tests/test_a1_integration.py](../../../challenge/distillation/tests/test_a1_integration.py)
- [challenge/distillation/tests/test_student_contract.py](../../../challenge/distillation/tests/test_student_contract.py)
- [challenge/distillation/train.py](../../../challenge/distillation/train.py)

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-training.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/distillation/student_contract.py`

来源 SHA256：`b26b01307b2d19a33319834b5c5392eecf99b863ce0a406bdbaaaedb6e1afa47`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `validate_student_outputs` / 27 | `not isinstance(outputs, Mapping)` | `raise TypeError('Student forward must return a mapping of named heads')` |
| `validate_student_outputs` / 43 | `missing` | `raise ValueError('Student output is missing head(s): ' + ', '.join(missing))` |
| `validate_student_outputs` / 48 | `not torch.is_tensor(value)` | `raise TypeError(f'Student head {name!r} must be a torch.Tensor')` |
| `validate_student_outputs` / 50 | `tuple(value.shape) != tuple(shape)` | `raise ValueError(f'Student head {name!r} has shape {tuple(value.shape)}; expected {shape}')` |
| `validate_student_outputs` / 54 | `not value.is_floating_point()` | `raise TypeError(f'Student head {name!r} must use a floating dtype')` |
| `validate_student_outputs` / 56 | `value.device != label_device` | `raise ValueError(f'Student head {name!r} is on {value.device}; labels are on {label_device}')` |
| `validate_student_outputs` / 60 | `not torch.isfinite(value).all()` | `raise ValueError(f'Student head {name!r} contains NaN or infinity')` |
| `validate_finite_gradients` / 69 | `bad` | `raise RuntimeError('non-finite Student gradient(s): ' + ', '.join(bad[:20]))` |
