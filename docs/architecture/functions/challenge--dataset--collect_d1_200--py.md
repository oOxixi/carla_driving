# collect_d1_200：功能记录

上级模块：[模块说明](../modules/challenge-data.md) · 实现：[challenge/dataset/collect_d1_200.py](../../../challenge/dataset/collect_d1_200.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [原始样本、冻结发布与派生训练视图](dataset-release-view.md)

## 功能职责与范围

collect_d1_200

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `read_json`

源码位置：[challenge/dataset/collect_d1_200.py 第 28 行](../../../challenge/dataset/collect_d1_200.py#L28)。类型：`FunctionDef`。

```python
read_json(path: Path) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `read_jsonl`

源码位置：[challenge/dataset/collect_d1_200.py 第 35 行](../../../challenge/dataset/collect_d1_200.py#L35)。类型：`FunctionDef`。

```python
read_jsonl(path: Path) -> list[dict[str, Any]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `write_json`

源码位置：[challenge/dataset/collect_d1_200.py 第 50 行](../../../challenge/dataset/collect_d1_200.py#L50)。类型：`FunctionDef`。

```python
write_json(path: Path, value: Any) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `write_jsonl`

源码位置：[challenge/dataset/collect_d1_200.py 第 58 行](../../../challenge/dataset/collect_d1_200.py#L58)。类型：`FunctionDef`。

```python
write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `count_jsonl`

源码位置：[challenge/dataset/collect_d1_200.py 第 65 行](../../../challenge/dataset/collect_d1_200.py#L65)。类型：`FunctionDef`。

```python
count_jsonl(path: Path) -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `sha256_file`

源码位置：[challenge/dataset/collect_d1_200.py 第 69 行](../../../challenge/dataset/collect_d1_200.py#L69)。类型：`FunctionDef`。

```python
sha256_file(path: Path) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `canonical_json_sha256`

源码位置：[challenge/dataset/collect_d1_200.py 第 77 行](../../../challenge/dataset/collect_d1_200.py#L77)。类型：`FunctionDef`。

```python
canonical_json_sha256(value: Any) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `git`

源码位置：[challenge/dataset/collect_d1_200.py 第 88 行](../../../challenge/dataset/collect_d1_200.py#L88)。类型：`FunctionDef`。

```python
git(repo: Path, *args: str) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `current_head`

源码位置：[challenge/dataset/collect_d1_200.py 第 100 行](../../../challenge/dataset/collect_d1_200.py#L100)。类型：`FunctionDef`。

```python
current_head(repo: Path) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `current_branch`

源码位置：[challenge/dataset/collect_d1_200.py 第 104 行](../../../challenge/dataset/collect_d1_200.py#L104)。类型：`FunctionDef`。

```python
current_branch(repo: Path) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `verify_tracked_file_matches_head`

源码位置：[challenge/dataset/collect_d1_200.py 第 108 行](../../../challenge/dataset/collect_d1_200.py#L108)。类型：`FunctionDef`。

```python
verify_tracked_file_matches_head(repo: Path, relative_path: str) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `load_registry`

源码位置：[challenge/dataset/collect_d1_200.py 第 164 行](../../../challenge/dataset/collect_d1_200.py#L164)。类型：`FunctionDef`。

```python
load_registry(path: Path) -> list[dict[str, str]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `teacher_health`

源码位置：[challenge/dataset/collect_d1_200.py 第 169 行](../../../challenge/dataset/collect_d1_200.py#L169)。类型：`FunctionDef`。

```python
teacher_health(service_url: str) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `load_teacher_manifest`

源码位置：[challenge/dataset/collect_d1_200.py 第 188 行](../../../challenge/dataset/collect_d1_200.py#L188)。类型：`FunctionDef`。

```python
load_teacher_manifest(repo: Path) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `load_model_artifact_manifest`

源码位置：[challenge/dataset/collect_d1_200.py 第 212 行](../../../challenge/dataset/collect_d1_200.py#L212)。类型：`FunctionDef`。

```python
load_model_artifact_manifest(path: Path) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `runner_preflight`

源码位置：[challenge/dataset/collect_d1_200.py 第 252 行](../../../challenge/dataset/collect_d1_200.py#L252)。类型：`FunctionDef`。

```python
runner_preflight(runner_python: str, repo: Path) -> dict[str, str]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `carla_port_preflight`

源码位置：[challenge/dataset/collect_d1_200.py 第 279 行](../../../challenge/dataset/collect_d1_200.py#L279)。类型：`FunctionDef`。

```python
carla_port_preflight(host: str, port: int) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `sort_key`

源码位置：[challenge/dataset/collect_d1_200.py 第 286 行](../../../challenge/dataset/collect_d1_200.py#L286)。类型：`FunctionDef`。

```python
sort_key(row: dict[str, str]) -> tuple[int, int, str]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `build_positive_plan`

源码位置：[challenge/dataset/collect_d1_200.py 第 300 行](../../../challenge/dataset/collect_d1_200.py#L300)。类型：`FunctionDef`。

```python
build_positive_plan(registry: list[dict[str, str]]) -> list[dict[str, str]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `write_plan`

源码位置：[challenge/dataset/collect_d1_200.py 第 309 行](../../../challenge/dataset/collect_d1_200.py#L309)。类型：`FunctionDef`。

```python
write_plan(plan: list[dict[str, str]], out_dir: Path) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `load_run_state`

源码位置：[challenge/dataset/collect_d1_200.py 第 320 行](../../../challenge/dataset/collect_d1_200.py#L320)。类型：`FunctionDef`。

```python
load_run_state(path: Path) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `save_run_state`

源码位置：[challenge/dataset/collect_d1_200.py 第 329 行](../../../challenge/dataset/collect_d1_200.py#L329)。类型：`FunctionDef`。

```python
save_run_state(path: Path, state: dict[str, Any]) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `log_files_for_scenario`

源码位置：[challenge/dataset/collect_d1_200.py 第 333 行](../../../challenge/dataset/collect_d1_200.py#L333)。类型：`FunctionDef`。

```python
log_files_for_scenario(log_dir: Path, scenario_id: str) -> list[str]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `run_scenario`

源码位置：[challenge/dataset/collect_d1_200.py 第 337 行](../../../challenge/dataset/collect_d1_200.py#L337)。类型：`FunctionDef`。

```python
run_scenario(*, repo: Path, runner_python: str, scenario_path: str, service_url: str, log_dir: Path, image_prefix: str, host: str, port: int, timeout_ms: int) -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `collect_from_logs`

源码位置：[challenge/dataset/collect_d1_200.py 第 370 行](../../../challenge/dataset/collect_d1_200.py#L370)。类型：`FunctionDef`。

```python
collect_from_logs(*, repo: Path, python: str, log_dir: Path, dataset_dir: Path) -> tuple[int, int]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `referenced_target_ids`

源码位置：[challenge/dataset/collect_d1_200.py 第 401 行](../../../challenge/dataset/collect_d1_200.py#L401)。类型：`FunctionDef`。

```python
referenced_target_ids(plan: dict[str, Any]) -> list[str]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `primary_sample_class`

源码位置：[challenge/dataset/collect_d1_200.py 第 415 行](../../../challenge/dataset/collect_d1_200.py#L415)。类型：`FunctionDef`。

```python
primary_sample_class(sample: dict[str, Any]) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `enrich_canonical`

源码位置：[challenge/dataset/collect_d1_200.py 第 427 行](../../../challenge/dataset/collect_d1_200.py#L427)。类型：`FunctionDef`。

```python
enrich_canonical(sample: dict[str, Any], *, collection_head: str, teacher_manifest: dict[str, Any], registry_by_scenario: dict[str, dict[str, str]]) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `student_view_or_reason`

源码位置：[challenge/dataset/collect_d1_200.py 第 502 行](../../../challenge/dataset/collect_d1_200.py#L502)。类型：`FunctionDef`。

```python
student_view_or_reason(sample: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `rebuild_outputs`

源码位置：[challenge/dataset/collect_d1_200.py 第 584 行](../../../challenge/dataset/collect_d1_200.py#L584)。类型：`FunctionDef`。

```python
rebuild_outputs(*, raw_path: Path, dataset_dir: Path, collection_head: str, teacher_manifest: dict[str, Any], registry_by_scenario: dict[str, dict[str, str]]) -> dict[str, int]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `validate_canonical`

源码位置：[challenge/dataset/collect_d1_200.py 第 646 行](../../../challenge/dataset/collect_d1_200.py#L646)。类型：`FunctionDef`。

```python
validate_canonical(repo: Path, python: str, path: Path) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `capture_provenance`

源码位置：[challenge/dataset/collect_d1_200.py 第 659 行](../../../challenge/dataset/collect_d1_200.py#L659)。类型：`FunctionDef`。

```python
capture_provenance(*, repo: Path, out_path: Path, health: dict[str, Any], teacher_manifest: dict[str, Any], teacher_artifact_evidence: dict[str, Any], runner_info: dict[str, str], service_url: str, registry_path: Path, collector_identity: dict[str, Any] | None, config_id: str, formal_code_gate: bool) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[challenge/dataset/collect_d1_200.py 第 709 行](../../../challenge/dataset/collect_d1_200.py#L709)。类型：`FunctionDef`。

```python
main() -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `read_json` 调用：`ValueError`, `isinstance`, `json.loads`, `path.read_text`.
- `read_jsonl` 调用：`ValueError`, `enumerate`, `isinstance`, `json.loads`, `path.is_file`, `path.open`, `raw.strip`, `rows.append`.
- `write_json` 调用：`json.dumps`, `path.parent.mkdir`, `path.write_text`.
- `write_jsonl` 调用：`f.write`, `json.dumps`, `path.open`, `path.parent.mkdir`.
- `count_jsonl` 调用：`len`, `read_jsonl`.
- `sha256_file` 调用：`f.read`, `h.hexdigest`, `h.update`, `hashlib.sha256`, `iter`, `path.open`.
- `canonical_json_sha256` 调用：`hashlib.sha256`, `hashlib.sha256(payload).hexdigest`, `json.dumps`, `json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode`.
- `git` 调用：`result.stdout.strip`, `subprocess.run`.
- `current_head` 调用：`git`.
- `current_branch` 调用：`git`.
- `verify_tracked_file_matches_head` 调用：`RuntimeError`, `hashlib.sha256`, `hashlib.sha256(head_bytes).hexdigest`, `hashlib.sha256(worktree_bytes).hexdigest`, `subprocess.run`, `worktree_path.is_file`, `worktree_path.read_bytes`.
- `load_registry` 调用：`csv.DictReader`, `list`, `path.open`.
- `teacher_health` 调用：`RuntimeError`, `all`, `checks.items`, `checks.values`, `data.get`, `isinstance`, `json.loads`, `key.upper`, `print`, `r.read`, `r.read().decode`, `service_url.rstrip`, `urllib.request.urlopen`.
- `load_teacher_manifest` 调用：`RuntimeError`, `data.get`, `expected.items`, `json.dumps`, `print`, `read_json`.
- `load_model_artifact_manifest` 调用：`RuntimeError`, `canonical_json_sha256`, `data.get`, `expected.items`, `isinstance`, `json.dumps`, `len`, `print`, `read_json`, `sha256_file`, `str`.
- `runner_preflight` 调用：`RuntimeError`, `len`, `print`, `result.stdout.splitlines`, `subprocess.run`, `x.strip`.
- `carla_port_preflight` 调用：`print`, `socket.create_connection`.
- `sort_key` 调用：`any`, `int`, `row.get`, `row.get('scenario_path', '').lower`, `row.get('source_bucket', '').upper`.
- `build_positive_plan` 调用：`row.get`, `rows.sort`.
- `write_plan` 调用：`(out_dir / 'd1_collection_plan.csv').open`, `csv.DictWriter`, `list`, `plan[0].keys`, `write_json`, `writer.writeheader`, `writer.writerows`.
- `load_run_state` 调用：`RuntimeError`, `isinstance`, `path.is_file`, `read_json`, `state.get`.
- `save_run_state` 调用：`write_json`.
- `log_files_for_scenario` 调用：`log_dir.glob`, `sorted`, `str`.
- `run_scenario` 调用：`print`, `str`, `subprocess.run`.
- `collect_from_logs` 调用：`RuntimeError`, `count_jsonl`, `log_dir.glob`, `sorted`, `str`, `subprocess.run`.
- `referenced_target_ids` 调用：`isinstance`, `plan.get`, `result.append`, `step.get`, `target.get`.
- `primary_sample_class` 调用：`ValueError`, `isinstance`, `sample.get`, `sc.get`, `str`, `str(value or 'NORMAL').strip`, `str(value or 'NORMAL').strip().lower`.
- `enrich_canonical` 调用：`RuntimeError`, `isinstance`, `json.dumps`, `json.loads`, `meta.get`, `meta.setdefault`, `out.setdefault`, `primary_sample_class`, `registry_by_scenario.get`, `registry_row.get`, `registry_scenario_path.startswith`, `str`, `str(registry_row.get('source_bucket') or '').upper`.
- `student_view_or_reason` 调用：`closed_loop.get`, `dict`, `enumerate`, `ids.append`, `isinstance`, `json.dumps`, `json.loads`, `len`, `normalized_quality.update`, `primary_sample_class`, `quality.get`, `referenced_target_ids`, `request.get`, `sample.get`, `target.get`.
- `rebuild_outputs` 调用：`Counter`, `canonical_rows.append`, `dict`, `enrich_canonical`, `len`, `quarantine_rows.append`, `read_jsonl`, `reasons.items`, `sample.get`, `sorted`, `student_rows.append`, `student_view_or_reason`, `write_json`, `write_jsonl`.
- `validate_canonical` 调用：`RuntimeError`, `path.is_file`, `path.stat`, `print`, `str`, `subprocess.run`.
- `capture_provenance` 调用：`current_branch`, `current_head`, `sha256_file`, `str`, `write_json`.
- `main` 调用：`(repo / args.output_dir).resolve`, `(repo / args.registry).resolve`, `(repo / artifact_manifest_path).resolve`, `FileNotFoundError`, `Path`, `Path(__file__).resolve`, `RuntimeError`, `SystemExit`, `argparse.ArgumentParser`, `artifact_manifest_path.is_absolute`, `build_positive_plan`, `canonical_json_sha256`, `capture_provenance`, `carla_port_preflight`, `collect_from_logs`, `current_branch`, `current_head`, `d.mkdir`, `direct.is_file`, `images.relative_to`, `int`, `isinstance`, `key.upper`, `len`, `load_model_artifact_manifest`, `load_registry`, `load_run_state`, `load_teacher_manifest`, `log_files_for_scenario`, `parser.add_argument`, `parser.parse_args`, `print`, `process_failures.append`, `raw_valid_path.is_file`, `rebuild_outputs`, `row.get`, `run_entry.get`, `run_scenario`, `runner_preflight`, `save_run_state`, `scenario_file.is_absolute`, `scenario_file.relative_to`, `set`, `sha256_file`, `sorted`, `state['runs'].get`, `str`, `sum`, `summary.items`, `teacher_health`, `time.sleep`, `time.time`, `under_scenarios.is_file`, `validate_canonical`, `verify_tracked_file_matches_head`, `write_json`, `write_plan`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `collect_from_logs`，第 397 行：`RuntimeError('collector.py failed')`。
- `enrich_canonical`，第 456 行：`RuntimeError(f'sample scenario_id is absent from registry: {scenario_id!r}')`。
- `enrich_canonical`，第 465 行：`RuntimeError(f'invalid source_bucket for {scenario_id}: {source_bucket!r}')`。
- `enrich_canonical`，第 474 行：`RuntimeError(f'registry scenario_path missing for {scenario_id}')`。
- `load_model_artifact_manifest`，第 216 行：`RuntimeError('Teacher artifact manifest has no file inventory')`。
- `load_model_artifact_manifest`，第 235 行：`RuntimeError('Teacher artifact manifest does not match pinned artifact: ' + json.dumps(mismatch, ensure_ascii=False))`。
- `load_run_state`，第 325 行：`RuntimeError('run_state.json has invalid runs object')`。
- `load_teacher_manifest`，第 204 行：`RuntimeError('teacher_baseline_manifest.json does not match pinned Teacher: ' + json.dumps(bad, ensure_ascii=False))`。
- `main`，第 758 行：`SystemExit('--target-valid must be >=1')`。
- `main`，第 760 行：`SystemExit('--max-scenarios must be >=1')`。
- `main`，第 847 行：`RuntimeError(f'duplicate scenario_id in registry: {scenario_id}')`。
- `main`，第 915 行：`RuntimeError('registry TRAIN_POSITIVE row missing scenario path/id')`。
- `main`，第 927 行：`FileNotFoundError(f'scenario file not found: {scenario_path}; checked {direct} and {under_scenarios}')`。
- `primary_sample_class`，第 423 行：`ValueError(f'unsupported sample_class: {value!r}')`。
- `read_json`，第 31 行：`ValueError(f'{path}: expected JSON object')`。
- `read_jsonl`，第 45 行：`ValueError(f'{path}:{line_no}: expected JSON object')`。
- `runner_preflight`，第 267 行：`RuntimeError('Configured runner Python cannot import CARLA:\n' + result.stderr)`。
- `runner_preflight`，第 272 行：`RuntimeError('Runner Python preflight returned unexpected output')`。
- `teacher_health`，第 173 行：`RuntimeError('Teacher health payload is not an object')`。
- `teacher_health`，第 184 行：`RuntimeError('Pinned Teacher health/identity gate failed')`。
- `validate_canonical`，第 655 行：`RuntimeError('validate_dataset.py failed')`。
- `verify_tracked_file_matches_head`，第 115 行：`RuntimeError(f'required tracked file missing: {relative_path}')`。
- `verify_tracked_file_matches_head`，第 127 行：`RuntimeError(f'formal collection requires Git-tracked file: {relative_path}')`。
- `verify_tracked_file_matches_head`，第 140 行：`RuntimeError(f'cannot read HEAD version of {relative_path}')`。
- `verify_tracked_file_matches_head`，第 151 行：`RuntimeError(f'formal collection code differs from HEAD: {relative_path}; commit the exact collector before collecting formal data')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 711 行：`parser.add_argument('--registry', default='artifacts/b1_d1_registry_v3/scenario_registry_v3.csv')`。
- 第 715 行：`parser.add_argument('--output-dir', default='artifacts/b1_d1_pinned')`。
- 第 719 行：`parser.add_argument('--target-valid', type=int, default=DEFAULT_TARGET_VALID)`。
- 第 724 行：`parser.add_argument('--qwen-service-url', default='http://127.0.0.1:18004')`。
- 第 728 行：`parser.add_argument('--teacher-artifact-manifest', default='artifacts/b1_teacher_pinned/teacher_model_manifest.json', help='Manifest emitted by teacher_model_fingerprint.py for the loaded Teacher')`。
- 第 733 行：`parser.add_argument('--runner-python', default='/home/dcase_task2/miniconda3/envs/voice/bin/python')`。
- 第 737 行：`parser.add_argument('--carla-host', default='127.0.0.1')`。
- 第 738 行：`parser.add_argument('--carla-port', type=int, default=2000)`。
- 第 739 行：`parser.add_argument('--qwen-timeout-ms', type=int, default=5000)`。
- 第 740 行：`parser.add_argument('--dry-run', action='store_true')`。
- 第 741 行：`parser.add_argument('--allow-uncommitted-code', action='store_true', help='Development/testing only. Formal B1 collection must omit this flag so the exact collector must match Git HEAD.')`。
- 第 749 行：`parser.add_argument('--max-scenarios', type=int, default=None, help='Run at most N not-yet-completed scenario runs (for staged validation).')`。

## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [challenge/distillation/tests/test_b1_d1_interface.py](../../../challenge/distillation/tests/test_b1_d1_interface.py)

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-data.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/dataset/collect_d1_200.py`

来源 SHA256：`d9ddfae0f98b80a4272961891a7a862cf123a9eee684e177bd4c007cdfd5ea74`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 711 | `'--registry'` | `default='artifacts/b1_d1_registry_v3/scenario_registry_v3.csv'` |
| 715 | `'--output-dir'` | `default='artifacts/b1_d1_pinned'` |
| 719 | `'--target-valid'` | `type=int; default=DEFAULT_TARGET_VALID` |
| 724 | `'--qwen-service-url'` | `default='http://127.0.0.1:18004'` |
| 728 | `'--teacher-artifact-manifest'` | `default='artifacts/b1_teacher_pinned/teacher_model_manifest.json'; help='Manifest emitted by teacher_model_fingerprint.py for the loaded Teacher'` |
| 733 | `'--runner-python'` | `default='/home/dcase_task2/miniconda3/envs/voice/bin/python'` |
| 737 | `'--carla-host'` | `default='127.0.0.1'` |
| 738 | `'--carla-port'` | `type=int; default=2000` |
| 739 | `'--qwen-timeout-ms'` | `type=int; default=5000` |
| 740 | `'--dry-run'` | `action='store_true'` |
| 741 | `'--allow-uncommitted-code'` | `action='store_true'; help='Development/testing only. Formal B1 collection must omit this flag so the exact collector must match Git HEAD.'` |
| 749 | `'--max-scenarios'` | `type=int; default=None; help='Run at most N not-yet-completed scenario runs (for staged validation).'` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `read_json` / 31 | `not isinstance(value, dict)` | `raise ValueError(f'{path}: expected JSON object')` |
| `read_jsonl` / 45 | `not isinstance(value, dict)` | `raise ValueError(f'{path}:{line_no}: expected JSON object')` |
| `verify_tracked_file_matches_head` / 115 | `not worktree_path.is_file()` | `raise RuntimeError(f'required tracked file missing: {relative_path}')` |
| `verify_tracked_file_matches_head` / 127 | `tracked.returncode != 0` | `raise RuntimeError(f'formal collection requires Git-tracked file: {relative_path}')` |
| `verify_tracked_file_matches_head` / 140 | `head_blob.returncode != 0` | `raise RuntimeError(f'cannot read HEAD version of {relative_path}')` |
| `verify_tracked_file_matches_head` / 151 | `worktree_bytes != head_bytes` | `raise RuntimeError(f'formal collection code differs from HEAD: {relative_path}; commit the exact collector before collecting formal data')` |
| `teacher_health` / 173 | `not isinstance(data, dict)` | `raise RuntimeError('Teacher health payload is not an object')` |
| `teacher_health` / 184 | `not all(checks.values())` | `raise RuntimeError('Pinned Teacher health/identity gate failed')` |
| `load_teacher_manifest` / 204 | `bad` | `raise RuntimeError('teacher_baseline_manifest.json does not match pinned Teacher: ' + json.dumps(bad, ensure_ascii=False))` |
| `load_model_artifact_manifest` / 216 | `not isinstance(files, list) or not files` | `raise RuntimeError('Teacher artifact manifest has no file inventory')` |
| `load_model_artifact_manifest` / 235 | `mismatch` | `raise RuntimeError('Teacher artifact manifest does not match pinned artifact: ' + json.dumps(mismatch, ensure_ascii=False))` |
| `runner_preflight` / 267 | `result.returncode != 0` | `raise RuntimeError('Configured runner Python cannot import CARLA:\n' + result.stderr)` |
| `runner_preflight` / 272 | `len(lines) < 2` | `raise RuntimeError('Runner Python preflight returned unexpected output')` |
| `load_run_state` / 325 | `not isinstance(state.get('runs'), dict)` | `raise RuntimeError('run_state.json has invalid runs object')` |
| `collect_from_logs` / 397 | `rc != 0` | `raise RuntimeError('collector.py failed')` |
| `primary_sample_class` / 423 | `normalized not in {'normal', 'complex', 'safety_critical'}` | `raise ValueError(f'unsupported sample_class: {value!r}')` |
| `enrich_canonical` / 456 | `registry_row is None` | `raise RuntimeError(f'sample scenario_id is absent from registry: {scenario_id!r}')` |
| `enrich_canonical` / 465 | `source_bucket not in {'SEEN', 'VARIANT', 'UNSEEN'}` | `raise RuntimeError(f'invalid source_bucket for {scenario_id}: {source_bucket!r}')` |
| `enrich_canonical` / 474 | `not registry_scenario_path` | `raise RuntimeError(f'registry scenario_path missing for {scenario_id}')` |
| `validate_canonical` / 655 | `rc != 0` | `raise RuntimeError('validate_dataset.py failed')` |
| `main` / 758 | `args.target_valid < 1` | `raise SystemExit('--target-valid must be >=1')` |
| `main` / 760 | `args.max_scenarios is not None and args.max_scenarios < 1` | `raise SystemExit('--max-scenarios must be >=1')` |
| `main` / 847 | `scenario_id in registry_by_scenario` | `raise RuntimeError(f'duplicate scenario_id in registry: {scenario_id}')` |
| `main` / 915 | `not scenario_path or not scenario_id` | `raise RuntimeError('registry TRAIN_POSITIVE row missing scenario path/id')` |
| `main` / 927 | `not scenario_file.is_absolute() AND NOT (direct.is_file()) AND NOT (under_scenarios.is_file())` | `raise FileNotFoundError(f'scenario file not found: {scenario_path}; checked {direct} and {under_scenarios}')` |
