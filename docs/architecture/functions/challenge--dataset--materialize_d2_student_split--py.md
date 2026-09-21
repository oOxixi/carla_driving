# materialize_d2_student_split：功能记录

上级模块：[模块说明](../modules/challenge-data.md) · 实现：[challenge/dataset/materialize_d2_student_split.py](../../../challenge/dataset/materialize_d2_student_split.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [原始样本、冻结发布与派生训练视图](dataset-release-view.md)

## 功能职责与范围

materialize_d2_student_split

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `sha256_file`

源码位置：[challenge/dataset/materialize_d2_student_split.py 第 24 行](../../../challenge/dataset/materialize_d2_student_split.py#L24)。类型：`FunctionDef`。

```python
sha256_file(path: Path) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `read_jsonl`

源码位置：[challenge/dataset/materialize_d2_student_split.py 第 32 行](../../../challenge/dataset/materialize_d2_student_split.py#L32)。类型：`FunctionDef`。

```python
read_jsonl(path: Path) -> list[dict[str, Any]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `write_jsonl`

源码位置：[challenge/dataset/materialize_d2_student_split.py 第 45 行](../../../challenge/dataset/materialize_d2_student_split.py#L45)。类型：`FunctionDef`。

```python
write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `write_json`

源码位置：[challenge/dataset/materialize_d2_student_split.py 第 52 行](../../../challenge/dataset/materialize_d2_student_split.py#L52)。类型：`FunctionDef`。

```python
write_json(path: Path, obj: Any) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[challenge/dataset/materialize_d2_student_split.py 第 60 行](../../../challenge/dataset/materialize_d2_student_split.py#L60)。类型：`FunctionDef`。

```python
main() -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main.materialize`

源码位置：[challenge/dataset/materialize_d2_student_split.py 第 188 行](../../../challenge/dataset/materialize_d2_student_split.py#L188)。类型：`FunctionDef`。

```python
main.materialize(ids_in_order: list[str], split: str) -> list[dict[str, Any]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `sha256_file` 调用：`f.read`, `h.hexdigest`, `h.update`, `hashlib.sha256`, `iter`, `path.open`.
- `read_jsonl` 调用：`RuntimeError`, `enumerate`, `isinstance`, `json.loads`, `path.open`, `raw.strip`, `rows.append`.
- `write_jsonl` 调用：`f.write`, `json.dumps`, `path.open`, `path.parent.mkdir`.
- `write_json` 调用：`json.dumps`, `path.parent.mkdir`, `path.write_text`.
- `main` 调用：`(r.get('metadata') or {}).get`, `(r.get('sample_class') or {}).get`, `(record.get('input') or {}).get`, `(repo / args.canonical_pool).resolve`, `(repo / args.output_dir).resolve`, `(repo / args.pool_manifest).resolve`, `(repo / args.split_dir).resolve`, `(repo / args.student_pool).resolve`, `Counter`, `Path`, `Path(__file__).resolve`, `RuntimeError`, `any`, `ap.add_argument`, `ap.parse_args`, `argparse.ArgumentParser`, `base.current_branch`, `base.current_head`, `base.verify_tracked_file_matches_head`, `canonical_pool.relative_to`, `dict`, `isinstance`, `json.dumps`, `json.loads`, `leakage.get`, `len`, `materialize`, `meta.get`, `out.append`, `out_dir.mkdir`, `path.is_file`, `policy.get`, `pool_manifest.relative_to`, `print`, `r.get`, `read_jsonl`, `record.get`, `record.setdefault`, `set`, `sha256_file`, `split_manifest.read_text`, `split_manifest.relative_to`, `split_manifest_obj.get`, `str`, `student_pool.relative_to`, `teacher.get`, `train_canonical.relative_to`, `val_canonical.relative_to`, `write_json`, `write_jsonl`.
- `materialize` 调用：`(record.get('input') or {}).get`, `RuntimeError`, `isinstance`, `json.dumps`, `json.loads`, `len`, `meta.get`, `out.append`, `policy.get`, `record.get`, `record.setdefault`, `teacher.get`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `main`，第 109 行：`RuntimeError(f'required input missing: {path}')`。
- `main`，第 112 行：`RuntimeError('canonical training-pool SHA mismatch')`。
- `main`，第 114 行：`RuntimeError('student training-pool SHA mismatch')`。
- `main`，第 116 行：`RuntimeError('training-pool manifest SHA mismatch')`。
- `main`，第 139 行：`RuntimeError(f'canonical pool count != {EXPECTED_TOTAL}')`。
- `main`，第 141 行：`RuntimeError(f'student pool count != {EXPECTED_TOTAL}')`。
- `main`，第 143 行：`RuntimeError(f'train count != {EXPECTED_TRAIN_COUNT}')`。
- `main`，第 145 行：`RuntimeError(f'val count != {EXPECTED_VAL_COUNT}')`。
- `main`，第 159 行：`RuntimeError(f'{name} contains missing sample_id')`。
- `main`，第 161 行：`RuntimeError(f'{name} contains duplicate sample_id')`。
- `main`，第 163 行：`RuntimeError(f'{name} count mismatch')`。
- `main`，第 171 行：`RuntimeError('canonical/student pool sample-id sets differ')`。
- `main`，第 173 行：`RuntimeError('train/val sample-id overlap')`。
- `main`，第 175 行：`RuntimeError('train/val membership does not partition the canonical pool')`。
- `main`，第 181 行：`RuntimeError('split manifest source SHA does not match canonical pool')`。
- `main`，第 183 行：`RuntimeError('split manifest strategy is not stratified')`。
- `main`，第 186 行：`RuntimeError('split manifest leakage check did not pass')`。
- `main`，第 194 行：`RuntimeError(f'non-eligible Student record: {sid}')`。
- `main`，第 197 行：`RuntimeError(f'metadata must be object: {sid}')`。
- `main`，第 199 行：`RuntimeError(f'Student contract mismatch: {sid}')`。
- `main`，第 202 行：`RuntimeError(f'Student target overflow: {sid}')`。
- `main`，第 206 行：`RuntimeError(f'teacher.maneuver_plan missing: {sid}')`。
- `main`，第 227 行：`RuntimeError('group_key leakage after materialization')`。
- `materialize`，第 194 行：`RuntimeError(f'non-eligible Student record: {sid}')`。
- `materialize`，第 197 行：`RuntimeError(f'metadata must be object: {sid}')`。
- `materialize`，第 199 行：`RuntimeError(f'Student contract mismatch: {sid}')`。
- `materialize`，第 202 行：`RuntimeError(f'Student target overflow: {sid}')`。
- `materialize`，第 206 行：`RuntimeError(f'teacher.maneuver_plan missing: {sid}')`。
- `read_jsonl`，第 40 行：`RuntimeError(f'{path}:{line_no}: JSON object required')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 62 行：`ap.add_argument('--canonical-pool', default='artifacts/b1_d2_training_pool_v0/canonical_eligible.jsonl')`。
- 第 66 行：`ap.add_argument('--student-pool', default='artifacts/b1_d2_training_pool_v0/student_eligible.jsonl')`。
- 第 70 行：`ap.add_argument('--pool-manifest', default='artifacts/b1_d2_training_pool_v0/training_pool_manifest.json')`。
- 第 74 行：`ap.add_argument('--split-dir', default='artifacts/b1_d2_split_v1')`。
- 第 78 行：`ap.add_argument('--output-dir', default='artifacts/b1_d2_student_split_v1')`。
- 第 82 行：`ap.add_argument('--dataset-version', default=EXPECTED_DATASET_VERSION)`。
- 第 86 行：`ap.add_argument('--dry-run', action='store_true')`。
- 第 87 行：`ap.add_argument('--allow-uncommitted-code', action='store_true')`。

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

### `challenge/dataset/materialize_d2_student_split.py`

来源 SHA256：`4e6f134aab580c021ae6be39adff5779322b1e1769a8674a37960aebd15fdde0`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 62 | `'--canonical-pool'` | `default='artifacts/b1_d2_training_pool_v0/canonical_eligible.jsonl'` |
| 66 | `'--student-pool'` | `default='artifacts/b1_d2_training_pool_v0/student_eligible.jsonl'` |
| 70 | `'--pool-manifest'` | `default='artifacts/b1_d2_training_pool_v0/training_pool_manifest.json'` |
| 74 | `'--split-dir'` | `default='artifacts/b1_d2_split_v1'` |
| 78 | `'--output-dir'` | `default='artifacts/b1_d2_student_split_v1'` |
| 82 | `'--dataset-version'` | `default=EXPECTED_DATASET_VERSION` |
| 86 | `'--dry-run'` | `action='store_true'` |
| 87 | `'--allow-uncommitted-code'` | `action='store_true'` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `read_jsonl` / 40 | `not isinstance(row, dict)` | `raise RuntimeError(f'{path}:{line_no}: JSON object required')` |
| `main` / 109 | `not path.is_file()` | `raise RuntimeError(f'required input missing: {path}')` |
| `main` / 112 | `sha256_file(canonical_pool) != EXPECTED_CANONICAL_POOL_SHA256` | `raise RuntimeError('canonical training-pool SHA mismatch')` |
| `main` / 114 | `sha256_file(student_pool) != EXPECTED_STUDENT_POOL_SHA256` | `raise RuntimeError('student training-pool SHA mismatch')` |
| `main` / 116 | `sha256_file(pool_manifest) != EXPECTED_POOL_MANIFEST_SHA256` | `raise RuntimeError('training-pool manifest SHA mismatch')` |
| `main` / 139 | `len(canonical_rows) != EXPECTED_TOTAL` | `raise RuntimeError(f'canonical pool count != {EXPECTED_TOTAL}')` |
| `main` / 141 | `len(student_rows) != EXPECTED_TOTAL` | `raise RuntimeError(f'student pool count != {EXPECTED_TOTAL}')` |
| `main` / 143 | `len(train_rows) != EXPECTED_TRAIN_COUNT` | `raise RuntimeError(f'train count != {EXPECTED_TRAIN_COUNT}')` |
| `main` / 145 | `len(val_rows) != EXPECTED_VAL_COUNT` | `raise RuntimeError(f'val count != {EXPECTED_VAL_COUNT}')` |
| `main` / 159 | `any((not isinstance(x, str) or not x for x in ids))` | `raise RuntimeError(f'{name} contains missing sample_id')` |
| `main` / 161 | `len(ids) != len(set(ids))` | `raise RuntimeError(f'{name} contains duplicate sample_id')` |
| `main` / 163 | `len(ids) != expected` | `raise RuntimeError(f'{name} count mismatch')` |
| `main` / 171 | `canonical_id_set != student_id_set` | `raise RuntimeError('canonical/student pool sample-id sets differ')` |
| `main` / 173 | `train_id_set & val_id_set` | `raise RuntimeError('train/val sample-id overlap')` |
| `main` / 175 | `train_id_set &#124; val_id_set != canonical_id_set` | `raise RuntimeError('train/val membership does not partition the canonical pool')` |
| `main` / 181 | `split_manifest_obj.get('source_sha256') != EXPECTED_CANONICAL_POOL_SHA256` | `raise RuntimeError('split manifest source SHA does not match canonical pool')` |
| `main` / 183 | `split_manifest_obj.get('strategy') != 'stratified'` | `raise RuntimeError('split manifest strategy is not stratified')` |
| `main` / 186 | `leakage.get('passed') is not True` | `raise RuntimeError('split manifest leakage check did not pass')` |
| `main` / 227 | `train_groups & val_groups` | `raise RuntimeError('group_key leakage after materialization')` |
| `main.materialize` / 194 | `not isinstance(policy, dict) or policy.get('train_eligible') is not True` | `raise RuntimeError(f'non-eligible Student record: {sid}')` |
| `main.materialize` / 197 | `not isinstance(meta, dict)` | `raise RuntimeError(f'metadata must be object: {sid}')` |
| `main.materialize` / 199 | `meta.get('student_contract') != EXPECTED_STUDENT_CONTRACT` | `raise RuntimeError(f'Student contract mismatch: {sid}')` |
| `main.materialize` / 202 | `len(targets) > 8` | `raise RuntimeError(f'Student target overflow: {sid}')` |
| `main.materialize` / 206 | `not isinstance(plan, dict)` | `raise RuntimeError(f'teacher.maneuver_plan missing: {sid}')` |
