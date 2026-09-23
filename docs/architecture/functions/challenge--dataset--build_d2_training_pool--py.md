# build_d2_training_pool：功能记录

上级模块：[模块说明](../modules/challenge-data.md) · 实现：[challenge/dataset/build_d2_training_pool.py](../../../challenge/dataset/build_d2_training_pool.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [原始样本、冻结发布与派生训练视图](dataset-release-view.md)

## 功能职责与范围

build_d2_training_pool

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `sha256_file`

源码位置：[challenge/dataset/build_d2_training_pool.py 第 21 行](../../../challenge/dataset/build_d2_training_pool.py#L21)。类型：`FunctionDef`。

```python
sha256_file(path: Path) -> str
```

`sha256_file` 生成内容或文件的稳定身份摘要，用于计划、发布或provenance绑定；摘要口径区分原始字节与规范化JSON，不能混用。

### `write_json`

源码位置：[challenge/dataset/build_d2_training_pool.py 第 29 行](../../../challenge/dataset/build_d2_training_pool.py#L29)。类型：`FunctionDef`。

```python
write_json(path: Path, value: Any) -> None
```

`write_json` 将已构造结果写入目标路径或发布目录；文件写成不代表样本合格，调用前后仍需核对原子性、SHA256、行数和manifest引用。

### `write_jsonl`

源码位置：[challenge/dataset/build_d2_training_pool.py 第 37 行](../../../challenge/dataset/build_d2_training_pool.py#L37)。类型：`FunctionDef`。

```python
write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None
```

`write_jsonl` 将已构造结果写入目标路径或发布目录；文件写成不代表样本合格，调用前后仍需核对原子性、SHA256、行数和manifest引用。

### `get_meta`

源码位置：[challenge/dataset/build_d2_training_pool.py 第 44 行](../../../challenge/dataset/build_d2_training_pool.py#L44)。类型：`FunctionDef`。

```python
get_meta(row: dict[str, Any]) -> dict[str, Any]
```

`get_meta` 读取或派生数据治理所需的输入，不修改源发布；缺失、类型和回退语义以函数返回及本页异常表为准，调用方仍须固定数据版本与来源清单。

### `main`

源码位置：[challenge/dataset/build_d2_training_pool.py 第 49 行](../../../challenge/dataset/build_d2_training_pool.py#L49)。类型：`FunctionDef`。

```python
main() -> int
```

解析命令行参数并编排本脚本的数据读取、身份校验、生成/采集与落盘步骤；退出码和产物是否可发布取决于本页所列拒绝条件，不能只凭文件生成成功判定。

## 内部调用与异常路径

- `sha256_file` 调用：`f.read`, `h.hexdigest`, `h.update`, `hashlib.sha256`, `iter`, `path.open`.
- `write_json` 调用：`json.dumps`, `path.parent.mkdir`, `path.write_text`.
- `write_jsonl` 调用：`f.write`, `json.dumps`, `path.open`, `path.parent.mkdir`.
- `get_meta` 调用：`isinstance`, `row.get`.
- `main` 调用：`(r.get('sample_class') or {}).get`, `(repo / args.canonical).resolve`, `(repo / args.d1_manifest).resolve`, `(repo / args.output_dir).resolve`, `Counter`, `Path`, `Path(__file__).resolve`, `RuntimeError`, `affected_groups[str(group_key)].append`, `ap.add_argument`, `ap.parse_args`, `argparse.ArgumentParser`, `base.current_branch`, `base.current_head`, `base.read_jsonl`, `base.student_view_or_reason`, `base.verify_tracked_file_matches_head`, `by_group_bad.items`, `canonical_path.is_file`, `canonical_path.relative_to`, `d1_manifest_path.is_file`, `d1_manifest_path.relative_to`, `defaultdict`, `dict`, `eligible_canonical.append`, `eligible_ids.add`, `eligible_student.append`, `get_meta`, `get_meta(r).get`, `isinstance`, `json.dumps`, `len`, `meta.get`, `out.mkdir`, `policy.get`, `print`, `q.get`, `quarantine.append`, `r.get`, `report_out.write_text`, `request.get`, `sample.get`, `seen_sample_ids.add`, `set`, `sha256_file`, `sorted`, `str`, `teacher.get`, `view.get`, `write_json`, `write_jsonl`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `main`，第 72 行：`RuntimeError(f'canonical dataset missing: {canonical_path}')`。
- `main`，第 74 行：`RuntimeError(f'D1 manifest missing: {d1_manifest_path}')`。
- `main`，第 80 行：`RuntimeError(f'D1 canonical SHA mismatch: expected={SOURCE_D1_CANONICAL_SHA256} actual={canonical_sha}')`。
- `main`，第 85 行：`RuntimeError(f'D1 manifest SHA mismatch: expected={SOURCE_D1_MANIFEST_SHA256} actual={manifest_sha}')`。
- `main`，第 111 行：`RuntimeError(f'expected 228 D1 canonical samples, got {len(rows)}')`。
- `main`，第 126 行：`RuntimeError('canonical sample missing sample_id')`。
- `main`，第 128 行：`RuntimeError(f'duplicate canonical sample_id: {sample_id}')`。
- `main`，第 135 行：`RuntimeError(f'student view unexpectedly missing: {sample_id}')`。
- `main`，第 139 行：`RuntimeError(f'training_policy missing in rebuilt view: {sample_id}')`。
- `main`，第 141 行：`RuntimeError(f'rebuilt view is not train eligible: {sample_id}')`。
- `main`，第 145 行：`RuntimeError(f'rebuilt view metadata missing: {sample_id}')`。
- `main`，第 147 行：`RuntimeError(f"student contract mismatch for {sample_id}: {meta.get('student_contract')!r}")`。
- `main`，第 152 行：`RuntimeError(f'student_max_targets mismatch: {sample_id}')`。
- `main`，第 154 行：`RuntimeError(f'student_no_target_index mismatch: {sample_id}')`。
- `main`，第 158 行：`RuntimeError(f'student input missing: {sample_id}')`。
- `main`，第 164 行：`RuntimeError(f'student target overflow: {sample_id}')`。
- `main`，第 169 行：`RuntimeError(f'teacher maneuver plan missing: {sample_id}')`。
- `main`，第 172 行：`RuntimeError(f'duplicate eligible sample_id: {sample_id}')`。
- `main`，第 199 行：`RuntimeError(f'expected 214 current-contract eligible canonical samples, got {len(eligible_canonical)}')`。
- `main`，第 204 行：`RuntimeError(f'expected 214 current-contract student views, got {len(eligible_student)}')`。
- `main`，第 208 行：`RuntimeError(f'expected 14 current-contract quarantined samples, got {len(quarantine)}')`。
- `main`，第 217 行：`RuntimeError('contract quarantine reasons changed: ' + json.dumps(dict(reasons), ensure_ascii=False, sort_keys=True))`。
- `main`，第 223 行：`RuntimeError(f'expected 13 affected groups, got {len(affected_groups)}')`。
- `main`，第 230 行：`RuntimeError('eligible canonical/student sample-id sets differ')`。
- `main`，第 249 行：`RuntimeError(f"eligible sample missing group_key: {r['sample_id']}")`。
- `main`，第 399 行：`RuntimeError('eligible canonical reread count mismatch')`。
- `main`，第 401 行：`RuntimeError('eligible student reread count mismatch')`。
- `main`，第 403 行：`RuntimeError('quarantine reread count mismatch')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 51 行：`ap.add_argument('--canonical', default='artifacts/b1_d1_delivery_v0/dataset_sample_228.jsonl')`。
- 第 55 行：`ap.add_argument('--d1-manifest', default='artifacts/b1_d1_delivery_v0/dataset_manifest_v0.json')`。
- 第 59 行：`ap.add_argument('--output-dir', default='artifacts/b1_d2_training_pool_v0')`。
- 第 63 行：`ap.add_argument('--dry-run', action='store_true')`。
- 第 64 行：`ap.add_argument('--allow-uncommitted-code', action='store_true')`。

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

### `challenge/dataset/build_d2_training_pool.py`

来源 SHA256：`3c3e7e22ea7066339b9f4478f0b457c8680dcfe9c4882767938fbfa48eb24802`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 51 | `'--canonical'` | `default='artifacts/b1_d1_delivery_v0/dataset_sample_228.jsonl'` |
| 55 | `'--d1-manifest'` | `default='artifacts/b1_d1_delivery_v0/dataset_manifest_v0.json'` |
| 59 | `'--output-dir'` | `default='artifacts/b1_d2_training_pool_v0'` |
| 63 | `'--dry-run'` | `action='store_true'` |
| 64 | `'--allow-uncommitted-code'` | `action='store_true'` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `main` / 72 | `not canonical_path.is_file()` | `raise RuntimeError(f'canonical dataset missing: {canonical_path}')` |
| `main` / 74 | `not d1_manifest_path.is_file()` | `raise RuntimeError(f'D1 manifest missing: {d1_manifest_path}')` |
| `main` / 80 | `canonical_sha != SOURCE_D1_CANONICAL_SHA256` | `raise RuntimeError(f'D1 canonical SHA mismatch: expected={SOURCE_D1_CANONICAL_SHA256} actual={canonical_sha}')` |
| `main` / 85 | `manifest_sha != SOURCE_D1_MANIFEST_SHA256` | `raise RuntimeError(f'D1 manifest SHA mismatch: expected={SOURCE_D1_MANIFEST_SHA256} actual={manifest_sha}')` |
| `main` / 111 | `len(rows) != 228` | `raise RuntimeError(f'expected 228 D1 canonical samples, got {len(rows)}')` |
| `main` / 126 | `not isinstance(sample_id, str) or not sample_id` | `raise RuntimeError('canonical sample missing sample_id')` |
| `main` / 128 | `sample_id in seen_sample_ids` | `raise RuntimeError(f'duplicate canonical sample_id: {sample_id}')` |
| `main` / 135 | `reason is None AND view is None` | `raise RuntimeError(f'student view unexpectedly missing: {sample_id}')` |
| `main` / 139 | `reason is None AND not isinstance(policy, dict)` | `raise RuntimeError(f'training_policy missing in rebuilt view: {sample_id}')` |
| `main` / 141 | `reason is None AND policy.get('train_eligible') is not True` | `raise RuntimeError(f'rebuilt view is not train eligible: {sample_id}')` |
| `main` / 145 | `reason is None AND not isinstance(meta, dict)` | `raise RuntimeError(f'rebuilt view metadata missing: {sample_id}')` |
| `main` / 147 | `reason is None AND meta.get('student_contract') != EXPECTED_STUDENT_CONTRACT` | `raise RuntimeError(f"student contract mismatch for {sample_id}: {meta.get('student_contract')!r}")` |
| `main` / 152 | `reason is None AND meta.get('student_max_targets') != EXPECTED_MAX_TARGETS` | `raise RuntimeError(f'student_max_targets mismatch: {sample_id}')` |
| `main` / 154 | `reason is None AND meta.get('student_no_target_index') != EXPECTED_NO_TARGET_INDEX` | `raise RuntimeError(f'student_no_target_index mismatch: {sample_id}')` |
| `main` / 158 | `reason is None AND not isinstance(request, dict)` | `raise RuntimeError(f'student input missing: {sample_id}')` |
| `main` / 164 | `reason is None AND len(targets) > EXPECTED_MAX_TARGETS` | `raise RuntimeError(f'student target overflow: {sample_id}')` |
| `main` / 169 | `reason is None AND not isinstance(plan, dict)` | `raise RuntimeError(f'teacher maneuver plan missing: {sample_id}')` |
| `main` / 172 | `reason is None AND sample_id in eligible_ids` | `raise RuntimeError(f'duplicate eligible sample_id: {sample_id}')` |
| `main` / 199 | `len(eligible_canonical) != 214` | `raise RuntimeError(f'expected 214 current-contract eligible canonical samples, got {len(eligible_canonical)}')` |
| `main` / 204 | `len(eligible_student) != 214` | `raise RuntimeError(f'expected 214 current-contract student views, got {len(eligible_student)}')` |
| `main` / 208 | `len(quarantine) != 14` | `raise RuntimeError(f'expected 14 current-contract quarantined samples, got {len(quarantine)}')` |
| `main` / 217 | `dict(reasons) != expected_reasons` | `raise RuntimeError('contract quarantine reasons changed: ' + json.dumps(dict(reasons), ensure_ascii=False, sort_keys=True))` |
| `main` / 223 | `len(affected_groups) != 13` | `raise RuntimeError(f'expected 13 affected groups, got {len(affected_groups)}')` |
| `main` / 230 | `canonical_ids != student_ids` | `raise RuntimeError('eligible canonical/student sample-id sets differ')` |
| `main` / 249 | `not g` | `raise RuntimeError(f"eligible sample missing group_key: {r['sample_id']}")` |
| `main` / 399 | `len(base.read_jsonl(canonical_out)) != 214` | `raise RuntimeError('eligible canonical reread count mismatch')` |
| `main` / 401 | `len(base.read_jsonl(student_out)) != 214` | `raise RuntimeError('eligible student reread count mismatch')` |
| `main` / 403 | `len(base.read_jsonl(quarantine_out)) != 14` | `raise RuntimeError('quarantine reread count mismatch')` |
