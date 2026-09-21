# runtime：功能记录

上级模块：[模块说明](../modules/support-qwen.md) · 实现：[qwen_service/runtime.py](../../../qwen_service/runtime.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [服务模式、动作组装与health](qwen-service-semantics.md)

## 功能职责与范围

Bounded execution and observable metrics for Qwen inference.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `ServiceBusyError`

源码位置：[qwen_service/runtime.py 第 21 行](../../../qwen_service/runtime.py#L21)。类型：`ClassDef`。

Raised when every bounded model worker is occupied.

### `InferenceTimeoutError`

源码位置：[qwen_service/runtime.py 第 25 行](../../../qwen_service/runtime.py#L25)。类型：`ClassDef`。

Raised when a request exceeds its wall-clock inference deadline.

### `ModelInferenceError`

源码位置：[qwen_service/runtime.py 第 29 行](../../../qwen_service/runtime.py#L29)。类型：`ClassDef`。

Raised when the model or strict output boundary rejects a request.

### `QwenServiceRuntime`

源码位置：[qwen_service/runtime.py 第 33 行](../../../qwen_service/runtime.py#L33)。类型：`ClassDef`。

Keep one loaded model behind a bounded, fail-closed request boundary.

### `QwenServiceRuntime.__init__`

源码位置：[qwen_service/runtime.py 第 36 行](../../../qwen_service/runtime.py#L36)。类型：`FunctionDef`。

```python
QwenServiceRuntime.__init__(self, adapter: object, *, model_name: str, max_concurrency: int=1, timeout_s: float=5.0, metrics_window: int=1000, gpu_stats: Callable[[], Mapping[str, Any]] | None=None, clock: Callable[[], float]=time.monotonic) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `QwenServiceRuntime.health`

源码位置：[qwen_service/runtime.py 第 87 行](../../../qwen_service/runtime.py#L87)。类型：`FunctionDef`。

```python
QwenServiceRuntime.health(self) -> dict[str, object]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `QwenServiceRuntime.infer`

源码位置：[qwen_service/runtime.py 第 97 行](../../../qwen_service/runtime.py#L97)。类型：`FunctionDef`。

```python
QwenServiceRuntime.infer(self, payload: Mapping[str, object]) -> dict[str, object]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `QwenServiceRuntime.metrics`

源码位置：[qwen_service/runtime.py 第 140 行](../../../qwen_service/runtime.py#L140)。类型：`FunctionDef`。

```python
QwenServiceRuntime.metrics(self) -> dict[str, object]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `QwenServiceRuntime.close`

源码位置：[qwen_service/runtime.py 第 172 行](../../../qwen_service/runtime.py#L172)。类型：`FunctionDef`。

```python
QwenServiceRuntime.close(self) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `QwenServiceRuntime._record`

源码位置：[qwen_service/runtime.py 第 182 行](../../../qwen_service/runtime.py#L182)。类型：`FunctionDef`。

```python
QwenServiceRuntime._record(self, outcome: str, elapsed_ms: float) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `QwenServiceRuntime._release_slot`

源码位置：[qwen_service/runtime.py 第 194 行](../../../qwen_service/runtime.py#L194)。类型：`FunctionDef`。

```python
QwenServiceRuntime._release_slot(self, _future: Future[object]) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_parse_context`

源码位置：[qwen_service/runtime.py 第 200 行](../../../qwen_service/runtime.py#L200)。类型：`FunctionDef`。

```python
_parse_context(payload: Mapping[str, object]) -> QwenInputContext
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_latency_summary`

源码位置：[qwen_service/runtime.py 第 236 行](../../../qwen_service/runtime.py#L236)。类型：`FunctionDef`。

```python
_latency_summary(values: list[float]) -> dict[str, object]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_percentile`

源码位置：[qwen_service/runtime.py 第 255 行](../../../qwen_service/runtime.py#L255)。类型：`FunctionDef`。

```python
_percentile(ordered: list[float], quantile: float) -> float
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_torch_gpu_stats`

源码位置：[qwen_service/runtime.py 第 267 行](../../../qwen_service/runtime.py#L267)。类型：`FunctionDef`。

```python
_torch_gpu_stats() -> dict[str, object]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `_parse_context` 调用：`QwenInputContext`, `TypeError`, `ValueError`, `isinstance`, `set`, `sorted`.
- `_latency_summary` 调用：`_percentile`, `len`, `round`, `sorted`, `sum`.
- `_percentile` 调用：`len`, `math.ceil`, `math.floor`.
- `_torch_gpu_stats` 调用：`round`, `torch.cuda.current_device`, `torch.cuda.get_device_name`, `torch.cuda.is_available`, `torch.cuda.max_memory_allocated`, `torch.cuda.memory_allocated`, `torch.cuda.memory_reserved`.
- `__init__` 调用：`BoundedSemaphore`, `Lock`, `ThreadPoolExecutor`, `TypeError`, `ValueError`, `callable`, `clock`, `deque`, `float`, `getattr`, `isinstance`, `math.isfinite`, `model_name.strip`, `type`.
- `infer` 调用：`InferenceTimeoutError`, `ModelInferenceError`, `RuntimeError`, `ServiceBusyError`, `_parse_context`, `future.add_done_callback`, `future.result`, `round`, `self._clock`, `self._executor.submit`, `self._record`, `self._release_slot`, `self._slots.acquire`, `type`, `validate_qwen_response`.
- `metrics` 调用：`_latency_summary`, `dict`, `list`, `max`, `round`, `self._clock`, `self._gpu_stats`, `type`.
- `close` 调用：`callable`, `close`, `getattr`, `self._executor.shutdown`.
- `_record` 调用：`ValueError`, `max`, `self._latencies_ms.append`.
- `_release_slot` 调用：`self._slots.release`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__init__`，第 49 行：`TypeError('adapter must provide infer(context)')`。
- `__init__`，第 51 行：`ValueError('model_name must be a non-empty string')`。
- `__init__`，第 53 行：`ValueError('max_concurrency must be a positive integer')`。
- `__init__`，第 60 行：`ValueError('timeout_s must be finite and positive')`。
- `__init__`，第 62 行：`ValueError('metrics_window must be a positive integer')`。
- `_parse_context`，第 202 行：`TypeError('request body must be a JSON object')`。
- `_parse_context`，第 216 行：`ValueError(f'request fields mismatch; missing={sorted(required - fields)}, unknown={sorted(fields - required)}')`。
- `_parse_context`，第 221 行：`ValueError(f'schema_version must be {QWEN_BOUNDARY_SCHEMA_VERSION}')`。
- `_record`，第 191 行：`ValueError(f'unsupported outcome: {outcome}')`。
- `infer`，第 101 行：`RuntimeError('Qwen service runtime is closed')`。
- `infer`，第 106 行：`ServiceBusyError('all Qwen inference slots are occupied')`。
- `infer`，第 119 行：`InferenceTimeoutError(f'Qwen inference exceeded {self._timeout_s:.3f}s')`。
- `infer`，第 126 行：`ModelInferenceError(f'{type(error).__name__}: {error}')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [integration/qwen_boundary.py](../../../integration/qwen_boundary.py)

静态 import 消费者（含测试）：

- [qwen_service/tests/test_runtime.py](../../../qwen_service/tests/test_runtime.py)
- [qwen_service/tests/test_server.py](../../../qwen_service/tests/test_server.py)

## 后续修改需要一起阅读

- [上级模块](../modules/support-qwen.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `qwen_service/runtime.py`

来源 SHA256：`3fa489772d095fb58b99b6fbe717f08d19cddaf2cf90398566135fedacd57f0b`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `QwenServiceRuntime.__init__` / 49 | `not callable(infer)` | `raise TypeError('adapter must provide infer(context)')` |
| `QwenServiceRuntime.__init__` / 51 | `type(model_name) is not str or not model_name.strip()` | `raise ValueError('model_name must be a non-empty string')` |
| `QwenServiceRuntime.__init__` / 53 | `type(max_concurrency) is not int or max_concurrency < 1` | `raise ValueError('max_concurrency must be a positive integer')` |
| `QwenServiceRuntime.__init__` / 60 | `type(timeout_s) not in (int, float) or isinstance(timeout_s, bool) or (not math.isfinite(float(timeout_s))) or (float(timeout_s) <= 0.0)` | `raise ValueError('timeout_s must be finite and positive')` |
| `QwenServiceRuntime.__init__` / 62 | `type(metrics_window) is not int or metrics_window < 1` | `raise ValueError('metrics_window must be a positive integer')` |
| `QwenServiceRuntime.infer` / 101 | `self._closed` | `raise RuntimeError('Qwen service runtime is closed')` |
| `QwenServiceRuntime.infer` / 106 | `not self._slots.acquire(blocking=False)` | `raise ServiceBusyError('all Qwen inference slots are occupied')` |
| `QwenServiceRuntime.infer` / 119 | `except FutureTimeoutError` | `raise InferenceTimeoutError(f'Qwen inference exceeded {self._timeout_s:.3f}s') from error` |
| `QwenServiceRuntime.infer` / 126 | `except Exception` | `raise ModelInferenceError(f'{type(error).__name__}: {error}') from error` |
| `QwenServiceRuntime._record` / 191 | `NOT (outcome == 'succeeded') AND NOT (outcome == 'failed') AND NOT (outcome == 'timed_out')` | `raise ValueError(f'unsupported outcome: {outcome}')` |
| `_parse_context` / 202 | `not isinstance(payload, Mapping)` | `raise TypeError('request body must be a JSON object')` |
| `_parse_context` / 216 | `fields != required` | `raise ValueError(f'request fields mismatch; missing={sorted(required - fields)}, unknown={sorted(fields - required)}')` |
| `_parse_context` / 221 | `payload['schema_version'] != QWEN_BOUNDARY_SCHEMA_VERSION` | `raise ValueError(f'schema_version must be {QWEN_BOUNDARY_SCHEMA_VERSION}')` |
