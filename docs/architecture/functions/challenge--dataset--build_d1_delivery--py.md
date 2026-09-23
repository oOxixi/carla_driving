# build_d1_delivery：功能记录

上级模块：[模块说明](../modules/challenge-data.md) · 实现：[challenge/dataset/build_d1_delivery.py](../../../challenge/dataset/build_d1_delivery.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [原始样本、冻结发布与派生训练视图](dataset-release-view.md)

## 功能职责与范围

build_d1_delivery

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `sha256_file`

源码位置：[challenge/dataset/build_d1_delivery.py 第 20 行](../../../challenge/dataset/build_d1_delivery.py#L20)。类型：`FunctionDef`。

```python
sha256_file(path: Path) -> str
```

`sha256_file` 生成内容或文件的稳定身份摘要，用于计划、发布或provenance绑定；摘要口径区分原始字节与规范化JSON，不能混用。

### `write_jsonl`

源码位置：[challenge/dataset/build_d1_delivery.py 第 28 行](../../../challenge/dataset/build_d1_delivery.py#L28)。类型：`FunctionDef`。

```python
write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None
```

`write_jsonl` 将已构造结果写入目标路径或发布目录；文件写成不代表样本合格，调用前后仍需核对原子性、SHA256、行数和manifest引用。

### `write_json`

源码位置：[challenge/dataset/build_d1_delivery.py 第 35 行](../../../challenge/dataset/build_d1_delivery.py#L35)。类型：`FunctionDef`。

```python
write_json(path: Path, value: Any) -> None
```

`write_json` 将已构造结果写入目标路径或发布目录；文件写成不代表样本合格，调用前后仍需核对原子性、SHA256、行数和manifest引用。

### `get_meta`

源码位置：[challenge/dataset/build_d1_delivery.py 第 43 行](../../../challenge/dataset/build_d1_delivery.py#L43)。类型：`FunctionDef`。

```python
get_meta(row: dict[str, Any]) -> dict[str, Any]
```

`get_meta` 读取或派生数据治理所需的输入，不修改源发布；缺失、类型和回退语义以函数返回及本页异常表为准，调用方仍须固定数据版本与来源清单。

### `validate_teacher_identity`

源码位置：[challenge/dataset/build_d1_delivery.py 第 48 行](../../../challenge/dataset/build_d1_delivery.py#L48)。类型：`FunctionDef`。

```python
validate_teacher_identity(rows: list[dict[str, Any]]) -> dict[str, str]
```

`validate_teacher_identity` 执行当前阶段的拒绝式门禁；只覆盖函数读取的字段/文件，成功不能替代Teacher服务、闭环终态、切分防泄漏或下游A3预检。

### `audit_groups`

源码位置：[challenge/dataset/build_d1_delivery.py 第 62 行](../../../challenge/dataset/build_d1_delivery.py#L62)。类型：`FunctionDef`。

```python
audit_groups(base_rows, ext_rows) -> 未声明返回类型
```

`audit_groups` 参与分组、候选或确定性切分与分配；必须保持同组不跨split、seed可复现并记录未满足配额，不能靠重跑挑选有利结果。

### `schema_markdown`

源码位置：[challenge/dataset/build_d1_delivery.py 第 96 行](../../../challenge/dataset/build_d1_delivery.py#L96)。类型：`FunctionDef`。

```python
schema_markdown() -> str
```

`schema_markdown` 定义本脚本使用的数据或状态封装；字段含义由构造处和消费者共同约束，不能脱离发布版本解释。

### `quality_markdown`

源码位置：[challenge/dataset/build_d1_delivery.py 第 125 行](../../../challenge/dataset/build_d1_delivery.py#L125)。类型：`FunctionDef`。

```python
quality_markdown(counts, group_audit, source_counts, class_counts, quarantine_counts, collection_sha_counts, failures) -> str
```

`quality_markdown` 定义本脚本使用的数据或状态封装；字段含义由构造处和消费者共同约束，不能脱离发布版本解释。

### `main`

源码位置：[challenge/dataset/build_d1_delivery.py 第 176 行](../../../challenge/dataset/build_d1_delivery.py#L176)。类型：`FunctionDef`。

```python
main() -> int
```

解析命令行参数并编排本脚本的数据读取、身份校验、生成/采集与落盘步骤；退出码和产物是否可发布取决于本页所列拒绝条件，不能只凭文件生成成功判定。

## 内部调用与异常路径

- `sha256_file` 调用：`f.read`, `h.hexdigest`, `h.update`, `hashlib.sha256`, `iter`, `path.open`.
- `write_jsonl` 调用：`f.write`, `json.dumps`, `path.open`, `path.parent.mkdir`.
- `write_json` 调用：`json.dumps`, `path.parent.mkdir`, `path.write_text`.
- `get_meta` 调用：`isinstance`, `row.get`.
- `validate_teacher_identity` 调用：`RuntimeError`, `expected.items`, `get_meta`, `get_meta(r).get`.
- `audit_groups` 调用：`Counter`, `RuntimeError`, `counts.values`, `defaultdict`, `get_meta`, `get_meta(r).get`, `len`, `max`, `meta.get`, `owners.items`, `owners[str(g)].add`, `set`, `sorted`, `str`, `sum`.
- `quality_markdown` 调用：`dict`, `json.dumps`.
- `main` 调用：`(out / 'dataset_manifest_v0.sha256').write_text`, `(r.get('sample_class') or {}).get`, `(repo / args.output_dir).resolve`, `(repo / v).resolve`, `(run_state.get('runs') or {}).items`, `Counter`, `Path`, `Path(__file__).resolve`, `RuntimeError`, `ap.add_argument`, `ap.parse_args`, `argparse.ArgumentParser`, `audit_groups`, `base.current_branch`, `base.current_head`, `base.read_json`, `base.read_jsonl`, `base.verify_tracked_file_matches_head`, `dict`, `final_prov.get`, `final_summary.get`, `get_meta`, `get_meta(r).get`, `isinstance`, `item.get`, `len`, `out.mkdir`, `path.is_file`, `path.relative_to`, `paths.items`, `paths.values`, `print`, `quality_markdown`, `quality_out.write_text`, `r.get`, `raw_paths.items`, `run_state.get`, `schema_markdown`, `schema_out.write_text`, `set`, `sha256_file`, `sorted`, `str`, `validate_teacher_identity`, `write_json`, `write_jsonl`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `audit_groups`，第 74 行：`RuntimeError('extension sample missing group_key/extension_id')`。
- `audit_groups`，第 78 行：`RuntimeError(f'base/extension overlap: {sorted(overlap)}')`。
- `audit_groups`，第 81 行：`RuntimeError(f'multi-owner extension groups: {bad}')`。
- `main`，第 207 行：`RuntimeError(f'missing input: {name}={path}')`。
- `main`，第 234 行：`RuntimeError(f'expected 228/228, got {len(canonical)}/{len(student)}')`。
- `main`，第 239 行：`RuntimeError('missing sample_id')`。
- `main`，第 241 行：`RuntimeError('duplicate canonical sample_id')`。
- `main`，第 243 行：`RuntimeError('duplicate student sample_id')`。
- `main`，第 245 行：`RuntimeError('canonical/student sample-id sets differ')`。
- `main`，第 252 行：`RuntimeError(f'unexpected source buckets: {dict(source_counts)}')`。
- `main`，第 264 行：`RuntimeError(f'unexpected quarantine reasons: {dict(quarantine_counts)}')`。
- `main`，第 268 行：`RuntimeError('combined_valid != 228')`。
- `main`，第 270 行：`RuntimeError('minimum_reached != true')`。
- `main`，第 272 行：`RuntimeError('target_reached != true')`。
- `main`，第 276 行：`RuntimeError('finalization provenance is not formal')`。
- `main`，第 290 行：`RuntimeError(f'process failure set changed: {failures}')`。
- `main`，第 398 行：`RuntimeError('canonical reread mismatch')`。
- `main`，第 400 行：`RuntimeError('student reread mismatch')`。
- `main`，第 402 行：`RuntimeError('quarantine reread mismatch')`。
- `validate_teacher_identity`，第 58 行：`RuntimeError(f'{key} mismatch: {values!r}')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 178 行：`ap.add_argument('--base-canonical', default='artifacts/b1_d1_pinned_formal/dataset/d1_valid.jsonl')`。
- 第 179 行：`ap.add_argument('--base-student', default='artifacts/b1_d1_pinned_formal/dataset/d1_student_eligible.jsonl')`。
- 第 180 行：`ap.add_argument('--base-provenance', default='artifacts/b1_d1_pinned_formal/provenance_manifest.json')`。
- 第 181 行：`ap.add_argument('--extension-canonical', default='artifacts/b1_d1_extension_final/dataset/extension_valid.jsonl')`。
- 第 182 行：`ap.add_argument('--extension-student', default='artifacts/b1_d1_extension_final/dataset/extension_student_eligible.jsonl')`。
- 第 183 行：`ap.add_argument('--extension-quarantine', default='artifacts/b1_d1_extension_final/dataset/extension_quarantine.jsonl')`。
- 第 184 行：`ap.add_argument('--extension-finalization-summary', default='artifacts/b1_d1_extension_final/finalization_summary.json')`。
- 第 185 行：`ap.add_argument('--extension-finalization-provenance', default='artifacts/b1_d1_extension_final/finalization_provenance.json')`。
- 第 186 行：`ap.add_argument('--extension-run-state', default='artifacts/b1_d1_extension_formal/run_state.json')`。
- 第 187 行：`ap.add_argument('--output-dir', default='artifacts/b1_d1_delivery_v0')`。
- 第 188 行：`ap.add_argument('--dry-run', action='store_true')`。
- 第 189 行：`ap.add_argument('--allow-uncommitted-code', action='store_true')`。

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

### `challenge/dataset/build_d1_delivery.py`

来源 SHA256：`b7d70ae30e26394f64872bd5bf175ca38489773f95e53837bad19da879000a1d`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 178 | `'--base-canonical'` | `default='artifacts/b1_d1_pinned_formal/dataset/d1_valid.jsonl'` |
| 179 | `'--base-student'` | `default='artifacts/b1_d1_pinned_formal/dataset/d1_student_eligible.jsonl'` |
| 180 | `'--base-provenance'` | `default='artifacts/b1_d1_pinned_formal/provenance_manifest.json'` |
| 181 | `'--extension-canonical'` | `default='artifacts/b1_d1_extension_final/dataset/extension_valid.jsonl'` |
| 182 | `'--extension-student'` | `default='artifacts/b1_d1_extension_final/dataset/extension_student_eligible.jsonl'` |
| 183 | `'--extension-quarantine'` | `default='artifacts/b1_d1_extension_final/dataset/extension_quarantine.jsonl'` |
| 184 | `'--extension-finalization-summary'` | `default='artifacts/b1_d1_extension_final/finalization_summary.json'` |
| 185 | `'--extension-finalization-provenance'` | `default='artifacts/b1_d1_extension_final/finalization_provenance.json'` |
| 186 | `'--extension-run-state'` | `default='artifacts/b1_d1_extension_formal/run_state.json'` |
| 187 | `'--output-dir'` | `default='artifacts/b1_d1_delivery_v0'` |
| 188 | `'--dry-run'` | `action='store_true'` |
| 189 | `'--allow-uncommitted-code'` | `action='store_true'` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `validate_teacher_identity` / 58 | `values != {wanted}` | `raise RuntimeError(f'{key} mismatch: {values!r}')` |
| `audit_groups` / 74 | `not g or not eid` | `raise RuntimeError('extension sample missing group_key/extension_id')` |
| `audit_groups` / 78 | `overlap` | `raise RuntimeError(f'base/extension overlap: {sorted(overlap)}')` |
| `audit_groups` / 81 | `bad` | `raise RuntimeError(f'multi-owner extension groups: {bad}')` |
| `main` / 207 | `not path.is_file()` | `raise RuntimeError(f'missing input: {name}={path}')` |
| `main` / 234 | `len(canonical) != 228 or len(student) != 228` | `raise RuntimeError(f'expected 228/228, got {len(canonical)}/{len(student)}')` |
| `main` / 239 | `None in canonical_ids or None in student_ids` | `raise RuntimeError('missing sample_id')` |
| `main` / 241 | `len(canonical_ids) != len(set(canonical_ids))` | `raise RuntimeError('duplicate canonical sample_id')` |
| `main` / 243 | `len(student_ids) != len(set(student_ids))` | `raise RuntimeError('duplicate student sample_id')` |
| `main` / 245 | `set(canonical_ids) != set(student_ids)` | `raise RuntimeError('canonical/student sample-id sets differ')` |
| `main` / 252 | `set(source_counts) - {'SEEN', 'VARIANT'}` | `raise RuntimeError(f'unexpected source buckets: {dict(source_counts)}')` |
| `main` / 264 | `set(quarantine_counts) - {'COMMAND_TERMINAL_NOT_SUCCEEDED'}` | `raise RuntimeError(f'unexpected quarantine reasons: {dict(quarantine_counts)}')` |
| `main` / 268 | `final_summary.get('combined_valid') != 228` | `raise RuntimeError('combined_valid != 228')` |
| `main` / 270 | `final_summary.get('minimum_reached') is not True` | `raise RuntimeError('minimum_reached != true')` |
| `main` / 272 | `final_summary.get('target_reached') is not True` | `raise RuntimeError('target_reached != true')` |
| `main` / 276 | `final_prov.get('formal_code_gate') is not True` | `raise RuntimeError('finalization provenance is not formal')` |
| `main` / 290 | `set(failures) != expected_failures` | `raise RuntimeError(f'process failure set changed: {failures}')` |
| `main` / 398 | `len(base.read_jsonl(canonical_out)) != 228` | `raise RuntimeError('canonical reread mismatch')` |
| `main` / 400 | `len(base.read_jsonl(student_out)) != 228` | `raise RuntimeError('student reread mismatch')` |
| `main` / 402 | `len(base.read_jsonl(quarantine_out)) != len(quarantine)` | `raise RuntimeError('quarantine reread mismatch')` |
