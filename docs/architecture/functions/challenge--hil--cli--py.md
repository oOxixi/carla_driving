# cli：功能记录

上级模块：[模块说明](../modules/challenge-hil.md) · 实现：[challenge/hil/cli.py](../../../challenge/hil/cli.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [Adapter能力、时钟域与测量范围](hil-trace-semantics.md)

## 功能职责与范围

Command line entry points for the B3 measurement toolkit.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `_build_hardware_env`

源码位置：[challenge/hil/cli.py 第 72 行](../../../challenge/hil/cli.py#L72)。类型：`FunctionDef`。

```python
_build_hardware_env(args: argparse.Namespace, identity: CandidateIdentity, artifact: str | Path | None) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `version_of`

源码位置：[challenge/hil/cli.py 第 163 行](../../../challenge/hil/cli.py#L163)。类型：`FunctionDef`。

```python
version_of(module_name: str) -> str | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `package_version`

源码位置：[challenge/hil/cli.py 第 171 行](../../../challenge/hil/cli.py#L171)。类型：`FunctionDef`。

```python
package_version(distribution: str) -> str | None
```

Version of an installed distribution, without importing it.

### `runtime_libraries`

源码位置：[challenge/hil/cli.py 第 181 行](../../../challenge/hil/cli.py#L181)。类型：`FunctionDef`。

```python
runtime_libraries() -> dict[str, str | None]
```

Every library whose version can change a measurement.

### `_probe_from_args`

源码位置：[challenge/hil/cli.py 第 194 行](../../../challenge/hil/cli.py#L194)。类型：`FunctionDef`。

```python
_probe_from_args(command: str | None, fields: str | None, name: str) -> ProbeCommand | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_telemetry_spec`

源码位置：[challenge/hil/cli.py 第 208 行](../../../challenge/hil/cli.py#L208)。类型：`FunctionDef`。

```python
_telemetry_spec(args: argparse.Namespace) -> TelemetrySpec
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_build_runtime`

源码位置：[challenge/hil/cli.py 第 223 行](../../../challenge/hil/cli.py#L223)。类型：`FunctionDef`。

```python
_build_runtime(args: argparse.Namespace) -> PlannerRuntime
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `command_schema`

源码位置：[challenge/hil/cli.py 第 247 行](../../../challenge/hil/cli.py#L247)。类型：`FunctionDef`。

```python
command_schema(args: argparse.Namespace) -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `command_selftest`

源码位置：[challenge/hil/cli.py 第 261 行](../../../challenge/hil/cli.py#L261)。类型：`FunctionDef`。

```python
command_selftest(_: argparse.Namespace) -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_add_shared_args`

源码位置：[challenge/hil/cli.py 第 322 行](../../../challenge/hil/cli.py#L322)。类型：`FunctionDef`。

```python
_add_shared_args(parser: argparse.ArgumentParser, *, out_help: str) -> None
```

Arguments every measurement subcommand needs, defined exactly once.

### `build_parser`

源码位置：[challenge/hil/cli.py 第 375 行](../../../challenge/hil/cli.py#L375)。类型：`FunctionDef`。

```python
build_parser() -> argparse.ArgumentParser
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_warn_if_busy`

源码位置：[challenge/hil/cli.py 第 464 行](../../../challenge/hil/cli.py#L464)。类型：`FunctionDef`。

```python
_warn_if_busy(hardware_env: Mapping[str, Any], log: Any, threshold: float=20.0) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_load_cases`

源码位置：[challenge/hil/cli.py 第 486 行](../../../challenge/hil/cli.py#L486)。类型：`FunctionDef`。

```python
_load_cases(args: argparse.Namespace) -> tuple[list[Any], dict[str, Any]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `command_freeze`

源码位置：[challenge/hil/cli.py 第 507 行](../../../challenge/hil/cli.py#L507)。类型：`FunctionDef`。

```python
command_freeze(args: argparse.Namespace) -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `command_consistency`

源码位置：[challenge/hil/cli.py 第 539 行](../../../challenge/hil/cli.py#L539)。类型：`FunctionDef`。

```python
command_consistency(args: argparse.Namespace) -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `command_handoff`

源码位置：[challenge/hil/cli.py 第 580 行](../../../challenge/hil/cli.py#L580)。类型：`FunctionDef`。

```python
command_handoff(args: argparse.Namespace) -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `command_artifact`

源码位置：[challenge/hil/cli.py 第 605 行](../../../challenge/hil/cli.py#L605)。类型：`FunctionDef`。

```python
command_artifact(args: argparse.Namespace) -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `command_contract`

源码位置：[challenge/hil/cli.py 第 625 行](../../../challenge/hil/cli.py#L625)。类型：`FunctionDef`。

```python
command_contract(args: argparse.Namespace) -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `command_soak`

源码位置：[challenge/hil/cli.py 第 643 行](../../../challenge/hil/cli.py#L643)。类型：`FunctionDef`。

```python
command_soak(args: argparse.Namespace) -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `command_soak.log`

源码位置：[challenge/hil/cli.py 第 648 行](../../../challenge/hil/cli.py#L648)。类型：`FunctionDef`。

```python
command_soak.log(message: str) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `command_run`

源码位置：[challenge/hil/cli.py 第 720 行](../../../challenge/hil/cli.py#L720)。类型：`FunctionDef`。

```python
command_run(args: argparse.Namespace) -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `command_run.log`

源码位置：[challenge/hil/cli.py 第 725 行](../../../challenge/hil/cli.py#L725)。类型：`FunctionDef`。

```python
command_run.log(message: str) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[challenge/hil/cli.py 第 960 行](../../../challenge/hil/cli.py#L960)。类型：`FunctionDef`。

```python
main(argv: Sequence[str] | None=None) -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `_build_hardware_env` 调用：`Path`, `Path(artifact).is_file`, `Path(artifact).resolve`, `bool`, `clock_resolution_ns`, `cpu_calibration_ms`, `cpu_frequency_mhz`, `datetime.now`, `datetime.now(timezone.utc).isoformat`, `float`, `getattr`, `identity.to_dict`, `machine_load_percent`, `os.cpu_count`, `path.stat`, `path.suffix.lstrip`, `path.suffix.lstrip('.').lower`, `platform.machine`, `platform.node`, `platform.platform`, `platform.processor`, `platform.version`, `power_source`, `runtime_libraries`, `sha256_file`, `str`, `sys.version.split`, `teacher_baselines`, `time.get_clock_info`, `version_of`.
- `version_of` 调用：`__import__`, `getattr`.
- `package_version` 调用：`version`.
- `runtime_libraries` 调用：`package_version`.
- `_probe_from_args` 调用：`(fields or '').split`, `ProbeCommand`, `part.strip`, `shlex.split`, `tuple`.
- `_telemetry_spec` 调用：`TelemetrySpec`, `_probe_from_args`.
- `_build_runtime` 调用：`AdapterError`, `BoardCliRuntime`, `InProcessStudentRuntime`, `OnnxModelRuntime`, `Path`.
- `command_schema` 调用：`FILE_SCHEMAS.items`, `Path`, `json.dumps`, `len`, `list`, `output.mkdir`, `print`, `write_json`.
- `command_selftest` 调用：`CandidateIdentity`, `LatencyCollector`, `StageTrace`, `abs`, `backwards.mark`, `claim_scope`, `collector.add`, `collector.report`, `enumerate`, `failures.append`, `identity.to_dict`, `json.dumps`, `len`, `out_of_order.mark`, `percentile`, `print`, `set`, `trace.durations_ms`, `trace.finish`, `trace.mark`.
- `_add_shared_args` 调用：`parser.add_argument`, `platform.machine`, `platform.processor`.
- `build_parser` 调用：`_add_shared_args`, `argparse.ArgumentParser`, `artifact.add_argument`, `artifact.set_defaults`, `consistency.add_argument`, `consistency.set_defaults`, `contract.add_argument`, `contract.set_defaults`, `freeze.add_argument`, `freeze.set_defaults`, `handoff.add_argument`, `handoff.set_defaults`, `parser.add_subparsers`, `run.add_argument`, `run.set_defaults`, `schema.add_argument`, `schema.set_defaults`, `selftest.set_defaults`, `soak.add_argument`, `soak.set_defaults`, `sub.add_parser`.
- `_warn_if_busy` 调用：`frequency.get`, `hardware_env.get`, `isinstance`, `log`.
- `_load_cases` 调用：`getattr`, `len`, `load_frozen_snapshot`, `load_replay_cases`, `sum`.
- `command_freeze` 调用：`freeze_snapshot`, `json.dumps`, `len`, `load_frozen_snapshot`, `print`.
- `command_consistency` 调用：`AdapterError`, `OnnxOutputSource`, `Path`, `TorchOutputSource`, `_load_cases`, `compare_sources`, `item.get`, `json.dumps`, `max`, `print`, `sorted`, `sorted(report['cases'], key=lambda item: item.get('max_abs_diff') or -1)[-1].get`, `write_json`.
- `command_handoff` 调用：`AdapterError`, `Path`, `Path(args.run).resolve`, `export_handoff`, `failure_path.is_file`, `failure_path.read_text`, `json.dumps`, `json.loads`, `plans_path.is_file`, `print`, `read_jsonl`, `replay_path.is_file`.
- `command_artifact` 调用：`Path`, `candidate.is_file`, `json.dumps`, `print`, `str`, `target.mkdir`, `verify_onnx_artifact`, `write_json`.
- `command_contract` 调用：`Path`, `_build_runtime`, `_load_cases`, `check_runtime_contract`, `json.dumps`, `max`, `print`, `str`, `target.mkdir`, `write_json`.
- `command_soak` 调用：`Path`, `Path(args.out).resolve`, `RunDir`, `_build_hardware_env`, `_build_runtime`, `_load_cases`, `_telemetry_spec`, `_warn_if_busy`, `bool`, `build_report`, `claim_scope`, `hardware_env.get`, `json.dumps`, `len`, `log`, `new_run_id`, `print`, `report_filename`, `run_dir.build_manifest`, `run_dir.path`, `run_dir.path(report_filename(args.device_class)).write_text`, `run_dir.write_hardware_env`, `run_soak`, `runtime.capabilities.to_dict`, `str`, `write_soak_files`.
- `command_run` 调用：`(result.rounds[-1].telemetry if result.rounds else {}).get`, `FILE_SCHEMAS.items`, `LatencyCollector`, `OnnxModelRuntime`, `OnnxOutputSource`, `Path`, `Path(args.out).resolve`, `RunDir`, `TorchOutputSource`, `_build_hardware_env`, `_build_runtime`, `_load_cases`, `_telemetry_spec`, `_warn_if_busy`, `backend_consistency.get`, `bench_report.items`, `bench_report['metrics_ms'].get`, `bool`, `build_failure_cases`, `build_report`, `case_info.get`, `claim_scope`, `collector.add`, `collector.report`, `compare_sources`, `export_handoff`, `extra_notes.append`, `getattr`, `hardware_env.get`, `int`, `json.dumps`, `latency_report.items`, `len`, `list`, `log`, `max`, `min`, `model_runtime.bench_model_only`, `model_runtime.identity.to_dict`, `new_run_id`, `print`, `report_filename`, `result.collector.report`, `result.summary`, `run_dir.build_manifest`, `run_dir.path`, `run_dir.path(report_filename(args.device_class)).write_text`, `run_dir.write_hardware_env`, `run_failure_cases`, `run_rounds`, `runtime.capabilities.to_dict`, `runtime.identity.to_dict`, `stats.get`, `str`, `sum`, `verifier`, `write_csv`, `write_json`, `write_jsonl`.
- `main` 调用：`args.func`, `build_parser`, `int`, `parser.parse_args`, `print`.
- `log` 调用：`print`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `_build_runtime`，第 236 行：`AdapterError('--board-command is required for the board adapter')`。
- `_build_runtime`，第 244 行：`AdapterError(f'unsupported adapter: {args.adapter}')`。
- `command_consistency`，第 544 行：`AdapterError('--onnx is required together with --baseline-onnx')`。
- `command_handoff`，第 586 行：`AdapterError(f'missing {replay_path}')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 324 行：`parser.add_argument('--repo', required=True, help='carla_driving checkout')`。
- 第 325 行：`parser.add_argument('--out', required=True, help=out_help)`。
- 第 326 行：`parser.add_argument('--delivery', help='B1 delivery root (request set + rgb manifest)')`。
- 第 327 行：`parser.add_argument('--requests', help='explicit request JSONL path')`。
- 第 328 行：`parser.add_argument('--frozen', help='frozen replay snapshot directory')`。
- 第 329 行：`parser.add_argument('--adapter', default='inprocess', choices=['inprocess', 'onnx', 'board', 'both'])`。
- 第 334 行：`parser.add_argument('--onnx', help='ONNX artifact for the model-only chain')`。
- 第 335 行：`parser.add_argument('--weights', help='FP32 weights for the in-process chain')`。
- 第 336 行：`parser.add_argument('--weights-manifest', help='A3 weight manifest JSON')`。
- 第 337 行：`parser.add_argument('--board-command', help='A4 runtime command (stdin JSON, stdout JSON)')`。
- 第 338 行：`parser.add_argument('--board-artifact', help='board model artifact for identity hashing')`。
- 第 339 行：`parser.add_argument('--model-id', default=UNRESOLVED)`。
- 第 340 行：`parser.add_argument('--config-id', default=UNRESOLVED)`。
- 第 341 行：`parser.add_argument('--dataset-version', default=UNRESOLVED)`。
- 第 342 行：`parser.add_argument('--model-seed', type=int, default=20260911, help='torch seed for the random-initialized structure (A1 freezes 20260911)')`。
- 第 348 行：`parser.add_argument('--run-id', default=None)`。
- 第 349 行：`parser.add_argument('--device-class', default='X86_WORKSTATION', choices=['X86_WORKSTATION', 'J6P_BOARD'])`。
- 第 354 行：`parser.add_argument('--accelerator-kind', default='cpu')`。
- 第 355 行：`parser.add_argument('--accelerator-name', default=platform.processor() or platform.machine())`。
- 第 356 行：`parser.add_argument('--bpu-arch', default=None)`。
- 第 357 行：`parser.add_argument('--openexplorer-version', default=None)`。
- 第 358 行：`parser.add_argument('--cpu-governor', default=None)`。
- 第 359 行：`parser.add_argument('--power-method', default='EXTERNAL_METER')`。
- 第 360 行：`parser.add_argument('--power-scope', default='board_total')`。
- 第 361 行：`parser.add_argument('--power-probe-point', default='NOT_MEASURED')`。
- 第 362 行：`parser.add_argument('--power-probe-command', default=None)`。
- 第 363 行：`parser.add_argument('--power-probe-fields', default='power_w,voltage_v,current_a')`。
- 第 364 行：`parser.add_argument('--power-notes', default='')`。
- 第 365 行：`parser.add_argument('--utilization-scope', default='board_total')`。
- 第 366 行：`parser.add_argument('--utilization-probe-command', default=None)`。
- 第 367 行：`parser.add_argument('--utilization-probe-fields', default='bpu_percent,cpu_percent,ddr_bandwidth_gbps')`。
- 第 371 行：`parser.add_argument('--telemetry-interval-s', type=float, default=1.0)`。
- 第 372 行：`parser.add_argument('--quiet', action='store_true')`。
- 第 383 行：`schema.add_argument('--out', default='schemas')`。
- 第 388 行：`run.add_argument('--rounds', type=int, default=3)`。
- 第 389 行：`run.add_argument('--warmup', type=int, default=5)`。
- 第 390 行：`run.add_argument('--limit', type=int, default=None, help='cap the number of replayed cases')`。
- 第 391 行：`run.add_argument('--no-failures', action='store_true', help='skip the abnormal input suite')`。
- 第 392 行：`run.add_argument('--no-handoff', action='store_true', help='skip the A3 handoff export')`。
- 第 393 行：`run.add_argument('--verify-consistency', action='store_true', help='compare raw torch and ONNX outputs on the first requests')`。
- 第 398 行：`run.add_argument('--consistency-rtol', type=float, default=DEFAULT_RTOL)`。
- 第 399 行：`run.add_argument('--consistency-atol', type=float, default=DEFAULT_ATOL)`。
- 第 400 行：`run.add_argument('--verify-backend-consistency', action='store_true', help='prove the instrumented stage path matches StudentBackend.infer')`。
- 第 409 行：`soak.add_argument('--limit', type=int, default=None, help='cap the number of cases')`。
- 第 410 行：`soak.add_argument('--duration-minutes', type=float, default=30.0)`。
- 第 411 行：`soak.add_argument('--recovery-probe-cases', type=int, default=10)`。
- 第 418 行：`contract.add_argument('--limit', type=int, default=5)`。
- 第 419 行：`contract.add_argument('--latency-budget-ms', type=float, default=1000.0)`。
- 第 425 行：`artifact.add_argument('--repo', required=True, help='carla_driving checkout')`。
- 第 426 行：`artifact.add_argument('--onnx', help='ONNX artifact (defaults to the A1 structure export)')`。
- 第 427 行：`artifact.add_argument('--reference-structure', help='producer model_structure.json')`。
- 第 428 行：`artifact.add_argument('--expected-opset', type=int, default=17)`。
- 第 429 行：`artifact.add_argument('--out', help='optional directory for artifact_report.json')`。
- 第 433 行：`freeze.add_argument('--delivery', help='B1 delivery root')`。
- 第 434 行：`freeze.add_argument('--requests', help='explicit request JSONL path')`。
- 第 435 行：`freeze.add_argument('--repo', help='carla_driving checkout (for raw rgb_ref fallback)')`。
- 第 436 行：`freeze.add_argument('--out', required=True, help='snapshot root directory')`。
- 第 437 行：`freeze.add_argument('--name', required=True, help='snapshot name')`。
- 第 438 行：`freeze.add_argument('--limit', type=int, default=None)`。
- 第 439 行：`freeze.add_argument('--no-copy-rgb', action='store_true')`。
- 第 443 行：`consistency.add_argument('--repo', required=True)`。
- 第 444 行：`consistency.add_argument('--onnx', help='candidate ONNX artifact')`。
- 第 445 行：`consistency.add_argument('--baseline-onnx', help='reference ONNX (e.g. FP32) for INT8 checks')`。
- 第 446 行：`consistency.add_argument('--weights', help='torch weights for the reference path')`。
- 第 447 行：`consistency.add_argument('--delivery', help='B1 delivery root for the request set')`。
- 第 448 行：`consistency.add_argument('--frozen', help='frozen snapshot directory')`。
- 第 449 行：`consistency.add_argument('--requests', help='explicit request JSONL path')`。
- 第 450 行：`consistency.add_argument('--limit', type=int, default=5)`。
- 第 451 行：`consistency.add_argument('--rtol', type=float, default=DEFAULT_RTOL)`。
- 第 452 行：`consistency.add_argument('--atol', type=float, default=DEFAULT_ATOL)`。
- 第 453 行：`consistency.add_argument('--model-seed', type=int, default=20260911)`。
- 第 454 行：`consistency.add_argument('--out', help='optional report path')`。
- 第 458 行：`handoff.add_argument('--run', required=True, help='finished run directory')`。
- 第 459 行：`handoff.add_argument('--out', help='output directory (defaults to <run>/handoff)')`。

## 上下游与关联验证

静态导入的项目内实现：

- [challenge/hil/artifact.py](../../../challenge/hil/artifact.py)
- [challenge/hil/columns.py](../../../challenge/hil/columns.py)
- [challenge/hil/consistency.py](../../../challenge/hil/consistency.py)
- [challenge/hil/contract.py](../../../challenge/hil/contract.py)
- [challenge/hil/failure_cases.py](../../../challenge/hil/failure_cases.py)
- [challenge/hil/freeze.py](../../../challenge/hil/freeze.py)
- [challenge/hil/handoff.py](../../../challenge/hil/handoff.py)
- [challenge/hil/identity.py](../../../challenge/hil/identity.py)
- [challenge/hil/provenance.py](../../../challenge/hil/provenance.py)
- [challenge/hil/replay.py](../../../challenge/hil/replay.py)
- [challenge/hil/report.py](../../../challenge/hil/report.py)
- [challenge/hil/rounds.py](../../../challenge/hil/rounds.py)
- [challenge/hil/run_io.py](../../../challenge/hil/run_io.py)
- [challenge/hil/runtime_adapter.py](../../../challenge/hil/runtime_adapter.py)
- [challenge/hil/samplers.py](../../../challenge/hil/samplers.py)
- [challenge/hil/stability.py](../../../challenge/hil/stability.py)
- [challenge/hil/stages.py](../../../challenge/hil/stages.py)

静态 import 消费者（含测试）：

- 未发现静态 import 消费者；命令行、间接注册、文件路径加载不在此清单内。

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-hil.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/hil/cli.py`

来源 SHA256：`061018dae6e9741d60e1f05b4cd91561755e6665563cdd115c48a29cbdd82617`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 324 | `'--repo'` | `required=True; help='carla_driving checkout'` |
| 325 | `'--out'` | `required=True; help=out_help` |
| 326 | `'--delivery'` | `help='B1 delivery root (request set + rgb manifest)'` |
| 327 | `'--requests'` | `help='explicit request JSONL path'` |
| 328 | `'--frozen'` | `help='frozen replay snapshot directory'` |
| 329 | `'--adapter'` | `default='inprocess'; choices=['inprocess', 'onnx', 'board', 'both']` |
| 334 | `'--onnx'` | `help='ONNX artifact for the model-only chain'` |
| 335 | `'--weights'` | `help='FP32 weights for the in-process chain'` |
| 336 | `'--weights-manifest'` | `help='A3 weight manifest JSON'` |
| 337 | `'--board-command'` | `help='A4 runtime command (stdin JSON, stdout JSON)'` |
| 338 | `'--board-artifact'` | `help='board model artifact for identity hashing'` |
| 339 | `'--model-id'` | `default=UNRESOLVED` |
| 340 | `'--config-id'` | `default=UNRESOLVED` |
| 341 | `'--dataset-version'` | `default=UNRESOLVED` |
| 342 | `'--model-seed'` | `type=int; default=20260911; help='torch seed for the random-initialized structure (A1 freezes 20260911)'` |
| 348 | `'--run-id'` | `default=None` |
| 349 | `'--device-class'` | `default='X86_WORKSTATION'; choices=['X86_WORKSTATION', 'J6P_BOARD']` |
| 354 | `'--accelerator-kind'` | `default='cpu'` |
| 355 | `'--accelerator-name'` | `default=platform.processor() or platform.machine()` |
| 356 | `'--bpu-arch'` | `default=None` |
| 357 | `'--openexplorer-version'` | `default=None` |
| 358 | `'--cpu-governor'` | `default=None` |
| 359 | `'--power-method'` | `default='EXTERNAL_METER'` |
| 360 | `'--power-scope'` | `default='board_total'` |
| 361 | `'--power-probe-point'` | `default='NOT_MEASURED'` |
| 362 | `'--power-probe-command'` | `default=None` |
| 363 | `'--power-probe-fields'` | `default='power_w,voltage_v,current_a'` |
| 364 | `'--power-notes'` | `default=''` |
| 365 | `'--utilization-scope'` | `default='board_total'` |
| 366 | `'--utilization-probe-command'` | `default=None` |
| 367 | `'--utilization-probe-fields'` | `default='bpu_percent,cpu_percent,ddr_bandwidth_gbps'` |
| 371 | `'--telemetry-interval-s'` | `type=float; default=1.0` |
| 372 | `'--quiet'` | `action='store_true'` |
| 383 | `'--out'` | `default='schemas'` |
| 388 | `'--rounds'` | `type=int; default=3` |
| 389 | `'--warmup'` | `type=int; default=5` |
| 390 | `'--limit'` | `type=int; default=None; help='cap the number of replayed cases'` |
| 391 | `'--no-failures'` | `action='store_true'; help='skip the abnormal input suite'` |
| 392 | `'--no-handoff'` | `action='store_true'; help='skip the A3 handoff export'` |
| 393 | `'--verify-consistency'` | `action='store_true'; help='compare raw torch and ONNX outputs on the first requests'` |
| 398 | `'--consistency-rtol'` | `type=float; default=DEFAULT_RTOL` |
| 399 | `'--consistency-atol'` | `type=float; default=DEFAULT_ATOL` |
| 400 | `'--verify-backend-consistency'` | `action='store_true'; help='prove the instrumented stage path matches StudentBackend.infer'` |
| 409 | `'--limit'` | `type=int; default=None; help='cap the number of cases'` |
| 410 | `'--duration-minutes'` | `type=float; default=30.0` |
| 411 | `'--recovery-probe-cases'` | `type=int; default=10` |
| 418 | `'--limit'` | `type=int; default=5` |
| 419 | `'--latency-budget-ms'` | `type=float; default=1000.0` |
| 425 | `'--repo'` | `required=True; help='carla_driving checkout'` |
| 426 | `'--onnx'` | `help='ONNX artifact (defaults to the A1 structure export)'` |
| 427 | `'--reference-structure'` | `help='producer model_structure.json'` |
| 428 | `'--expected-opset'` | `type=int; default=17` |
| 429 | `'--out'` | `help='optional directory for artifact_report.json'` |
| 433 | `'--delivery'` | `help='B1 delivery root'` |
| 434 | `'--requests'` | `help='explicit request JSONL path'` |
| 435 | `'--repo'` | `help='carla_driving checkout (for raw rgb_ref fallback)'` |
| 436 | `'--out'` | `required=True; help='snapshot root directory'` |
| 437 | `'--name'` | `required=True; help='snapshot name'` |
| 438 | `'--limit'` | `type=int; default=None` |
| 439 | `'--no-copy-rgb'` | `action='store_true'` |
| 443 | `'--repo'` | `required=True` |
| 444 | `'--onnx'` | `help='candidate ONNX artifact'` |
| 445 | `'--baseline-onnx'` | `help='reference ONNX (e.g. FP32) for INT8 checks'` |
| 446 | `'--weights'` | `help='torch weights for the reference path'` |
| 447 | `'--delivery'` | `help='B1 delivery root for the request set'` |
| 448 | `'--frozen'` | `help='frozen snapshot directory'` |
| 449 | `'--requests'` | `help='explicit request JSONL path'` |
| 450 | `'--limit'` | `type=int; default=5` |
| 451 | `'--rtol'` | `type=float; default=DEFAULT_RTOL` |
| 452 | `'--atol'` | `type=float; default=DEFAULT_ATOL` |
| 453 | `'--model-seed'` | `type=int; default=20260911` |
| 454 | `'--out'` | `help='optional report path'` |
| 458 | `'--run'` | `required=True; help='finished run directory'` |
| 459 | `'--out'` | `help='output directory (defaults to <run>/handoff)'` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `_build_runtime` / 236 | `args.adapter == 'board' AND not args.board_command` | `raise AdapterError('--board-command is required for the board adapter')` |
| `_build_runtime` / 244 | `本地无直接if；检查上下文` | `raise AdapterError(f'unsupported adapter: {args.adapter}')` |
| `command_consistency` / 544 | `args.baseline_onnx AND not args.onnx` | `raise AdapterError('--onnx is required together with --baseline-onnx')` |
| `command_handoff` / 586 | `not replay_path.is_file()` | `raise AdapterError(f'missing {replay_path}')` |
