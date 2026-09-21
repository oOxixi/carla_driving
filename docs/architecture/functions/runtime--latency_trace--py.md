# latency_trace：功能记录

上级模块：[模块说明](../modules/vehicle-planner.md) · 实现：[runtime/latency_trace.py](../../../runtime/latency_trace.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [异步等待、旧结果拒绝与多层命令ID](async-plan-dispatch.md)
- [计划可行性校验与内部步骤展开](plan-validation-compilation.md)

## 功能职责与范围

Full-chain monotonic timestamp collection and percentile reporting.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `StageTrace.trace_id: str`；默认：`未在声明处设置`。
- `StageTrace.path_type: str`；默认：`未在声明处设置`。
- `StageTrace.clock_ns: Callable[[], int]`；默认：`time.monotonic_ns`。
- `StageTrace.timestamps_ns: dict[str, int]`；默认：`field(default_factory=dict)`。
- `StageTrace.outcome: str | None`；默认：`None`。
- `StageTrace.reason_code: str | None`；默认：`None`。

## 功能入口：输入、输出与实现说明

<a id="fn--percentile"></a>

### `_percentile`

源码位置：[runtime/latency_trace.py 第 31 行](../../../runtime/latency_trace.py#L31)。类型：`FunctionDef`。

```python
_percentile(values: list[float], quantile: float) -> float | None
```

先排序样本，再按位置(len-1)×q做线性插值，不是最近秩算法；空样本返回 None。调用方传0.95计算p95，单位沿用输入毫秒。

<a id="fn--statistics"></a>

### `_statistics`

源码位置：[runtime/latency_trace.py 第 44 行](../../../runtime/latency_trace.py#L44)。类型：`FunctionDef`。

```python
_statistics(values: list[float]) -> dict[str, float | int | None]
```

汇总 count/mean/p95/p99/max，空集合保留 count=0、其余统计无值；不剔除失败请求或异常长尾，也不做置信区间估计。

<a id="fn-stagetrace"></a>

### `StageTrace`

源码位置：[runtime/latency_trace.py 第 55 行](../../../runtime/latency_trace.py#L55)。类型：`ClassDef`。

One command trace; stages may be skipped but never reordered.

<a id="fn-stagetrace-mark"></a>

### `StageTrace.mark`

源码位置：[runtime/latency_trace.py 第 65 行](../../../runtime/latency_trace.py#L65)。类型：`FunctionDef`。

```python
StageTrace.mark(self, stage: str, *, timestamp_ns: int | None=None) -> int
```

stage 必须在预定义10阶段内，不可重复、倒序或时间回退；timestamp_ns 须非负整数，未传使用单调时钟。允许跳过阶段，缺失阶段不自动补零；不检查是否已经 finish。

<a id="fn-stagetrace-finish"></a>

### `StageTrace.finish`

源码位置：[runtime/latency_trace.py 第 82 行](../../../runtime/latency_trace.py#L82)。类型：`FunctionDef`。

```python
StageTrace.finish(self, outcome: str, *, reason_code: str | None=None) -> None
```

outcome 要求非空字符串，保存 outcome 与 reason_code；可重复调用覆盖终态，没有一次性冻结机制，调用方须控制生命周期。

<a id="fn-stagetrace-durations-ms"></a>

### `StageTrace.durations_ms`

源码位置：[runtime/latency_trace.py 第 88 行](../../../runtime/latency_trace.py#L88)。类型：`FunctionDef`。

```python
StageTrace.durations_ms(self) -> dict[str, float]
```

计算相邻实际记录阶段耗时，并在所需端点存在时计算 e2e/post_nlu/qwen/control 等汇总，纳秒除以1e6。缺端点就没有该项，不伪造0；跳过阶段会形成跨阶段间隔。

<a id="fn-stagetrace-to-dict"></a>

### `StageTrace.to_dict`

源码位置：[runtime/latency_trace.py 第 113 行](../../../runtime/latency_trace.py#L113)。类型：`FunctionDef`。

```python
StageTrace.to_dict(self) -> dict[str, Any]
```

导出 trace_id/path_type、阶段时间戳副本、耗时、终态和原因码；只生成记录，不写文件，也不证明终态已设置。

<a id="fn-latencycollector"></a>

### `LatencyCollector`

源码位置：[runtime/latency_trace.py 第 124 行](../../../runtime/latency_trace.py#L124)。类型：`ClassDef`。

Thread-safe collection of completed command traces.

<a id="fn-latencycollector---init--"></a>

### `LatencyCollector.__init__`

源码位置：[runtime/latency_trace.py 第 127 行](../../../runtime/latency_trace.py#L127)。类型：`FunctionDef`。

```python
LatencyCollector.__init__(self) -> None
```

建立内存记录列表和锁，不创建文件或后台汇总线程；长期运行需要调用方管理记录规模。

<a id="fn-latencycollector-add"></a>

### `LatencyCollector.add`

源码位置：[runtime/latency_trace.py 第 131 行](../../../runtime/latency_trace.py#L131)。类型：`FunctionDef`。

```python
LatencyCollector.add(self, trace: StageTrace) -> None
```

要求 StageTrace 且已经 finish，取其 to_dict 快照后锁内追加；同一 trace_id 可重复加入，不做去重或替换。

<a id="fn-latencycollector-report"></a>

### `LatencyCollector.report`

源码位置：[runtime/latency_trace.py 第 139 行](../../../runtime/latency_trace.py#L139)。类型：`FunctionDef`。

```python
LatencyCollector.report(self) -> dict[str, Any]
```

锁内取记录的 JSON 深复制，汇总总数、按path_type分组及各耗时指标统计，保留含outcome的原始records；耗时包含成功和失败请求，按path_type分组，不按outcome分组或自动限定成功样本，各指标因缺阶段而样本数不同。

<a id="fn-latencycollector-write"></a>

### `LatencyCollector.write`

源码位置：[runtime/latency_trace.py 第 177 行](../../../runtime/latency_trace.py#L177)。类型：`FunctionDef`。

```python
LatencyCollector.write(self, path: str | Path) -> Path
```

创建输出父目录并将 report 直接覆盖写为 JSON，返回 Path；非原子替换，写盘错误向上传播，不自动清空内存记录。

<a id="fn-summarize-latency-records"></a>

### `summarize_latency_records`

源码位置：[runtime/latency_trace.py 第 187 行](../../../runtime/latency_trace.py#L187)。类型：`FunctionDef`。

```python
summarize_latency_records(records: list[Mapping[str, Any]]) -> dict[str, Any]
```

Small utility for existing JSONL timestamps and benchmark scripts.

records中每项需trace_id/path_type；按STAGES顺序取timestamps_ns并int转换后mark，缺outcome用UNKNOWN，再加入collector。不是按原字典顺序检查阶段，也不读取JSONL文件本身；整数转换和mark校验失败继续抛出。

## 内部调用与异常路径

- `_percentile` 调用：`int`, `len`, `math.ceil`, `math.floor`, `sorted`.
- `_statistics` 调用：`_percentile`, `len`, `max`, `statistics.fmean`.
- `summarize_latency_records` 调用：`LatencyCollector`, `StageTrace`, `collector.add`, `collector.report`, `int`, `record.get`, `str`, `trace.finish`, `trace.mark`.
- `mark` 调用：`ValueError`, `max`, `self.clock_ns`, `type`.
- `finish` 调用：`ValueError`, `type`.
- `durations_ms` 调用：`sorted`, `zip`.
- `to_dict` 调用：`dict`, `self.durations_ms`.
- `__init__` 调用：`Lock`.
- `add` 调用：`TypeError`, `ValueError`, `isinstance`, `self._records.append`, `trace.to_dict`.
- `report` 调用：`_statistics`, `datetime.now`, `datetime.now(timezone.utc).isoformat`, `float`, `json.dumps`, `json.loads`, `len`, `sorted`, `str`.
- `write` 调用：`Path`, `json.dumps`, `self.report`, `target.parent.mkdir`, `target.write_text`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `add`，第 133 行：`TypeError('trace must be StageTrace')`。
- `add`，第 135 行：`ValueError('trace must be finished before collection')`。
- `finish`，第 84 行：`ValueError('outcome must be non-empty')`。
- `mark`，第 67 行：`ValueError(f'unknown latency stage: {stage!r}')`。
- `mark`，第 69 行：`ValueError(f'latency stage already marked: {stage}')`。
- `mark`，第 72 行：`ValueError('timestamp_ns must be a non-negative integer')`。
- `mark`，第 76 行：`ValueError(f'latency stage {stage} is out of order after {last_stage}')`。
- `mark`，第 78 行：`ValueError('latency timestamps must be monotonic')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [runtime/__init__.py](../../../runtime/__init__.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-planner.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

<a id="fn-runtime-latency-trace-py"></a>

### `runtime/latency_trace.py`

来源 SHA256：`e5123cbd98fa24b8d75e01967b918b929dc3f421c79a7adcfac2291a4b1b59a4`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `StageTrace.trace_id` | `str` | `无声明默认；构造/赋值方提供` |
| `StageTrace.path_type` | `str` | `无声明默认；构造/赋值方提供` |
| `StageTrace.clock_ns` | `Callable[[], int]` | `time.monotonic_ns` |
| `StageTrace.timestamps_ns` | `dict[str, int]` | `field(default_factory=dict)` |
| `StageTrace.outcome` | `str &#124; None` | `None` |
| `StageTrace.reason_code` | `str &#124; None` | `None` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `StageTrace.mark` / 67 | `stage not in STAGE_INDEX` | `raise ValueError(f'unknown latency stage: {stage!r}')` |
| `StageTrace.mark` / 69 | `stage in self.timestamps_ns` | `raise ValueError(f'latency stage already marked: {stage}')` |
| `StageTrace.mark` / 72 | `type(value) is not int or value < 0` | `raise ValueError('timestamp_ns must be a non-negative integer')` |
| `StageTrace.mark` / 76 | `self.timestamps_ns AND STAGE_INDEX[stage] <= STAGE_INDEX[last_stage]` | `raise ValueError(f'latency stage {stage} is out of order after {last_stage}')` |
| `StageTrace.mark` / 78 | `self.timestamps_ns AND value < self.timestamps_ns[last_stage]` | `raise ValueError('latency timestamps must be monotonic')` |
| `StageTrace.finish` / 84 | `type(outcome) is not str or not outcome` | `raise ValueError('outcome must be non-empty')` |
| `LatencyCollector.add` / 133 | `not isinstance(trace, StageTrace)` | `raise TypeError('trace must be StageTrace')` |
| `LatencyCollector.add` / 135 | `trace.outcome is None` | `raise ValueError('trace must be finished before collection')` |
