# class_balance：功能记录

上级模块：[模块说明](../modules/challenge-training.md) · 实现：[challenge/distillation/class_balance.py](../../../challenge/distillation/class_balance.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [各Head损失、mask与加权](distillation-objective.md)
- [恢复、纯权重候选与晋级身份](checkpoint-and-promotion.md)

## 功能职责与范围

Optional Train-only class weighting for imbalanced structured labels.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `compute_class_weights`

源码位置：[challenge/distillation/class_balance.py 第 26 行](../../../challenge/distillation/class_balance.py#L26)。类型：`FunctionDef`。

```python
compute_class_weights(samples: Iterable[Mapping[str, Any]], *, heads: Sequence[str], max_steps: int, max_targets: int, smoothing: float=1.0, max_weight: float=5.0) -> tuple[dict[str, list[float]], dict[str, list[int]]]
```

Compute bounded inverse-frequency weights from Train labels only.

## 内部调用与异常路径

- `compute_class_weights` 调用：`', '.join`, `Counter`, `ValueError`, `float`, `int`, `len`, `max`, `min`, `range`, `set`, `set(heads).difference`, `sorted`, `sum`, `zip`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `compute_class_weights`，第 37 行：`ValueError('smoothing must be positive and max_weight must be >= 1')`。
- `compute_class_weights`，第 40 行：`ValueError('unsupported class-balance head(s): ' + ', '.join(sorted(unknown)))`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [challenge/distillation/label_encoder.py](../../../challenge/distillation/label_encoder.py)

静态 import 消费者（含测试）：

- [challenge/distillation/tests/test_losses.py](../../../challenge/distillation/tests/test_losses.py)
- [challenge/distillation/train.py](../../../challenge/distillation/train.py)

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-training.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/distillation/class_balance.py`

来源 SHA256：`e3dd6d077852231a45055fd8ae4dd06dbb1f85569150571760f5f9094f4e89d5`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `compute_class_weights` / 37 | `smoothing <= 0.0 or max_weight < 1.0` | `raise ValueError('smoothing must be positive and max_weight must be >= 1')` |
| `compute_class_weights` / 40 | `unknown` | `raise ValueError('unsupported class-balance head(s): ' + ', '.join(sorted(unknown)))` |
