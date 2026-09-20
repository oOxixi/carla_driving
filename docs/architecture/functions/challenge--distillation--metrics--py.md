# metrics：功能记录

上级模块：[模块说明](../modules/challenge-training.md) · 实现：[challenge/distillation/metrics.py](../../../challenge/distillation/metrics.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [各Head损失、mask与加权](distillation-objective.md)
- [恢复、纯权重候选与晋级身份](checkpoint-and-promotion.md)

## 功能职责与范围

Per-head validation metrics for Student plans.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `compute_batch_metrics`

源码位置：[challenge/distillation/metrics.py 第 12 行](../../../challenge/distillation/metrics.py#L12)。类型：`FunctionDef`。

```python
compute_batch_metrics(outputs: Mapping[str, Tensor], labels: Mapping[str, Tensor], sample_classes: Sequence[str]) -> dict[str, float]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `metric_denominators`

源码位置：[challenge/distillation/metrics.py 第 63 行](../../../challenge/distillation/metrics.py#L63)。类型：`FunctionDef`。

```python
metric_denominators(labels: Mapping[str, Tensor], sample_classes: Sequence[str]) -> dict[str, float]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `average_metrics`

源码位置：[challenge/distillation/metrics.py 第 91 行](../../../challenge/distillation/metrics.py#L91)。类型：`FunctionDef`。

```python
average_metrics(rows: Sequence[Mapping[str, float]], weights: Sequence[Mapping[str, float]] | None=None) -> dict[str, float]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_accuracy`

源码位置：[challenge/distillation/metrics.py 第 115 行](../../../challenge/distillation/metrics.py#L115)。类型：`FunctionDef`。

```python
_accuracy(correct: Tensor, mask: Tensor) -> float
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_masked_mae`

源码位置：[challenge/distillation/metrics.py 第 120 行](../../../challenge/distillation/metrics.py#L120)。类型：`FunctionDef`。

```python
_masked_mae(predicted: Tensor, target: Tensor, mask: Tensor) -> float
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_recall`

源码位置：[challenge/distillation/metrics.py 第 127 行](../../../challenge/distillation/metrics.py#L127)。类型：`FunctionDef`。

```python
_recall(predicted: Tensor, truth: Tensor) -> float
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `compute_batch_metrics` 调用：`_accuracy`, `_masked_mae`, `_recall`, `confirmation_correct.float`, `confirmation_correct.float().mean`, `confirmation_correct.float().mean().item`, `labels['replan_conditions'].bool`, `labels['requires_confirmation'].bool`, `labels['step_mask'].bool`, `labels['target_speed_mask'].bool`, `outputs['behavior_logits'].argmax`, `outputs['behavior_logits'].argmax(-1).eq`, `outputs['completion_type_logits'].argmax`, `outputs['completion_type_logits'].argmax(-1).eq`, `outputs['on_failure_logits'].argmax`, `outputs['on_failure_logits'].argmax(-1).eq`, `outputs['plan_length_logits'].argmax`, `outputs['plan_length_logits'].argmax(-1).eq`, `outputs['replan_condition_logits'].ge`, `outputs['requires_confirmation_logits'].reshape`, `outputs['requires_confirmation_logits'].reshape(-1).ge`, `outputs['requires_confirmation_logits'].reshape(-1).ge(0).eq`, `outputs['target_lane_logits'].argmax`, `outputs['target_lane_logits'].argmax(-1).eq`, `outputs['target_pointer_logits'].argmax`, `outputs['target_pointer_logits'].argmax(-1).eq`, `per_sample_steps_correct.all`, `plan_length_correct.float`, `plan_length_correct.float().mean`, `plan_length_correct.float().mean().item`, `sequence_correct.float`, `sequence_correct.float().mean`, `sequence_correct.float().mean().item`, `torch.tensor`, `torch.tensor([item == 'safety_critical' for item in sample_classes], dtype=torch.bool, device=mask.device).unsqueeze`.
- `metric_denominators` 调用：`(labels['target_speed_mask'].bool() & mask).sum`, `(labels['target_speed_mask'].bool() & mask).sum().item`, `enumerate`, `float`, `int`, `labels['replan_conditions'].bool`, `labels['replan_conditions'].bool().sum`, `labels['replan_conditions'].bool().sum().item`, `labels['step_mask'].bool`, `labels['target_speed_mask'].bool`, `mask.sum`, `mask.sum().item`, `mask[index].sum`, `mask[index].sum().item`, `sum`.
- `average_metrics` 调用：`ValueError`, `float`, `len`, `math.isfinite`, `set`, `set.intersection`, `sorted`, `sum`, `weight.get`, `zip`.
- `_accuracy` 调用：`(correct & mask).float`, `(correct & mask).float().sum`, `(correct & mask).float().sum().item`, `float`, `int`, `mask.sum`, `mask.sum().item`.
- `_masked_mae` 调用：`(predicted.sub(target).abs() * mask).sum`, `(predicted.sub(target).abs() * mask).sum().item`, `float`, `int`, `mask.sum`, `mask.sum().item`, `predicted.sub`, `predicted.sub(target).abs`.
- `_recall` 调用：`(predicted & truth).sum`, `(predicted & truth).sum().item`, `float`, `int`, `truth.sum`, `truth.sum().item`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `average_metrics`，第 100 行：`ValueError('metric rows and weight rows must have the same length')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [challenge/distillation/evaluate.py](../../../challenge/distillation/evaluate.py)

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-training.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/distillation/metrics.py`

来源 SHA256：`ee4374378b8fc9b5648f01cab6d52b39895baa12a149549092e29767b92da3fa`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `average_metrics` / 100 | `len(weight_rows) != len(rows)` | `raise ValueError('metric rows and weight rows must have the same length')` |
