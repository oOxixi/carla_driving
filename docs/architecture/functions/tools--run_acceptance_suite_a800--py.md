# run_acceptance_suite_a800：功能记录

上级模块：[模块说明](../modules/support-tools.md) · 实现：[tools/run_acceptance_suite_a800.py](../../../tools/run_acceptance_suite_a800.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [维护工具的运行上下文和证据范围](environment-delivery.md)

## 功能职责与范围

Run all 83 scored acceptance scenarios once on the prepared A800 host.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `percentile`

源码位置：[tools/run_acceptance_suite_a800.py 第 23 行](../../../tools/run_acceptance_suite_a800.py#L23)。类型：`FunctionDef`。

```python
percentile(values: list[float], quantile: float) -> float | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `distribution`

源码位置：[tools/run_acceptance_suite_a800.py 第 34 行](../../../tools/run_acceptance_suite_a800.py#L34)。类型：`FunctionDef`。

```python
distribution(values: list[float]) -> dict[str, float | int | None]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `read_rows`

源码位置：[tools/run_acceptance_suite_a800.py 第 44 行](../../../tools/run_acceptance_suite_a800.py#L44)。类型：`FunctionDef`。

```python
read_rows(log_dir: Path) -> tuple[list[dict], str | None]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `parse_run`

源码位置：[tools/run_acceptance_suite_a800.py 第 55 行](../../../tools/run_acceptance_suite_a800.py#L55)。类型：`FunctionDef`。

```python
parse_run(log_dir: Path, console: str) -> dict[str, object]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `fetch_json`

源码位置：[tools/run_acceptance_suite_a800.py 第 122 行](../../../tools/run_acceptance_suite_a800.py#L122)。类型：`FunctionDef`。

```python
fetch_json(url: str) -> dict[str, object] | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `completed_scenario_ids`

源码位置：[tools/run_acceptance_suite_a800.py 第 131 行](../../../tools/run_acceptance_suite_a800.py#L131)。类型：`FunctionDef`。

```python
completed_scenario_ids(roots: list[Path], valid_ids: set[str]) -> set[str]
```

Return suite IDs that already own a readable terminal summary.

### `warm_qwen_service`

源码位置：[tools/run_acceptance_suite_a800.py 第 148 行](../../../tools/run_acceptance_suite_a800.py#L148)。类型：`FunctionDef`。

```python
warm_qwen_service(*, project: Path, base_url: str, count: int) -> dict[str, float | int | None]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `write_report`

源码位置：[tools/run_acceptance_suite_a800.py 第 235 行](../../../tools/run_acceptance_suite_a800.py#L235)。类型：`FunctionDef`。

```python
write_report(path: Path, metadata: dict[str, object], records: list[dict[str, object]]) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `should_stop_after_record`

源码位置：[tools/run_acceptance_suite_a800.py 第 277 行](../../../tools/run_acceptance_suite_a800.py#L277)。类型：`FunctionDef`。

```python
should_stop_after_record(status: object, *, fail_fast: bool) -> bool
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `child_environment`

源码位置：[tools/run_acceptance_suite_a800.py 第 281 行](../../../tools/run_acceptance_suite_a800.py#L281)。类型：`FunctionDef`。

```python
child_environment(project: Path, base: dict[str, str] | None=None) -> dict[str, str]
```

Prepend the checkout without hiding host-provided runtime dependencies.

### `main`

源码位置：[tools/run_acceptance_suite_a800.py 第 292 行](../../../tools/run_acceptance_suite_a800.py#L292)。类型：`FunctionDef`。

```python
main() -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `percentile` 调用：`len`, `math.ceil`, `math.floor`, `sorted`.
- `distribution` 调用：`len`, `max`, `percentile`, `statistics.fmean`.
- `read_rows` 调用：`json.loads`, `line.strip`, `log_dir.glob`, `logs[-1].read_text`, `logs[-1].read_text(encoding='utf-8').splitlines`, `path.stat`, `sorted`, `str`.
- `parse_run` 调用：`alignment_checks.append`, `all`, `bucket.append`, `check.get`, `complete[-1].get`, `console.splitlines`, `distribution`, `extension.get`, `float`, `isinstance`, `json.loads`, `latency.get`, `qwen.get`, `qwen['checks'].get`, `read_rows`, `row.get`, `sensor_to_control_ms.append`, `sensor_to_trajectory_ms.append`, `summary.get`, `summary.get('acceptance', {}).get`, `summary.get('score', {}).get`, `timing.get`.
- `fetch_json` 调用：`isinstance`, `json.loads`, `response.read`, `urlopen`.
- `completed_scenario_ids` 调用：`completed.add`, `json.loads`, `path.read_text`, `payload.get`, `root.exists`, `root.rglob`, `set`, `str`.
- `warm_qwen_service` 调用：`QwenServiceClient`, `ValueError`, `bytes`, `client.infer`, `distribution`, `image.is_file`, `image.relative_to`, `image.relative_to(project).as_posix`, `image.write_bytes`, `image_root.mkdir`, `latencies.append`, `len`, `list`, `range`, `request['scene_capabilities'].pop`, `time.monotonic_ns`, `time.perf_counter_ns`.
- `write_report` 调用：`distribution`, `float`, `json.dumps`, `len`, `path.write_text`, `record.get`, `sum`.
- `should_stop_after_record` 调用：`bool`, `str`.
- `child_environment` 调用：`dict`, `env.get`, `env.get('PYTHONPATH', '').strip`, `os.pathsep.join`, `str`.
- `main` 调用：`(root / 'console.log').write_text`, `(suite / 'matrix.json').read_text`, `(suite / item['path']).read_text`, `RuntimeError`, `ValueError`, `argparse.ArgumentParser`, `args.output.resolve`, `args.project.resolve`, `args.qwen_image_root.resolve`, `args.qwen_service_url.rstrip`, `child_environment`, `completed_scenario_ids`, `enumerate`, `fetch_json`, `float`, `health.get`, `isinstance`, `json.loads`, `len`, `log_dir.mkdir`, `matrix['counts'].get`, `max`, `metadata.get`, `os.environ.get`, `output.mkdir`, `parse_run`, `parser.add_argument`, `parser.error`, `parser.parse_args`, `path.resolve`, `print`, `qwen_image_root.mkdir`, `read_rows`, `records.append`, `row.get`, `row['latency'].get`, `set`, `should_stop_after_record`, `sorted`, `str`, `subprocess.check_output`, `subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=project, text=True, stderr=subprocess.DEVNULL).strip`, `subprocess.run`, `time.perf_counter`, `warm_qwen_service`, `write_report`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `main`，第 357 行：`RuntimeError(f'one-shot total run requires exactly {expected_total} current scenarios and zero extensions')`。
- `main`，第 369 行：`ValueError(f'unknown included scenario IDs: {sorted(unknown_included)}')`。
- `main`，第 378 行：`RuntimeError(f'production Qwen service is not ready: {health}')`。
- `warm_qwen_service`，第 152 行：`ValueError('warmup count must be non-negative')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 294 行：`parser.add_argument('--project', type=Path, required=True)`。
- 第 295 行：`parser.add_argument('--python', type=Path, required=True)`。
- 第 296 行：`parser.add_argument('--output', type=Path, required=True)`。
- 第 297 行：`parser.add_argument('--qwen-service-url', default='http://127.0.0.1:8765')`。
- 第 298 行：`parser.add_argument('--qwen-image-root', type=Path, help='shared Qwen image root; use a tmpfs such as /dev/shm to avoid per-process cold disk writes')`。
- 第 302 行：`parser.add_argument('--carla-host', default='127.0.0.1')`。
- 第 303 行：`parser.add_argument('--carla-port', type=int, default=2000)`。
- 第 304 行：`parser.add_argument('--warmup-requests', type=int, default=20)`。
- 第 305 行：`parser.add_argument('--qwen-timeout-ms', type=float, default=300.0, help='per-command Qwen deadline; keep 300 ms for formal A800 measurement')`。
- 第 309 行：`parser.add_argument('--hardware', default=os.environ.get('VALIDATION_HARDWARE', 'NVIDIA A800-SXM4-80GB'), help='truthful hardware label stored in the evidence report')`。
- 第 313 行：`parser.add_argument('--cuda', default=os.environ.get('VALIDATION_CUDA', '13.2'), help='CUDA runtime label stored in the evidence report')`。
- 第 317 行：`parser.add_argument('--fail-fast', action='store_true', help='stop after writing the first non-SUCCEEDED scenario result')`。
- 第 321 行：`parser.add_argument('--skip-summary-root', action='append', type=Path, default=[], help='skip scenarios that already have a terminal *.summary.json below this root')`。
- 第 325 行：`parser.add_argument('--exclude-scenario-id', action='append', default=[], help='exclude a scenario from a diagnostic/resume run without marking it complete')`。
- 第 329 行：`parser.add_argument('--include-scenario-id', action='append', default=[], help='run only these scenario IDs for a targeted diagnostic rerun')`。
- 第 333 行：`parser.add_argument('--suite-revision', default='4238023+server-carla-perception-e2e', help='deployment revision used when the server copy has no .git directory')`。

## 上下游与关联验证

静态导入的项目内实现：

- [qwen_service/client.py](../../../qwen_service/client.py)

静态 import 消费者（含测试）：

- [integration/tests/test_acceptance_suite_a800_runner.py](../../../integration/tests/test_acceptance_suite_a800_runner.py)

## 后续修改需要一起阅读

- [上级模块](../modules/support-tools.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `tools/run_acceptance_suite_a800.py`

来源 SHA256：`b7822e4b87ec86ca2261f1fd81b35522e548cb0be1c057c7c31369ae886f7647`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 294 | `'--project'` | `type=Path; required=True` |
| 295 | `'--python'` | `type=Path; required=True` |
| 296 | `'--output'` | `type=Path; required=True` |
| 297 | `'--qwen-service-url'` | `default='http://127.0.0.1:8765'` |
| 298 | `'--qwen-image-root'` | `type=Path; help='shared Qwen image root; use a tmpfs such as /dev/shm to avoid per-process cold disk writes'` |
| 302 | `'--carla-host'` | `default='127.0.0.1'` |
| 303 | `'--carla-port'` | `type=int; default=2000` |
| 304 | `'--warmup-requests'` | `type=int; default=20` |
| 305 | `'--qwen-timeout-ms'` | `type=float; default=300.0; help='per-command Qwen deadline; keep 300 ms for formal A800 measurement'` |
| 309 | `'--hardware'` | `default=os.environ.get('VALIDATION_HARDWARE', 'NVIDIA A800-SXM4-80GB'); help='truthful hardware label stored in the evidence report'` |
| 313 | `'--cuda'` | `default=os.environ.get('VALIDATION_CUDA', '13.2'); help='CUDA runtime label stored in the evidence report'` |
| 317 | `'--fail-fast'` | `action='store_true'; help='stop after writing the first non-SUCCEEDED scenario result'` |
| 321 | `'--skip-summary-root'` | `action='append'; type=Path; default=[]; help='skip scenarios that already have a terminal *.summary.json below this root'` |
| 325 | `'--exclude-scenario-id'` | `action='append'; default=[]; help='exclude a scenario from a diagnostic/resume run without marking it complete'` |
| 329 | `'--include-scenario-id'` | `action='append'; default=[]; help='run only these scenario IDs for a targeted diagnostic rerun'` |
| 333 | `'--suite-revision'` | `default='4238023+server-carla-perception-e2e'; help='deployment revision used when the server copy has no .git directory'` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `warm_qwen_service` / 152 | `count < 0` | `raise ValueError('warmup count must be non-negative')` |
| `main` / 357 | `len(all_scenarios) != expected_total or matrix['counts'].get('extension_required') != 0` | `raise RuntimeError(f'one-shot total run requires exactly {expected_total} current scenarios and zero extensions')` |
| `main` / 369 | `unknown_included` | `raise ValueError(f'unknown included scenario IDs: {sorted(unknown_included)}')` |
| `main` / 378 | `not health or health.get('production_ready') is not True` | `raise RuntimeError(f'production Qwen service is not ready: {health}')` |

### 环境参数读取位置

这里只记录源码表达式，不读取当前进程环境；缓存与覆盖关系需查调用时机。

| 来源/行 | 环境变量表达式 | 源码fallback |
|---|---|---|
| `tools/run_acceptance_suite_a800.py:310` | `'VALIDATION_HARDWARE'` | `'NVIDIA A800-SXM4-80GB'` |
| `tools/run_acceptance_suite_a800.py:314` | `'VALIDATION_CUDA'` | `'13.2'` |
