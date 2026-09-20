# evaluate：功能记录

上级模块：[模块说明](../modules/challenge-training.md) · 实现：[challenge/distillation/evaluate.py](../../../challenge/distillation/evaluate.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [各Head损失、mask与加权](distillation-objective.md)
- [恢复、纯权重候选与晋级身份](checkpoint-and-promotion.md)

## 功能职责与范围

Validation loop shared by smoke training and the future A1 Student.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `evaluate`

源码位置：[challenge/distillation/evaluate.py 第 15 行](../../../challenge/distillation/evaluate.py#L15)。类型：`FunctionDef`。

```python
evaluate(model: torch.nn.Module, batches: Iterable[dict[str, Any]], loss_fn: torch.nn.Module, *, device: torch.device, max_targets: int) -> dict[str, float]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `move_batch_to_device`

源码位置：[challenge/distillation/evaluate.py 第 65 行](../../../challenge/distillation/evaluate.py#L65)。类型：`FunctionDef`。

```python
move_batch_to_device(batch: dict[str, Any], device: torch.device) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `evaluate` 调用：`average_metrics`, `class_metrics.items`, `components.items`, `compute_batch_metrics`, `enumerate`, `float`, `forward_student`, `len`, `loss_fn`, `metric_denominators`, `metrics.update`, `model.eval`, `move_batch_to_device`, `moved['labels'].items`, `name.startswith`, `outputs.items`, `rows.append`, `torch.no_grad`, `total.item`, `validate_student_outputs`, `value.item`, `weight_rows.append`, `weights.update`.
- `move_batch_to_device` 调用：`batch['labels'].items`, `batch['model_inputs'].items`, `torch.is_tensor`, `value.to`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- 未发现显式 raise；不代表运行不会失败。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [challenge/distillation/metrics.py](../../../challenge/distillation/metrics.py)
- [challenge/distillation/student_contract.py](../../../challenge/distillation/student_contract.py)

静态 import 消费者（含测试）：

- [challenge/distillation/ablation_eval.py](../../../challenge/distillation/ablation_eval.py)
- [challenge/distillation/tests/test_evaluate_class_metrics.py](../../../challenge/distillation/tests/test_evaluate_class_metrics.py)
- [challenge/distillation/train.py](../../../challenge/distillation/train.py)

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-training.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/distillation/evaluate.py`

来源 SHA256：`089089bdf88762b754de347f4c00c27004d3d9e907d63883f73925b23aaba256`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
