# stages：功能记录

上级模块：[模块说明](../modules/challenge-hil.md) · 实现：[challenge/hil/stages.py](../../../challenge/hil/stages.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [Adapter能力、时钟域与测量范围](hil-trace-semantics.md)

## 功能职责与范围

Challenge-chain latency instrumentation and percentile statistics.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `StageTrace.trace_id: str`；默认：`未在声明处设置`。
- `StageTrace.case_id: str`；默认：`''`。
- `StageTrace.round_index: int`；默认：`0`。
- `StageTrace.phase: str`；默认：`'measured'`。
- `StageTrace.clock_ns: Callable[[], int]`；默认：`time.perf_counter_ns`。
- `StageTrace.timestamps_ns: dict[str, int]`；默认：`field(default_factory=dict)`。
- `StageTrace.outcome: str | None`；默认：`None`。
- `StageTrace.reason_code: str | None`；默认：`None`。
- `StageTrace.outcome_detail: str | None`；默认：`None`。
- `StageTrace.stage_source: str`；默认：`'INSTRUMENTED'`。
- `StageTrace.clock_domain: str`；默认：`'monotonic_host'`。

## 功能入口：输入、输出与实现说明

### `clock_resolution_ns`

源码位置：[challenge/hil/stages.py 第 63 行](../../../challenge/hil/stages.py#L63)。类型：`FunctionDef`。

```python
clock_resolution_ns() -> float
```

Resolution of the monotonic clock used for every latency mark.

### `percentile`

源码位置：[challenge/hil/stages.py 第 68 行](../../../challenge/hil/stages.py#L68)。类型：`FunctionDef`。

```python
percentile(values: Iterable[float], quantile: float) -> float | None
```

Linear interpolation percentile, matching runtime/latency_trace.py.

### `summarize`

源码位置：[challenge/hil/stages.py 第 84 行](../../../challenge/hil/stages.py#L84)。类型：`FunctionDef`。

```python
summarize(values: Iterable[float]) -> dict[str, float | int | None]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `StageOrderError`

源码位置：[challenge/hil/stages.py 第 98 行](../../../challenge/hil/stages.py#L98)。类型：`ClassDef`。

A mark violated the declared stage order or monotonicity.

### `StageTrace`

源码位置：[challenge/hil/stages.py 第 103 行](../../../challenge/hil/stages.py#L103)。类型：`ClassDef`。

One planner invocation's monotonic timestamps.

Stages may be skipped (a rejected request never reaches ``plan_ready``) but
must never be reordered or stamped with a decreasing clock value.

### `StageTrace.__post_init__`

源码位置：[challenge/hil/stages.py 第 122 行](../../../challenge/hil/stages.py#L122)。类型：`FunctionDef`。

```python
StageTrace.__post_init__(self) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `StageTrace.mark`

源码位置：[challenge/hil/stages.py 第 130 行](../../../challenge/hil/stages.py#L130)。类型：`FunctionDef`。

```python
StageTrace.mark(self, stage: str, timestamp_ns: int | None=None) -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `StageTrace.finish`

源码位置：[challenge/hil/stages.py 第 147 行](../../../challenge/hil/stages.py#L147)。类型：`FunctionDef`。

```python
StageTrace.finish(self, outcome: str, *, reason_code: str | None=None, detail: str | None=None) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `StageTrace.durations_ms`

源码位置：[challenge/hil/stages.py 第 160 行](../../../challenge/hil/stages.py#L160)。类型：`FunctionDef`。

```python
StageTrace.durations_ms(self) -> dict[str, float]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `StageTrace.missing_stages`

源码位置：[challenge/hil/stages.py 第 180 行](../../../challenge/hil/stages.py#L180)。类型：`FunctionDef`。

```python
StageTrace.missing_stages(self) -> tuple[str, ...]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `StageTrace.to_csv_row`

源码位置：[challenge/hil/stages.py 第 183 行](../../../challenge/hil/stages.py#L183)。类型：`FunctionDef`。

```python
StageTrace.to_csv_row(self, *, run_id: str, identity: Mapping[str, str], wall_time_utc: str | None=None) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `StageTrace.to_dict`

源码位置：[challenge/hil/stages.py 第 212 行](../../../challenge/hil/stages.py#L212)。类型：`FunctionDef`。

```python
StageTrace.to_dict(self) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `LatencyCollector`

源码位置：[challenge/hil/stages.py 第 229 行](../../../challenge/hil/stages.py#L229)。类型：`ClassDef`。

Collect finished traces and aggregate them by phase and round.

### `LatencyCollector.__init__`

源码位置：[challenge/hil/stages.py 第 232 行](../../../challenge/hil/stages.py#L232)。类型：`FunctionDef`。

```python
LatencyCollector.__init__(self) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `LatencyCollector.add`

源码位置：[challenge/hil/stages.py 第 235 行](../../../challenge/hil/stages.py#L235)。类型：`FunctionDef`。

```python
LatencyCollector.add(self, trace: StageTrace) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `LatencyCollector.__len__`

源码位置：[challenge/hil/stages.py 第 240 行](../../../challenge/hil/stages.py#L240)。类型：`FunctionDef`。

```python
LatencyCollector.__len__(self) -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `LatencyCollector.traces`

源码位置：[challenge/hil/stages.py 第 243 行](../../../challenge/hil/stages.py#L243)。类型：`FunctionDef`。

```python
LatencyCollector.traces(self) -> tuple[StageTrace, ...]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `LatencyCollector.report`

源码位置：[challenge/hil/stages.py 第 246 行](../../../challenge/hil/stages.py#L246)。类型：`FunctionDef`。

```python
LatencyCollector.report(self, *, run_id: str, identity: Mapping[str, str]) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `LatencyCollector._metrics`

源码位置：[challenge/hil/stages.py 第 279 行](../../../challenge/hil/stages.py#L279)。类型：`FunctionDef`。

```python
LatencyCollector._metrics(self, traces: list[StageTrace]) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `LatencyCollector._outcome_counts`

源码位置：[challenge/hil/stages.py 第 291 行](../../../challenge/hil/stages.py#L291)。类型：`FunctionDef`。

```python
LatencyCollector._outcome_counts(self) -> dict[str, int]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `clock_resolution_ns` 调用：`float`, `time.get_clock_info`.
- `percentile` 调用：`ValueError`, `float`, `int`, `len`, `math.ceil`, `math.floor`, `sorted`.
- `summarize` 调用：`float`, `len`, `max`, `percentile`, `statistics.fmean`.
- `__post_init__` 调用：`ValueError`, `isinstance`.
- `mark` 调用：`StageOrderError`, `ValueError`, `max`, `self.clock_ns`, `type`.
- `finish` 调用：`ValueError`, `isinstance`.
- `missing_stages` 调用：`tuple`.
- `to_csv_row` 调用：`'|'.join`, `datetime.now`, `datetime.now(timezone.utc).isoformat`, `durations.get`, `identity.get`, `row.get`, `self.durations_ms`, `self.missing_stages`, `self.timestamps_ns.get`.
- `to_dict` 调用：`dict`, `list`, `self.durations_ms`, `self.missing_stages`.
- `add` 调用：`ValueError`, `self._traces.append`.
- `__len__` 调用：`len`.
- `traces` 调用：`tuple`.
- `report` 调用：`clock_resolution_ns`, `datetime.now`, `datetime.now(timezone.utc).isoformat`, `dict`, `len`, `self._metrics`, `self._outcome_counts`, `sorted`, `str`, `trace.to_csv_row`.
- `_metrics` 调用：`summarize`, `trace.durations_ms`.
- `_outcome_counts` 调用：`counts.get`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__post_init__`，第 124 行：`ValueError('trace_id must be a non-empty string')`。
- `__post_init__`，第 126 行：`ValueError("phase must be 'warmup' or 'measured'")`。
- `__post_init__`，第 128 行：`ValueError('unsupported stage_source')`。
- `add`，第 237 行：`ValueError('trace must be finished before collection')`。
- `finish`，第 155 行：`ValueError('outcome must be a non-empty string')`。
- `mark`，第 132 行：`ValueError(f'unknown latency stage: {stage!r}')`。
- `mark`，第 134 行：`StageOrderError(f'stage already marked: {stage}')`。
- `mark`，第 137 行：`StageOrderError('timestamp_ns must be a non-negative integer')`。
- `mark`，第 141 行：`StageOrderError(f'{stage} is out of order after {last}')`。
- `mark`，第 143 行：`StageOrderError('timestamps must be non-decreasing')`。
- `percentile`，第 74 行：`ValueError('quantile must be within [0, 1]')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [challenge/hil/columns.py](../../../challenge/hil/columns.py)

静态 import 消费者（含测试）：

- [challenge/hil/__init__.py](../../../challenge/hil/__init__.py)
- [challenge/hil/cli.py](../../../challenge/hil/cli.py)
- [challenge/hil/contract.py](../../../challenge/hil/contract.py)
- [challenge/hil/replay.py](../../../challenge/hil/replay.py)
- [challenge/hil/report.py](../../../challenge/hil/report.py)
- [challenge/hil/rounds.py](../../../challenge/hil/rounds.py)
- [challenge/hil/runtime_adapter.py](../../../challenge/hil/runtime_adapter.py)
- [challenge/hil/stability.py](../../../challenge/hil/stability.py)
- [challenge/hil/tests/fakes.py](../../../challenge/hil/tests/fakes.py)
- [challenge/hil/tests/test_contract.py](../../../challenge/hil/tests/test_contract.py)
- [challenge/hil/tests/test_stages.py](../../../challenge/hil/tests/test_stages.py)

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-hil.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/hil/stages.py`

来源 SHA256：`397eddc12f867e3f6c680d633df519634f8c0db0e18deb475afd77ace1c5d9a6`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `StageTrace.trace_id` | `str` | `无声明默认；构造/赋值方提供` |
| `StageTrace.case_id` | `str` | `''` |
| `StageTrace.round_index` | `int` | `0` |
| `StageTrace.phase` | `str` | `'measured'` |
| `StageTrace.clock_ns` | `Callable[[], int]` | `time.perf_counter_ns` |
| `StageTrace.timestamps_ns` | `dict[str, int]` | `field(default_factory=dict)` |
| `StageTrace.outcome` | `str &#124; None` | `None` |
| `StageTrace.reason_code` | `str &#124; None` | `None` |
| `StageTrace.outcome_detail` | `str &#124; None` | `None` |
| `StageTrace.stage_source` | `str` | `'INSTRUMENTED'` |
| `StageTrace.clock_domain` | `str` | `'monotonic_host'` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `percentile` / 74 | `not 0.0 <= quantile <= 1.0` | `raise ValueError('quantile must be within [0, 1]')` |
| `StageTrace.__post_init__` / 124 | `not isinstance(self.trace_id, str) or not self.trace_id` | `raise ValueError('trace_id must be a non-empty string')` |
| `StageTrace.__post_init__` / 126 | `self.phase not in {'warmup', 'measured'}` | `raise ValueError("phase must be 'warmup' or 'measured'")` |
| `StageTrace.__post_init__` / 128 | `self.stage_source not in {'INSTRUMENTED', 'NOT_INSTRUMENTED', 'PARTIAL'}` | `raise ValueError('unsupported stage_source')` |
| `StageTrace.mark` / 132 | `stage not in STAGE_INDEX` | `raise ValueError(f'unknown latency stage: {stage!r}')` |
| `StageTrace.mark` / 134 | `stage in self.timestamps_ns` | `raise StageOrderError(f'stage already marked: {stage}')` |
| `StageTrace.mark` / 137 | `type(value) is not int or value < 0` | `raise StageOrderError('timestamp_ns must be a non-negative integer')` |
| `StageTrace.mark` / 141 | `self.timestamps_ns AND STAGE_INDEX[stage] <= STAGE_INDEX[last]` | `raise StageOrderError(f'{stage} is out of order after {last}')` |
| `StageTrace.mark` / 143 | `self.timestamps_ns AND value < self.timestamps_ns[last]` | `raise StageOrderError('timestamps must be non-decreasing')` |
| `StageTrace.finish` / 155 | `not isinstance(outcome, str) or not outcome` | `raise ValueError('outcome must be a non-empty string')` |
| `LatencyCollector.add` / 237 | `trace.outcome is None` | `raise ValueError('trace must be finished before collection')` |
