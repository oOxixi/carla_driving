# voice_adapter：功能记录

上级模块：[模块说明](../modules/vehicle-behavior.md) · 实现：[integration/voice_adapter.py](../../../integration/voice_adapter.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [授权、确认、过期与停车保持](command-lifecycle.md)
- [前置条件锁存、步骤完成与重规划](maneuver-progress.md)

## 功能职责与范围

Translate the voice-group envelope into the A/C runtime command contract.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `VoiceDiagnostic.code: str`；默认：`未在声明处设置`。
- `VoiceDiagnostic.message: str`；默认：`未在声明处设置`。
- `VoiceCommandMetadata.source_text: str`；默认：`未在声明处设置`。
- `VoiceCommandMetadata.intent: str`；默认：`未在声明处设置`。
- `VoiceCommandMetadata.parameters: dict[str, object]`；默认：`未在声明处设置`。
- `VoiceCommandMetadata.status: str`；默认：`未在声明处设置`。
- `VoiceCommandMetadata.ambiguity_type: str`；默认：`未在声明处设置`。
- `VoiceCommandMetadata.errors: tuple[VoiceDiagnostic, ...]`；默认：`未在声明处设置`。
- `VoiceCommandMetadata.warnings: tuple[VoiceDiagnostic, ...]`；默认：`未在声明处设置`。
- `VoiceCommandMetadata.t_audio_start_ns: int | None`；默认：`未在声明处设置`。
- `VoiceCommandMetadata.t_asr_end_ns: int | None`；默认：`未在声明处设置`。
- `VoiceCommandMetadata.t_intent_end_ns: int | None`；默认：`未在声明处设置`。
- `AdaptedVoiceCommand.command: DrivingCommand`；默认：`未在声明处设置`。
- `AdaptedVoiceCommand.metadata: VoiceCommandMetadata`；默认：`未在声明处设置`。
- `AdaptedVoiceCommand.control_authorized: bool`；默认：`True`。
- `AdaptedVoiceCommand.feedback: ExecutionFeedback | None`；默认：`None`。

## 功能入口：输入、输出与实现说明

<a id="fn-voicediagnostic"></a>

### `VoiceDiagnostic`

源码位置：[integration/voice_adapter.py 第 35 行](../../../integration/voice_adapter.py#L35)。类型：`ClassDef`。

Normalized diagnostic emitted by either voice pipeline revision.

<a id="fn-voicecommandmetadata"></a>

### `VoiceCommandMetadata`

源码位置：[integration/voice_adapter.py 第 43 行](../../../integration/voice_adapter.py#L43)。类型：`ClassDef`。

Auditable voice fields which do not belong in A's minimal contract.

<a id="fn-adaptedvoicecommand"></a>

### `AdaptedVoiceCommand`

源码位置：[integration/voice_adapter.py 第 59 行](../../../integration/voice_adapter.py#L59)。类型：`ClassDef`。

A command ready for A/C plus its immutable audit metadata.

冻结dataclass只阻止属性重新绑定；metadata.parameters是可变dict的顶层拷贝，嵌套值仍可能共享。“immutable audit metadata”不能理解为深度不可变或持久化审计。

<a id="fn-voicecommandadapter"></a>

### `VoiceCommandAdapter`

源码位置：[integration/voice_adapter.py 第 68 行](../../../integration/voice_adapter.py#L68)。类型：`ClassDef`。

Validate and safely adapt the JSON returned by ``voice_group.pipeline``.

<a id="fn-voicecommandadapter---init--"></a>

### `VoiceCommandAdapter.__init__`

源码位置：[integration/voice_adapter.py 第 71 行](../../../integration/voice_adapter.py#L71)。类型：`FunctionDef`。

```python
VoiceCommandAdapter.__init__(self, *, default_ttl_s: float=3.0, default_slow_speed_mps: float=2.0) -> None
```

default_ttl_s默认3秒须有限正数；default_slow_speed_mps默认2m/s须有限非负。仿真接收时刻由adapt调用方提供，构造不读取宿主时间。

<a id="fn-voicecommandadapter-adapt"></a>

### `VoiceCommandAdapter.adapt`

源码位置：[integration/voice_adapter.py 第 83 行](../../../integration/voice_adapter.py#L83)。类型：`FunctionDef`。

```python
VoiceCommandAdapter.adapt(self, envelope: Mapping[str, object], *, now_s: float) -> AdaptedVoiceCommand
```

Create a CARLA-time command from a voice envelope.

``now_s`` must be the simulation timestamp of the frame receiving the
envelope.  It intentionally is not inferred from voice timestamps, since
monotonic host time and CARLA simulation time have distinct origins.

now_s在try之前要求有限非负，错误直接抛出；非Mapping envelope或内部TypeError/ValueError返回_rejected。这里只转换，不登记FSM；control_authorized代表输入未被拒绝，仍需尊重command.requires_confirmation。

<a id="fn-voicecommandadapter--adapt-validated"></a>

### `VoiceCommandAdapter._adapt_validated`

源码位置：[integration/voice_adapter.py 第 98 行](../../../integration/voice_adapter.py#L98)。类型：`FunctionDef`。

```python
VoiceCommandAdapter._adapt_validated(self, envelope: Mapping[str, object], now: float) -> AdaptedVoiceCommand
```

校验版本1.0、ID/source/intent/status/ambiguity文本，parameters须plain dict，diagnostics须list，confidence与确认布尔合法。expiry=now+正TTL；status非valid、UNKNOWN或errors非空返回未授权NO_OP。合法输入按intent/compiled_maneuver映内部action，并保留语音纳秒元数据；control_authorized=True仍可能requires_confirmation=True，不等于可立即推进。

<a id="fn-voicecommandadapter--rejected"></a>

### `VoiceCommandAdapter._rejected`

源码位置：[integration/voice_adapter.py 第 152 行](../../../integration/voice_adapter.py#L152)。类型：`FunctionDef`。

```python
VoiceCommandAdapter._rejected(self, envelope: Mapping[str, object], now: float, reason: str, *, errors: tuple[VoiceDiagnostic, ...] | None=None, warnings: tuple[VoiceDiagnostic, ...] | None=None) -> AdaptedVoiceCommand
```

Return an auditable NO_OP without granting longitudinal authority.

生成confidence=0、NO_OP、is_ambiguous=True和REJECTED反馈，control_authorized=False；errors追加VEHICLE_ADAPTER_REJECTED，坏TTL回默认、坏时间戳丢None。保留可用元数据但不应覆盖当前合法活动命令；ControlRuntime.submit_voice在此结果分支只缓存反馈即返回。

<a id="fn-voicecommandadapter--runtime-fields"></a>

### `VoiceCommandAdapter._runtime_fields`

源码位置：[integration/voice_adapter.py 第 190 行](../../../integration/voice_adapter.py#L190)。类型：`FunctionDef`。

```python
VoiceCommandAdapter._runtime_fields(self, intent: str, parameters: Mapping[str, object], *, compiled_maneuver: bool=False) -> tuple[str, float | None, bool]
```

EMERGENCY_STOP→EMERGENCY_BRAKE，STOP保持；SET_SPEED和带速度SLOW_DOWN→SET_SPEED(m/s)。SLOW_DOWN仅当mode=RELATIVE、action=DECELERATE且无speed时用默认2m/s；KEEP_LANE不带速度。复杂动作默认MULTIMODAL_DECISION并强制确认；compiled_maneuver=True时PULL_OVER→STOP、其他复杂动作→KEEP_LANE，不在此验证真实计划/路线授权，信任外层接线。

<a id="fn--speed-command-fields"></a>

### `_speed_command_fields`

源码位置：[integration/voice_adapter.py 第 226 行](../../../integration/voice_adapter.py#L226)。类型：`FunctionDef`。

```python
_speed_command_fields(intent_parameters: Mapping[str, object], intent: str) -> tuple[str, float, bool]
```

SET_SPEED/SLOW_DOWN要求数值speed非bool；unit缺省km/h，支持km/h/kph/kmh/公里每小时斜杠写法、m/s/mps/米每秒斜杠写法，strip/lower/去空格后匹配；km/h除3.6。有限非负才返回(SET_SPEED,target,False)，未知单位拒绝，没有最大速度夹取。

<a id="fn--required-text"></a>

### `_required_text`

源码位置：[integration/voice_adapter.py 第 248 行](../../../integration/voice_adapter.py#L248)。类型：`FunctionDef`。

```python
_required_text(data: Mapping[str, object], name: str) -> str
```

要求exact str且strip后非空，但返回原字符串；intent只upper、status只lower而不strip，带前后空白的枚举可能被拒绝。ID/source保留原始空白。

<a id="fn--nonnegative-number"></a>

### `_nonnegative_number`

源码位置：[integration/voice_adapter.py 第 255 行](../../../integration/voice_adapter.py#L255)。类型：`FunctionDef`。

```python
_nonnegative_number(name: str, value: object) -> float
```

exact int/float、非bool、有限>=0，返回float；adapt的now_s在外层try之前校验，坏now会直接抛错，不生成NO_OP。

<a id="fn--positive-number"></a>

### `_positive_number`

源码位置：[integration/voice_adapter.py 第 264 行](../../../integration/voice_adapter.py#L264)。类型：`FunctionDef`。

```python
_positive_number(name: str, value: object) -> float
```

有限非负检查后拒绝0，返回float；用于默认TTL和envelope.valid_duration_s，单位仿真秒。

<a id="fn--confidence"></a>

### `_confidence`

源码位置：[integration/voice_adapter.py 第 271 行](../../../integration/voice_adapter.py#L271)。类型：`FunctionDef`。

```python
_confidence(data: Mapping[str, object]) -> float
```

优先confidence，缺键才取intent_confidence；两键都缺/显式None会报错，不像HighLevelCommandAdapter默认0。须有限[0,1]，低于配置阈值但格式合法的值保留给确认逻辑。

<a id="fn--optional-bool"></a>

### `_optional_bool`

源码位置：[integration/voice_adapter.py 第 279 行](../../../integration/voice_adapter.py#L279)。类型：`FunctionDef`。

```python
_optional_bool(data: Mapping[str, object], name: str, *, default: bool) -> bool
```

缺键用调用者default，存在值必须exact bool；用于confirm_required/compiled_maneuver，不接受字符串true或整数1。

<a id="fn--diagnostic-tuple"></a>

### `_diagnostic_tuple`

源码位置：[integration/voice_adapter.py 第 286 行](../../../integration/voice_adapter.py#L286)。类型：`FunctionDef`。

```python
_diagnostic_tuple(value: object, name: str) -> tuple[VoiceDiagnostic, ...]
```

仅接受list；非空字符串转(code=原串,message=原串)，Mapping项需非空字符串code及字符串message（允许空message）。坏项直接报错，返回VoiceDiagnostic tuple，不strip保存内容。

<a id="fn--diagnostic-tuple-lenient"></a>

### `_diagnostic_tuple_lenient`

源码位置：[integration/voice_adapter.py 第 304 行](../../../integration/voice_adapter.py#L304)。类型：`FunctionDef`。

```python
_diagnostic_tuple_lenient(value: object) -> tuple[VoiceDiagnostic, ...]
```

None按空list，严格诊断转换失败时整组返回空tuple，不保留前面已成功元素；用于拒绝路径避免再次失败。

<a id="fn--safe-text"></a>

### `_safe_text`

源码位置：[integration/voice_adapter.py 第 311 行](../../../integration/voice_adapter.py#L311)。类型：`FunctionDef`。

```python
_safe_text(value: object, default: str) -> str
```

非空str strip后返回，否则default；用于被拒绝输入的身份/源文字提取，不用于正常路径枚举校验。

<a id="fn--optional-timestamp"></a>

### `_optional_timestamp`

源码位置：[integration/voice_adapter.py 第 315 行](../../../integration/voice_adapter.py#L315)。类型：`FunctionDef`。

```python
_optional_timestamp(data: Mapping[str, object], name: str) -> int | None
```

缺失/None返回None，其余为非负exact int；不核对audio/asr/intent先后，也不将宿主纳秒作为命令过期秒。

<a id="fn--optional-timestamp-lenient"></a>

### `_optional_timestamp_lenient`

源码位置：[integration/voice_adapter.py 第 324 行](../../../integration/voice_adapter.py#L324)。类型：`FunctionDef`。

```python
_optional_timestamp_lenient(data: Mapping[str, object], name: str) -> int | None
```

严格时间戳校验失败转None，在NO_OP拒绝metadata里保留其余可用诊断；不会悄悄改变正常成功路径的校验标准。

## 内部调用与异常路径

- `_speed_command_fields` 调用：`TypeError`, `ValueError`, `float`, `isinstance`, `math.isfinite`, `parameters.get`, `type`, `unit.strip`, `unit.strip().lower`, `unit.strip().lower().replace`.
- `_required_text` 调用：`ValueError`, `data.get`, `type`, `value.strip`.
- `_nonnegative_number` 调用：`TypeError`, `ValueError`, `float`, `isinstance`, `math.isfinite`, `type`.
- `_positive_number` 调用：`ValueError`, `_nonnegative_number`.
- `_confidence` 调用：`ValueError`, `_nonnegative_number`, `data.get`.
- `_optional_bool` 调用：`TypeError`, `data.get`, `type`.
- `_diagnostic_tuple` 调用：`TypeError`, `VoiceDiagnostic`, `code.strip`, `isinstance`, `item.get`, `item.strip`, `result.append`, `tuple`, `type`.
- `_diagnostic_tuple_lenient` 调用：`_diagnostic_tuple`.
- `_safe_text` 调用：`type`, `value.strip`.
- `_optional_timestamp` 调用：`ValueError`, `data.get`, `type`.
- `_optional_timestamp_lenient` 调用：`_optional_timestamp`.
- `__init__` 调用：`_nonnegative_number`, `_positive_number`.
- `adapt` 调用：`_nonnegative_number`, `isinstance`, `self._adapt_validated`, `self._rejected`, `str`.
- `_adapt_validated` 调用：`'; '.join`, `AdaptedVoiceCommand`, `DrivingCommand`, `TypeError`, `ValueError`, `VoiceCommandMetadata`, `_confidence`, `_diagnostic_tuple`, `_optional_bool`, `_optional_timestamp`, `_positive_number`, `_required_text`, `_required_text(envelope, 'intent').upper`, `_required_text(envelope, 'status').lower`, `ambiguity_type.upper`, `bool`, `dict`, `envelope.get`, `self._rejected`, `self._runtime_fields`, `type`.
- `_rejected` 调用：`AdaptedVoiceCommand`, `DrivingCommand`, `ExecutionFeedback`, `VoiceCommandMetadata`, `VoiceDiagnostic`, `_diagnostic_tuple_lenient`, `_optional_timestamp_lenient`, `_positive_number`, `_safe_text`, `_safe_text(envelope.get('intent'), 'UNKNOWN').upper`, `_safe_text(envelope.get('status'), 'invalid').lower`, `dict`, `envelope.get`, `type`.
- `_runtime_fields` 调用：`_speed_command_fields`, `parameters.get`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `_adapt_validated`，第 101 行：`ValueError(f'unsupported voice schema_version: {version!r}')`。
- `_adapt_validated`，第 106 行：`ValueError(f'unsupported voice intent: {intent!r}')`。
- `_adapt_validated`，第 109 行：`TypeError('parameters must be a plain dict')`。
- `_confidence`，第 275 行：`ValueError('confidence must be <= 1.0')`。
- `_diagnostic_tuple`，第 288 行：`TypeError(f'{name} must be a list')`。
- `_diagnostic_tuple`，第 297 行：`TypeError(f'{name} objects require non-empty code and string message')`。
- `_diagnostic_tuple`，第 300 行：`TypeError(f'{name} entries must be strings or {{code, message}} objects')`。
- `_nonnegative_number`，第 257 行：`TypeError(f'{name} must be an int or float')`。
- `_nonnegative_number`，第 260 行：`ValueError(f'{name} must be finite and non-negative')`。
- `_optional_bool`，第 282 行：`TypeError(f'{name} must be bool')`。
- `_optional_timestamp`，第 320 行：`ValueError(f'{name} must be a non-negative int or null')`。
- `_positive_number`，第 267 行：`ValueError(f'{name} must be positive')`。
- `_required_text`，第 251 行：`ValueError(f'{name} must be a non-empty string')`。
- `_speed_command_fields`，第 231 行：`ValueError(f'{intent} requires numeric parameters.speed')`。
- `_speed_command_fields`，第 234 行：`TypeError(f'{intent} parameters.unit must be a string')`。
- `_speed_command_fields`，第 241 行：`ValueError(f'unsupported {intent} unit: {unit!r}')`。
- `_speed_command_fields`，第 243 行：`ValueError(f'{intent} target speed must be finite and non-negative')`。
- `_speed_command_fields`，第 245 行：`ValueError(f'unsupported speed intent: {intent}')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [car_control_A/__init__.py](../../../car_control_A/__init__.py)

静态 import 消费者（含测试）：

- [car_control_A/tests/test_high_level_command.py](../../../car_control_A/tests/test_high_level_command.py)
- [integration/__init__.py](../../../integration/__init__.py)
- [integration/runtime_loop.py](../../../integration/runtime_loop.py)
- [integration/tests/test_carla_runner_helpers.py](../../../integration/tests/test_carla_runner_helpers.py)
- [integration/tests/test_voice_adapter.py](../../../integration/tests/test_voice_adapter.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-behavior.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

<a id="fn-integration-voice-adapter-py"></a>

### `integration/voice_adapter.py`

来源 SHA256：`d92c880f3c8a5d01b8ba200ded5652b37a07803927b2a55e85c64e2dcd13c6c8`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `VoiceDiagnostic.code` | `str` | `无声明默认；构造/赋值方提供` |
| `VoiceDiagnostic.message` | `str` | `无声明默认；构造/赋值方提供` |
| `VoiceCommandMetadata.source_text` | `str` | `无声明默认；构造/赋值方提供` |
| `VoiceCommandMetadata.intent` | `str` | `无声明默认；构造/赋值方提供` |
| `VoiceCommandMetadata.parameters` | `dict[str, object]` | `无声明默认；构造/赋值方提供` |
| `VoiceCommandMetadata.status` | `str` | `无声明默认；构造/赋值方提供` |
| `VoiceCommandMetadata.ambiguity_type` | `str` | `无声明默认；构造/赋值方提供` |
| `VoiceCommandMetadata.errors` | `tuple[VoiceDiagnostic, ...]` | `无声明默认；构造/赋值方提供` |
| `VoiceCommandMetadata.warnings` | `tuple[VoiceDiagnostic, ...]` | `无声明默认；构造/赋值方提供` |
| `VoiceCommandMetadata.t_audio_start_ns` | `int &#124; None` | `无声明默认；构造/赋值方提供` |
| `VoiceCommandMetadata.t_asr_end_ns` | `int &#124; None` | `无声明默认；构造/赋值方提供` |
| `VoiceCommandMetadata.t_intent_end_ns` | `int &#124; None` | `无声明默认；构造/赋值方提供` |
| `AdaptedVoiceCommand.command` | `DrivingCommand` | `无声明默认；构造/赋值方提供` |
| `AdaptedVoiceCommand.metadata` | `VoiceCommandMetadata` | `无声明默认；构造/赋值方提供` |
| `AdaptedVoiceCommand.control_authorized` | `bool` | `True` |
| `AdaptedVoiceCommand.feedback` | `ExecutionFeedback &#124; None` | `None` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `VoiceCommandAdapter._adapt_validated` / 101 | `version != VOICE_SCHEMA_VERSION` | `raise ValueError(f'unsupported voice schema_version: {version!r}')` |
| `VoiceCommandAdapter._adapt_validated` / 106 | `intent not in _ALLOWED_INTENTS` | `raise ValueError(f'unsupported voice intent: {intent!r}')` |
| `VoiceCommandAdapter._adapt_validated` / 109 | `type(parameters) is not dict` | `raise TypeError('parameters must be a plain dict')` |
| `_speed_command_fields` / 231 | `intent == 'SET_SPEED' or intent == 'SLOW_DOWN' AND type(speed) not in (int, float) or isinstance(speed, bool)` | `raise ValueError(f'{intent} requires numeric parameters.speed')` |
| `_speed_command_fields` / 234 | `intent == 'SET_SPEED' or intent == 'SLOW_DOWN' AND type(unit) is not str` | `raise TypeError(f'{intent} parameters.unit must be a string')` |
| `_speed_command_fields` / 241 | `intent == 'SET_SPEED' or intent == 'SLOW_DOWN' AND NOT (normalized_unit in {'km/h', 'kph', 'kmh', '公里/小时', '千米/小时'}) AND NOT (normalized_unit in {'m/s', 'mps', '米/秒'})` | `raise ValueError(f'unsupported {intent} unit: {unit!r}')` |
| `_speed_command_fields` / 243 | `intent == 'SET_SPEED' or intent == 'SLOW_DOWN' AND not math.isfinite(target) or target < 0.0` | `raise ValueError(f'{intent} target speed must be finite and non-negative')` |
| `_speed_command_fields` / 245 | `本地无直接if；检查上下文` | `raise ValueError(f'unsupported speed intent: {intent}')` |
| `_required_text` / 251 | `type(value) is not str or not value.strip()` | `raise ValueError(f'{name} must be a non-empty string')` |
| `_nonnegative_number` / 257 | `type(value) not in (int, float) or isinstance(value, bool)` | `raise TypeError(f'{name} must be an int or float')` |
| `_nonnegative_number` / 260 | `not math.isfinite(result) or result < 0.0` | `raise ValueError(f'{name} must be finite and non-negative')` |
| `_positive_number` / 267 | `result <= 0.0` | `raise ValueError(f'{name} must be positive')` |
| `_confidence` / 275 | `result > 1.0` | `raise ValueError('confidence must be <= 1.0')` |
| `_optional_bool` / 282 | `type(value) is not bool` | `raise TypeError(f'{name} must be bool')` |
| `_diagnostic_tuple` / 288 | `type(value) is not list` | `raise TypeError(f'{name} must be a list')` |
| `_diagnostic_tuple` / 297 | `NOT (type(item) is str and item.strip()) AND isinstance(item, Mapping) AND type(code) is not str or not code.strip() or type(message) is not str` | `raise TypeError(f'{name} objects require non-empty code and string message')` |
| `_diagnostic_tuple` / 300 | `NOT (type(item) is str and item.strip()) AND NOT (isinstance(item, Mapping))` | `raise TypeError(f'{name} entries must be strings or {{code, message}} objects')` |
| `_optional_timestamp` / 320 | `type(value) is not int or value < 0` | `raise ValueError(f'{name} must be a non-negative int or null')` |
