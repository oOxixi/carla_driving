# collector：功能记录

上级模块：[模块说明](../modules/challenge-data.md) · 实现：[challenge/dataset/collector.py](../../../challenge/dataset/collector.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [原始样本、冻结发布与派生训练视图](dataset-release-view.md)

## 功能职责与范围

Build B1 Teacher-distillation samples from ScenarioEvidenceRecorder JSONL.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `canonical_json`

源码位置：[challenge/dataset/collector.py 第 39 行](../../../challenge/dataset/collector.py#L39)。类型：`FunctionDef`。

```python
canonical_json(value: Any) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `sha256_bytes`

源码位置：[challenge/dataset/collector.py 第 48 行](../../../challenge/dataset/collector.py#L48)。类型：`FunctionDef`。

```python
sha256_bytes(data: bytes) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `sha256_file`

源码位置：[challenge/dataset/collector.py 第 52 行](../../../challenge/dataset/collector.py#L52)。类型：`FunctionDef`。

```python
sha256_file(path: Path) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `stable_route_hash`

源码位置：[challenge/dataset/collector.py 第 62 行](../../../challenge/dataset/collector.py#L62)。类型：`FunctionDef`。

```python
stable_route_hash(route: Any) -> str | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `read_jsonl`

源码位置：[challenge/dataset/collector.py 第 71 行](../../../challenge/dataset/collector.py#L71)。类型：`FunctionDef`。

```python
read_jsonl(path: Path) -> list[dict[str, Any]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `load_scenario`

源码位置：[challenge/dataset/collector.py 第 96 行](../../../challenge/dataset/collector.py#L96)。类型：`FunctionDef`。

```python
load_scenario(repo_root: Path, config_path: str | None) -> dict[str, Any] | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `index_rows`

源码位置：[challenge/dataset/collector.py 第 119 行](../../../challenge/dataset/collector.py#L119)。类型：`FunctionDef`。

```python
index_rows(rows: list[dict[str, Any]]) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `extract_model_request`

源码位置：[challenge/dataset/collector.py 第 170 行](../../../challenge/dataset/collector.py#L170)。类型：`FunctionDef`。

```python
extract_model_request(row: dict[str, Any]) -> dict[str, Any] | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `extract_teacher_plan`

源码位置：[challenge/dataset/collector.py 第 188 行](../../../challenge/dataset/collector.py#L188)。类型：`FunctionDef`。

```python
extract_teacher_plan(row: dict[str, Any]) -> dict[str, Any] | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `extract_model_timing`

源码位置：[challenge/dataset/collector.py 第 206 行](../../../challenge/dataset/collector.py#L206)。类型：`FunctionDef`。

```python
extract_model_timing(row: dict[str, Any]) -> dict[str, Any] | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `get_disposition`

源码位置：[challenge/dataset/collector.py 第 224 行](../../../challenge/dataset/collector.py#L224)。类型：`FunctionDef`。

```python
get_disposition(row: dict[str, Any]) -> str | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `find_rgb`

源码位置：[challenge/dataset/collector.py 第 238 行](../../../challenge/dataset/collector.py#L238)。类型：`FunctionDef`。

```python
find_rgb(repo_root: Path, rgb_ref: Any) -> tuple[Path | None, bool]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `classify_sample`

源码位置：[challenge/dataset/collector.py 第 255 行](../../../challenge/dataset/collector.py#L255)。类型：`FunctionDef`。

```python
classify_sample(model_request: dict[str, Any], teacher_plan: dict[str, Any], closed_loop: dict[str, Any]) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `classify_training_role`

源码位置：[challenge/dataset/collector.py 第 325 行](../../../challenge/dataset/collector.py#L325)。类型：`FunctionDef`。

```python
classify_training_role(structurally_valid: bool, closed_loop: dict[str, Any]) -> tuple[str, list[str]]
```

Separate structural validity from positive distillation eligibility.

### `extract_closed_loop`

源码位置：[challenge/dataset/collector.py 第 404 行](../../../challenge/dataset/collector.py#L404)。类型：`FunctionDef`。

```python
extract_closed_loop(run_complete: dict[str, Any] | None, command_id: str, maneuver_events: list[dict[str, Any]]) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `validate_pair`

源码位置：[challenge/dataset/collector.py 第 511 行](../../../challenge/dataset/collector.py#L511)。类型：`FunctionDef`。

```python
validate_pair(model_request: dict[str, Any] | None, teacher_plan: dict[str, Any] | None, rgb_exists: bool, resolve_disposition: str | None) -> tuple[bool, list[str]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `target_grounding`

源码位置：[challenge/dataset/collector.py 第 648 行](../../../challenge/dataset/collector.py#L648)。类型：`FunctionDef`。

```python
target_grounding(model_request: dict[str, Any], teacher_plan: dict[str, Any]) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `build_sample`

源码位置：[challenge/dataset/collector.py 第 735 行](../../../challenge/dataset/collector.py#L735)。类型：`FunctionDef`。

```python
build_sample(*, repo_root: Path, log_path: Path, run_start: dict[str, Any] | None, run_complete: dict[str, Any] | None, submit: dict[str, Any], resolve: dict[str, Any], maneuver_events: list[dict[str, Any]], scenario_data: dict[str, Any] | None, dataset_version: str) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `build_run_level_rejection`

源码位置：[challenge/dataset/collector.py 第 1221 行](../../../challenge/dataset/collector.py#L1221)。类型：`FunctionDef`。

```python
build_run_level_rejection(*, log_path: Path, dataset_version: str, run_start: dict[str, Any] | None, failure: dict[str, Any] | None, reason: str) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `collect_file`

源码位置：[challenge/dataset/collector.py 第 1309 行](../../../challenge/dataset/collector.py#L1309)。类型：`FunctionDef`。

```python
collect_file(*, repo_root: Path, log_path: Path, dataset_version: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `write_jsonl`

源码位置：[challenge/dataset/collector.py 第 1574 行](../../../challenge/dataset/collector.py#L1574)。类型：`FunctionDef`。

```python
write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[challenge/dataset/collector.py 第 1601 行](../../../challenge/dataset/collector.py#L1601)。类型：`FunctionDef`。

```python
main() -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `canonical_json` 调用：`json.dumps`.
- `sha256_bytes` 调用：`hashlib.sha256`, `hashlib.sha256(data).hexdigest`.
- `sha256_file` 调用：`f.read`, `h.hexdigest`, `h.update`, `hashlib.sha256`, `iter`, `path.open`.
- `stable_route_hash` 调用：`canonical_json`, `canonical_json(route).encode`, `hashlib.sha256`, `hashlib.sha256(canonical_json(route).encode('utf-8')).hexdigest`.
- `read_jsonl` 调用：`ValueError`, `enumerate`, `isinstance`, `json.loads`, `line.strip`, `path.open`, `rows.append`.
- `load_scenario` 调用：`Path`, `isinstance`, `json.loads`, `p.is_absolute`, `p.is_file`, `p.read_text`.
- `index_rows` 调用：`isinstance`, `maneuver_events.setdefault`, `maneuver_events.setdefault(command_id, []).append`, `next`, `r.get`, `resolves.setdefault`, `resolves.setdefault(command_id, []).append`, `reversed`, `row.get`, `str`, `str(row.get('phase', '')).upper`, `submits.setdefault`, `submits.setdefault(command_id, []).append`.
- `extract_model_request` 调用：`isinstance`, `orchestration.get`, `payload.get`, `row.get`.
- `extract_teacher_plan` 调用：`isinstance`, `orchestration.get`, `payload.get`, `row.get`.
- `extract_model_timing` 调用：`isinstance`, `orchestration.get`, `payload.get`, `row.get`.
- `get_disposition` 调用：`isinstance`, `payload.get`, `row.get`.
- `find_rgb` 调用：`Path`, `isinstance`, `p.is_absolute`, `p.is_file`, `p.resolve`.
- `classify_sample` 调用：`any`, `isinstance`, `len`, `model_request.get`, `scene_summary.get`, `step.get`, `str`, `teacher_plan.get`.
- `classify_training_role` 调用：`closed_loop.get`, `int`, `str`.
- `extract_closed_loop` 调用：`acceptance.get`, `bool`, `isinstance`, `payload.get`, `row.get`, `run_complete.get`, `statuses.get`, `summary.get`.
- `validate_pair` 调用：`isinstance`, `len`, `model_request.get`, `reasons.append`, `teacher_plan.get`.
- `target_grounding` 调用：`isinstance`, `len`, `model_request.get`, `referenced.append`, `step.get`, `target.get`, `teacher_plan.get`.
- `build_sample` 调用：`canonical_json`, `canonical_json(group_payload).encode`, `canonical_json(sample_identity).encode`, `classify_sample`, `classify_training_role`, `copy.deepcopy`, `extract_closed_loop`, `extract_model_request`, `extract_model_timing`, `extract_teacher_plan`, `find_rgb`, `get_disposition`, `isinstance`, `model_request.get`, `rejection_reasons.append`, `rgb_path.relative_to`, `rgb_path.relative_to(repo_root).as_posix`, `rgb_path.stat`, `run_config.get`, `run_start.get`, `scenario_data.get`, `scene_summary.get`, `sha256_bytes`, `sha256_file`, `stable_route_hash`, `str`, `submit.get`, `target_grounding`, `teacher_plan.get`, `validate_pair`.
- `build_run_level_rejection` 调用：`config.get`, `copy.deepcopy`, `isinstance`, `run_start.get`, `str`.
- `collect_file` 调用：`accepted.append`, `build_run_level_rejection`, `build_sample`, `extract_model_request`, `index_rows`, `isinstance`, `load_scenario`, `maneuver_events.get`, `read_jsonl`, `rejected.append`, `resolve_req.get`, `resolves.get`, `row.get`, `run_config.get`, `run_start.get`, `str`, `submit_req.get`, `submits.items`.
- `write_jsonl` 调用：`f.write`, `json.dumps`, `path.open`, `path.parent.mkdir`.
- `main` 调用：`(repo_root / log_path).resolve`, `Path`, `Path(args.repo_root).expanduser`, `Path(args.repo_root).expanduser().resolve`, `Path(item).expanduser`, `accepted_all.extend`, `argparse.ArgumentParser`, `collect_file`, `deduped.append`, `duplicate_ids.append`, `len`, `log_path.is_absolute`, `parser.add_argument`, `parser.parse_args`, `print`, `rejected_all.extend`, `sample_ids.add`, `set`, `write_jsonl`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `read_jsonl`，第 82 行：`ValueError(f'{path}:{line_no}: invalid JSON: {exc}')`。
- `read_jsonl`，第 87 行：`ValueError(f'{path}:{line_no}: row is not a JSON object')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 1604 行：`parser.add_argument('--repo-root', default='.')`。
- 第 1609 行：`parser.add_argument('--input-log', action='append', required=True, help='ScenarioEvidenceRecorder JSONL; repeat for multiple files')`。
- 第 1619 行：`parser.add_argument('--output', required=True)`。
- 第 1624 行：`parser.add_argument('--rejected-output', required=True)`。
- 第 1629 行：`parser.add_argument('--dataset-version', default=DEFAULT_DATASET_VERSION)`。

## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [challenge/dataset/tests/test_collector_governance.py](../../../challenge/dataset/tests/test_collector_governance.py)

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-data.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/dataset/collector.py`

来源 SHA256：`792528d5564130ed8982f552e1207e3fa97eaaea3b992cdaaeea0370de002485`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 1604 | `'--repo-root'` | `default='.'` |
| 1609 | `'--input-log'` | `action='append'; required=True; help='ScenarioEvidenceRecorder JSONL; repeat for multiple files'` |
| 1619 | `'--output'` | `required=True` |
| 1624 | `'--rejected-output'` | `required=True` |
| 1629 | `'--dataset-version'` | `default=DEFAULT_DATASET_VERSION` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `read_jsonl` / 82 | `except json.JSONDecodeError` | `raise ValueError(f'{path}:{line_no}: invalid JSON: {exc}') from exc` |
| `read_jsonl` / 87 | `not isinstance(row, dict)` | `raise ValueError(f'{path}:{line_no}: row is not a JSON object')` |
