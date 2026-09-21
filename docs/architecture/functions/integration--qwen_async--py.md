# qwen_async：功能记录

上级模块：[模块说明](../modules/vehicle-planner.md) · 实现：[integration/qwen_async.py](../../../integration/qwen_async.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [异步等待、旧结果拒绝与多层命令ID](async-plan-dispatch.md)
- [计划可行性校验与内部步骤展开](plan-validation-compilation.md)

## 功能职责与范围

Non-blocking boundary between slow Qwen inference and the CARLA loop.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `AsyncDecisionResult.sequence: int`；默认：`未在声明处设置`。
- `AsyncDecisionResult.status: str`；默认：`未在声明处设置`。
- `AsyncDecisionResult.submitted_sim_time_s: float`；默认：`未在声明处设置`。
- `AsyncDecisionResult.age_s: float`；默认：`未在声明处设置`。
- `AsyncDecisionResult.high_level_command: Mapping[str, Any] | None`；默认：`None`。
- `AsyncDecisionResult.runtime_command: Mapping[str, Any] | None`；默认：`None`。
- `AsyncDecisionResult.error: str | None`；默认：`None`。
- `_Request.sequence: int`；默认：`未在声明处设置`。
- `_Request.context: Any`；默认：`未在声明处设置`。
- `_Request.submitted_sim_time_s: float`；默认：`未在声明处设置`。

## 功能入口：输入、输出与实现说明

<a id="fn-asyncdecisionresult"></a>

### `AsyncDecisionResult`

源码位置：[integration/qwen_async.py 第 19 行](../../../integration/qwen_async.py#L19)。类型：`ClassDef`。

旧remote异步结果：sequence、status、提交仿真秒、age_s、可空高层/运行命令和错误。age由latest更新，不是HTTP耗时。

<a id="fn-asyncdecisionresult-ready"></a>

### `AsyncDecisionResult.ready`

源码位置：[integration/qwen_async.py 第 29 行](../../../integration/qwen_async.py#L29)。类型：`FunctionDef`。

```python
AsyncDecisionResult.ready(self) -> bool
```

仅status恰等READY为True；不在此检查年龄，需经latest处理TTL。

<a id="fn-asyncdecisionresult-watchdog-alerts"></a>

### `AsyncDecisionResult.watchdog_alerts`

源码位置：[integration/qwen_async.py 第 33 行](../../../integration/qwen_async.py#L33)。类型：`FunctionDef`。

```python
AsyncDecisionResult.watchdog_alerts(self) -> tuple[str, ...]
```

Return deterministic fail-closed alerts for every non-ready state.

READY返回空tuple；其他状态调用fail_closed生成告警，未知status会抛错。结果属性不等于车辆已应用安全停车，需要调用方把告警交安全层。

<a id="fn--request"></a>

### `_Request`

源码位置：[integration/qwen_async.py 第 44 行](../../../integration/qwen_async.py#L44)。类型：`ClassDef`。

将递增sequence、context引用与submitted_sim_time_s绑在一起；不深拷贝context。

<a id="fn-asyncqwendecisionbridge"></a>

### `AsyncQwenDecisionBridge`

源码位置：[integration/qwen_async.py 第 50 行](../../../integration/qwen_async.py#L50)。类型：`ClassDef`。

Run one slow high-level inference function outside the control loop.

The queue retains only the newest waiting request. A result is usable only
while its simulation-time TTL is fresh. Errors and stale results never
produce an executable command, so callers can fail closed.

<a id="fn-asyncqwendecisionbridge---init--"></a>

### `AsyncQwenDecisionBridge.__init__`

源码位置：[integration/qwen_async.py 第 59 行](../../../integration/qwen_async.py#L59)。类型：`FunctionDef`。

```python
AsyncQwenDecisionBridge.__init__(self, infer: Callable[[Any], Mapping[str, Any]], *, source_text: Callable[[Any], str] | None=None, ttl_s: float=3.0, max_inference_s: float=5.0, command_ttl_s: float=30.0) -> None
```

infer必须可调用；队列固定1，立即启动daemon。ttl_s默认3仿真秒、max_inference_s默认5墙钟秒、command_ttl_s默认30执行秒；后两者检查有限正数，ttl_s仅类型/正值比较，不能声称同样拒绝NaN。

<a id="fn-asyncqwendecisionbridge-submit"></a>

### `AsyncQwenDecisionBridge.submit`

源码位置：[integration/qwen_async.py 第 107 行](../../../integration/qwen_async.py#L107)。类型：`FunctionDef`。

```python
AsyncQwenDecisionBridge.submit(self, context: Any, *, now_s: float) -> int
```

检查非负有限仿真时间与closed，递增sequence并写PENDING，墙钟预算从提交开始包含排队。等待队列满则替换最旧；正在infer的旧请求不取消，返回序号。

<a id="fn-asyncqwendecisionbridge-latest"></a>

### `AsyncQwenDecisionBridge.latest`

源码位置：[integration/qwen_async.py 第 132 行](../../../integration/qwen_async.py#L132)。类型：`FunctionDef`。

```python
AsyncQwenDecisionBridge.latest(self, *, now_s: float) -> AsyncDecisionResult | None
```

未提交返回None；PENDING墙钟超过max_inference变TIMEOUT并保存，晚返回不可覆盖。READY仿真age>ttl才返回STALE（恰等TTL仍READY）；STALE是返回副本，不改内部READY。年龄下限0。

<a id="fn-asyncqwendecisionbridge-close"></a>

### `AsyncQwenDecisionBridge.close`

源码位置：[integration/qwen_async.py 第 172 行](../../../integration/qwen_async.py#L172)。类型：`FunctionDef`。

```python
AsyncQwenDecisionBridge.close(self, *, timeout_s: float=1.0) -> None
```

closed幂等，放None哨兵、满则淘汰等待请求，join默认最多1s；不会终止执行中的网络/模型调用。

<a id="fn-asyncqwendecisionbridge---enter--"></a>

### `AsyncQwenDecisionBridge.__enter__`

源码位置：[integration/qwen_async.py 第 187 行](../../../integration/qwen_async.py#L187)。类型：`FunctionDef`。

```python
AsyncQwenDecisionBridge.__enter__(self) -> 'AsyncQwenDecisionBridge'
```

返回已启动对象，不重启worker。

<a id="fn-asyncqwendecisionbridge---exit--"></a>

### `AsyncQwenDecisionBridge.__exit__`

源码位置：[integration/qwen_async.py 第 190 行](../../../integration/qwen_async.py#L190)。类型：`FunctionDef`。

```python
AsyncQwenDecisionBridge.__exit__(self, *_: object) -> None
```

close并让原异常继续传播。

<a id="fn-asyncqwendecisionbridge--run"></a>

### `AsyncQwenDecisionBridge._run`

源码位置：[integration/qwen_async.py 第 193 行](../../../integration/qwen_async.py#L193)。类型：`FunctionDef`。

```python
AsyncQwenDecisionBridge._run(self) -> None
```

worker推理→validate_qwen_response→build_high_level_command→A adapter；异常封为ERROR。只有sequence仍最新且状态仍PENDING才写回，旧结果/超时结果被丢弃；命令TTL采用command_ttl_s。

<a id="fn--sim-time"></a>

### `_sim_time`

源码位置：[integration/qwen_async.py 第 237 行](../../../integration/qwen_async.py#L237)。类型：`FunctionDef`。

```python
_sim_time(value: float) -> float
```

精确int/float（bool拒绝），转float且须有限非负；错误类型TypeError，其余ValueError。

## 内部调用与异常路径

- `_sim_time` 调用：`TypeError`, `ValueError`, `float`, `math.isfinite`, `type`.
- `watchdog_alerts` 调用：`fail_closed`.
- `__init__` 调用：`Lock`, `Queue`, `Thread`, `TypeError`, `ValueError`, `callable`, `float`, `getattr`, `isinstance`, `math.isfinite`, `self._thread.start`, `str`, `type`.
- `submit` 调用：`AsyncDecisionResult`, `RuntimeError`, `_Request`, `_sim_time`, `self._queue.get_nowait`, `self._queue.put_nowait`, `time.monotonic`.
- `latest` 调用：`AsyncDecisionResult`, `_sim_time`, `max`, `time.monotonic`.
- `close` 调用：`float`, `max`, `self._queue.get_nowait`, `self._queue.put_nowait`, `self._thread.join`.
- `__exit__` 调用：`self.close`.
- `_run` 调用：`AsyncDecisionResult`, `HighLevelCommandAdapter`, `ValueError`, `adapter.adapt`, `build_high_level_command`, `runtime.get`, `self._infer`, `self._queue.get`, `self._source_text`, `type`, `validate_qwen_response`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__init__`，第 69 行：`TypeError('infer must be callable')`。
- `__init__`，第 71 行：`ValueError('ttl_s must be positive')`。
- `__init__`，第 78 行：`ValueError('max_inference_s must be finite and positive')`。
- `__init__`，第 85 行：`ValueError('command_ttl_s must be finite and positive')`。
- `_run`，第 210 行：`ValueError('Qwen command failed A boundary validation')`。
- `_sim_time`，第 239 行：`TypeError('now_s must be numeric')`。
- `_sim_time`，第 242 行：`ValueError('now_s must be finite and non-negative')`。
- `submit`，第 111 行：`RuntimeError('Qwen decision bridge is closed')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [car_control_A/high_level_command.py](../../../car_control_A/high_level_command.py)
- [integration/qwen_boundary.py](../../../integration/qwen_boundary.py)
- [integration/qwen_command_adapter.py](../../../integration/qwen_command_adapter.py)

静态 import 消费者（含测试）：

- [integration/__init__.py](../../../integration/__init__.py)
- [integration/carla_runner.py](../../../integration/carla_runner.py)
- [integration/tests/test_qwen_async.py](../../../integration/tests/test_qwen_async.py)
- [integration/tests/test_qwen_async_supersede.py](../../../integration/tests/test_qwen_async_supersede.py)
- [integration/tests/test_qwen_async_timeout.py](../../../integration/tests/test_qwen_async_timeout.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-planner.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

<a id="fn-integration-qwen-async-py"></a>

### `integration/qwen_async.py`

来源 SHA256：`8b07006b19e3778cb222088a3341119ec0eacebd187e243c3d8c559bbd1c313f`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `AsyncDecisionResult.sequence` | `int` | `无声明默认；构造/赋值方提供` |
| `AsyncDecisionResult.status` | `str` | `无声明默认；构造/赋值方提供` |
| `AsyncDecisionResult.submitted_sim_time_s` | `float` | `无声明默认；构造/赋值方提供` |
| `AsyncDecisionResult.age_s` | `float` | `无声明默认；构造/赋值方提供` |
| `AsyncDecisionResult.high_level_command` | `Mapping[str, Any] &#124; None` | `None` |
| `AsyncDecisionResult.runtime_command` | `Mapping[str, Any] &#124; None` | `None` |
| `AsyncDecisionResult.error` | `str &#124; None` | `None` |
| `_Request.sequence` | `int` | `无声明默认；构造/赋值方提供` |
| `_Request.context` | `Any` | `无声明默认；构造/赋值方提供` |
| `_Request.submitted_sim_time_s` | `float` | `无声明默认；构造/赋值方提供` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `AsyncQwenDecisionBridge.__init__` / 69 | `not callable(infer)` | `raise TypeError('infer must be callable')` |
| `AsyncQwenDecisionBridge.__init__` / 71 | `type(ttl_s) not in (int, float) or ttl_s <= 0.0` | `raise ValueError('ttl_s must be positive')` |
| `AsyncQwenDecisionBridge.__init__` / 78 | `type(max_inference_s) not in (int, float) or isinstance(max_inference_s, bool) or (not math.isfinite(float(max_inference_s))) or (max_inference_s <= 0.0)` | `raise ValueError('max_inference_s must be finite and positive')` |
| `AsyncQwenDecisionBridge.__init__` / 85 | `type(command_ttl_s) not in (int, float) or isinstance(command_ttl_s, bool) or (not math.isfinite(float(command_ttl_s))) or (command_ttl_s <= 0.0)` | `raise ValueError('command_ttl_s must be finite and positive')` |
| `AsyncQwenDecisionBridge.submit` / 111 | `self._closed` | `raise RuntimeError('Qwen decision bridge is closed')` |
| `AsyncQwenDecisionBridge._run` / 210 | `runtime.get('status') != 'valid'` | `raise ValueError('Qwen command failed A boundary validation')` |
| `_sim_time` / 239 | `type(value) not in (int, float)` | `raise TypeError('now_s must be numeric')` |
| `_sim_time` / 242 | `not math.isfinite(result) or result < 0.0` | `raise ValueError('now_s must be finite and non-negative')` |
