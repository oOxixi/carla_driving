# qwen_boundary：功能记录

上级模块：[模块说明](../modules/vehicle-planner.md) · 实现：[integration/qwen_boundary.py](../../../integration/qwen_boundary.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [异步等待、旧结果拒绝与多层命令ID](async-plan-dispatch.md)
- [计划可行性校验与内部步骤展开](plan-validation-compilation.md)

## 功能职责与范围

Strict CARLA-independent request/response boundary for Qwen decisions.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `QwenInputContext.request_id: str`；默认：`未在声明处设置`。
- `QwenInputContext.frame: int`；默认：`未在声明处设置`。
- `QwenInputContext.sim_time_s: float`；默认：`未在声明处设置`。
- `QwenInputContext.voice_command: str`；默认：`未在声明处设置`。
- `QwenInputContext.rgb_ref: str | None`；默认：`未在声明处设置`。
- `QwenInputContext.scene_state: Mapping[str, Any]`；默认：`未在声明处设置`。
- `QwenInputContext.perception: Mapping[str, Any]`；默认：`未在声明处设置`。
- `QwenInputContext.safety_state: Mapping[str, Any]`；默认：`未在声明处设置`。
- `QwenBoundaryFailure.status: str`；默认：`未在声明处设置`。
- `QwenBoundaryFailure.error: str`；默认：`未在声明处设置`。
- `QwenBoundaryFailure.watchdog_alerts: tuple[str, ...]`；默认：`未在声明处设置`。

## 功能入口：输入、输出与实现说明

<a id="fn-qweninputcontext"></a>

### `QwenInputContext`

源码位置：[integration/qwen_boundary.py 第 27 行](../../../integration/qwen_boundary.py#L27)。类型：`ClassDef`。

JSON-safe multimodal context passed to a Qwen adapter.

``rgb_ref`` identifies an image owned by the caller.  Keeping binary image
data outside this contract makes logging/replay deterministic while a real
model adapter may resolve the reference to pixels.

<a id="fn-qweninputcontext---post-init--"></a>

### `QwenInputContext.__post_init__`

源码位置：[integration/qwen_boundary.py 第 44 行](../../../integration/qwen_boundary.py#L44)。类型：`FunctionDef`。

```python
QwenInputContext.__post_init__(self) -> None
```

校验 request_id 为去空白非空字符串、frame 为非负整数（拒绝 bool）、sim_time_s 为有限非负秒数；voice_command 必须为字符串，rgb_ref 为非空字符串或 None。scene_state/perception/safety_state 经严格 JSON 检查后包装为 MappingProxyType；只保护顶层，嵌套对象仍与调用方共享，不是深度不可变快照。

<a id="fn-qweninputcontext-to-payload"></a>

### `QwenInputContext.to_payload`

源码位置：[integration/qwen_boundary.py 第 73 行](../../../integration/qwen_boundary.py#L73)。类型：`FunctionDef`。

```python
QwenInputContext.to_payload(self) -> dict[str, Any]
```

返回 HTTP/日志可序列化字典，保留 frame、仿真秒数和图像引用；三个状态映射各做顶层 dict 拷贝，嵌套对象不深复制，也不读取图像文件。

<a id="fn-qwenboundaryfailure"></a>

### `QwenBoundaryFailure`

源码位置：[integration/qwen_boundary.py 第 88 行](../../../integration/qwen_boundary.py#L88)。类型：`ClassDef`。

Fail-closed signal consumed by the deterministic control/watchdog path.

<a id="fn-qwenboundaryfailure---post-init--"></a>

### `QwenBoundaryFailure.__post_init__`

源码位置：[integration/qwen_boundary.py 第 95 行](../../../integration/qwen_boundary.py#L95)。类型：`FunctionDef`。

```python
QwenBoundaryFailure.__post_init__(self) -> None
```

status 仅允许 PENDING/TIMEOUT/STALE/ERROR；error 必须为非空字符串；watchdog_alerts 注解为 tuple，但运行时仅检查 truthy，不强制容器和元素类型。此处不逐个检查告警元素类型，不产生车辆控制量。

<a id="fn-validate-qwen-response"></a>

### `validate_qwen_response`

源码位置：[integration/qwen_boundary.py 第 104 行](../../../integration/qwen_boundary.py#L104)。类型：`FunctionDef`。

```python
validate_qwen_response(payload: object) -> dict[str, Any]
```

Parse and strictly normalize one high-level Qwen decision.

A single JSON-only Markdown fence is normalized because Qwen2.5-VL may
add that wrapper even when explicitly asked for raw JSON.  Extra prose,
multiple fences, unknown fields and low-level controls remain rejected.
The returned plain dict is safe to pass to the Day22 command adapter.

必填action/confidence/requires_confirmation；仅START/STOP/SLOW_DOWN/SET_SPEED/EMERGENCY_STOP，confidence有限[0,1]，确认必须exact bool。速度有限[0,50]m/s，SET_SPEED必须提供；STOP/EMERGENCY_STOP的显式0速度被去掉，非零拒绝，START不能带速度。可选reason_zh/decision_source/target_track_id须非空文本，visual_valid须bool；目标是否实际存在由Strict适配器另查，不在此函数完成。

<a id="fn--unwrap-single-json-fence"></a>

### `_unwrap_single_json_fence`

源码位置：[integration/qwen_boundary.py 第 178 行](../../../integration/qwen_boundary.py#L178)。类型：`FunctionDef`。

```python
_unwrap_single_json_fence(payload: str) -> str
```

仅剥除包住整个响应的一层 JSON Markdown fence；发现嵌套 fence 抛 ValueError。不是从解释文字中搜索 JSON；最终结构仍由 validate_qwen_response 校验。

<a id="fn-fail-closed"></a>

### `fail_closed`

源码位置：[integration/qwen_boundary.py 第 192 行](../../../integration/qwen_boundary.py#L192)。类型：`FunctionDef`。

```python
fail_closed(status: str, error: str) -> QwenBoundaryFailure
```

Convert a non-ready Qwen state into a deterministic watchdog signal.

status strip/upper后按PENDING→QWEN_PENDING、TIMEOUT→QWEN_TIMEOUT、STALE→QWEN_STALE、ERROR→QWEN_ERROR映射单告警tuple，未知值抛ValueError。error转str且空时用状态文本；只返回边界信号，不直接控制车辆。

<a id="fn--json-mapping"></a>

### `_json_mapping`

源码位置：[integration/qwen_boundary.py 第 208 行](../../../integration/qwen_boundary.py#L208)。类型：`FunctionDef`。

```python
_json_mapping(name: str, value: Mapping[str, Any]) -> dict[str, Any]
```

要求 Mapping 且顶层键全为字符串，以 allow_nan=False 的 JSON 序列化拒绝非 JSON 对象和非有限数，再返回顶层 dict；没有 JSON 往返深拷贝，嵌套引用仍共享。

<a id="fn--nonempty-text"></a>

### `_nonempty_text`

源码位置：[integration/qwen_boundary.py 第 219 行](../../../integration/qwen_boundary.py#L219)。类型：`FunctionDef`。

```python
_nonempty_text(value: object, name: str) -> str
```

要求字符串且 strip 后非空，返回去空白文本，否则按字段名抛 TypeError/ValueError。

<a id="fn--bounded-number"></a>

### `_bounded_number`

源码位置：[integration/qwen_boundary.py 第 225 行](../../../integration/qwen_boundary.py#L225)。类型：`FunctionDef`。

```python
_bounded_number(value: object, name: str, minimum: float, maximum: float) -> float
```

拒绝 bool 和非 int/float，要求有限且位于给定闭区间，返回 float。上下界单位来自调用字段，例如置信度无量纲、速度 m/s。

## 内部调用与异常路径

- `validate_qwen_response` 调用：`','.join`, `FORBIDDEN_LOW_LEVEL_FIELDS.intersection`, `TypeError`, `ValueError`, `_bounded_number`, `_nonempty_text`, `_nonempty_text(payload['action'], 'action').upper`, `_unwrap_single_json_fence`, `isinstance`, `json.loads`, `payload.get`, `set`, `sorted`, `type`.
- `_unwrap_single_json_fence` 调用：`ValueError`, `match.group`, `match.group('body').strip`, `payload.strip`, `re.fullmatch`, `stripped.startswith`.
- `fail_closed` 调用：`QwenBoundaryFailure`, `ValueError`, `str`, `str(status).strip`, `str(status).strip().upper`.
- `_json_mapping` 调用：`TypeError`, `ValueError`, `any`, `dict`, `json.dumps`, `type`.
- `_nonempty_text` 调用：`ValueError`, `type`, `value.strip`.
- `_bounded_number` 调用：`TypeError`, `ValueError`, `float`, `isinstance`, `math.isfinite`, `type`.
- `__post_init__` 调用：`MappingProxyType`, `TypeError`, `ValueError`, `_json_mapping`, `float`, `getattr`, `isinstance`, `math.isfinite`, `object.__setattr__`, `self.request_id.strip`, `self.rgb_ref.strip`, `type`.
- `to_payload` 调用：`dict`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__post_init__`，第 46 行：`ValueError('request_id must be a non-empty string')`。
- `__post_init__`，第 48 行：`ValueError('frame must be a non-negative integer')`。
- `__post_init__`，第 55 行：`ValueError('sim_time_s must be finite and non-negative')`。
- `__post_init__`，第 57 行：`TypeError('voice_command must be a string')`。
- `__post_init__`，第 61 行：`ValueError('rgb_ref must be a non-empty string or None')`。
- `__post_init__`，第 65 行：`TypeError(f'{name} must be a mapping')`。
- `__post_init__`，第 97 行：`ValueError('unsupported Qwen failure status')`。
- `__post_init__`，第 99 行：`ValueError('error must be non-empty')`。
- `__post_init__`，第 101 行：`ValueError('fail-closed result requires a watchdog alert')`。
- `_bounded_number`，第 227 行：`TypeError(f'{name} must be numeric')`。
- `_bounded_number`，第 230 行：`ValueError(f'{name} must be finite and in [{minimum}, {maximum}]')`。
- `_json_mapping`，第 211 行：`TypeError(f'{name} keys must be strings')`。
- `_json_mapping`，第 215 行：`ValueError(f'{name} must contain JSON-safe finite values')`。
- `_nonempty_text`，第 221 行：`ValueError(f'{name} must be a non-empty string')`。
- `_unwrap_single_json_fence`，第 188 行：`ValueError('Qwen response must be one JSON object without prose')`。
- `fail_closed`，第 204 行：`ValueError(f'unsupported Qwen failure status: {status!r}')`。
- `validate_qwen_response`，第 117 行：`ValueError('Qwen response must be one JSON object without prose')`。
- `validate_qwen_response`，第 119 行：`TypeError('Qwen response must be a mapping or JSON object string')`。
- `validate_qwen_response`，第 123 行：`ValueError('Qwen response contains forbidden low-level fields: ' + ','.join(sorted(forbidden)))`。
- `validate_qwen_response`，第 130 行：`ValueError(f'Qwen response fields mismatch; missing={sorted(missing)}, unknown={sorted(unknown)}')`。
- `validate_qwen_response`，第 137 行：`ValueError(f'unsupported Qwen action: {action}')`。
- `validate_qwen_response`，第 141 行：`TypeError('requires_confirmation must be bool')`。
- `validate_qwen_response`，第 150 行：`ValueError('SET_SPEED requires target_speed_mps')`。
- `validate_qwen_response`，第 161 行：`ValueError(f'{action} must not include target_speed_mps')`。
- `validate_qwen_response`，第 173 行：`TypeError('visual_valid must be bool')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [car_control_A/high_level_command.py](../../../car_control_A/high_level_command.py)
- [integration/qwen_command_adapter.py](../../../integration/qwen_command_adapter.py)

静态 import 消费者（含测试）：

- [integration/__init__.py](../../../integration/__init__.py)
- [integration/carla_runner.py](../../../integration/carla_runner.py)
- [integration/offline_replay.py](../../../integration/offline_replay.py)
- [integration/qwen_async.py](../../../integration/qwen_async.py)
- [integration/qwen_remote_backend.py](../../../integration/qwen_remote_backend.py)
- [integration/qwen_service_client.py](../../../integration/qwen_service_client.py)
- [integration/qwen_vl_adapter.py](../../../integration/qwen_vl_adapter.py)
- [integration/scenario_runner_agent.py](../../../integration/scenario_runner_agent.py)
- [integration/tests/test_qwen_boundary.py](../../../integration/tests/test_qwen_boundary.py)
- [integration/tests/test_qwen_remote_backend.py](../../../integration/tests/test_qwen_remote_backend.py)
- [integration/tests/test_qwen_vl_adapter.py](../../../integration/tests/test_qwen_vl_adapter.py)
- [qwen_service/runtime.py](../../../qwen_service/runtime.py)
- [qwen_service/service.py](../../../qwen_service/service.py)
- [qwen_service/tests/test_server.py](../../../qwen_service/tests/test_server.py)
- [tools/qwen_remote_smoke.py](../../../tools/qwen_remote_smoke.py)
- [tools/run_four_modal_full_chain.py](../../../tools/run_four_modal_full_chain.py)
- [tools/run_long_stability.py](../../../tools/run_long_stability.py)
- [tools/run_qwen_batch_benchmark.py](../../../tools/run_qwen_batch_benchmark.py)
- [tools/run_qwen_carla_closed_loop.py](../../../tools/run_qwen_carla_closed_loop.py)
- [tools/run_qwen_latency_gate.py](../../../tools/run_qwen_latency_gate.py)
- [tools/run_qwen_vl_decision.py](../../../tools/run_qwen_vl_decision.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-planner.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

<a id="fn-integration-qwen-boundary-py"></a>

### `integration/qwen_boundary.py`

来源 SHA256：`e6cad5cda70a1cea55ad7f0243b9e74fbbb490ef779ca1f21dea6fbaee8b6d3c`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `QwenInputContext.request_id` | `str` | `无声明默认；构造/赋值方提供` |
| `QwenInputContext.frame` | `int` | `无声明默认；构造/赋值方提供` |
| `QwenInputContext.sim_time_s` | `float` | `无声明默认；构造/赋值方提供` |
| `QwenInputContext.voice_command` | `str` | `无声明默认；构造/赋值方提供` |
| `QwenInputContext.rgb_ref` | `str &#124; None` | `无声明默认；构造/赋值方提供` |
| `QwenInputContext.scene_state` | `Mapping[str, Any]` | `无声明默认；构造/赋值方提供` |
| `QwenInputContext.perception` | `Mapping[str, Any]` | `无声明默认；构造/赋值方提供` |
| `QwenInputContext.safety_state` | `Mapping[str, Any]` | `无声明默认；构造/赋值方提供` |
| `QwenBoundaryFailure.status` | `str` | `无声明默认；构造/赋值方提供` |
| `QwenBoundaryFailure.error` | `str` | `无声明默认；构造/赋值方提供` |
| `QwenBoundaryFailure.watchdog_alerts` | `tuple[str, ...]` | `无声明默认；构造/赋值方提供` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `QwenInputContext.__post_init__` / 46 | `type(self.request_id) is not str or not self.request_id.strip()` | `raise ValueError('request_id must be a non-empty string')` |
| `QwenInputContext.__post_init__` / 48 | `type(self.frame) is not int or self.frame < 0` | `raise ValueError('frame must be a non-negative integer')` |
| `QwenInputContext.__post_init__` / 55 | `type(self.sim_time_s) not in (int, float) or isinstance(self.sim_time_s, bool) or (not math.isfinite(float(self.sim_time_s))) or (self.sim_time_s < 0.0)` | `raise ValueError('sim_time_s must be finite and non-negative')` |
| `QwenInputContext.__post_init__` / 57 | `type(self.voice_command) is not str` | `raise TypeError('voice_command must be a string')` |
| `QwenInputContext.__post_init__` / 61 | `self.rgb_ref is not None and (type(self.rgb_ref) is not str or not self.rgb_ref.strip())` | `raise ValueError('rgb_ref must be a non-empty string or None')` |
| `QwenInputContext.__post_init__` / 65 | `not isinstance(value, Mapping)` | `raise TypeError(f'{name} must be a mapping')` |
| `QwenBoundaryFailure.__post_init__` / 97 | `self.status not in {'PENDING', 'TIMEOUT', 'STALE', 'ERROR'}` | `raise ValueError('unsupported Qwen failure status')` |
| `QwenBoundaryFailure.__post_init__` / 99 | `type(self.error) is not str or not self.error` | `raise ValueError('error must be non-empty')` |
| `QwenBoundaryFailure.__post_init__` / 101 | `not self.watchdog_alerts` | `raise ValueError('fail-closed result requires a watchdog alert')` |
| `validate_qwen_response` / 117 | `type(payload) is str AND except json.JSONDecodeError` | `raise ValueError('Qwen response must be one JSON object without prose') from error` |
| `validate_qwen_response` / 119 | `not isinstance(payload, Mapping)` | `raise TypeError('Qwen response must be a mapping or JSON object string')` |
| `validate_qwen_response` / 123 | `forbidden` | `raise ValueError('Qwen response contains forbidden low-level fields: ' + ','.join(sorted(forbidden)))` |
| `validate_qwen_response` / 130 | `missing or unknown` | `raise ValueError(f'Qwen response fields mismatch; missing={sorted(missing)}, unknown={sorted(unknown)}')` |
| `validate_qwen_response` / 137 | `action not in SUPPORTED_INTENTS` | `raise ValueError(f'unsupported Qwen action: {action}')` |
| `validate_qwen_response` / 141 | `type(confirmation) is not bool` | `raise TypeError('requires_confirmation must be bool')` |
| `validate_qwen_response` / 150 | `action == 'SET_SPEED' and target is None` | `raise ValueError('SET_SPEED requires target_speed_mps')` |
| `validate_qwen_response` / 161 | `target is not None AND NOT (action in {'STOP', 'EMERGENCY_STOP'} and normalized_target == 0.0) AND action not in {'SET_SPEED', 'SLOW_DOWN'}` | `raise ValueError(f'{action} must not include target_speed_mps')` |
| `validate_qwen_response` / 173 | `'visual_valid' in payload AND type(payload['visual_valid']) is not bool` | `raise TypeError('visual_valid must be bool')` |
| `_unwrap_single_json_fence` / 188 | `match is None or '' in match.group('body')` | `raise ValueError('Qwen response must be one JSON object without prose')` |
| `fail_closed` / 204 | `except KeyError` | `raise ValueError(f'unsupported Qwen failure status: {status!r}') from exception` |
| `_json_mapping` / 211 | `any((type(key) is not str for key in copied))` | `raise TypeError(f'{name} keys must be strings')` |
| `_json_mapping` / 215 | `except (TypeError, ValueError)` | `raise ValueError(f'{name} must contain JSON-safe finite values') from error` |
| `_nonempty_text` / 221 | `type(value) is not str or not value.strip()` | `raise ValueError(f'{name} must be a non-empty string')` |
| `_bounded_number` / 227 | `type(value) not in (int, float) or isinstance(value, bool)` | `raise TypeError(f'{name} must be numeric')` |
| `_bounded_number` / 230 | `not math.isfinite(result) or not minimum <= result <= maximum` | `raise ValueError(f'{name} must be finite and in [{minimum}, {maximum}]')` |
