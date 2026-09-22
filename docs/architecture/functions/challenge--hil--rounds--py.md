# rounds：功能记录

上级模块：[模块说明](../modules/challenge-hil.md) · 实现：[challenge/hil/rounds.py](../../../challenge/hil/rounds.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [Adapter能力、时钟域与测量范围](hil-trace-semantics.md)

## 功能职责与范围

Repeat a frozen configuration several times and keep every raw sample.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `RoundResult.round_index: int`；默认：`未在声明处设置`。
- `RoundResult.case_count: int`；默认：`未在声明处设置`。
- `RoundResult.ready: int`；默认：`未在声明处设置`。
- `RoundResult.structural_pass: int`；默认：`未在声明处设置`。
- `RoundResult.started_at_utc: str`；默认：`未在声明处设置`。
- `RoundResult.duration_s: float`；默认：`未在声明处设置`。
- `RoundResult.telemetry: dict[str, Any]`；默认：`未在声明处设置`。
- `RoundResult.error: str | None`；默认：`None`。
- `RunResult.collector: LatencyCollector`；默认：`field(default_factory=LatencyCollector)`。
- `RunResult.replay_rows: list[dict[str, Any]]`；默认：`field(default_factory=list)`。
- `RunResult.plan_rows: list[dict[str, Any]]`；默认：`field(default_factory=list)`。
- `RunResult.rounds: list[RoundResult]`；默认：`field(default_factory=list)`。
- `RunResult.memory_rows: list[dict[str, Any]]`；默认：`field(default_factory=list)`。
- `RunResult.power_rows: list[dict[str, Any]]`；默认：`field(default_factory=list)`。
- `RunResult.utilization_rows: list[dict[str, Any]]`；默认：`field(default_factory=list)`。
- `RunResult.telemetry_errors: list[str]`；默认：`field(default_factory=list)`。
- `RunResult.warmup_traces: int`；默认：`0`。

## 功能入口：输入、输出与实现说明

### `RoundResult`

源码位置：[challenge/hil/rounds.py 第 17 行](../../../challenge/hil/rounds.py#L17)。类型：`ClassDef`。

`RoundResult` HIL协议类，封装runtime、能力、身份、trace、回放、轮次或采样状态；默认字段不是实测结果，必须随证据序列化。

### `RoundResult.to_dict`

源码位置：[challenge/hil/rounds.py 第 27 行](../../../challenge/hil/rounds.py#L27)。类型：`FunctionDef`。

```python
RoundResult.to_dict(self) -> dict[str, Any]
```

`to_dict` 构造或汇总HIL身份、阶段、统计、环境或报告字段；计算口径依赖有效样本和单一时钟域，UNKNOWN与缺测需原样保留。

### `RunResult`

源码位置：[challenge/hil/rounds.py 第 41 行](../../../challenge/hil/rounds.py#L41)。类型：`ClassDef`。

`RunResult` HIL协议类，封装runtime、能力、身份、trace、回放、轮次或采样状态；默认字段不是实测结果，必须随证据序列化。

### `RunResult.summary`

源码位置：[challenge/hil/rounds.py 第 52 行](../../../challenge/hil/rounds.py#L52)。类型：`FunctionDef`。

```python
RunResult.summary(self) -> dict[str, Any]
```

`summary` 构造或汇总HIL身份、阶段、统计、环境或报告字段；计算口径依赖有效样本和单一时钟域，UNKNOWN与缺测需原样保留。

### `run_rounds`

源码位置：[challenge/hil/rounds.py 第 68 行](../../../challenge/hil/rounds.py#L68)。类型：`FunctionDef`。

```python
run_rounds(runtime: PlannerRuntime, cases: Sequence[ReplayCase], *, run_id: str, rounds: int=3, warmup: int=5, telemetry: TelemetrySpec | None=None, progress: Callable[[str], None] | None=None) -> RunResult
```

Warm up once, then run `rounds` identical measurement windows.

### `run_rounds.emit`

源码位置：[challenge/hil/rounds.py 第 83 行](../../../challenge/hil/rounds.py#L83)。类型：`FunctionDef`。

```python
run_rounds.emit(message: str) -> None
```

`emit` 写出冻结快照、handoff、trace、遥测或报告产物；文件必须绑定候选身份、输入哈希和环境，写盘成功不是Gate通过。

## 内部调用与异常路径

- `run_rounds` 调用：`BackgroundMonitor`, `RoundResult`, `RunResult`, `ValueError`, `datetime.now`, `datetime.now(timezone.utc).isoformat`, `emit`, `int`, `len`, `min`, `monitor.start`, `monitor.stop`, `monitor.summary`, `progress`, `range`, `replay.summary.get`, `result.collector.add`, `result.memory_rows.extend`, `result.plan_rows.extend`, `result.power_rows.extend`, `result.replay_rows.extend`, `result.rounds.append`, `result.telemetry_errors.extend`, `result.utilization_rows.extend`, `run_replay`, `runtime.infer`, `time.monotonic`, `type`.
- `summary` 调用：`item.to_dict`, `len`, `self.collector.traces`, `sum`.
- `emit` 调用：`progress`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `run_rounds`，第 80 行：`ValueError('rounds must be >= 1')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [challenge/hil/replay.py](../../../challenge/hil/replay.py)
- [challenge/hil/runtime_adapter.py](../../../challenge/hil/runtime_adapter.py)
- [challenge/hil/samplers.py](../../../challenge/hil/samplers.py)
- [challenge/hil/stages.py](../../../challenge/hil/stages.py)

静态 import 消费者（含测试）：

- [challenge/hil/cli.py](../../../challenge/hil/cli.py)

## 后续修改需要一起阅读

- [上级模块](../modules/challenge-hil.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `challenge/hil/rounds.py`

来源 SHA256：`ca9f945dcd4ee0b4d01c7f5759347feff55ae3a62a85dbafd59c942bb8f9b1f0`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `RoundResult.round_index` | `int` | `无声明默认；构造/赋值方提供` |
| `RoundResult.case_count` | `int` | `无声明默认；构造/赋值方提供` |
| `RoundResult.ready` | `int` | `无声明默认；构造/赋值方提供` |
| `RoundResult.structural_pass` | `int` | `无声明默认；构造/赋值方提供` |
| `RoundResult.started_at_utc` | `str` | `无声明默认；构造/赋值方提供` |
| `RoundResult.duration_s` | `float` | `无声明默认；构造/赋值方提供` |
| `RoundResult.telemetry` | `dict[str, Any]` | `无声明默认；构造/赋值方提供` |
| `RoundResult.error` | `str &#124; None` | `None` |
| `RunResult.collector` | `LatencyCollector` | `field(default_factory=LatencyCollector)` |
| `RunResult.replay_rows` | `list[dict[str, Any]]` | `field(default_factory=list)` |
| `RunResult.plan_rows` | `list[dict[str, Any]]` | `field(default_factory=list)` |
| `RunResult.rounds` | `list[RoundResult]` | `field(default_factory=list)` |
| `RunResult.memory_rows` | `list[dict[str, Any]]` | `field(default_factory=list)` |
| `RunResult.power_rows` | `list[dict[str, Any]]` | `field(default_factory=list)` |
| `RunResult.utilization_rows` | `list[dict[str, Any]]` | `field(default_factory=list)` |
| `RunResult.telemetry_errors` | `list[str]` | `field(default_factory=list)` |
| `RunResult.warmup_traces` | `int` | `0` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `run_rounds` / 80 | `rounds < 1` | `raise ValueError('rounds must be >= 1')` |
