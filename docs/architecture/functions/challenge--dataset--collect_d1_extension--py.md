# collect_d1_extension：功能记录

上级模块：[模块说明](../modules/challenge-data.md) · 实现：[challenge/dataset/collect_d1_extension.py](../../../challenge/dataset/collect_d1_extension.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [原始样本、冻结发布与派生训练视图](dataset-release-view.md)

## 功能职责与范围

collect_d1_extension

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `canonical_json_sha256`

源码位置：[challenge/dataset/collect_d1_extension.py 第 13 行](../../../challenge/dataset/collect_d1_extension.py#L13)。类型：`FunctionDef`。

```python
canonical_json_sha256(value) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `verify_plan`

源码位置：[challenge/dataset/collect_d1_extension.py 第 17 行](../../../challenge/dataset/collect_d1_extension.py#L17)。类型：`FunctionDef`。

```python
verify_plan(path: Path) -> 未声明返回类型
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `run_seed_variant`

源码位置：[challenge/dataset/collect_d1_extension.py 第 55 行](../../../challenge/dataset/collect_d1_extension.py#L55)。类型：`FunctionDef`。

```python
run_seed_variant(repo: Path, runner_python: str, scenario_path: str, seed: int, service_url: str, log_dir: Path, image_prefix: str, host: str, port: int, timeout_ms: int) -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `collect_one_log`

源码位置：[challenge/dataset/collect_d1_extension.py 第 76 行](../../../challenge/dataset/collect_d1_extension.py#L76)。类型：`FunctionDef`。

```python
collect_one_log(repo: Path, runner_python: str, log_path: Path, tmp_dir: Path, eid: str) -> 未声明返回类型
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `append_jsonl`

源码位置：[challenge/dataset/collect_d1_extension.py 第 91 行](../../../challenge/dataset/collect_d1_extension.py#L91)。类型：`FunctionDef`。

```python
append_jsonl(path: Path, rows) -> 未声明返回类型
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[challenge/dataset/collect_d1_extension.py 第 99 行](../../../challenge/dataset/collect_d1_extension.py#L99)。类型：`FunctionDef`。

```python
main() -> 未声明返回类型
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main.group_key_of`

源码位置：[challenge/dataset/collect_d1_extension.py 第 279 行](../../../challenge/dataset/collect_d1_extension.py#L279)。类型：`FunctionDef`。

```python
main.group_key_of(row) -> 未声明返回类型
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `canonical_json_sha256` 调用：`hashlib.sha256`, `hashlib.sha256(raw).hexdigest`, `json.dumps`, `json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode`.
- `verify_plan` 调用：`RuntimeError`, `base.read_json`, `body.pop`, `canonical_json_sha256`, `dict`, `isinstance`, `plan.get`, `r.get`, `seen.add`, `seen_seeds.add`, `set`, `str`, `str(r.get('source_bucket') or '').upper`.
- `run_seed_variant` 调用：`print`, `str`, `subprocess.run`.
- `collect_one_log` 调用：`RuntimeError`, `base.read_jsonl`, `str`, `subprocess.run`.
- `append_jsonl` 调用：`f.write`, `json.dumps`, `path.open`, `path.parent.mkdir`.
- `main` 调用：`(repo / args.base_dataset).resolve`, `(repo / args.base_provenance).resolve`, `(repo / args.output_dir).resolve`, `(repo / args.plan).resolve`, `(repo / args.registry).resolve`, `(repo / args.teacher_artifact_manifest).resolve`, `(row.get('metadata') or {}).get`, `(sample.get('metadata') or {}).get`, `Path`, `Path(__file__).resolve`, `RuntimeError`, `ap.add_argument`, `ap.parse_args`, `append_jsonl`, `argparse.ArgumentParser`, `base.carla_port_preflight`, `base.current_branch`, `base.current_head`, `base.enrich_canonical`, `base.load_model_artifact_manifest`, `base.load_registry`, `base.load_run_state`, `base.load_teacher_manifest`, `base.read_json`, `base.read_jsonl`, `base.runner_preflight`, `base.save_run_state`, `base.sha256_file`, `base.student_view_or_reason`, `base.teacher_health`, `base.validate_canonical`, `base.verify_tracked_file_matches_head`, `base.write_json`, `base_ds.relative_to`, `base_prov.get`, `canon.append`, `canonical_json_sha256`, `collect_one_log`, `d.mkdir`, `extension_group_owners.get`, `group_key_of`, `images.relative_to`, `int`, `isinstance`, `json.dumps`, `len`, `logs.glob`, `meta.get`, `meta.update`, `out.mkdir`, `output_path.touch`, `p.is_file`, `p.stat`, `plan.get`, `plan_path.relative_to`, `print`, `prior.get`, `quar.append`, `r.get`, `registry_path.relative_to`, `row.get`, `run_seed_variant`, `sample.get`, `sample.setdefault`, `scenario_file.is_file`, `scenario_file.relative_to`, `set`, `sorted`, `state['runs'].get`, `state['runs'].items`, `str`, `stud.append`, `time.time`, `v.get`, `verify_plan`.
- `group_key_of` 调用：`meta.get`, `row.get`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `collect_one_log`，第 88 行：`RuntimeError(f'collector.py failed for {eid}')`。
- `main`，第 127 行：`RuntimeError(f'required file missing: {p}')`。
- `main`，第 134 行：`RuntimeError('base provenance is not formal')`。
- `main`，第 136 行：`RuntimeError('base dataset count differs from plan')`。
- `main`，第 138 行：`RuntimeError('base dataset SHA differs from plan')`。
- `main`，第 140 行：`RuntimeError('base git SHA differs from plan')`。
- `main`，第 142 行：`RuntimeError('base config ID differs from plan')`。
- `main`，第 156 行：`RuntimeError('extension plan reuses formal base seed values: ' + json.dumps(sorted(seed_overlap)))`。
- `main`，第 162 行：`RuntimeError('extension plan does not have globally unique seeds')`。
- `main`，第 302 行：`RuntimeError('existing extension contains missing group_key')`。
- `main`，第 307 行：`RuntimeError('existing extension contains missing extension_id')`。
- `main`，第 312 行：`RuntimeError('existing extension/base group overlap: ' + str(group_key))`。
- `main`，第 319 行：`RuntimeError(f'existing extension group has multiple owners: group={group_key} owners={owner},{extension_id}')`。
- `main`，第 345 行：`RuntimeError(f'scenario not found: {scenario_path}')`。
- `verify_plan`，第 24 行：`RuntimeError(f'plan hash mismatch expected={expected} actual={actual}')`。
- `verify_plan`，第 27 行：`RuntimeError('plan list missing')`。
- `verify_plan`，第 34 行：`RuntimeError(f'bad extension_id {eid!r}')`。
- `verify_plan`，第 39 行：`RuntimeError(f'extension_seed must be int for {eid}: {seed!r}')`。
- `verify_plan`，第 43 行：`RuntimeError(f'duplicate extension_seed in formal plan: {seed}')`。
- `verify_plan`，第 48 行：`RuntimeError(f'unsupported extension_type: {eid}')`。
- `verify_plan`，第 50 行：`RuntimeError(f'protected policy leaked: {eid}')`。
- `verify_plan`，第 52 行：`RuntimeError(f'protected source bucket leaked: {eid}')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 101 行：`ap.add_argument('--plan', default='artifacts/b1_d1_extension_plan/d1_extension_plan_formal.json')`。
- 第 102 行：`ap.add_argument('--registry', default='artifacts/b1_d1_registry_final/scenario_registry_v3.csv')`。
- 第 103 行：`ap.add_argument('--base-dataset', default='artifacts/b1_d1_pinned_formal/dataset/d1_valid.jsonl')`。
- 第 104 行：`ap.add_argument('--base-provenance', default='artifacts/b1_d1_pinned_formal/provenance_manifest.json')`。
- 第 105 行：`ap.add_argument('--teacher-artifact-manifest', default='artifacts/b1_teacher_pinned/teacher_model_manifest_latest.json')`。
- 第 106 行：`ap.add_argument('--output-dir', default='artifacts/b1_d1_extension_formal')`。
- 第 107 行：`ap.add_argument('--qwen-service-url', default='http://127.0.0.1:18004')`。
- 第 108 行：`ap.add_argument('--runner-python', default='/home/dcase_task2/miniconda3/envs/voice/bin/python')`。
- 第 109 行：`ap.add_argument('--carla-host', default='127.0.0.1')`。
- 第 110 行：`ap.add_argument('--carla-port', type=int, default=2000)`。
- 第 111 行：`ap.add_argument('--qwen-timeout-ms', type=int, default=5000)`。
- 第 112 行：`ap.add_argument('--max-runs', type=int, default=None)`。
- 第 113 行：`ap.add_argument('--dry-run', action='store_true')`。
- 第 114 行：`ap.add_argument('--allow-uncommitted-code', action='store_true')`。

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

### `challenge/dataset/collect_d1_extension.py`

来源 SHA256：`f7c937b0aca7078f1e91946a64bfef19ff55d4babc84125727267951e85ccd41`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 101 | `'--plan'` | `default='artifacts/b1_d1_extension_plan/d1_extension_plan_formal.json'` |
| 102 | `'--registry'` | `default='artifacts/b1_d1_registry_final/scenario_registry_v3.csv'` |
| 103 | `'--base-dataset'` | `default='artifacts/b1_d1_pinned_formal/dataset/d1_valid.jsonl'` |
| 104 | `'--base-provenance'` | `default='artifacts/b1_d1_pinned_formal/provenance_manifest.json'` |
| 105 | `'--teacher-artifact-manifest'` | `default='artifacts/b1_teacher_pinned/teacher_model_manifest_latest.json'` |
| 106 | `'--output-dir'` | `default='artifacts/b1_d1_extension_formal'` |
| 107 | `'--qwen-service-url'` | `default='http://127.0.0.1:18004'` |
| 108 | `'--runner-python'` | `default='/home/dcase_task2/miniconda3/envs/voice/bin/python'` |
| 109 | `'--carla-host'` | `default='127.0.0.1'` |
| 110 | `'--carla-port'` | `type=int; default=2000` |
| 111 | `'--qwen-timeout-ms'` | `type=int; default=5000` |
| 112 | `'--max-runs'` | `type=int; default=None` |
| 113 | `'--dry-run'` | `action='store_true'` |
| 114 | `'--allow-uncommitted-code'` | `action='store_true'` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `verify_plan` / 24 | `expected != actual` | `raise RuntimeError(f'plan hash mismatch expected={expected} actual={actual}')` |
| `verify_plan` / 27 | `not isinstance(rows, list)` | `raise RuntimeError('plan list missing')` |
| `verify_plan` / 34 | `not eid or eid in seen` | `raise RuntimeError(f'bad extension_id {eid!r}')` |
| `verify_plan` / 39 | `not isinstance(seed, int)` | `raise RuntimeError(f'extension_seed must be int for {eid}: {seed!r}')` |
| `verify_plan` / 43 | `seed in seen_seeds` | `raise RuntimeError(f'duplicate extension_seed in formal plan: {seed}')` |
| `verify_plan` / 48 | `r.get('extension_type') != EXTENSION_TYPE` | `raise RuntimeError(f'unsupported extension_type: {eid}')` |
| `verify_plan` / 50 | `r.get('policy_class') != ALLOWED_POLICY` | `raise RuntimeError(f'protected policy leaked: {eid}')` |
| `verify_plan` / 52 | `str(r.get('source_bucket') or '').upper() not in ALLOWED_BUCKETS` | `raise RuntimeError(f'protected source bucket leaked: {eid}')` |
| `collect_one_log` / 88 | `rc != 0` | `raise RuntimeError(f'collector.py failed for {eid}')` |
| `main` / 127 | `not p.is_file()` | `raise RuntimeError(f'required file missing: {p}')` |
| `main` / 134 | `base_prov.get('formal_code_gate') is not True` | `raise RuntimeError('base provenance is not formal')` |
| `main` / 136 | `len(base_rows) != int(plan.get('base_dataset_count') or -1)` | `raise RuntimeError('base dataset count differs from plan')` |
| `main` / 138 | `base.sha256_file(base_ds) != plan.get('base_dataset_file_sha256')` | `raise RuntimeError('base dataset SHA differs from plan')` |
| `main` / 140 | `base_prov.get('collection_repo_git_sha') != plan.get('base_collection_repo_git_sha')` | `raise RuntimeError('base git SHA differs from plan')` |
| `main` / 142 | `base_prov.get('config_id') != plan.get('base_config_id')` | `raise RuntimeError('base config ID differs from plan')` |
| `main` / 156 | `seed_overlap` | `raise RuntimeError('extension plan reuses formal base seed values: ' + json.dumps(sorted(seed_overlap)))` |
| `main` / 162 | `len(planned_seed_values) != len(plan['plan'])` | `raise RuntimeError('extension plan does not have globally unique seeds')` |
| `main` / 302 | `not group_key` | `raise RuntimeError('existing extension contains missing group_key')` |
| `main` / 307 | `not extension_id` | `raise RuntimeError('existing extension contains missing extension_id')` |
| `main` / 312 | `group_key in base_group_keys` | `raise RuntimeError('existing extension/base group overlap: ' + str(group_key))` |
| `main` / 319 | `owner is not None and owner != extension_id` | `raise RuntimeError(f'existing extension group has multiple owners: group={group_key} owners={owner},{extension_id}')` |
| `main` / 345 | `not scenario_file.is_file()` | `raise RuntimeError(f'scenario not found: {scenario_path}')` |
