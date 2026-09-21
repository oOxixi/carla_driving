# samplers：功能记录

上级模块：[模块说明](../modules/challenge-hil.md) · 实现：[challenge/hil/samplers.py](../../../challenge/hil/samplers.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [Adapter能力、时钟域与测量范围](hil-trace-semantics.md)

## 功能职责与范围

Process/board telemetry sampling with explicit not-measured reporting.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `ProbeCommand.name: str`；默认：`未在声明处设置`。
- `ProbeCommand.command: tuple[str, ...]`；默认：`未在声明处设置`。
- `ProbeCommand.fields: tuple[str, ...]`；默认：`未在声明处设置`。
- `ProbeCommand.timeout_s: float`；默认：`10.0`。
- `TelemetrySpec.interval_s: float`；默认：`1.0`。
- `TelemetrySpec.power_probe: ProbeCommand | None`；默认：`None`。
- `TelemetrySpec.power_scope: str`；默认：`'board_total'`。
- `TelemetrySpec.power_probe_point: str`；默认：`'NOT_MEASURED'`。
- `TelemetrySpec.utilization_probe: ProbeCommand | None`；默认：`None`。
- `TelemetrySpec.utilization_scope: str`；默认：`'board_total'`。
- `TelemetrySpec.temperature_probe: ProbeCommand | None`；默认：`None`。

## 功能入口：输入、输出与实现说明

### `_now`

源码位置：[challenge/hil/samplers.py 第 21 行](../../../challenge/hil/samplers.py#L21)。类型：`FunctionDef`。

```python
_now() -> tuple[str, int]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_memory_backend`

源码位置：[challenge/hil/samplers.py 第 27 行](../../../challenge/hil/samplers.py#L27)。类型：`FunctionDef`。

```python
_memory_backend() -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `sample_process_memory`

源码位置：[challenge/hil/samplers.py 第 39 行](../../../challenge/hil/samplers.py#L39)。类型：`FunctionDef`。

```python
sample_process_memory(backend: str | None=None) -> dict[str, Any]
```

Return rss/peak RSS of the current process in KiB.

``backend`` is only used by tests to exercise a specific path; production
callers leave it as ``None`` and get automatic selection.

### `machine_load_percent`

源码位置：[challenge/hil/samplers.py 第 83 行](../../../challenge/hil/samplers.py#L83)。类型：`FunctionDef`。

```python
machine_load_percent(interval_s: float=0.5) -> float | None
```

System-wide CPU load over a short window, or None when unavailable.

A latency measurement taken on a busy machine is not comparable with one
taken on an idle machine, so the load at the start of a run is part of the
measurement environment rather than a diagnostic nicety.

### `power_source`

源码位置：[challenge/hil/samplers.py 第 100 行](../../../challenge/hil/samplers.py#L100)。类型：`FunctionDef`。

```python
power_source() -> str
```

``AC`` / ``BATTERY`` / ``UNKNOWN`` for the current host.

On battery, Windows reduces the CPU clock (observed ~60% of nominal), which
changes latency by several times over.  A run's power state therefore has to
travel with its numbers.

### `power_source.SYSTEM_POWER_STATUS`

源码位置：[challenge/hil/samplers.py 第 111 行](../../../challenge/hil/samplers.py#L111)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `cpu_frequency_mhz`

源码位置：[challenge/hil/samplers.py 第 133 行](../../../challenge/hil/samplers.py#L133)。类型：`FunctionDef`。

```python
cpu_frequency_mhz() -> dict[str, float | None]
```

Best-effort current/max CPU clock; None where the platform hides it.

### `cpu_calibration_ms`

源码位置：[challenge/hil/samplers.py 第 151 行](../../../challenge/hil/samplers.py#L151)。类型：`FunctionDef`。

```python
cpu_calibration_ms(repeats: int=5, size: int=512, trials: int=3) -> float | None
```

A fixed multi-threaded CPU workload, reported as the best of N trials.

Observed on this project: the same ONNX inference measured 2.7 ms, 27 ms and
92 ms on the same machine at different times, with the OS power state and
the achieved clock explaining only part of it.  A fixed calibration
workload is the only reliable way to tell whether two runs are comparable,
so it travels with the environment instead of being reconstructed later.

The **minimum** of several trials is reported: transient interference only
ever makes a trial slower, so the fastest trial is the most stable estimate
of what the machine can do.  Single-shot sampling was measured to swing
7.2 -> 18.7 ms between runs on this host, which is too noisy to compare
against.

### `_read_process_memory_counters`

源码位置：[challenge/hil/samplers.py 第 188 行](../../../challenge/hil/samplers.py#L188)。类型：`FunctionDef`。

```python
_read_process_memory_counters() -> tuple[Any, bool]
```

Query the Win32 process memory counters with explicit ctypes signatures.

Without ``argtypes``/``restype`` ctypes marshals the 64-bit process handle
as a 32-bit int and the call fails with a zero return value, which is
exactly the bug this function exists to avoid.

### `_read_process_memory_counters.PROCESS_MEMORY_COUNTERS`

源码位置：[challenge/hil/samplers.py 第 198 行](../../../challenge/hil/samplers.py#L198)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ProbeCommand`

源码位置：[challenge/hil/samplers.py 第 230 行](../../../challenge/hil/samplers.py#L230)。类型：`ClassDef`。

External probe expected to print one JSON object on stdout.

### `ProbeCommand.read`

源码位置：[challenge/hil/samplers.py 第 238 行](../../../challenge/hil/samplers.py#L238)。类型：`FunctionDef`。

```python
ProbeCommand.read(self) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `TelemetrySpec`

源码位置：[challenge/hil/samplers.py 第 253 行](../../../challenge/hil/samplers.py#L253)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `TelemetrySpec.__post_init__`

源码位置：[challenge/hil/samplers.py 第 262 行](../../../challenge/hil/samplers.py#L262)。类型：`FunctionDef`。

```python
TelemetrySpec.__post_init__(self) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `BackgroundMonitor`

源码位置：[challenge/hil/samplers.py 第 267 行](../../../challenge/hil/samplers.py#L267)。类型：`ClassDef`。

Sample memory every interval; power/utilization only if probed.

### `BackgroundMonitor.__init__`

源码位置：[challenge/hil/samplers.py 第 270 行](../../../challenge/hil/samplers.py#L270)。类型：`FunctionDef`。

```python
BackgroundMonitor.__init__(self, spec: TelemetrySpec | None=None, *, run_id: str='', round_index: int=0) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `BackgroundMonitor._cpu_percent_sampler`

源码位置：[challenge/hil/samplers.py 第 284 行](../../../challenge/hil/samplers.py#L284)。类型：`FunctionDef`。

```python
BackgroundMonitor._cpu_percent_sampler() -> Callable[[], float | None]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `BackgroundMonitor.start`

源码位置：[challenge/hil/samplers.py 第 293 行](../../../challenge/hil/samplers.py#L293)。类型：`FunctionDef`。

```python
BackgroundMonitor.start(self) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `BackgroundMonitor._loop`

源码位置：[challenge/hil/samplers.py 第 298 行](../../../challenge/hil/samplers.py#L298)。类型：`FunctionDef`。

```python
BackgroundMonitor._loop(self) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `BackgroundMonitor.sample_once`

源码位置：[challenge/hil/samplers.py 第 302 行](../../../challenge/hil/samplers.py#L302)。类型：`FunctionDef`。

```python
BackgroundMonitor.sample_once(self) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `BackgroundMonitor._power_row`

源码位置：[challenge/hil/samplers.py 第 328 行](../../../challenge/hil/samplers.py#L328)。类型：`FunctionDef`。

```python
BackgroundMonitor._power_row(self, wall: str, monotonic: int, index: int) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `BackgroundMonitor._utilization_row`

源码位置：[challenge/hil/samplers.py 第 371 行](../../../challenge/hil/samplers.py#L371)。类型：`FunctionDef`。

```python
BackgroundMonitor._utilization_row(self, wall: str, monotonic: int, index: int) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `BackgroundMonitor.stop`

源码位置：[challenge/hil/samplers.py 第 399 行](../../../challenge/hil/samplers.py#L399)。类型：`FunctionDef`。

```python
BackgroundMonitor.stop(self) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `BackgroundMonitor.summary`

源码位置：[challenge/hil/samplers.py 第 405 行](../../../challenge/hil/samplers.py#L405)。类型：`FunctionDef`。

```python
BackgroundMonitor.summary(self) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `BackgroundMonitor.summary.values`

源码位置：[challenge/hil/samplers.py 第 406 行](../../../challenge/hil/samplers.py#L406)。类型：`FunctionDef`。

```python
BackgroundMonitor.summary.values(rows: list[dict[str, Any]], key: str) -> list[float]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `_now` 调用：`datetime.now`, `datetime.now(timezone.utc).isoformat`, `time.perf_counter_ns`.
- `_memory_backend` 调用：`os.path.isdir`.
- `sample_process_memory` 调用：`OSError`, `RuntimeError`, `ValueError`, `_memory_backend`, `_read_process_memory_counters`, `float`, `getattr`, `line.split`, `line.startswith`, `open`, `psutil.Process`, `psutil.Process().memory_info`, `values.get`.
- `machine_load_percent` 调用：`float`, `psutil.cpu_percent`.
- `power_source` 调用：`SYSTEM_POWER_STATUS`, `ctypes.WinDLL`, `ctypes.WinDLL('kernel32', use_last_error=True).GetSystemPowerStatus`, `ctypes.byref`, `int`, `{0: 'BATTERY', 1: 'AC'}.get`.
- `cpu_frequency_mhz` 调用：`float`, `psutil.cpu_freq`.
- `cpu_calibration_ms` 调用：`matrix.T.copy`, `max`, `min`, `np.arange`, `np.arange(size * size, dtype=np.float32).reshape`, `range`, `time.perf_counter_ns`.
- `_read_process_memory_counters` 调用：`PROCESS_MEMORY_COUNTERS`, `bool`, `ctypes.POINTER`, `ctypes.WinDLL`, `ctypes.byref`, `ctypes.sizeof`, `kernel32.GetCurrentProcess`, `psapi.GetProcessMemoryInfo`.
- `read` 调用：`ValueError`, `completed.stdout.strip`, `isinstance`, `json.loads`, `list`, `payload.get`, `subprocess.run`.
- `__post_init__` 调用：`ValueError`, `isinstance`.
- `__init__` 调用：`TelemetrySpec`, `self._cpu_percent_sampler`, `threading.Event`.
- `_cpu_percent_sampler` 调用：`process.cpu_percent`, `psutil.Process`.
- `start` 调用：`self._thread.start`, `self.sample_once`, `threading.Thread`.
- `_loop` 调用：`self._stop.wait`, `self.sample_once`.
- `sample_once` 调用：`_now`, `sample_process_memory`, `self._power_row`, `self._utilization_row`, `self.errors.append`, `self.memory_rows.append`, `self.power_rows.append`, `self.utilization_rows.append`, `type`.
- `_power_row` 调用：`row.update`, `self.errors.append`, `self.spec.power_probe.read`, `self.spec.power_probe.read().items`, `type`.
- `_utilization_row` 调用：`(row['notes'] + ';bpu_not_measured').strip`, `self._cpu_sampler`, `self.errors.append`, `self.spec.utilization_probe.read`, `self.spec.utilization_probe.read().items`, `type`.
- `stop` 调用：`self._stop.set`, `self._thread.join`, `self.sample_once`.
- `summary` 调用：`bool`, `float`, `isinstance`, `len`, `list`, `max`, `row.get`, `sum`, `values`.
- `values` 调用：`float`, `isinstance`, `row.get`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__post_init__`，第 264 行：`ValueError('interval_s must be positive')`。
- `read`，第 248 行：`ValueError(f'probe {self.name} must print a JSON object')`。
- `sample_process_memory`，第 47 行：`ValueError(f'unknown memory backend: {backend!r}')`。
- `sample_process_memory`，第 52 行：`RuntimeError('psutil backend requested but psutil is missing')`。
- `sample_process_memory`，第 75 行：`OSError('GetProcessMemoryInfo failed')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [challenge/hil/cli.py](../../../challenge/hil/cli.py)
- [challenge/hil/rounds.py](../../../challenge/hil/rounds.py)
- [challenge/hil/stability.py](../../../challenge/hil/stability.py)
- [challenge/hil/tests/test_freeze_stability_handoff.py](../../../challenge/hil/tests/test_freeze_stability_handoff.py)
- [challenge/hil/tests/test_identity_and_io.py](../../../challenge/hil/tests/test_identity_and_io.py)

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-hil.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/hil/samplers.py`

来源 SHA256：`e440b2ed7877e9ec950155d292e3394e569d9ee39be274241d2a51c6a533d7c1`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `ProbeCommand.name` | `str` | `无声明默认；构造/赋值方提供` |
| `ProbeCommand.command` | `tuple[str, ...]` | `无声明默认；构造/赋值方提供` |
| `ProbeCommand.fields` | `tuple[str, ...]` | `无声明默认；构造/赋值方提供` |
| `ProbeCommand.timeout_s` | `float` | `10.0` |
| `TelemetrySpec.interval_s` | `float` | `1.0` |
| `TelemetrySpec.power_probe` | `ProbeCommand &#124; None` | `None` |
| `TelemetrySpec.power_scope` | `str` | `'board_total'` |
| `TelemetrySpec.power_probe_point` | `str` | `'NOT_MEASURED'` |
| `TelemetrySpec.utilization_probe` | `ProbeCommand &#124; None` | `None` |
| `TelemetrySpec.utilization_scope` | `str` | `'board_total'` |
| `TelemetrySpec.temperature_probe` | `ProbeCommand &#124; None` | `None` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `sample_process_memory` / 47 | `backend not in {'psutil', 'proc_status', 'win32_psapi'}` | `raise ValueError(f'unknown memory backend: {backend!r}')` |
| `sample_process_memory` / 52 | `backend == 'psutil' AND except ImportError` | `raise RuntimeError('psutil backend requested but psutil is missing') from error` |
| `sample_process_memory` / 75 | `not ok` | `raise OSError('GetProcessMemoryInfo failed')` |
| `ProbeCommand.read` / 248 | `not isinstance(payload, dict)` | `raise ValueError(f'probe {self.name} must print a JSON object')` |
| `TelemetrySpec.__post_init__` / 264 | `not isinstance(self.interval_s, (int, float)) or self.interval_s <= 0` | `raise ValueError('interval_s must be positive')` |
