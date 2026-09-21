# audit_d2_view：功能记录

上级模块：[模块说明](../modules/challenge-training.md) · 实现：[challenge/distillation/audit_d2_view.py](../../../challenge/distillation/audit_d2_view.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [各Head损失、mask与加权](distillation-objective.md)
- [恢复、纯权重候选与晋级身份](checkpoint-and-promotion.md)

## 功能职责与范围

Read-only label and coverage audit for the signed B1 D2 A3 view.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `summarize_split`

源码位置：[challenge/distillation/audit_d2_view.py 第 21 行](../../../challenge/distillation/audit_d2_view.py#L21)。类型：`FunctionDef`。

```python
summarize_split(rows: list[Mapping[str, Any]]) -> dict[str, Any]
```

Count training labels without reading protected Test candidates.

### `audit_view`

源码位置：[challenge/distillation/audit_d2_view.py 第 94 行](../../../challenge/distillation/audit_d2_view.py#L94)。类型：`FunctionDef`。

```python
audit_view(release_dir: Path, view_dir: Path) -> dict[str, Any]
```

Fail closed on changed inputs; report coverage, not model quality.

### `main`

源码位置：[challenge/distillation/audit_d2_view.py 第 166 行](../../../challenge/distillation/audit_d2_view.py#L166)。类型：`FunctionDef`。

```python
main() -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `summarize_split` 调用：`Counter`, `DistillationLabelEncoder`, `ValueError`, `_sample_class`, `behaviors.items`, `bool`, `class_family.items`, `class_scenario.items`, `classes.items`, `cohorts.items`, `completion_types.items`, `dict`, `encoder.encode`, `enumerate`, `failure_actions.items`, `families.items`, `int`, `isinstance`, `len`, `maps.items`, `metadata.get`, `plan_lengths.items`, `row.get`, `scenario_ids.items`, `set`, `sorted`, `str`, `sum`, `target_lanes.items`, `teacher.get`.
- `audit_view` 调用：`(release_dir / 'release_manifest.json').read_text`, `(repo / relative).resolve`, `(view_dir / 'a3_view_manifest.json').read_text`, `ValueError`, `any`, `canonical_text_sha256`, `json.loads`, `json.loads((release_dir / 'release_manifest.json').read_text(encoding='utf-8')).get`, `len`, `load_jsonl`, `manifest.get`, `manifest['cohort_manifest_shas'].items`, `manifest['files'].items`, `path.is_relative_to`, `release_dir.resolve`, `row.get`, `row.get('metadata', {}).get`, `set`, `str`, `summarize_split`, `validate_release`, `view_dir.resolve`.
- `main` 调用：`Path`, `argparse.ArgumentParser`, `args.output.parent.mkdir`, `args.output.write_text`, `audit_view`, `json.dumps`, `parser.add_argument`, `parser.parse_args`, `print`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `audit_view`，第 100 行：`ValueError('B1 signed release validation failed')`。
- `audit_view`，第 103 行：`ValueError('B1 release is not signed')`。
- `audit_view`，第 105 行：`ValueError('A3 view version mismatch')`。
- `audit_view`，第 109 行：`ValueError('A3 view was not derived from this signed B1 release')`。
- `audit_view`，第 112 行：`ValueError(f'A3 view file changed: {name}')`。
- `audit_view`，第 117 行：`ValueError(f'Teacher cohort manifest changed: {relative}')`。
- `audit_view`，第 125 行：`ValueError(f'duplicate {split} sample ID')`。
- `audit_view`，第 127 行：`ValueError(f'A3 {split} contains a mismatched split label')`。
- `audit_view`，第 129 行：`ValueError(f'A3 {split} contains a mismatched dataset version')`。
- `audit_view`，第 131 行：`ValueError(f'A3 {split} count differs from view manifest')`。
- `audit_view`，第 135 行：`ValueError('A3 Train and Val sample IDs overlap')`。
- `audit_view`，第 139 行：`ValueError('duplicate A3 excluded sample ID')`。
- `audit_view`，第 141 行：`ValueError('excluded sample reentered A3 supervision')`。
- `audit_view`，第 143 行：`ValueError('excluded count differs from view manifest')`。
- `audit_view`，第 153 行：`ValueError(f'A3 retained/excluded IDs do not partition B1 {split}')`。
- `summarize_split`，第 41 行：`ValueError(f'unsupported sample class: {sample_class}')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 168 行：`parser.add_argument('--release-dir', type=Path, default=Path('challenge/dataset/releases/d2_v1_1'))`。
- 第 169 行：`parser.add_argument('--view-dir', type=Path, default=Path('artifacts/a3_d2_v1_1_positive_view_v1'))`。
- 第 170 行：`parser.add_argument('--output', type=Path, default=Path('artifacts/a3_d2_prep/label_coverage.json'))`。

## 上下游与关联验证

静态导入的项目内实现：

- [challenge/dataset/build_a3_d2_view.py](../../../challenge/dataset/build_a3_d2_view.py)
- [challenge/dataset/validate_d2_release.py](../../../challenge/dataset/validate_d2_release.py)
- [challenge/distillation/dataset.py](../../../challenge/distillation/dataset.py)
- [challenge/distillation/label_encoder.py](../../../challenge/distillation/label_encoder.py)

静态 import 消费者（含测试）：

- [challenge/distillation/ablation_eval.py](../../../challenge/distillation/ablation_eval.py)
- [challenge/distillation/tests/test_audit_d2_view.py](../../../challenge/distillation/tests/test_audit_d2_view.py)
- [challenge/distillation/train.py](../../../challenge/distillation/train.py)
- [challenge/distillation/validate_a1_inputs.py](../../../challenge/distillation/validate_a1_inputs.py)

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-training.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/distillation/audit_d2_view.py`

来源 SHA256：`60c4f3a1beb422d3b8403c26f4bb2421b7d751cf70e89ca1c29845b2835ce074`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 168 | `'--release-dir'` | `type=Path; default=Path('challenge/dataset/releases/d2_v1_1')` |
| 169 | `'--view-dir'` | `type=Path; default=Path('artifacts/a3_d2_v1_1_positive_view_v1')` |
| 170 | `'--output'` | `type=Path; default=Path('artifacts/a3_d2_prep/label_coverage.json')` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `summarize_split` / 41 | `sample_class not in {'normal', 'complex', 'safety_critical'}` | `raise ValueError(f'unsupported sample class: {sample_class}')` |
| `audit_view` / 100 | `not release['valid'] or release['authoritative_manifest'] != 'release_manifest.json'` | `raise ValueError('B1 signed release validation failed')` |
| `audit_view` / 103 | `json.loads((release_dir / 'release_manifest.json').read_text(encoding='utf-8')).get('status') != 'B1_SIGNED_PASS'` | `raise ValueError('B1 release is not signed')` |
| `audit_view` / 105 | `manifest.get('view_version') != VIEW_VERSION` | `raise ValueError('A3 view version mismatch')` |
| `audit_view` / 109 | `manifest.get('source_release_manifest_sha256') != canonical_text_sha256(release_dir / 'release_manifest.json')` | `raise ValueError('A3 view was not derived from this signed B1 release')` |
| `audit_view` / 112 | `canonical_text_sha256(view_dir / name) != details['sha256']` | `raise ValueError(f'A3 view file changed: {name}')` |
| `audit_view` / 117 | `not path.is_relative_to(repo) or canonical_text_sha256(path) != expected_sha` | `raise ValueError(f'Teacher cohort manifest changed: {relative}')` |
| `audit_view` / 125 | `len(set(ids)) != len(ids)` | `raise ValueError(f'duplicate {split} sample ID')` |
| `audit_view` / 127 | `any((row.get('metadata', {}).get('split') != split for row in rows))` | `raise ValueError(f'A3 {split} contains a mismatched split label')` |
| `audit_view` / 129 | `any((row.get('metadata', {}).get('dataset_version') != VIEW_VERSION for row in rows))` | `raise ValueError(f'A3 {split} contains a mismatched dataset version')` |
| `audit_view` / 131 | `len(rows) != manifest['counts'][split]` | `raise ValueError(f'A3 {split} count differs from view manifest')` |
| `audit_view` / 135 | `split_ids['train'] & split_ids['val']` | `raise ValueError('A3 Train and Val sample IDs overlap')` |
| `audit_view` / 139 | `len(set(excluded_ids)) != len(excluded_ids)` | `raise ValueError('duplicate A3 excluded sample ID')` |
| `audit_view` / 141 | `set(excluded_ids) & (split_ids['train'] &#124; split_ids['val'])` | `raise ValueError('excluded sample reentered A3 supervision')` |
| `audit_view` / 143 | `len(excluded_rows) != manifest['counts']['excluded']` | `raise ValueError('excluded count differs from view manifest')` |
| `audit_view` / 153 | `release_ids != split_ids[split] &#124; excluded_split` | `raise ValueError(f'A3 retained/excluded IDs do not partition B1 {split}')` |
