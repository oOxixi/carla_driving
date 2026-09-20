# split_dataset：功能记录

上级模块：[模块说明](../modules/challenge-data.md) · 实现：[challenge/dataset/split_dataset.py](../../../challenge/dataset/split_dataset.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [原始样本、冻结发布与派生训练视图](dataset-release-view.md)

## 功能职责与范围

split_dataset

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `read_jsonl`

源码位置：[challenge/dataset/split_dataset.py 第 18 行](../../../challenge/dataset/split_dataset.py#L18)。类型：`FunctionDef`。

```python
read_jsonl(path: Path) -> list[dict[str, Any]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `write_jsonl`

源码位置：[challenge/dataset/split_dataset.py 第 43 行](../../../challenge/dataset/split_dataset.py#L43)。类型：`FunctionDef`。

```python
write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `write_json`

源码位置：[challenge/dataset/split_dataset.py 第 64 行](../../../challenge/dataset/split_dataset.py#L64)。类型：`FunctionDef`。

```python
write_json(path: Path, value: dict[str, Any]) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `sha256_file`

源码位置：[challenge/dataset/split_dataset.py 第 84 行](../../../challenge/dataset/split_dataset.py#L84)。类型：`FunctionDef`。

```python
sha256_file(path: Path) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `get_metadata`

源码位置：[challenge/dataset/split_dataset.py 第 97 行](../../../challenge/dataset/split_dataset.py#L97)。类型：`FunctionDef`。

```python
get_metadata(sample: dict[str, Any]) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `get_group_key`

源码位置：[challenge/dataset/split_dataset.py 第 110 行](../../../challenge/dataset/split_dataset.py#L110)。类型：`FunctionDef`。

```python
get_group_key(sample: dict[str, Any]) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `get_group_signature`

源码位置：[challenge/dataset/split_dataset.py 第 125 行](../../../challenge/dataset/split_dataset.py#L125)。类型：`FunctionDef`。

```python
get_group_signature(sample: dict[str, Any]) -> tuple[Any, Any, Any, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `validate_groups`

源码位置：[challenge/dataset/split_dataset.py 第 138 行](../../../challenge/dataset/split_dataset.py#L138)。类型：`FunctionDef`。

```python
validate_groups(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `group_class_counts`

源码位置：[challenge/dataset/split_dataset.py 第 179 行](../../../challenge/dataset/split_dataset.py#L179)。类型：`FunctionDef`。

```python
group_class_counts(samples: list[dict[str, Any]]) -> Counter
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `choose_val_groups`

源码位置：[challenge/dataset/split_dataset.py 第 197 行](../../../challenge/dataset/split_dataset.py#L197)。类型：`FunctionDef`。

```python
choose_val_groups(groups: dict[str, list[dict[str, Any]]], val_ratio: float, seed: int) -> set[str]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `choose_val_groups_stratified`

源码位置：[challenge/dataset/split_dataset.py 第 291 行](../../../challenge/dataset/split_dataset.py#L291)。类型：`FunctionDef`。

```python
choose_val_groups_stratified(groups: dict[str, list[dict[str, Any]]], val_ratio: float, seed: int, *, trials: int=50000, min_val_groups: int=12) -> set[str]
```

Deterministic randomized search over whole groups.

Hard constraints:
  - validation sample count within target +/- 4;
  - at least min_val_groups;
  - every global sample class represented;
  - every global source bucket represented;
  - every global scenario family represented.

The objective then prefers distributions close to the full dataset.

### `choose_val_groups_stratified.sample_class`

源码位置：[challenge/dataset/split_dataset.py 第 328 行](../../../challenge/dataset/split_dataset.py#L328)。类型：`FunctionDef`。

```python
choose_val_groups_stratified.sample_class(sample: dict[str, Any]) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `choose_val_groups_stratified.source_bucket`

源码位置：[challenge/dataset/split_dataset.py 第 334 行](../../../challenge/dataset/split_dataset.py#L334)。类型：`FunctionDef`。

```python
choose_val_groups_stratified.source_bucket(sample: dict[str, Any]) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `choose_val_groups_stratified.scenario_family`

源码位置：[challenge/dataset/split_dataset.py 第 338 行](../../../challenge/dataset/split_dataset.py#L338)。类型：`FunctionDef`。

```python
choose_val_groups_stratified.scenario_family(sample: dict[str, Any]) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `choose_val_groups_stratified.selected_rows`

源码位置：[challenge/dataset/split_dataset.py 第 372 行](../../../challenge/dataset/split_dataset.py#L372)。类型：`FunctionDef`。

```python
choose_val_groups_stratified.selected_rows(keys: list[str]) -> list[dict[str, Any]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `choose_val_groups_stratified.objective`

源码位置：[challenge/dataset/split_dataset.py 第 381 行](../../../challenge/dataset/split_dataset.py#L381)。类型：`FunctionDef`。

```python
choose_val_groups_stratified.objective(keys: list[str]) -> float | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `build_split`

源码位置：[challenge/dataset/split_dataset.py 第 493 行](../../../challenge/dataset/split_dataset.py#L493)。类型：`FunctionDef`。

```python
build_split(rows: list[dict[str, Any]], groups: dict[str, list[dict[str, Any]]], val_groups: set[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `assert_no_leakage`

源码位置：[challenge/dataset/split_dataset.py 第 515 行](../../../challenge/dataset/split_dataset.py#L515)。类型：`FunctionDef`。

```python
assert_no_leakage(train: list[dict[str, Any]], val: list[dict[str, Any]]) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `build_manifest`

源码位置：[challenge/dataset/split_dataset.py 第 556 行](../../../challenge/dataset/split_dataset.py#L556)。类型：`FunctionDef`。

```python
build_manifest(*, split_name: str, rows: list[dict[str, Any]], output_path: Path, dataset_version: str) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[challenge/dataset/split_dataset.py 第 629 行](../../../challenge/dataset/split_dataset.py#L629)。类型：`FunctionDef`。

```python
main() -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `read_jsonl` 调用：`ValueError`, `enumerate`, `isinstance`, `json.loads`, `line.strip`, `path.open`, `rows.append`.
- `write_jsonl` 调用：`f.write`, `json.dumps`, `path.open`, `path.parent.mkdir`.
- `write_json` 调用：`json.dumps`, `path.parent.mkdir`, `path.write_text`.
- `sha256_file` 调用：`f.read`, `h.hexdigest`, `h.update`, `hashlib.sha256`, `iter`, `path.open`.
- `get_metadata` 调用：`ValueError`, `isinstance`, `sample.get`.
- `get_group_key` 调用：`ValueError`, `get_metadata`, `isinstance`, `metadata.get`, `sample.get`.
- `get_group_signature` 调用：`get_metadata`, `metadata.get`.
- `validate_groups` 调用：`ValueError`, `defaultdict`, `dict`, `get_group_key`, `get_group_signature`, `groups[group_key].append`, `isinstance`, `sample.get`, `seen_sample_ids.add`, `set`.
- `group_class_counts` 调用：`Counter`, `isinstance`, `sample.get`, `sample_class.get`, `str`.
- `choose_val_groups` 调用：`ValueError`, `abs`, `group_keys.remove`, `group_keys.sort`, `groups.keys`, `groups.values`, `len`, `max`, `min`, `random.Random`, `rng.shuffle`, `round`, `selected.add`, `selected.remove`, `set`, `sorted`, `sum`.
- `choose_val_groups_stratified` 调用：`Counter`, `ValueError`, `abs`, `chosen.append`, `get_metadata`, `global_bucket_counts.items`, `global_class_counts.items`, `global_family_counts.items`, `groups.keys`, `groups.values`, `isinstance`, `len`, `max`, `metadata.get`, `objective`, `random.Random`, `range`, `rng.random`, `rng.shuffle`, `round`, `sample.get`, `sample_class`, `scenario_family`, `selected_rows`, `set`, `sorted`, `source_bucket`, `str`, `value.get`.
- `build_split` 调用：`get_group_key`, `train.append`, `val.append`.
- `assert_no_leakage` 调用：`','.join`, `ValueError`, `get_group_key`, `sample.get`, `sorted`, `str`.
- `build_manifest` 调用：`Counter`, `datetime.now`, `datetime.now(timezone.utc).isoformat`, `dict`, `get_metadata`, `isinstance`, `len`, `metadata.get`, `sample.get`, `sample_class.get`, `sha256_file`, `str`.
- `main` 调用：`Counter`, `Counter((str(get_metadata(sample).get('scenario_family')) for sample in val)).items`, `Counter((str(get_metadata(sample).get('source_bucket')) for sample in val)).items`, `Path`, `SystemExit`, `argparse.ArgumentParser`, `assert_no_leakage`, `build_manifest`, `build_split`, `choose_val_groups`, `choose_val_groups_stratified`, `datetime.now`, `datetime.now(timezone.utc).isoformat`, `dict`, `get_group_key`, `get_metadata`, `get_metadata(sample).get`, `group_class_counts`, `group_class_counts(train).items`, `group_class_counts(val).items`, `len`, `output_dir.mkdir`, `parser.add_argument`, `parser.parse_args`, `print`, `read_jsonl`, `sha256_file`, `sorted`, `str`, `validate_groups`, `write_json`, `write_jsonl`.
- `sample_class` 调用：`isinstance`, `sample.get`, `str`, `value.get`.
- `source_bucket` 调用：`get_metadata`, `metadata.get`, `str`.
- `scenario_family` 调用：`get_metadata`, `metadata.get`, `str`.
- `objective` 调用：`Counter`, `abs`, `global_bucket_counts.items`, `global_class_counts.items`, `global_family_counts.items`, `len`, `sample_class`, `scenario_family`, `selected_rows`, `set`, `source_bucket`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `assert_no_leakage`，第 532 行：`ValueError('GROUP_LEAKAGE_DETECTED: ' + ','.join(sorted(overlap)))`。
- `assert_no_leakage`，第 550 行：`ValueError('SAMPLE_ID_LEAKAGE_DETECTED: ' + ','.join(sorted(sample_overlap)))`。
- `choose_val_groups`，第 208 行：`ValueError('need at least 2 groups for Train/Val split')`。
- `choose_val_groups_stratified`，第 321 行：`ValueError('dataset too small for stratified split')`。
- `choose_val_groups_stratified`，第 486 行：`ValueError('NO_VALID_STRATIFIED_GROUP_SPLIT_FOUND')`。
- `get_group_key`，第 118 行：`ValueError(f"sample {sample.get('sample_id')} missing group_key")`。
- `get_metadata`，第 103 行：`ValueError(f"sample {sample.get('sample_id')} missing metadata")`。
- `main`，第 683 行：`SystemExit('--val-ratio must be between 0.05 and 0.50')`。
- `main`，第 693 行：`SystemExit('dataset must contain at least 2 samples')`。
- `main`，第 721 行：`SystemExit('Train split is empty')`。
- `main`，第 726 行：`SystemExit('Val split is empty')`。
- `read_jsonl`，第 29 行：`ValueError(f'{path}:{line_no}: invalid JSON: {exc}')`。
- `read_jsonl`，第 34 行：`ValueError(f'{path}:{line_no}: row is not a JSON object')`。
- `validate_groups`，第 150 行：`ValueError('sample without valid sample_id')`。
- `validate_groups`，第 155 行：`ValueError(f'duplicate sample_id: {sample_id}')`。
- `validate_groups`，第 166 行：`ValueError(f'group_key collision/inconsistency: {group_key}: {signatures[group_key]} != {signature}')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 632 行：`parser.add_argument('--input', required=True)`。
- 第 637 行：`parser.add_argument('--output-dir', required=True)`。
- 第 642 行：`parser.add_argument('--val-ratio', type=float, default=0.2)`。
- 第 648 行：`parser.add_argument('--seed', type=int, default=20260911)`。
- 第 654 行：`parser.add_argument('--dataset-version', default='teacher_distill_v0.1_smoke')`。
- 第 659 行：`parser.add_argument('--strategy', choices=['size_greedy', 'stratified'], default='size_greedy')`。
- 第 668 行：`parser.add_argument('--stratified-trials', type=int, default=50000)`。
- 第 674 行：`parser.add_argument('--min-val-groups', type=int, default=12)`。

## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- 未发现静态 import 消费者；命令行、间接注册、文件路径加载不在此清单内。

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-data.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/dataset/split_dataset.py`

来源 SHA256：`1eee5fd3e7892832a074e778ba7f9d34448788d808dac7824a289254bc6fb1fd`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 632 | `'--input'` | `required=True` |
| 637 | `'--output-dir'` | `required=True` |
| 642 | `'--val-ratio'` | `type=float; default=0.2` |
| 648 | `'--seed'` | `type=int; default=20260911` |
| 654 | `'--dataset-version'` | `default='teacher_distill_v0.1_smoke'` |
| 659 | `'--strategy'` | `choices=['size_greedy', 'stratified']; default='size_greedy'` |
| 668 | `'--stratified-trials'` | `type=int; default=50000` |
| 674 | `'--min-val-groups'` | `type=int; default=12` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `read_jsonl` / 29 | `except json.JSONDecodeError` | `raise ValueError(f'{path}:{line_no}: invalid JSON: {exc}') from exc` |
| `read_jsonl` / 34 | `not isinstance(row, dict)` | `raise ValueError(f'{path}:{line_no}: row is not a JSON object')` |
| `get_metadata` / 103 | `not isinstance(metadata, dict)` | `raise ValueError(f"sample {sample.get('sample_id')} missing metadata")` |
| `get_group_key` / 118 | `not isinstance(group_key, str) or not group_key` | `raise ValueError(f"sample {sample.get('sample_id')} missing group_key")` |
| `validate_groups` / 150 | `not isinstance(sample_id, str) or not sample_id` | `raise ValueError('sample without valid sample_id')` |
| `validate_groups` / 155 | `sample_id in seen_sample_ids` | `raise ValueError(f'duplicate sample_id: {sample_id}')` |
| `validate_groups` / 166 | `group_key in signatures AND signatures[group_key] != signature` | `raise ValueError(f'group_key collision/inconsistency: {group_key}: {signatures[group_key]} != {signature}')` |
| `choose_val_groups` / 208 | `len(groups) < 2` | `raise ValueError('need at least 2 groups for Train/Val split')` |
| `choose_val_groups_stratified` / 321 | `total_samples < 2` | `raise ValueError('dataset too small for stratified split')` |
| `choose_val_groups_stratified` / 486 | `best_keys is None` | `raise ValueError('NO_VALID_STRATIFIED_GROUP_SPLIT_FOUND')` |
| `assert_no_leakage` / 532 | `overlap` | `raise ValueError('GROUP_LEAKAGE_DETECTED: ' + ','.join(sorted(overlap)))` |
| `assert_no_leakage` / 550 | `sample_overlap` | `raise ValueError('SAMPLE_ID_LEAKAGE_DETECTED: ' + ','.join(sorted(sample_overlap)))` |
| `main` / 683 | `not 0.05 <= args.val_ratio <= 0.5` | `raise SystemExit('--val-ratio must be between 0.05 and 0.50')` |
| `main` / 693 | `len(rows) < 2` | `raise SystemExit('dataset must contain at least 2 samples')` |
| `main` / 721 | `not train` | `raise SystemExit('Train split is empty')` |
| `main` / 726 | `not val` | `raise SystemExit('Val split is empty')` |
