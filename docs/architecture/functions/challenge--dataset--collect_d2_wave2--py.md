# collect_d2_wave2：功能记录

上级模块：[模块说明](../modules/challenge-data.md) · 实现：[challenge/dataset/collect_d2_wave2.py](../../../challenge/dataset/collect_d2_wave2.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [原始样本、冻结发布与派生训练视图](dataset-release-view.md)

## 功能职责与范围

B1 D2 Wave2 Teacher-v4 expansion collector.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `load_json`

源码位置：[challenge/dataset/collect_d2_wave2.py 第 64 行](../../../challenge/dataset/collect_d2_wave2.py#L64)。类型：`FunctionDef`。

```python
load_json(path: Path) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `sha256_file`

源码位置：[challenge/dataset/collect_d2_wave2.py 第 71 行](../../../challenge/dataset/collect_d2_wave2.py#L71)。类型：`FunctionDef`。

```python
sha256_file(path: Path) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `canonical_json_sha256_without_field`

源码位置：[challenge/dataset/collect_d2_wave2.py 第 79 行](../../../challenge/dataset/collect_d2_wave2.py#L79)。类型：`FunctionDef`。

```python
canonical_json_sha256_without_field(value: dict[str, Any], field: str) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `git_output`

源码位置：[challenge/dataset/collect_d2_wave2.py 第 95 行](../../../challenge/dataset/collect_d2_wave2.py#L95)。类型：`FunctionDef`。

```python
git_output(repo: Path, *args: str) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `current_branch`

源码位置：[challenge/dataset/collect_d2_wave2.py 第 111 行](../../../challenge/dataset/collect_d2_wave2.py#L111)。类型：`FunctionDef`。

```python
current_branch(repo: Path) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `verify_collector_matches_head`

源码位置：[challenge/dataset/collect_d2_wave2.py 第 115 行](../../../challenge/dataset/collect_d2_wave2.py#L115)。类型：`FunctionDef`。

```python
verify_collector_matches_head(repo: Path) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `health`

源码位置：[challenge/dataset/collect_d2_wave2.py 第 155 行](../../../challenge/dataset/collect_d2_wave2.py#L155)。类型：`FunctionDef`。

```python
health(url: str, pinned: dict[str, Any]) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `verify_teacher_manifest`

源码位置：[challenge/dataset/collect_d2_wave2.py 第 190 行](../../../challenge/dataset/collect_d2_wave2.py#L190)。类型：`FunctionDef`。

```python
verify_teacher_manifest(path: Path) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `verify_teacher_repo`

源码位置：[challenge/dataset/collect_d2_wave2.py 第 230 行](../../../challenge/dataset/collect_d2_wave2.py#L230)。类型：`FunctionDef`。

```python
verify_teacher_repo(teacher_repo: Path) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `resolve_scenario_path`

源码位置：[challenge/dataset/collect_d2_wave2.py 第 270 行](../../../challenge/dataset/collect_d2_wave2.py#L270)。类型：`FunctionDef`。

```python
resolve_scenario_path(root: Path, scenario_path: str) -> Path | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `verify_plan`

源码位置：[challenge/dataset/collect_d2_wave2.py 第 288 行](../../../challenge/dataset/collect_d2_wave2.py#L288)。类型：`FunctionDef`。

```python
verify_plan(plan_path: Path, teacher_manifest: dict[str, Any], challenge_repo: Path, teacher_repo: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `empty_state`

源码位置：[challenge/dataset/collect_d2_wave2.py 第 510 行](../../../challenge/dataset/collect_d2_wave2.py#L510)。类型：`FunctionDef`。

```python
empty_state(*, plan: dict[str, Any], plan_path: Path, collector_repo_sha: str) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `validate_state_identity`

源码位置：[challenge/dataset/collect_d2_wave2.py 第 537 行](../../../challenge/dataset/collect_d2_wave2.py#L537)。类型：`FunctionDef`。

```python
validate_state_identity(state: dict[str, Any]) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `atomic_write_json`

源码位置：[challenge/dataset/collect_d2_wave2.py 第 573 行](../../../challenge/dataset/collect_d2_wave2.py#L573)。类型：`FunctionDef`。

```python
atomic_write_json(path: Path, value: dict[str, Any]) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `load_or_create_state`

源码位置：[challenge/dataset/collect_d2_wave2.py 第 600 行](../../../challenge/dataset/collect_d2_wave2.py#L600)。类型：`FunctionDef`。

```python
load_or_create_state(state_path: Path, *, resume: bool, plan: dict[str, Any], plan_path: Path, collector_repo_sha: str) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `select_runs`

源码位置：[challenge/dataset/collect_d2_wave2.py 第 633 行](../../../challenge/dataset/collect_d2_wave2.py#L633)。类型：`FunctionDef`。

```python
select_runs(runs: list[dict[str, Any]], state: dict[str, Any], *, start_index: int, max_runs: int | None, resume: bool) -> tuple[list[dict[str, Any]], int]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `clear_attempt_outputs`

源码位置：[challenge/dataset/collect_d2_wave2.py 第 691 行](../../../challenge/dataset/collect_d2_wave2.py#L691)。类型：`FunctionDef`。

```python
clear_attempt_outputs(item_log_dir: Path, item_image_dir: Path) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `run_case`

源码位置：[challenge/dataset/collect_d2_wave2.py 第 705 行](../../../challenge/dataset/collect_d2_wave2.py#L705)。类型：`FunctionDef`。

```python
run_case(teacher_repo: Path, challenge_repo: Path, item: dict[str, Any], service: str, logs_root: Path, images_root: Path) -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `collect_dataset`

源码位置：[challenge/dataset/collect_d2_wave2.py 第 809 行](../../../challenge/dataset/collect_d2_wave2.py#L809)。类型：`FunctionDef`。

```python
collect_dataset(repo: Path, logs_root: Path, dataset_root: Path) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[challenge/dataset/collect_d2_wave2.py 第 871 行](../../../challenge/dataset/collect_d2_wave2.py#L871)。类型：`FunctionDef`。

```python
main() -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `load_json` 调用：`RuntimeError`, `isinstance`, `json.loads`, `path.read_text`.
- `sha256_file` 调用：`f.read`, `h.hexdigest`, `h.update`, `hashlib.sha256`, `iter`, `path.open`.
- `canonical_json_sha256_without_field` 调用：`dict`, `hashlib.sha256`, `hashlib.sha256(raw).hexdigest`, `json.dumps`, `json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode`, `obj.pop`.
- `git_output` 调用：`' '.join`, `RuntimeError`, `result.stderr.strip`, `result.stdout.strip`, `str`, `subprocess.run`.
- `current_branch` 调用：`git_output`.
- `verify_collector_matches_head` 调用：`Path`, `RuntimeError`, `hashlib.sha256`, `hashlib.sha256(result.stdout).hexdigest`, `path.is_file`, `rel.as_posix`, `sha256_file`, `str`, `subprocess.run`.
- `health` 调用：`RuntimeError`, `data.get`, `json.loads`, `response.read`, `url.rstrip`, `urllib.request.urlopen`.
- `verify_teacher_manifest` 调用：`RuntimeError`, `expected.items`, `load_json`, `pinned.get`, `verification.get`.
- `verify_teacher_repo` 调用：`RuntimeError`, `git_output`, `str`, `teacher_repo.is_dir`, `teacher_repo.resolve`.
- `resolve_scenario_path` 调用：`Path`, `candidate.is_file`.
- `verify_plan` 调用：`RuntimeError`, `any`, `canonical_json_sha256_without_field`, `expected_teacher_values.items`, `isinstance`, `len`, `list`, `load_json`, `plan.get`, `plan_path.is_file`, `range`, `resolve_scenario_path`, `row.get`, `set`, `sha256_file`, `str`, `teacher_identity.get`, `type`.
- `empty_state` 调用：`plan_path.resolve`, `str`.
- `validate_state_identity` 调用：`RuntimeError`, `expected.items`, `isinstance`, `state.get`.
- `atomic_write_json` 调用：`json.dumps`, `path.parent.mkdir`, `path.with_suffix`, `tmp.replace`, `tmp.write_text`.
- `load_or_create_state` 调用：`RuntimeError`, `empty_state`, `load_json`, `state_path.exists`, `validate_state_identity`.
- `select_runs` 调用：`RuntimeError`, `filtered.append`, `isinstance`, `len`, `previous.get`, `state_runs.get`.
- `clear_attempt_outputs` 调用：`path.exists`, `shutil.rmtree`.
- `run_case` 调用：`clear_attempt_outputs`, `item_images.mkdir`, `item_images.relative_to`, `item_logs.mkdir`, `print`, `scenario_path.startswith`, `str`, `subprocess.run`.
- `collect_dataset` 调用：`RuntimeError`, `dataset_root.mkdir`, `logs_root.rglob`, `p.is_file`, `sorted`, `str`, `subprocess.run`.
- `main` 调用：`(repo / manifest_path).resolve`, `(repo / output_root).resolve`, `(repo / plan_path).resolve`, `(repo / teacher_repo).resolve`, `Path`, `Path(__file__).resolve`, `RuntimeError`, `argparse.ArgumentParser`, `atomic_write_json`, `bool`, `collect_dataset`, `current_branch`, `dataset_root.mkdir`, `git_output`, `health`, `images_root.mkdir`, `isinstance`, `len`, `load_or_create_state`, `logs_root.mkdir`, `manifest_path.is_absolute`, `manifest_path.resolve`, `output_root.exists`, `output_root.is_absolute`, `output_root.iterdir`, `output_root.mkdir`, `output_root.resolve`, `parser.add_argument`, `parser.parse_args`, `pinned.get`, `plan_path.is_absolute`, `plan_path.resolve`, `print`, `run_case`, `run_records.values`, `select_runs`, `sha256_file`, `state.setdefault`, `state['collector_repo_git_shas'].append`, `state_path.resolve`, `str`, `sum`, `teacher_repo.is_absolute`, `teacher_runtime.get`, `verify_collector_matches_head`, `verify_plan`, `verify_teacher_manifest`, `verify_teacher_repo`, `x.get`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `collect_dataset`，第 821 行：`RuntimeError('No ScenarioEvidenceRecorder JSONL logs found')`。
- `collect_dataset`，第 866 行：`RuntimeError('Wave2 collector.py post-processing failed')`。
- `git_output`，第 104 行：`RuntimeError(f"git {' '.join(args)} failed for {repo}: {result.stderr.strip()}")`。
- `health`，第 166 行：`RuntimeError(f"Teacher service not ready: {data.get('status')!r}")`。
- `health`，第 171 行：`RuntimeError('Teacher service production_ready is not true')`。
- `health`，第 176 行：`RuntimeError(f"Teacher service model mismatch: {data.get('model_id')!r} != {pinned['model_id']!r}")`。
- `health`，第 182 行：`RuntimeError(f"Teacher service qwen_mode mismatch: {data.get('qwen_mode')!r} != {pinned['qwen_mode']!r}")`。
- `load_json`，第 67 行：`RuntimeError(f'JSON object expected: {path}')`。
- `load_or_create_state`，第 610 行：`RuntimeError(f'run_state already exists: {state_path}. Use --resume only if continuing this exact Wave2 acquisition.')`。
- `load_or_create_state`，第 621 行：`RuntimeError(f'--resume requested but run_state missing: {state_path}')`。
- `main`，第 1089 行：`RuntimeError(f'Wave2 output root is not empty: {output_root}. Use a new root or --resume.')`。
- `select_runs`，第 645 行：`RuntimeError('--start-index must be >= 0')`。
- `select_runs`，第 650 行：`RuntimeError('--start-index exceeds plan length')`。
- `select_runs`，第 683 行：`RuntimeError('--max-runs must be >= 1')`。
- `validate_state_identity`，第 562 行：`RuntimeError(f'run_state identity mismatch for {key}: {actual!r} != {wanted!r}')`。
- `validate_state_identity`，第 568 行：`RuntimeError('run_state runs must be an object')`。
- `verify_collector_matches_head`，第 122 行：`RuntimeError(f'collector missing: {path}')`。
- `verify_collector_matches_head`，第 134 行：`RuntimeError('Wave2 collector is not tracked in HEAD; commit it before formal acquisition')`。
- `verify_collector_matches_head`，第 142 行：`RuntimeError(f'Wave2 collector differs from committed HEAD: worktree={worktree_sha} head={head_sha}')`。
- `verify_plan`，第 295 行：`RuntimeError(f'Wave2 plan missing: {plan_path}')`。
- `verify_plan`，第 302 行：`RuntimeError(f'Wave2 plan file SHA mismatch: {plan_file_sha} != {EXPECTED_PLAN_FILE_SHA256}')`。
- `verify_plan`，第 310 行：`RuntimeError(f"Wave2 plan_version mismatch: {plan.get('plan_version')!r}")`。
- `verify_plan`，第 316 行：`RuntimeError(f"Wave2 plan repo_git_sha mismatch: {plan.get('repo_git_sha')!r}")`。
- `verify_plan`，第 322 行：`RuntimeError('Wave2 plan was not generated through formal code gate')`。
- `verify_plan`，第 343 行：`RuntimeError(f'Wave2 plan canonical hash mismatch: embedded={embedded_canonical} recomputed={recomputed_canonical}')`。
- `verify_plan`，第 371 行：`RuntimeError(f'Plan Teacher mismatch for {key}: {actual!r} != {wanted!r}')`。
- `verify_plan`，第 379 行：`RuntimeError('Wave2 plan[] missing')`。
- `verify_plan`，第 384 行：`RuntimeError(f'Wave2 run count mismatch: {len(runs)} != {EXPECTED_RUNS}')`。
- `verify_plan`，第 406 行：`RuntimeError('Wave2 extension_id uniqueness failure')`。
- `verify_plan`，第 414 行：`RuntimeError('Wave2 extension_seed uniqueness failure')`。
- `verify_plan`，第 426 行：`RuntimeError(f'Wave2 seed namespace is not the exact frozen {EXPECTED_SEED_START}..{EXPECTED_SEED_END}')`。
- `verify_plan`，第 433 行：`RuntimeError(f"Non-TRAIN_POSITIVE row leaked into Wave2 plan: {row.get('extension_id')}")`。
- `verify_plan`，第 442 行：`RuntimeError(f"Forbidden source bucket in Wave2: {row.get('extension_id')} {row.get('source_bucket')!r}")`。
- `verify_plan`，第 452 行：`RuntimeError(f"Per-run Teacher profile mismatch: {row.get('extension_id')}")`。
- `verify_plan`，第 461 行：`RuntimeError(f"Per-run Teacher SHA mismatch: {row.get('extension_id')}")`。
- `verify_plan`，第 471 行：`RuntimeError('Wave2 row missing scenario_path')`。
- `verify_plan`，第 486 行：`RuntimeError('Scenario missing from challenge repo: ' + scenario_path)`。
- `verify_plan`，第 492 行：`RuntimeError('Scenario missing from Teacher repo: ' + scenario_path)`。
- `verify_plan`，第 502 行：`RuntimeError(f'Scenario differs between challenge and Teacher repos: {scenario_path}')`。
- `verify_teacher_manifest`，第 207 行：`RuntimeError(f'Teacher manifest mismatch for {key}: {actual!r} != {wanted!r}')`。
- `verify_teacher_manifest`，第 215 行：`RuntimeError('Teacher v4 directional semantic gate not frozen PASS')`。
- `verify_teacher_manifest`，第 223 行：`RuntimeError('Teacher v4 directional closed-loop gate not frozen PASS')`。
- `verify_teacher_repo`，第 234 行：`RuntimeError(f'Teacher repo does not exist: {teacher_repo}')`。
- `verify_teacher_repo`，第 245 行：`RuntimeError(f'Teacher HEAD mismatch: {head} != {EXPECTED_TEACHER_GIT_SHA}')`。
- `verify_teacher_repo`，第 258 行：`RuntimeError('Teacher tracked worktree is dirty:\n' + tracked_status)`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 874 行：`parser.add_argument('--plan', default=DEFAULT_PLAN)`。
- 第 879 行：`parser.add_argument('--teacher-manifest', default=DEFAULT_TEACHER_MANIFEST)`。
- 第 884 行：`parser.add_argument('--teacher-repo-root', default=DEFAULT_TEACHER_REPO_ROOT)`。
- 第 889 行：`parser.add_argument('--qwen-service-url', default=DEFAULT_SERVICE_URL)`。
- 第 894 行：`parser.add_argument('--output-root', default=DEFAULT_OUTPUT_ROOT)`。
- 第 899 行：`parser.add_argument('--start-index', type=int, default=0)`。
- 第 905 行：`parser.add_argument('--max-runs', type=int)`。
- 第 910 行：`parser.add_argument('--resume', action='store_true')`。
- 第 915 行：`parser.add_argument('--dry-run', action='store_true', help='Validate committed collector, frozen plan, Teacher manifest/repo, all scenario files, and live Teacher service health without executing CARLA.')`。

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

### `challenge/dataset/collect_d2_wave2.py`

来源 SHA256：`72a630db45d141ec417f2e33912a62e168ca975bcf5ef9f1434e135397f37e49`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 874 | `'--plan'` | `default=DEFAULT_PLAN` |
| 879 | `'--teacher-manifest'` | `default=DEFAULT_TEACHER_MANIFEST` |
| 884 | `'--teacher-repo-root'` | `default=DEFAULT_TEACHER_REPO_ROOT` |
| 889 | `'--qwen-service-url'` | `default=DEFAULT_SERVICE_URL` |
| 894 | `'--output-root'` | `default=DEFAULT_OUTPUT_ROOT` |
| 899 | `'--start-index'` | `type=int; default=0` |
| 905 | `'--max-runs'` | `type=int` |
| 910 | `'--resume'` | `action='store_true'` |
| 915 | `'--dry-run'` | `action='store_true'; help='Validate committed collector, frozen plan, Teacher manifest/repo, all scenario files, and live Teacher service health without executing CARLA.'` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `load_json` / 67 | `not isinstance(value, dict)` | `raise RuntimeError(f'JSON object expected: {path}')` |
| `git_output` / 104 | `result.returncode != 0` | `raise RuntimeError(f"git {' '.join(args)} failed for {repo}: {result.stderr.strip()}")` |
| `verify_collector_matches_head` / 122 | `not path.is_file()` | `raise RuntimeError(f'collector missing: {path}')` |
| `verify_collector_matches_head` / 134 | `result.returncode != 0` | `raise RuntimeError('Wave2 collector is not tracked in HEAD; commit it before formal acquisition')` |
| `verify_collector_matches_head` / 142 | `worktree_sha != head_sha` | `raise RuntimeError(f'Wave2 collector differs from committed HEAD: worktree={worktree_sha} head={head_sha}')` |
| `health` / 166 | `data.get('status') != 'READY'` | `raise RuntimeError(f"Teacher service not ready: {data.get('status')!r}")` |
| `health` / 171 | `data.get('production_ready') is not True` | `raise RuntimeError('Teacher service production_ready is not true')` |
| `health` / 176 | `data.get('model_id') != pinned['model_id']` | `raise RuntimeError(f"Teacher service model mismatch: {data.get('model_id')!r} != {pinned['model_id']!r}")` |
| `health` / 182 | `data.get('qwen_mode') != pinned['qwen_mode']` | `raise RuntimeError(f"Teacher service qwen_mode mismatch: {data.get('qwen_mode')!r} != {pinned['qwen_mode']!r}")` |
| `verify_teacher_manifest` / 207 | `actual != wanted` | `raise RuntimeError(f'Teacher manifest mismatch for {key}: {actual!r} != {wanted!r}')` |
| `verify_teacher_manifest` / 215 | `verification.get('directional_semantic_gate') != '8/8 PASS'` | `raise RuntimeError('Teacher v4 directional semantic gate not frozen PASS')` |
| `verify_teacher_manifest` / 223 | `verification.get('directional_closed_loop_gate') != '8/8 SUCCEEDED'` | `raise RuntimeError('Teacher v4 directional closed-loop gate not frozen PASS')` |
| `verify_teacher_repo` / 234 | `not teacher_repo.is_dir()` | `raise RuntimeError(f'Teacher repo does not exist: {teacher_repo}')` |
| `verify_teacher_repo` / 245 | `head != EXPECTED_TEACHER_GIT_SHA` | `raise RuntimeError(f'Teacher HEAD mismatch: {head} != {EXPECTED_TEACHER_GIT_SHA}')` |
| `verify_teacher_repo` / 258 | `tracked_status` | `raise RuntimeError('Teacher tracked worktree is dirty:\n' + tracked_status)` |
| `verify_plan` / 295 | `not plan_path.is_file()` | `raise RuntimeError(f'Wave2 plan missing: {plan_path}')` |
| `verify_plan` / 302 | `plan_file_sha != EXPECTED_PLAN_FILE_SHA256` | `raise RuntimeError(f'Wave2 plan file SHA mismatch: {plan_file_sha} != {EXPECTED_PLAN_FILE_SHA256}')` |
| `verify_plan` / 310 | `plan.get('plan_version') != EXPECTED_PLAN_VERSION` | `raise RuntimeError(f"Wave2 plan_version mismatch: {plan.get('plan_version')!r}")` |
| `verify_plan` / 316 | `plan.get('repo_git_sha') != EXPECTED_PLAN_REPO_SHA` | `raise RuntimeError(f"Wave2 plan repo_git_sha mismatch: {plan.get('repo_git_sha')!r}")` |
| `verify_plan` / 322 | `plan.get('formal_code_gate') is not True` | `raise RuntimeError('Wave2 plan was not generated through formal code gate')` |
| `verify_plan` / 343 | `embedded_canonical != EXPECTED_PLAN_CANONICAL_SHA256 or recomputed_canonical != EXPECTED_PLAN_CANONICAL_SHA256` | `raise RuntimeError(f'Wave2 plan canonical hash mismatch: embedded={embedded_canonical} recomputed={recomputed_canonical}')` |
| `verify_plan` / 371 | `actual != wanted` | `raise RuntimeError(f'Plan Teacher mismatch for {key}: {actual!r} != {wanted!r}')` |
| `verify_plan` / 379 | `not isinstance(runs, list)` | `raise RuntimeError('Wave2 plan[] missing')` |
| `verify_plan` / 384 | `len(runs) != EXPECTED_RUNS` | `raise RuntimeError(f'Wave2 run count mismatch: {len(runs)} != {EXPECTED_RUNS}')` |
| `verify_plan` / 406 | `any((not isinstance(x, str) or not x for x in ids)) or len(ids) != len(set(ids))` | `raise RuntimeError('Wave2 extension_id uniqueness failure')` |
| `verify_plan` / 414 | `any((type(x) is not int for x in seeds)) or len(seeds) != len(set(seeds))` | `raise RuntimeError('Wave2 extension_seed uniqueness failure')` |
| `verify_plan` / 426 | `seeds != expected_seeds` | `raise RuntimeError(f'Wave2 seed namespace is not the exact frozen {EXPECTED_SEED_START}..{EXPECTED_SEED_END}')` |
| `verify_plan` / 433 | `row.get('policy_class') != 'TRAIN_POSITIVE'` | `raise RuntimeError(f"Non-TRAIN_POSITIVE row leaked into Wave2 plan: {row.get('extension_id')}")` |
| `verify_plan` / 442 | `row.get('source_bucket') not in {'SEEN', 'VARIANT'}` | `raise RuntimeError(f"Forbidden source bucket in Wave2: {row.get('extension_id')} {row.get('source_bucket')!r}")` |
| `verify_plan` / 452 | `row.get('teacher_profile') != EXPECTED_TEACHER_PROFILE` | `raise RuntimeError(f"Per-run Teacher profile mismatch: {row.get('extension_id')}")` |
| `verify_plan` / 461 | `row.get('teacher_git_sha') != EXPECTED_TEACHER_GIT_SHA` | `raise RuntimeError(f"Per-run Teacher SHA mismatch: {row.get('extension_id')}")` |
| `verify_plan` / 471 | `not scenario_path` | `raise RuntimeError('Wave2 row missing scenario_path')` |
| `verify_plan` / 486 | `challenge_scenario is None` | `raise RuntimeError('Scenario missing from challenge repo: ' + scenario_path)` |
| `verify_plan` / 492 | `teacher_scenario is None` | `raise RuntimeError('Scenario missing from Teacher repo: ' + scenario_path)` |
| `verify_plan` / 502 | `sha256_file(challenge_scenario) != sha256_file(teacher_scenario)` | `raise RuntimeError(f'Scenario differs between challenge and Teacher repos: {scenario_path}')` |
| `validate_state_identity` / 562 | `actual != wanted` | `raise RuntimeError(f'run_state identity mismatch for {key}: {actual!r} != {wanted!r}')` |
| `validate_state_identity` / 568 | `not isinstance(state.get('runs'), dict)` | `raise RuntimeError('run_state runs must be an object')` |
| `load_or_create_state` / 610 | `state_path.exists() AND not resume` | `raise RuntimeError(f'run_state already exists: {state_path}. Use --resume only if continuing this exact Wave2 acquisition.')` |
| `load_or_create_state` / 621 | `resume` | `raise RuntimeError(f'--resume requested but run_state missing: {state_path}')` |
| `select_runs` / 645 | `start_index < 0` | `raise RuntimeError('--start-index must be >= 0')` |
| `select_runs` / 650 | `start_index > len(runs)` | `raise RuntimeError('--start-index exceeds plan length')` |
| `select_runs` / 683 | `max_runs is not None AND max_runs < 1` | `raise RuntimeError('--max-runs must be >= 1')` |
| `collect_dataset` / 821 | `not input_logs` | `raise RuntimeError('No ScenarioEvidenceRecorder JSONL logs found')` |
| `collect_dataset` / 866 | `result.returncode != 0` | `raise RuntimeError('Wave2 collector.py post-processing failed')` |
| `main` / 1089 | `output_root.exists() and (not args.resume) AND meaningful` | `raise RuntimeError(f'Wave2 output root is not empty: {output_root}. Use a new root or --resume.')` |
