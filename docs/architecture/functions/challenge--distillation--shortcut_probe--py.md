# shortcut_probe：功能记录

上级模块：[模块说明](../modules/challenge-training.md) · 实现：[challenge/distillation/shortcut_probe.py](../../../challenge/distillation/shortcut_probe.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [各Head损失、mask与加权](distillation-objective.md)
- [恢复、纯权重候选与晋级身份](checkpoint-and-promotion.md)

## 功能职责与范围

Measure how much of A3 Val can be solved by request hints without RGB.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `_first_behavior`

源码位置：[challenge/distillation/shortcut_probe.py 第 17 行](../../../challenge/distillation/shortcut_probe.py#L17)。类型：`FunctionDef`。

```python
_first_behavior(row: Mapping[str, Any]) -> str
```

`_first_behavior` 实现Dataset、批处理、过滤或报告辅助转换；它保留训练语义但不单独完成发布完整性、身份或泛化门禁。

### `_request`

源码位置：[challenge/distillation/shortcut_probe.py 第 24 行](../../../challenge/distillation/shortcut_probe.py#L24)。类型：`FunctionDef`。

```python
_request(row: Mapping[str, Any]) -> Mapping[str, Any]
```

`_request` 构造模型、输入打包器、mock样本或标签所需对象；mock/integration smoke只验证链路，禁止作为正式训练或晋级精度证据。

### `_hint_behavior`

源码位置：[challenge/distillation/shortcut_probe.py 第 31 行](../../../challenge/distillation/shortcut_probe.py#L31)。类型：`FunctionDef`。

```python
_hint_behavior(request: Mapping[str, Any]) -> str | None
```

`_hint_behavior` 实现Dataset、批处理、过滤或报告辅助转换；它保留训练语义但不单独完成发布完整性、身份或泛化门禁。

### `_plan_signature`

源码位置：[challenge/distillation/shortcut_probe.py 第 44 行](../../../challenge/distillation/shortcut_probe.py#L44)。类型：`FunctionDef`。

```python
_plan_signature(row: Mapping[str, Any], encoder: DistillationLabelEncoder) -> tuple[Any, ...]
```

`_plan_signature` 构造模型、输入打包器、mock样本或标签所需对象；mock/integration smoke只验证链路，禁止作为正式训练或晋级精度证据。

### `probe_records`

源码位置：[challenge/distillation/shortcut_probe.py 第 65 行](../../../challenge/distillation/shortcut_probe.py#L65)。类型：`FunctionDef`。

```python
probe_records(train_rows: list[Mapping[str, Any]], val_rows: list[Mapping[str, Any]]) -> dict[str, Any]
```

`probe_records` 执行评测、探针、hard-case收集或候选晋级步骤；结果必须区分Head指标、Adapter计划、闭环安全与独立数据角色。

### `main`

源码位置：[challenge/distillation/shortcut_probe.py 第 134 行](../../../challenge/distillation/shortcut_probe.py#L134)。类型：`FunctionDef`。

```python
main() -> int
```

解析训练、评测或晋级命令行参数，调用对应门禁并用退出码表达成功/拒绝；生成报告或候选不自动等于通过独立Validation或Frozen Test。

## 内部调用与异常路径

- `_first_behavior` 调用：`isinstance`, `row.get`, `str`, `teacher.get`.
- `_request` 调用：`ValueError`, `isinstance`, `row.get`.
- `_hint_behavior` 调用：`hint.get`, `request.get`, `str`, `str(hint.get('direction') or '').upper`, `str(hint.get('intent') or '').upper`.
- `_plan_signature` 调用：`_request`, `encoder.encode`, `isinstance`, `range`, `row.get`, `sum`, `teacher.get`, `tuple`.
- `probe_records` 调用：`Counter`, `DistillationLabelEncoder`, `_expanded_allowed_behaviors`, `_first_behavior`, `_hint_behavior`, `_plan_signature`, `_request`, `int`, `iter`, `len`, `next`, `plans_for_text.most_common`, `row.get`, `row.get('metadata', {}).get`, `str`, `text_plan_counts.get`, `text_plan_counts.setdefault`, `train_first.most_common`.
- `main` 调用：`Path`, `argparse.ArgumentParser`, `args.output.parent.mkdir`, `args.output.write_text`, `json.dumps`, `load_jsonl`, `parser.add_argument`, `parser.parse_args`, `print`, `probe_records`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `_request`，第 27 行：`ValueError('record lacks ModelRequest V1')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 136 行：`parser.add_argument('--view-dir', type=Path, default=Path('artifacts/a3_d2_v1_1_positive_view_v1'))`。
- 第 137 行：`parser.add_argument('--output', type=Path, default=Path('artifacts/a3_d2_prep/shortcut_probe.json'))`。

## 上下游与关联验证

静态导入的项目内实现：

- [challenge/distillation/dataset.py](../../../challenge/distillation/dataset.py)
- [challenge/distillation/label_encoder.py](../../../challenge/distillation/label_encoder.py)
- [challenge/student/preprocess.py](../../../challenge/student/preprocess.py)

静态 import 消费者（含测试）：

- [challenge/distillation/tests/test_shortcut_probe.py](../../../challenge/distillation/tests/test_shortcut_probe.py)

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-training.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/distillation/shortcut_probe.py`

来源 SHA256：`2c1b27087321495e33c224bea5cfb32ff24bee4fea28f55a5cf9ef259ad2f519`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 136 | `'--view-dir'` | `type=Path; default=Path('artifacts/a3_d2_v1_1_positive_view_v1')` |
| 137 | `'--output'` | `type=Path; default=Path('artifacts/a3_d2_prep/shortcut_probe.json')` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `_request` / 27 | `not isinstance(request, Mapping)` | `raise ValueError('record lacks ModelRequest V1')` |
