# label_encoder：功能记录

上级模块：[模块说明](../modules/challenge-training.md) · 实现：[challenge/distillation/label_encoder.py](../../../challenge/distillation/label_encoder.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [各Head损失、mask与加权](distillation-objective.md)
- [恢复、纯权重候选与晋级身份](checkpoint-and-promotion.md)

## 功能职责与范围

Encode frozen planner contracts into fixed-shape Student supervision.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `DistillationLabelEncoder.max_steps: int`；默认：`4`。
- `DistillationLabelEncoder.max_targets: int`；默认：`8`。
- `DistillationLabelEncoder.validate_contracts: bool`；默认：`True`。

## 功能入口：输入、输出与实现说明

### `LabelEncodingError`

源码位置：[challenge/distillation/label_encoder.py 第 38 行](../../../challenge/distillation/label_encoder.py#L38)。类型：`ClassDef`。

A valid planner record cannot be represented by the Student contract.

### `DistillationLabelEncoder`

源码位置：[challenge/distillation/label_encoder.py 第 43 行](../../../challenge/distillation/label_encoder.py#L43)。类型：`ClassDef`。

`DistillationLabelEncoder` 蒸馏训练类，封装Dataset、模型、标签、loss或错误合同；Head顺序、shape与训练身份受冻结Student契约约束。

### `DistillationLabelEncoder.__post_init__`

源码位置：[challenge/distillation/label_encoder.py 第 48 行](../../../challenge/distillation/label_encoder.py#L48)。类型：`FunctionDef`。

```python
DistillationLabelEncoder.__post_init__(self) -> None
```

`__post_init__` 固化本对象的训练结构、配置或依赖，并执行源码中的初始一致性检查；后续批次仍必须保持shape、device、dtype和身份一致。

### `DistillationLabelEncoder.vocabulary`

源码位置：[challenge/distillation/label_encoder.py 第 57 行](../../../challenge/distillation/label_encoder.py#L57)。类型：`FunctionDef`。

```python
DistillationLabelEncoder.vocabulary(self) -> dict[str, tuple[str, ...]]
```

`vocabulary` 把Teacher计划和当前ModelRequest候选编码为冻结Student标签；pointer按原targets顺序，越界、ID不匹配或超长计划必须拒绝。

### `DistillationLabelEncoder.encode`

源码位置：[challenge/distillation/label_encoder.py 第 66 行](../../../challenge/distillation/label_encoder.py#L66)。类型：`FunctionDef`。

```python
DistillationLabelEncoder.encode(self, request: Mapping[str, Any], plan: Mapping[str, Any]) -> dict[str, Any]
```

`encode` 把Teacher计划和当前ModelRequest候选编码为冻结Student标签；pointer按原targets顺序，越界、ID不匹配或超长计划必须拒绝。

### `DistillationLabelEncoder._target_pointer`

源码位置：[challenge/distillation/label_encoder.py 第 145 行](../../../challenge/distillation/label_encoder.py#L145)。类型：`FunctionDef`。

```python
DistillationLabelEncoder._target_pointer(self, target_id: object, target_positions: Mapping[str, int]) -> int
```

`_target_pointer` 把Teacher计划和当前ModelRequest候选编码为冻结Student标签；pointer按原targets顺序，越界、ID不匹配或超长计划必须拒绝。

### `_category_index`

源码位置：[challenge/distillation/label_encoder.py 第 161 行](../../../challenge/distillation/label_encoder.py#L161)。类型：`FunctionDef`。

```python
_category_index(values: Sequence[str], value: object, field_name: str) -> int
```

`_category_index` 把Teacher计划和当前ModelRequest候选编码为冻结Student标签；pointer按原targets顺序，越界、ID不匹配或超长计划必须拒绝。

## 内部调用与异常路径

- `_category_index` 调用：`LabelEncodingError`, `str`, `values.index`.
- `__post_init__` 调用：`TypeError`, `ValueError`, `type`.
- `encode` 调用：`LabelEncodingError`, `_INTERFACES.validate`, `_category_index`, `bool`, `completion.get`, `dict`, `enumerate`, `float`, `len`, `list`, `plan.get`, `request.get`, `self._target_pointer`, `step.get`, `str`, `target.get`.
- `_target_pointer` 调用：`LabelEncodingError`, `str`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__post_init__`，第 50 行：`ValueError('A1 Student V0 requires max_steps=4')`。
- `__post_init__`，第 52 行：`ValueError('A1 Student V0 requires max_targets=8')`。
- `__post_init__`，第 54 行：`TypeError('validate_contracts must be bool')`。
- `_category_index`，第 168 行：`LabelEncodingError(f'unsupported {field_name} value: {normalized!r}')`。
- `_target_pointer`，第 156 行：`LabelEncodingError(f'Teacher target_id {normalized!r} is absent from ModelRequest.targets')`。
- `encode`，第 78 行：`LabelEncodingError('Teacher plan request_id does not match ModelRequest')`。
- `encode`，第 80 行：`LabelEncodingError('Teacher plan command_id does not match ModelRequest')`。
- `encode`，第 84 行：`LabelEncodingError(f'Teacher plan has {len(steps)} steps; Student supports 1..{self.max_steps}')`。
- `encode`，第 89 行：`LabelEncodingError(f'ModelRequest has {len(targets)} targets; Student supports {self.max_targets}')`。
- `encode`，第 140 行：`LabelEncodingError(f'unsupported replan condition: {condition!r}')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [challenge/student/contract.py](../../../challenge/student/contract.py)
- [runtime/interface_registry.py](../../../runtime/interface_registry.py)

静态 import 消费者（含测试）：

- [challenge/distillation/__init__.py](../../../challenge/distillation/__init__.py)
- [challenge/distillation/audit_d2_view.py](../../../challenge/distillation/audit_d2_view.py)
- [challenge/distillation/class_balance.py](../../../challenge/distillation/class_balance.py)
- [challenge/distillation/dataset.py](../../../challenge/distillation/dataset.py)
- [challenge/distillation/dummy_student.py](../../../challenge/distillation/dummy_student.py)
- [challenge/distillation/preflight.py](../../../challenge/distillation/preflight.py)
- [challenge/distillation/shortcut_probe.py](../../../challenge/distillation/shortcut_probe.py)
- [challenge/distillation/student_contract.py](../../../challenge/distillation/student_contract.py)
- [challenge/distillation/tests/test_a1_integration.py](../../../challenge/distillation/tests/test_a1_integration.py)
- [challenge/distillation/tests/test_label_encoder.py](../../../challenge/distillation/tests/test_label_encoder.py)
- [challenge/distillation/train.py](../../../challenge/distillation/train.py)

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-training.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/distillation/label_encoder.py`

来源 SHA256：`8cddfba5f86a2b37bcc74065c12fc4a75a9028c62406a854ba4193dea9f09482`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `DistillationLabelEncoder.max_steps` | `int` | `4` |
| `DistillationLabelEncoder.max_targets` | `int` | `8` |
| `DistillationLabelEncoder.validate_contracts` | `bool` | `True` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `DistillationLabelEncoder.__post_init__` / 50 | `type(self.max_steps) is not int or self.max_steps != 4` | `raise ValueError('A1 Student V0 requires max_steps=4')` |
| `DistillationLabelEncoder.__post_init__` / 52 | `type(self.max_targets) is not int or self.max_targets != 8` | `raise ValueError('A1 Student V0 requires max_targets=8')` |
| `DistillationLabelEncoder.__post_init__` / 54 | `type(self.validate_contracts) is not bool` | `raise TypeError('validate_contracts must be bool')` |
| `DistillationLabelEncoder.encode` / 78 | `request.get('request_id') != plan.get('request_id')` | `raise LabelEncodingError('Teacher plan request_id does not match ModelRequest')` |
| `DistillationLabelEncoder.encode` / 80 | `request.get('command_id') != plan.get('command_id')` | `raise LabelEncodingError('Teacher plan command_id does not match ModelRequest')` |
| `DistillationLabelEncoder.encode` / 84 | `not steps or len(steps) > self.max_steps` | `raise LabelEncodingError(f'Teacher plan has {len(steps)} steps; Student supports 1..{self.max_steps}')` |
| `DistillationLabelEncoder.encode` / 89 | `len(targets) > self.max_targets` | `raise LabelEncodingError(f'ModelRequest has {len(targets)} targets; Student supports {self.max_targets}')` |
| `DistillationLabelEncoder.encode` / 140 | `except KeyError` | `raise LabelEncodingError(f'unsupported replan condition: {condition!r}') from error` |
| `DistillationLabelEncoder._target_pointer` / 156 | `except KeyError` | `raise LabelEncodingError(f'Teacher target_id {normalized!r} is absent from ModelRequest.targets') from error` |
| `_category_index` / 168 | `except ValueError` | `raise LabelEncodingError(f'unsupported {field_name} value: {normalized!r}') from error` |
