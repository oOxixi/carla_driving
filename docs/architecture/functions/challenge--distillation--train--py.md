# train：功能记录

上级模块：[模块说明](../modules/challenge-training.md) · 实现：[challenge/distillation/train.py](../../../challenge/distillation/train.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [各Head损失、mask与加权](distillation-objective.md)
- [恢复、纯权重候选与晋级身份](checkpoint-and-promotion.md)

## 功能职责与范围

Configuration-driven A3 distillation trainer.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `run_training`

源码位置：[challenge/distillation/train.py 第 55 行](../../../challenge/distillation/train.py#L55)。类型：`FunctionDef`。

```python
run_training(config: Mapping[str, Any], *, smoke: bool=False, output_dir_override: str | Path | None=None, resume_override: str | Path | None=None, integration_smoke: bool=False) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_validated_forward`

源码位置：[challenge/distillation/train.py 第 383 行](../../../challenge/distillation/train.py#L383)。类型：`FunctionDef`。

```python
_validated_forward(model: torch.nn.Module, batch: Mapping[str, Any], *, max_targets: int) -> Mapping[str, torch.Tensor]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_records`

源码位置：[challenge/distillation/train.py 第 394 行](../../../challenge/distillation/train.py#L394)。类型：`FunctionDef`。

```python
_records(cfg: Mapping[str, Any], *, smoke: bool, record_limit: int | None=None) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_audit_quarantined_hard_cases`

源码位置：[challenge/distillation/train.py 第 416 行](../../../challenge/distillation/train.py#L416)。类型：`FunctionDef`。

```python
_audit_quarantined_hard_cases(cfg: Mapping[str, Any], *, smoke: bool) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_build_model`

源码位置：[challenge/distillation/train.py 第 462 行](../../../challenge/distillation/train.py#L462)。类型：`FunctionDef`。

```python
_build_model(config: Mapping[str, Any], *, max_steps: int, max_targets: int) -> torch.nn.Module
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_build_input_packer`

源码位置：[challenge/distillation/train.py 第 477 行](../../../challenge/distillation/train.py#L477)。类型：`FunctionDef`。

```python
_build_input_packer(config: Mapping[str, Any] | None, *, max_steps: int, max_targets: int) -> Any
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_validate_config`

源码位置：[challenge/distillation/train.py 第 497 行](../../../challenge/distillation/train.py#L497)。类型：`FunctionDef`。

```python
_validate_config(value: Mapping[str, Any]) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_validate_frozen_identities`

源码位置：[challenge/distillation/train.py 第 515 行](../../../challenge/distillation/train.py#L515)。类型：`FunctionDef`。

```python
_validate_frozen_identities(cfg: Mapping[str, Any], *, integration_smoke: bool=False) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_device`

源码位置：[challenge/distillation/train.py 第 610 行](../../../challenge/distillation/train.py#L610)。类型：`FunctionDef`。

```python
_device(value: str) -> torch.device
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_seed_everything`

源码位置：[challenge/distillation/train.py 第 620 行](../../../challenge/distillation/train.py#L620)。类型：`FunctionDef`。

```python
_seed_everything(seed: int) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_git_sha`

源码位置：[challenge/distillation/train.py 第 632 行](../../../challenge/distillation/train.py#L632)。类型：`FunctionDef`。

```python
_git_sha() -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_git_is_dirty`

源码位置：[challenge/distillation/train.py 第 641 行](../../../challenge/distillation/train.py#L641)。类型：`FunctionDef`。

```python
_git_is_dirty() -> bool
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_strict_json`

源码位置：[challenge/distillation/train.py 第 651 行](../../../challenge/distillation/train.py#L651)。类型：`FunctionDef`。

```python
_strict_json(value: Any) -> Any
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_load_config`

源码位置：[challenge/distillation/train.py 第 661 行](../../../challenge/distillation/train.py#L661)。类型：`FunctionDef`。

```python
_load_config(path: str | Path) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[challenge/distillation/train.py 第 668 行](../../../challenge/distillation/train.py#L668)。类型：`FunctionDef`。

```python
main() -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `run_training` 调用：`(output_dir / 'quarantined_hard_cases_audit.json').write_text`, `(output_dir / 'training_summary.json').write_text`, `DataLoader`, `DistillationDataset`, `DistillationLabelEncoder`, `LossWeights.from_mapping`, `MultiHeadDistillationLoss`, `Path`, `Path(__file__).resolve`, `Path(output_dir_override or default_output).resolve`, `RuntimeError`, `ValueError`, `_audit_quarantined_hard_cases`, `_build_input_packer`, `_build_model`, `_device`, `_git_is_dirty`, `_git_sha`, `_records`, `_seed_everything`, `_strict_json`, `_validate_config`, `_validate_frozen_identities`, `_validated_forward`, `balance_cfg.get`, `best_path.is_file`, `bool`, `canonical_text_sha256`, `cfg.get`, `cfg['dataset'].get`, `cfg['distillation'].get`, `cfg['model'].get`, `cfg['model']['options'].get`, `cfg['teacher'].get`, `cfg['training'].get`, `collect_hard_cases`, `compute_class_weights`, `data_generator_state.cpu`, `dataset_cfg.get`, `deepcopy`, `evaluate`, `expected_version.startswith`, `export_candidate_weights`, `float`, `forward_student`, `generator.get_state`, `generator.set_state`, `hard_rows.extend`, `history.append`, `int`, `json.dumps`, `len`, `load_checkpoint`, `log_path.is_file`, `log_path.open`, `log_path.unlink`, `loss.backward`, `loss.item`, `loss_fn`, `make_collate_fn`, `math.isfinite`, `max`, `min`, `model.eval`, `model.parameters`, `model.to`, `model.train`, `move_batch_to_device`, `optimizer.step`, `optimizer.zero_grad`, `output_dir.mkdir`, `preflight_datasets`, `quarantined.get`, `range`, `restored.get`, `restored.get('extra_state', {}).get`, `save_checkpoint`, `sha256_file`, `str`, `stream.write`, `sum`, `torch.Generator`, `torch.Generator().manual_seed`, `torch.isfinite`, `torch.nn.utils.clip_grad_norm_`, `torch.no_grad`, `torch.optim.AdamW`, `train_losses.append`, `training.get`, `tuple`, `validate_finite_gradients`, `validate_student_outputs`, `write_hard_case_bundle`, `write_preflight_report`, `write_training_report`.
- `_validated_forward` 调用：`forward_student`, `validate_student_outputs`.
- `_records` 调用：`Path`, `Path(value).name.lower`, `ValueError`, `build_mock_records`, `dataset.get`, `float`, `int`, `len`, `load_jsonl`, `max`, `min`, `str`.
- `_audit_quarantined_hard_cases` 调用：`DistillationDataset`, `ValueError`, `cfg['dataset'].get`, `len`, `load_jsonl`, `metadata.get`, `plan.get`, `policy.get`, `reasons.get`, `record.get`, `sample_ids.append`, `str`, `str(record.get('sample_id', '')).strip`.
- `_build_model` 调用：`TypeError`, `ValueError`, `config.get`, `dict`, `factory`, `getattr`, `importlib.import_module`, `isinstance`, `options.update`, `str`, `str(config['factory']).partition`.
- `_build_input_packer` 调用：`TypeError`, `ValueError`, `callable`, `config.get`, `dict`, `factory`, `getattr`, `importlib.import_module`, `options.update`, `str`, `str(config['factory']).partition`.
- `_validate_config` 调用：`', '.join`, `ValueError`, `dict`, `int`, `required.difference`, `sorted`.
- `_validate_frozen_identities` 调用：`(repo / str(dataset_cfg['asset_root'])).resolve`, `(repo / str(dataset_cfg['release_manifest_path'])).resolve`, `(repo / str(dataset_cfg['view_manifest_path'])).resolve`, `(repo / str(dataset_cfg[config_key])).resolve`, `Path`, `Path(__file__).resolve`, `StudentModelConfig`, `ValueError`, `audit_view`, `canonical_text_sha256`, `cfg['model'].get`, `cfg['teacher'].get`, `dataset_cfg.get`, `json.loads`, `manifest_path.read_text`, `release.get`, `release_path.read_text`, `str`, `validate_release`, `view.get`, `view['cohort_manifest_shas'].items`, `view_path.read_text`.
- `_device` 调用：`RuntimeError`, `torch.cuda.is_available`, `torch.device`, `value.lower`.
- `_seed_everything` 调用：`RuntimeError`, `os.environ.get`, `random.seed`, `torch.cuda.is_available`, `torch.cuda.manual_seed_all`, `torch.manual_seed`, `torch.use_deterministic_algorithms`.
- `_git_sha` 调用：`subprocess.check_output`, `subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True, stderr=subprocess.DEVNULL).strip`.
- `_git_is_dirty` 调用：`bool`, `subprocess.check_output`, `subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=all'], text=True, stderr=subprocess.DEVNULL).strip`.
- `_strict_json` 调用：`_strict_json`, `isinstance`, `math.isfinite`, `value.items`.
- `_load_config` 调用：`Path`, `Path(path).read_text`, `ValueError`, `isinstance`, `yaml.safe_load`.
- `main` 调用：`_load_config`, `_strict_json`, `argparse.ArgumentParser`, `json.dumps`, `mode.add_argument`, `parser.add_argument`, `parser.add_mutually_exclusive_group`, `parser.parse_args`, `print`, `run_training`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `_audit_quarantined_hard_cases`，第 433 行：`ValueError('quarantined hard case is missing sample_id')`。
- `_audit_quarantined_hard_cases`，第 435 行：`ValueError(f'quarantined hard case leaked into Train/Val: {sample_id}')`。
- `_audit_quarantined_hard_cases`，第 437 行：`ValueError(f'hard case dataset version mismatch: {sample_id}')`。
- `_audit_quarantined_hard_cases`，第 441 行：`ValueError(f'hard case Teacher SHA mismatch: {sample_id}')`。
- `_audit_quarantined_hard_cases`，第 443 行：`ValueError(f'hard case Teacher model mismatch: {sample_id}')`。
- `_audit_quarantined_hard_cases`，第 446 行：`ValueError(f'hard case must be excluded from ordinary training: {sample_id}')`。
- `_audit_quarantined_hard_cases`，第 448 行：`ValueError(f'hard case policy_class is invalid: {sample_id}')`。
- `_audit_quarantined_hard_cases`，第 450 行：`ValueError(f'hard case must retain failed closed-loop evidence: {sample_id}')`。
- `_build_input_packer`，第 487 行：`ValueError('input.factory must use module:callable syntax')`。
- `_build_input_packer`，第 493 行：`TypeError('input factory must return a callable batch packer')`。
- `_build_model`，第 467 行：`ValueError('model.factory must use module:callable syntax')`。
- `_build_model`，第 473 行：`TypeError('model factory must return torch.nn.Module')`。
- `_device`，第 616 行：`RuntimeError('CUDA was requested but is unavailable')`。
- `_load_config`，第 664 行：`ValueError('training config must be a YAML object')`。
- `_records`，第 405 行：`ValueError('production training requires separate train_path and val_path')`。
- `_records`，第 408 行：`ValueError('the A3 trainer refuses frozen Test manifests')`。
- `_seed_everything`，第 622 行：`RuntimeError('deterministic CUDA training requires CUBLAS_WORKSPACE_CONFIG')`。
- `_validate_config`，第 505 行：`ValueError('missing training config keys: ' + ', '.join(sorted(missing)))`。
- `_validate_config`，第 507 行：`ValueError('ManeuverPlan V2 Student contract requires max_steps=4')`。
- `_validate_config`，第 509 行：`ValueError('max_targets must be positive')`。
- `_validate_config`，第 511 行：`ValueError('batch_size and epochs must be positive')`。
- `_validate_frozen_identities`，第 523 行：`ValueError(f'unsupported teacher identity_policy: {policy}')`。
- `_validate_frozen_identities`，第 538 行：`ValueError('signed D2 release policy is limited to integration smoke')`。
- `_validate_frozen_identities`，第 540 行：`ValueError('formal signed D2 policy cannot be used for integration smoke')`。
- `_validate_frozen_identities`，第 542 行：`ValueError('signed D2 release must identify mixed Teacher baselines')`。
- `_validate_frozen_identities`，第 545 行：`ValueError(f'signed D2 release Teacher {field} mismatch')`。
- `_validate_frozen_identities`，第 547 行：`ValueError('signed D2 release must verify Teacher identity')`。
- `_validate_frozen_identities`，第 549 行：`ValueError('signed D2 release must require pinned Teacher provenance')`。
- `_validate_frozen_identities`，第 551 行：`ValueError('signed D2 release must verify RGB')`。
- `_validate_frozen_identities`，第 556 行：`ValueError('signed D2 release view version mismatch')`。
- `_validate_frozen_identities`，第 561 行：`ValueError('B1 D2 release is not signed')`。
- `_validate_frozen_identities`，第 563 行：`ValueError('A3 view does not match signed B1 release')`。
- `_validate_frozen_identities`，第 565 行：`ValueError('B1 D2 release integrity gate failed')`。
- `_validate_frozen_identities`，第 569 行：`ValueError(f'A3 {split} path does not match signed view')`。
- `_validate_frozen_identities`，第 571 行：`ValueError(f'A3 {split} hash does not match signed view')`。
- `_validate_frozen_identities`，第 574 行：`ValueError(f'Teacher cohort manifest changed: {relative}')`。
- `_validate_frozen_identities`，第 576 行：`ValueError('signed D2 release RGB asset_root must be repository root')`。
- `_validate_frozen_identities`，第 581 行：`ValueError('legacy unpinned Teacher data is allowed only for integration smoke')`。
- `_validate_frozen_identities`，第 585 行：`ValueError('legacy Smoke must verify Teacher SHA and model ID')`。
- `_validate_frozen_identities`，第 587 行：`ValueError('legacy Smoke cannot claim pinned Teacher provenance')`。
- `_validate_frozen_identities`，第 589 行：`ValueError('legacy Smoke Teacher git_sha does not match frozen baseline')`。
- `_validate_frozen_identities`，第 591 行：`ValueError('legacy Smoke Teacher model_id does not match frozen baseline')`。
- `_validate_frozen_identities`，第 593 行：`ValueError('legacy Smoke must not claim a model revision')`。
- `_validate_frozen_identities`，第 595 行：`ValueError('legacy Smoke must not claim an artifact fingerprint')`。
- `_validate_frozen_identities`，第 598 行：`ValueError('teacher identity does not match challenge/teacher_baseline_manifest.json')`。
- `_validate_frozen_identities`，第 602 行：`ValueError('formal A3 training cannot disable Teacher identity checks')`。
- `_validate_frozen_identities`，第 604 行：`ValueError('formal A3 training requires pinned per-record provenance')`。
- `_validate_frozen_identities`，第 607 行：`ValueError('Student config_id does not match A1 V0 r3')`。
- `run_training`，第 64 行：`ValueError('mock smoke and production integration smoke are mutually exclusive')`。
- `run_training`，第 68 行：`RuntimeError('production A3 training requires a clean committed challenge worktree')`。
- `run_training`，第 92 行：`ValueError('production training requires separate train_path and val_path')`。
- `run_training`，第 95 行：`ValueError('replace dataset.version before production training')`。
- `run_training`，第 128 行：`ValueError(f"dataset preflight failed with {preflight['error_count']} error(s): {first}")`。
- `run_training`，第 270 行：`RuntimeError(f'non-finite training loss at step {global_step}')`。
- `run_training`，第 278 行：`RuntimeError(f'non-finite gradient norm at step {global_step}')`。
- `run_training`，第 289 行：`ValueError(f'unknown selection metric: {selection_metric}')`。
- `run_training`，第 326 行：`RuntimeError('training produced no finite validation candidate')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 670 行：`parser.add_argument('--config', default='challenge/distillation/train_config.yaml')`。
- 第 672 行：`mode.add_argument('--smoke', action='store_true', help='contract-valid mock pipeline')`。
- 第 673 行：`mode.add_argument('--integration-smoke', action='store_true', help='preflight all real records, then train at most 50+50 records for two updates')`。
- 第 677 行：`parser.add_argument('--output-dir')`。
- 第 678 行：`parser.add_argument('--resume')`。

## 上下游与关联验证

静态导入的项目内实现：

- [challenge/dataset/build_a3_d2_view.py](../../../challenge/dataset/build_a3_d2_view.py)
- [challenge/dataset/validate_d2_release.py](../../../challenge/dataset/validate_d2_release.py)
- [challenge/distillation/artifacts.py](../../../challenge/distillation/artifacts.py)
- [challenge/distillation/audit_d2_view.py](../../../challenge/distillation/audit_d2_view.py)
- [challenge/distillation/checkpoint.py](../../../challenge/distillation/checkpoint.py)
- [challenge/distillation/class_balance.py](../../../challenge/distillation/class_balance.py)
- [challenge/distillation/dataset.py](../../../challenge/distillation/dataset.py)
- [challenge/distillation/evaluate.py](../../../challenge/distillation/evaluate.py)
- [challenge/distillation/hard_cases.py](../../../challenge/distillation/hard_cases.py)
- [challenge/distillation/label_encoder.py](../../../challenge/distillation/label_encoder.py)
- [challenge/distillation/losses.py](../../../challenge/distillation/losses.py)
- [challenge/distillation/preflight.py](../../../challenge/distillation/preflight.py)
- [challenge/distillation/run_report.py](../../../challenge/distillation/run_report.py)
- [challenge/distillation/student_contract.py](../../../challenge/distillation/student_contract.py)
- [challenge/student/__init__.py](../../../challenge/student/__init__.py)

静态 import 消费者（含测试）：

- [challenge/distillation/tests/test_b1_smoke_integration.py](../../../challenge/distillation/tests/test_b1_smoke_integration.py)
- [challenge/distillation/tests/test_checkpoint.py](../../../challenge/distillation/tests/test_checkpoint.py)
- [challenge/distillation/tests/test_d2_v1_1_smoke_gate.py](../../../challenge/distillation/tests/test_d2_v1_1_smoke_gate.py)
- [challenge/distillation/tests/test_train_smoke.py](../../../challenge/distillation/tests/test_train_smoke.py)

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-training.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/distillation/train.py`

来源 SHA256：`bc9064760072de951233034a0e848dcec3547fab00017e3592895157d7136876`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 670 | `'--config'` | `default='challenge/distillation/train_config.yaml'` |
| 672 | `'--smoke'` | `action='store_true'; help='contract-valid mock pipeline'` |
| 673 | `'--integration-smoke'` | `action='store_true'; help='preflight all real records, then train at most 50+50 records for two updates'` |
| 677 | `'--output-dir'` | `` |
| 678 | `'--resume'` | `` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `run_training` / 64 | `smoke and integration_smoke` | `raise ValueError('mock smoke and production integration smoke are mutually exclusive')` |
| `run_training` / 68 | `not smoke and (not integration_smoke) and _git_is_dirty()` | `raise RuntimeError('production A3 training requires a clean committed challenge worktree')` |
| `run_training` / 92 | `not smoke AND not dataset_cfg.get('train_path') or not dataset_cfg.get('val_path')` | `raise ValueError('production training requires separate train_path and val_path')` |
| `run_training` / 95 | `not smoke AND expected_version.startswith('PENDING_')` | `raise ValueError('replace dataset.version before production training')` |
| `run_training` / 128 | `not smoke AND not preflight['valid']` | `raise ValueError(f"dataset preflight failed with {preflight['error_count']} error(s): {first}")` |
| `run_training` / 270 | `not torch.isfinite(loss)` | `raise RuntimeError(f'non-finite training loss at step {global_step}')` |
| `run_training` / 278 | `not torch.isfinite(gradient_norm)` | `raise RuntimeError(f'non-finite gradient norm at step {global_step}')` |
| `run_training` / 289 | `selection_metric not in validation` | `raise ValueError(f'unknown selection metric: {selection_metric}')` |
| `run_training` / 326 | `not best_path.is_file()` | `raise RuntimeError('training produced no finite validation candidate')` |
| `_records` / 405 | `not train_path or not val_path` | `raise ValueError('production training requires separate train_path and val_path')` |
| `_records` / 408 | `'test' in Path(value).name.lower() or 'frozen' in Path(value).name.lower()` | `raise ValueError('the A3 trainer refuses frozen Test manifests')` |
| `_audit_quarantined_hard_cases` / 433 | `not sample_id` | `raise ValueError('quarantined hard case is missing sample_id')` |
| `_audit_quarantined_hard_cases` / 435 | `sample_id in train_ids` | `raise ValueError(f'quarantined hard case leaked into Train/Val: {sample_id}')` |
| `_audit_quarantined_hard_cases` / 437 | `str(record.get('dataset_version')) != str(cfg['dataset']['version'])` | `raise ValueError(f'hard case dataset version mismatch: {sample_id}')` |
| `_audit_quarantined_hard_cases` / 441 | `metadata.get('teacher_git_sha') != cfg['teacher']['git_sha']` | `raise ValueError(f'hard case Teacher SHA mismatch: {sample_id}')` |
| `_audit_quarantined_hard_cases` / 443 | `(metadata.get('teacher_model_id') or plan.get('model_id')) != cfg['teacher']['model_id']` | `raise ValueError(f'hard case Teacher model mismatch: {sample_id}')` |
| `_audit_quarantined_hard_cases` / 446 | `policy.get('train_eligible') is not False` | `raise ValueError(f'hard case must be excluded from ordinary training: {sample_id}')` |
| `_audit_quarantined_hard_cases` / 448 | `policy.get('policy_class') != 'QUARANTINED_HARD_CASE'` | `raise ValueError(f'hard case policy_class is invalid: {sample_id}')` |
| `_audit_quarantined_hard_cases` / 450 | `policy.get('closed_loop_success') is not False` | `raise ValueError(f'hard case must retain failed closed-loop evidence: {sample_id}')` |
| `_build_model` / 467 | `not separator` | `raise ValueError('model.factory must use module:callable syntax')` |
| `_build_model` / 473 | `not isinstance(model, torch.nn.Module)` | `raise TypeError('model factory must return torch.nn.Module')` |
| `_build_input_packer` / 487 | `not separator` | `raise ValueError('input.factory must use module:callable syntax')` |
| `_build_input_packer` / 493 | `not callable(packer)` | `raise TypeError('input factory must return a callable batch packer')` |
| `_validate_config` / 505 | `missing` | `raise ValueError('missing training config keys: ' + ', '.join(sorted(missing)))` |
| `_validate_config` / 507 | `int(cfg['contract']['max_steps']) != 4` | `raise ValueError('ManeuverPlan V2 Student contract requires max_steps=4')` |
| `_validate_config` / 509 | `int(cfg['contract']['max_targets']) < 1` | `raise ValueError('max_targets must be positive')` |
| `_validate_config` / 511 | `int(cfg['training']['batch_size']) < 1 or int(cfg['training']['epochs']) < 1` | `raise ValueError('batch_size and epochs must be positive')` |
| `_validate_frozen_identities` / 523 | `policy not in {'frozen_manifest', 'legacy_unpinned_smoke', 'signed_d2_release_smoke', 'signed_d2_release_formal'}` | `raise ValueError(f'unsupported teacher identity_policy: {policy}')` |
| `_validate_frozen_identities` / 538 | `policy in {'signed_d2_release_smoke', 'signed_d2_release_formal'} AND policy == 'signed_d2_release_smoke' and (not integration_smoke)` | `raise ValueError('signed D2 release policy is limited to integration smoke')` |
| `_validate_frozen_identities` / 540 | `policy in {'signed_d2_release_smoke', 'signed_d2_release_formal'} AND policy == 'signed_d2_release_formal' and integration_smoke` | `raise ValueError('formal signed D2 policy cannot be used for integration smoke')` |
| `_validate_frozen_identities` / 542 | `policy in {'signed_d2_release_smoke', 'signed_d2_release_formal'} AND actual_teacher['git_sha'] != 'MULTI_PINNED_B1_D2_V1_1'` | `raise ValueError('signed D2 release must identify mixed Teacher baselines')` |
| `_validate_frozen_identities` / 545 | `policy in {'signed_d2_release_smoke', 'signed_d2_release_formal'} AND actual_teacher[field] != expected_teacher[field]` | `raise ValueError(f'signed D2 release Teacher {field} mismatch')` |
| `_validate_frozen_identities` / 547 | `policy in {'signed_d2_release_smoke', 'signed_d2_release_formal'} AND dataset_cfg.get('verify_teacher_identity') is not True` | `raise ValueError('signed D2 release must verify Teacher identity')` |
| `_validate_frozen_identities` / 549 | `policy in {'signed_d2_release_smoke', 'signed_d2_release_formal'} AND dataset_cfg.get('require_pinned_teacher_provenance') is not True` | `raise ValueError('signed D2 release must require pinned Teacher provenance')` |
| `_validate_frozen_identities` / 551 | `policy in {'signed_d2_release_smoke', 'signed_d2_release_formal'} AND dataset_cfg.get('require_rgb') is not True` | `raise ValueError('signed D2 release must verify RGB')` |
| `_validate_frozen_identities` / 556 | `policy in {'signed_d2_release_smoke', 'signed_d2_release_formal'} AND view.get('view_version') != VIEW_VERSION or dataset_cfg.get('version') != VIEW_VERSION` | `raise ValueError('signed D2 release view version mismatch')` |
| `_validate_frozen_identities` / 561 | `policy in {'signed_d2_release_smoke', 'signed_d2_release_formal'} AND release.get('status') != 'B1_SIGNED_PASS'` | `raise ValueError('B1 D2 release is not signed')` |
| `_validate_frozen_identities` / 563 | `policy in {'signed_d2_release_smoke', 'signed_d2_release_formal'} AND canonical_text_sha256(release_path) != view.get('source_release_manifest_sha256')` | `raise ValueError('A3 view does not match signed B1 release')` |
| `_validate_frozen_identities` / 565 | `policy in {'signed_d2_release_smoke', 'signed_d2_release_formal'} AND not validate_release(release_dir)['valid']` | `raise ValueError('B1 D2 release integrity gate failed')` |
| `_validate_frozen_identities` / 569 | `policy in {'signed_d2_release_smoke', 'signed_d2_release_formal'} AND path != view_path.parent / f'{split}.jsonl'` | `raise ValueError(f'A3 {split} path does not match signed view')` |
| `_validate_frozen_identities` / 571 | `policy in {'signed_d2_release_smoke', 'signed_d2_release_formal'} AND canonical_text_sha256(path) != view['files'][f'{split}.jsonl']['sha256']` | `raise ValueError(f'A3 {split} hash does not match signed view')` |
| `_validate_frozen_identities` / 574 | `policy in {'signed_d2_release_smoke', 'signed_d2_release_formal'} AND canonical_text_sha256(repo / relative) != expected_sha` | `raise ValueError(f'Teacher cohort manifest changed: {relative}')` |
| `_validate_frozen_identities` / 576 | `policy in {'signed_d2_release_smoke', 'signed_d2_release_formal'} AND (repo / str(dataset_cfg['asset_root'])).resolve() != repo` | `raise ValueError('signed D2 release RGB asset_root must be repository root')` |
| `_validate_frozen_identities` / 581 | `NOT (policy in {'signed_d2_release_smoke', 'signed_d2_release_formal'}) AND policy == 'legacy_unpinned_smoke' AND not integration_smoke` | `raise ValueError('legacy unpinned Teacher data is allowed only for integration smoke')` |
| `_validate_frozen_identities` / 585 | `NOT (policy in {'signed_d2_release_smoke', 'signed_d2_release_formal'}) AND policy == 'legacy_unpinned_smoke' AND dataset_cfg.get('verify_teacher_identity') is not True` | `raise ValueError('legacy Smoke must verify Teacher SHA and model ID')` |
| `_validate_frozen_identities` / 587 | `NOT (policy in {'signed_d2_release_smoke', 'signed_d2_release_formal'}) AND policy == 'legacy_unpinned_smoke' AND dataset_cfg.get('require_pinned_teacher_provenance') is not False` | `raise ValueError('legacy Smoke cannot claim pinned Teacher provenance')` |
| `_validate_frozen_identities` / 589 | `NOT (policy in {'signed_d2_release_smoke', 'signed_d2_release_formal'}) AND policy == 'legacy_unpinned_smoke' AND actual_teacher['git_sha'] != expected_teacher['git_sha']` | `raise ValueError('legacy Smoke Teacher git_sha does not match frozen baseline')` |
| `_validate_frozen_identities` / 591 | `NOT (policy in {'signed_d2_release_smoke', 'signed_d2_release_formal'}) AND policy == 'legacy_unpinned_smoke' AND actual_teacher['model_id'] != expected_teacher['model_id']` | `raise ValueError('legacy Smoke Teacher model_id does not match frozen baseline')` |
| `_validate_frozen_identities` / 593 | `NOT (policy in {'signed_d2_release_smoke', 'signed_d2_release_formal'}) AND policy == 'legacy_unpinned_smoke' AND actual_teacher['model_revision'] != 'NOT_RECORDED_BY_B1_SMOKE'` | `raise ValueError('legacy Smoke must not claim a model revision')` |
| `_validate_frozen_identities` / 595 | `NOT (policy in {'signed_d2_release_smoke', 'signed_d2_release_formal'}) AND policy == 'legacy_unpinned_smoke' AND actual_teacher['artifact_fingerprint_sha256'] != 'NOT_RECORDED_BY_B1_SMOKE'` | `raise ValueError('legacy Smoke must not claim an artifact fingerprint')` |
| `_validate_frozen_identities` / 598 | `NOT (policy in {'signed_d2_release_smoke', 'signed_d2_release_formal'}) AND NOT (policy == 'legacy_unpinned_smoke') AND actual_teacher != expected_teacher` | `raise ValueError('teacher identity does not match challenge/teacher_baseline_manifest.json')` |
| `_validate_frozen_identities` / 602 | `NOT (policy in {'signed_d2_release_smoke', 'signed_d2_release_formal'}) AND NOT (policy == 'legacy_unpinned_smoke') AND dataset_cfg.get('verify_teacher_identity') is not True` | `raise ValueError('formal A3 training cannot disable Teacher identity checks')` |
| `_validate_frozen_identities` / 604 | `NOT (policy in {'signed_d2_release_smoke', 'signed_d2_release_formal'}) AND NOT (policy == 'legacy_unpinned_smoke') AND dataset_cfg.get('require_pinned_teacher_provenance') is not True` | `raise ValueError('formal A3 training requires pinned per-record provenance')` |
| `_validate_frozen_identities` / 607 | `cfg['model'].get('model_id') == StudentPlannerV0.model_id AND cfg['model'].get('config_id') != StudentModelConfig().config_id` | `raise ValueError('Student config_id does not match A1 V0 r3')` |
| `_device` / 616 | `device.type == 'cuda' and (not torch.cuda.is_available())` | `raise RuntimeError('CUDA was requested but is unavailable')` |
| `_seed_everything` / 622 | `os.environ.get('CUBLAS_WORKSPACE_CONFIG') not in {':4096:8', ':16:8'}` | `raise RuntimeError('deterministic CUDA training requires CUBLAS_WORKSPACE_CONFIG')` |
| `_load_config` / 664 | `not isinstance(value, dict)` | `raise ValueError('training config must be a YAML object')` |

### 环境参数读取位置

这里只记录源码表达式，不读取当前进程环境；缓存与覆盖关系需查调用时机。

| 来源/行 | 环境变量表达式 | 源码fallback |
|---|---|---|
| `challenge/distillation/train.py:621` | `'CUBLAS_WORKSPACE_CONFIG'` | `None（未传默认）` |
