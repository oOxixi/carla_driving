# ablation_eval：功能记录

上级模块：[模块说明](../modules/challenge-training.md) · 实现：[challenge/distillation/ablation_eval.py](../../../challenge/distillation/ablation_eval.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [各Head损失、mask与加权](distillation-objective.md)
- [恢复、纯权重候选与晋级身份](checkpoint-and-promotion.md)

## 功能职责与范围

Read-only A3 Validation modality ablations for an existing FP32 checkpoint.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `masked_batches`

源码位置：[challenge/distillation/ablation_eval.py 第 25 行](../../../challenge/distillation/ablation_eval.py#L25)。类型：`FunctionDef`。

```python
masked_batches(batches: Iterable[dict[str, Any]], modality: str) -> Iterable[dict[str, Any]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `run_ablation`

源码位置：[challenge/distillation/ablation_eval.py 第 38 行](../../../challenge/distillation/ablation_eval.py#L38)。类型：`FunctionDef`。

```python
run_ablation(config_path: Path, output_dir: Path) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[challenge/distillation/ablation_eval.py 第 105 行](../../../challenge/distillation/ablation_eval.py#L105)。类型：`FunctionDef`。

```python
main() -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `masked_batches` 调用：`ValueError`, `torch.zeros_like`.
- `run_ablation` 调用：`DataLoader`, `DistillationDataset`, `LossWeights.from_mapping`, `MultiHeadDistillationLoss`, `Path`, `ValueError`, `audit_view`, `build_a1_input_packer`, `build_a1_student`, `config_path.read_text`, `evaluate`, `int`, `json.loads`, `len`, `load_checkpoint`, `load_jsonl`, `make_collate_fn`, `masked_batches`, `metrics.items`, `model.to`, `results.items`, `sha256_file`, `str`, `summary.get`, `summary_path.read_text`, `torch.cuda.is_available`, `torch.device`, `yaml.safe_load`.
- `main` 调用：`Path`, `argparse.ArgumentParser`, `args.output.parent.mkdir`, `args.output.write_text`, `json.dumps`, `metrics.items`, `parser.add_argument`, `parser.parse_args`, `print`, `report['metrics'].items`, `run_ablation`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `masked_batches`，第 27 行：`ValueError(f'unknown modality: {modality}')`。
- `run_ablation`，第 56 行：`ValueError('checkpoint is not a matching clean formal A3 candidate')`。
- `run_ablation`，第 59 行：`ValueError('best checkpoint hash mismatch')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 107 行：`parser.add_argument('--config', type=Path, default=Path('challenge/distillation/d2_v1_1_formal_config.yaml'))`。
- 第 108 行：`parser.add_argument('--run-dir', type=Path, default=Path('artifacts/challenge/distillation/d2_v1_1_fp32_baseline_v1'))`。
- 第 109 行：`parser.add_argument('--output', type=Path, default=Path('artifacts/a3_d2_prep/modality_ablation.json'))`。

## 上下游与关联验证

静态导入的项目内实现：

- [challenge/distillation/a1_student.py](../../../challenge/distillation/a1_student.py)
- [challenge/distillation/audit_d2_view.py](../../../challenge/distillation/audit_d2_view.py)
- [challenge/distillation/checkpoint.py](../../../challenge/distillation/checkpoint.py)
- [challenge/distillation/dataset.py](../../../challenge/distillation/dataset.py)
- [challenge/distillation/evaluate.py](../../../challenge/distillation/evaluate.py)
- [challenge/distillation/losses.py](../../../challenge/distillation/losses.py)

静态 import 消费者（含测试）：

- [challenge/distillation/tests/test_ablation_eval.py](../../../challenge/distillation/tests/test_ablation_eval.py)

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-training.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/distillation/ablation_eval.py`

来源 SHA256：`aa22a8e9fd2b9faf6cf2ca1a9731a1f96c0f3a1daac29297ca2d67fb34a5a38c`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 107 | `'--config'` | `type=Path; default=Path('challenge/distillation/d2_v1_1_formal_config.yaml')` |
| 108 | `'--run-dir'` | `type=Path; default=Path('artifacts/challenge/distillation/d2_v1_1_fp32_baseline_v1')` |
| 109 | `'--output'` | `type=Path; default=Path('artifacts/a3_d2_prep/modality_ablation.json')` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `masked_batches` / 27 | `modality not in MODALITIES` | `raise ValueError(f'unknown modality: {modality}')` |
| `run_ablation` / 56 | `summary.get('git_dirty') is not False or summary.get('integration_smoke_only') is not False or summary.get('smoke_only') is not False or (summary.get('candidate_gate_status') != 'PENDING_A3_FP32_GATE') or (summary.get('a3_view_manifest_sha256') != audit['view_manifest_sha256']) or (summary.get('release_manifest_sha256') != audit['release_manifest_sha256']) or (summary.get('config_id') != cfg['config_id'])` | `raise ValueError('checkpoint is not a matching clean formal A3 candidate')` |
| `run_ablation` / 59 | `sha256_file(checkpoint) != summary['best_checkpoint_sha256']` | `raise ValueError('best checkpoint hash mismatch')` |
