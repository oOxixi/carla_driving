# validate_a1_inputs：功能记录

上级模块：[模块说明](../modules/challenge-training.md) · 实现：[challenge/distillation/validate_a1_inputs.py](../../../challenge/distillation/validate_a1_inputs.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [各Head损失、mask与加权](distillation-objective.md)
- [恢复、纯权重候选与晋级身份](checkpoint-and-promotion.md)

## 功能职责与范围

Decode every A3 D2 Train/Val sample through A1's real four-modal packer.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `check_packed_batch`

源码位置：[challenge/distillation/validate_a1_inputs.py 第 25 行](../../../challenge/distillation/validate_a1_inputs.py#L25)。类型：`FunctionDef`。

```python
check_packed_batch(batch: Mapping[str, Any], expected_size: int) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `validate_inputs`

源码位置：[challenge/distillation/validate_a1_inputs.py 第 39 行](../../../challenge/distillation/validate_a1_inputs.py#L39)。类型：`FunctionDef`。

```python
validate_inputs(release_dir: Path, view_dir: Path, asset_root: Path, *, batch_size: int=8, max_errors: int=20) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[challenge/distillation/validate_a1_inputs.py 第 101 行](../../../challenge/distillation/validate_a1_inputs.py#L101)。类型：`FunctionDef`。

```python
main() -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `check_packed_batch` 调用：`EXPECTED_SHAPES.items`, `ValueError`, `set`, `sorted`, `torch.is_tensor`, `torch.isfinite`, `torch.isfinite(value).all`, `torch.isfinite(value).all().item`, `tuple`.
- `validate_inputs` 调用：`DistillationDataset`, `ValueError`, `any`, `audit_view`, `build_a1_input_packer`, `check_packed_batch`, `collate`, `len`, `load_jsonl`, `make_collate_fn`, `min`, `range`, `rows[index].get`, `samples.append`, `str`, `summary['errors'].append`, `summary['splits'].values`.
- `main` 调用：`Path`, `argparse.ArgumentParser`, `args.output.parent.mkdir`, `args.output.write_text`, `json.dumps`, `parser.add_argument`, `parser.parse_args`, `print`, `validate_inputs`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `check_packed_batch`，第 28 行：`ValueError(f'A1 modalities mismatch: {sorted(inputs)}')`。
- `check_packed_batch`，第 32 行：`ValueError(f'A1 {name} has wrong shape')`。
- `check_packed_batch`，第 34 行：`ValueError(f'A1 {name} contains non-finite values')`。
- `check_packed_batch`，第 36 行：`ValueError('A3 step mask has wrong shape')`。
- `validate_inputs`，第 48 行：`ValueError('batch_size and max_errors must be positive')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 103 行：`parser.add_argument('--release-dir', type=Path, default=Path('challenge/dataset/releases/d2_v1_1'))`。
- 第 104 行：`parser.add_argument('--view-dir', type=Path, default=Path('artifacts/a3_d2_v1_1_positive_view_v1'))`。
- 第 105 行：`parser.add_argument('--asset-root', type=Path, default=Path('.'))`。
- 第 106 行：`parser.add_argument('--batch-size', type=int, default=8)`。
- 第 107 行：`parser.add_argument('--output', type=Path, default=Path('artifacts/a3_d2_prep/a1_full_input_check.json'))`。

## 上下游与关联验证

静态导入的项目内实现：

- [challenge/distillation/a1_student.py](../../../challenge/distillation/a1_student.py)
- [challenge/distillation/audit_d2_view.py](../../../challenge/distillation/audit_d2_view.py)
- [challenge/distillation/dataset.py](../../../challenge/distillation/dataset.py)

静态 import 消费者（含测试）：

- [challenge/distillation/tests/test_validate_a1_inputs.py](../../../challenge/distillation/tests/test_validate_a1_inputs.py)

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-training.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/distillation/validate_a1_inputs.py`

来源 SHA256：`661c534374e5f275f32782d4f2ddeecbf9d85fec54b4fbca7cb304001b7da6db`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 103 | `'--release-dir'` | `type=Path; default=Path('challenge/dataset/releases/d2_v1_1')` |
| 104 | `'--view-dir'` | `type=Path; default=Path('artifacts/a3_d2_v1_1_positive_view_v1')` |
| 105 | `'--asset-root'` | `type=Path; default=Path('.')` |
| 106 | `'--batch-size'` | `type=int; default=8` |
| 107 | `'--output'` | `type=Path; default=Path('artifacts/a3_d2_prep/a1_full_input_check.json')` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `check_packed_batch` / 28 | `set(inputs) != set(EXPECTED_SHAPES)` | `raise ValueError(f'A1 modalities mismatch: {sorted(inputs)}')` |
| `check_packed_batch` / 32 | `not torch.is_tensor(value) or tuple(value.shape) != (expected_size, *shape)` | `raise ValueError(f'A1 {name} has wrong shape')` |
| `check_packed_batch` / 34 | `not torch.isfinite(value).all().item()` | `raise ValueError(f'A1 {name} contains non-finite values')` |
| `check_packed_batch` / 36 | `batch['labels']['step_mask'].shape != (expected_size, 4)` | `raise ValueError('A3 step mask has wrong shape')` |
| `validate_inputs` / 48 | `batch_size < 1 or max_errors < 1` | `raise ValueError('batch_size and max_errors must be positive')` |
