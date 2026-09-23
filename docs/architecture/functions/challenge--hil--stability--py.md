# stability：功能记录

上级模块：[模块说明](../modules/challenge-hil.md) · 实现：[challenge/hil/stability.py](../../../challenge/hil/stability.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [Adapter能力、时钟域与测量范围](hil-trace-semantics.md)

## 功能职责与范围

Long-duration soak with a memory/temperature drift check and recovery probe.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `_window`

源码位置：[challenge/hil/stability.py 第 26 行](../../../challenge/hil/stability.py#L26)。类型：`FunctionDef`。

```python
_window(rows: Sequence[dict[str, Any]], key: str, *, head: bool) -> list[float]
```

`_window` 实现本文件对应的HIL测量辅助步骤；具体输入、阶段、副作用和异常见本页签名/调用/拒绝表，修改时须同步schema与报告。

### `run_soak`

源码位置：[challenge/hil/stability.py 第 34 行](../../../challenge/hil/stability.py#L34)。类型：`FunctionDef`。

```python
run_soak(runtime: PlannerRuntime, cases: Sequence[ReplayCase], *, run_id: str, duration_s: float, telemetry: TelemetrySpec | None=None, recovery_probe_cases: int=10, progress: Callable[[str], None] | None=None) -> dict[str, Any]
```

`run_soak` 执行轮次、回放、长稳、子命令、benchmark或后台采样；warmup与measured分离，错误/超时/缺stage必须作为结果记录而非零时延。

### `run_soak.emit`

源码位置：[challenge/hil/stability.py 第 49 行](../../../challenge/hil/stability.py#L49)。类型：`FunctionDef`。

```python
run_soak.emit(message: str) -> None
```

`emit` 写出冻结快照、handoff、trace、遥测或报告产物；文件必须绑定候选身份、输入哈希和环境，写盘成功不是Gate通过。

### `write_soak_files`

源码位置：[challenge/hil/stability.py 第 176 行](../../../challenge/hil/stability.py#L176)。类型：`FunctionDef`。

```python
write_soak_files(run_dir, result: dict[str, Any]) -> dict[str, Any]
```

Persist soak evidence under ``stability_logs/``.

## 内部调用与异常路径

- `_window` 调用：`float`, `isinstance`, `len`, `max`, `row.get`.
- `run_soak` 调用：`BackgroundMonitor`, `ValueError`, `_window`, `bool`, `datetime.now`, `datetime.now(timezone.utc).isoformat`, `durations.get`, `emit`, `float`, `isinstance`, `latencies.append`, `len`, `max`, `monitor.start`, `monitor.stop`, `monitor.summary`, `outcomes.get`, `outcomes.items`, `percentile`, `probe_latencies.append`, `probe_outcomes.get`, `probe_outcomes.items`, `progress`, `range`, `rows.append`, `rss_samples.append`, `runtime.infer`, `sample_process_memory`, `statistics.fmean`, `sum`, `telemetry_summary.get`, `time.monotonic`, `time.perf_counter_ns`, `trace.durations_ms`.
- `write_soak_files` 调用：`run_dir.path`, `write_csv`, `write_json`, `write_jsonl`.
- `emit` 调用：`progress`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `run_soak`，第 45 行：`ValueError('soak requires at least one case')`。
- `run_soak`，第 47 行：`ValueError('duration_s must be positive')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [challenge/hil/columns.py](../../../challenge/hil/columns.py)
- [challenge/hil/replay.py](../../../challenge/hil/replay.py)
- [challenge/hil/run_io.py](../../../challenge/hil/run_io.py)
- [challenge/hil/runtime_adapter.py](../../../challenge/hil/runtime_adapter.py)
- [challenge/hil/samplers.py](../../../challenge/hil/samplers.py)
- [challenge/hil/stages.py](../../../challenge/hil/stages.py)

静态 import 消费者（含测试）：

- [challenge/hil/cli.py](../../../challenge/hil/cli.py)
- [challenge/hil/tests/test_freeze_stability_handoff.py](../../../challenge/hil/tests/test_freeze_stability_handoff.py)

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-hil.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/hil/stability.py`

来源 SHA256：`c294ad19156e4d2e5df5accd694dd9ee649f5e97e8f93472e55cc16e8af00267`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `run_soak` / 45 | `not cases` | `raise ValueError('soak requires at least one case')` |
| `run_soak` / 47 | `duration_s <= 0` | `raise ValueError('duration_s must be positive')` |
