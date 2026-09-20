# hard_cases：功能记录

上级模块：[模块说明](../modules/challenge-training.md) · 实现：[challenge/distillation/hard_cases.py](../../../challenge/distillation/hard_cases.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [各Head损失、mask与加权](distillation-objective.md)
- [恢复、纯权重候选与晋级身份](checkpoint-and-promotion.md)

## 功能职责与范围

Mine validation disagreements without exposing or tuning on frozen Test.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `collect_hard_cases`

源码位置：[challenge/distillation/hard_cases.py 第 14 行](../../../challenge/distillation/hard_cases.py#L14)。类型：`FunctionDef`。

```python
collect_hard_cases(batch: Mapping[str, Any], outputs: Mapping[str, torch.Tensor], *, split: str) -> list[dict[str, Any]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `write_hard_cases`

源码位置：[challenge/distillation/hard_cases.py 第 117 行](../../../challenge/distillation/hard_cases.py#L117)。类型：`FunctionDef`。

```python
write_hard_cases(path: str | Path, rows: list[Mapping[str, Any]]) -> Path
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `write_hard_case_bundle`

源码位置：[challenge/distillation/hard_cases.py 第 126 行](../../../challenge/distillation/hard_cases.py#L126)。类型：`FunctionDef`。

```python
write_hard_case_bundle(directory: str | Path, rows: list[Mapping[str, Any]]) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `collect_hard_cases` 调用：`(predicted_speed[index] - labels['target_speed_mps'][index].cpu()).abs`, `ValueError`, `active.sum`, `active.sum().item`, `batch['requests'][index].get`, `batch['teacher_plans'][index].get`, `bool`, `categories.append`, `comparisons.items`, `enumerate`, `failed.any`, `failed.nonzero`, `failed.nonzero().flatten`, `failed.nonzero().flatten().tolist`, `failed_speed.any`, `failed_speed.nonzero`, `failed_speed.nonzero().flatten`, `failed_speed.nonzero().flatten().tolist`, `int`, `labels['behavior'][index].cpu`, `labels['behavior'][index].cpu().tolist`, `labels['completion_type'][index].cpu`, `labels['completion_type'][index].cpu().tolist`, `labels['on_failure'][index].cpu`, `labels['on_failure'][index].cpu().tolist`, `labels['plan_length'][index].cpu`, `labels['plan_length'][index].cpu().item`, `labels['replan_conditions'][index].bool`, `labels['replan_conditions'][index].bool().cpu`, `labels['requires_confirmation'][index].cpu`, `labels['requires_confirmation'][index].cpu().item`, `labels['step_mask'].bool`, `labels['target_lane'][index].cpu`, `labels['target_lane'][index].cpu().tolist`, `labels['target_pointer'][index].cpu`, `labels['target_pointer'][index].cpu().tolist`, `labels['target_speed_mask'][index].bool`, `labels['target_speed_mask'][index].bool().cpu`, `labels['target_speed_mps'][index].cpu`, `len`, `mask[index].cpu`, `outputs['behavior_logits'].argmax`, `outputs['behavior_logits'].argmax(-1).cpu`, `outputs['completion_type_logits'].argmax`, `outputs['completion_type_logits'].argmax(-1).cpu`, `outputs['on_failure_logits'].argmax`, `outputs['on_failure_logits'].argmax(-1).cpu`, `outputs['plan_length_logits'].argmax`, `outputs['plan_length_logits'].argmax(-1).cpu`, `outputs['replan_condition_logits'].ge`, `outputs['replan_condition_logits'].ge(0).cpu`, `outputs['requires_confirmation_logits'].reshape`, `outputs['requires_confirmation_logits'].reshape(-1).ge`, `outputs['requires_confirmation_logits'].reshape(-1).ge(0).cpu`, `outputs['target_lane_logits'].argmax`, `outputs['target_lane_logits'].argmax(-1).cpu`, `outputs['target_pointer_logits'].argmax`, `outputs['target_pointer_logits'].argmax(-1).cpu`, `outputs['target_speed_mps'].cpu`, `predicted.ne`, `predicted_behavior[index].tolist`, `predicted_completion[index].tolist`, `predicted_confirmation[index].item`, `predicted_failure[index].tolist`, `predicted_lane[index].tolist`, `predicted_plan_length[index].item`, `predicted_target[index].tolist`, `rows.append`, `speed_error.gt`, `split.strip`, `split.strip().lower`, `str`, `tags.append`, `torch.equal`, `torch.no_grad`.
- `write_hard_cases` 调用：`Path`, `destination.open`, `destination.parent.mkdir`, `dict`, `json.dumps`, `stream.write`.
- `write_hard_case_bundle` 调用：`Counter`, `Path`, `category_counts.items`, `category_directory.glob`, `category_directory.is_dir`, `destination.parent.mkdir`, `destination.write_text`, `dict`, `json.dumps`, `len`, `row.get`, `sorted`, `stale.unlink`, `str`, `tag_counts.items`, `write_hard_cases`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `collect_hard_cases`，第 22 行：`ValueError('hard-case mining is forbidden on frozen Test data')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [challenge/distillation/train.py](../../../challenge/distillation/train.py)

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-training.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/distillation/hard_cases.py`

来源 SHA256：`4eef70e2b711101a697d91f61e14a10dc5662e9f471110234714c929c4eb2dbf`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `collect_hard_cases` / 22 | `'test' in normalized_split or 'frozen' in normalized_split` | `raise ValueError('hard-case mining is forbidden on frozen Test data')` |
