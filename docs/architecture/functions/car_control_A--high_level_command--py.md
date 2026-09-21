# high_level_command：功能记录

上级模块：[模块说明](../modules/vehicle-behavior.md) · 实现：[car_control_A/high_level_command.py](../../../car_control_A/high_level_command.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [授权、确认、过期与停车保持](command-lifecycle.md)
- [前置条件锁存、步骤完成与重规划](maneuver-progress.md)

## 功能职责与范围

Frozen high-level command boundary for Qwen/decision-module output.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

<a id="fn-is-high-level-command"></a>

### `is_high_level_command`

源码位置：[car_control_A/high_level_command.py 第 46 行](../../../car_control_A/high_level_command.py#L46)。类型：`FunctionDef`。

```python
is_high_level_command(payload: object) -> bool
```

Return True for Qwen-style command JSON, not legacy voice envelopes.

仅测试Mapping且有action、无intent；不校验schema/动作合法性。action与intent同时出现会走非高层识别路径，不能据False判断载荷一定符合voice协议。

<a id="fn-highlevelcommandadapter"></a>

### `HighLevelCommandAdapter`

源码位置：[car_control_A/high_level_command.py 第 51 行](../../../car_control_A/high_level_command.py#L51)。类型：`ClassDef`。

Convert Qwen high-level JSON into A's command envelope contract.

<a id="fn-highlevelcommandadapter---init--"></a>

### `HighLevelCommandAdapter.__init__`

源码位置：[car_control_A/high_level_command.py 第 54 行](../../../car_control_A/high_level_command.py#L54)。类型：`FunctionDef`。

```python
HighLevelCommandAdapter.__init__(self, *, default_ttl_s: float=3.0, default_slow_speed_mps: float=2.0) -> None
```

default_ttl_s默认3秒须有限正数；default_slow_speed_mps默认2m/s须有限非负。保存默认值，不加载模型或创建线程；与VoiceCommandAdapter的同名默认是两个独立实例配置。

<a id="fn-highlevelcommandadapter-adapt"></a>

### `HighLevelCommandAdapter.adapt`

源码位置：[car_control_A/high_level_command.py 第 60 行](../../../car_control_A/high_level_command.py#L60)。类型：`FunctionDef`。

```python
HighLevelCommandAdapter.adapt(self, payload: Mapping[str, object]) -> dict[str, object]
```

输入须Mapping；顶层精确小写禁止字段命中则返回invalid envelope，版本非1.0也返回invalid。其余字段格式错误可直接抛TypeError/ValueError（非统一返回invalid）；动作规范化并组装voice风格envelope。复杂动作valid但强制确认，未知动作invalid；visual_valid=False只加warning，本层不强制停车。只保留明列字段，target_track_id不会复制到输出，见M03-03。

<a id="fn-highlevelcommandadapter--runtime-fields"></a>

### `HighLevelCommandAdapter._runtime_fields`

源码位置：[car_control_A/high_level_command.py 第 135 行](../../../car_control_A/high_level_command.py#L135)。类型：`FunctionDef`。

```python
HighLevelCommandAdapter._runtime_fields(self, action: str, payload: Mapping[str, object], warnings: list[dict[str, str]]) -> tuple[str, dict[str, object], bool]
```

START映KEEP_LANE并加warning，EMERGENCY_BRAKE映EMERGENCY_STOP。SET_SPEED需要目标m/s，SLOW_DOWN缺速度用默认2m/s并告警；STOP/EMERGENCY_STOP/KEEP_LANE无参数。TURN*/CHANGE_LANE*提取方向，AVOID映AVOID_OBSTACLE，其余复杂枚举保留intent并要求确认；FOLLOW/YIELD等未列入集合则UNKNOWN。

<a id="fn-highlevelcommandadapter--invalid-envelope"></a>

### `HighLevelCommandAdapter._invalid_envelope`

源码位置：[car_control_A/high_level_command.py 第 176 行](../../../car_control_A/high_level_command.py#L176)。类型：`FunctionDef`。

```python
HighLevelCommandAdapter._invalid_envelope(self, payload: Mapping[str, object], intent: str, code: str, message: str) -> dict[str, object]
```

使用安全fallback ID/source，置status=invalid、confidence=0、ambiguity=INVALID_HIGH_LEVEL_COMMAND、空参数及指定errors；TTL使用本实例默认，坏timestamp宽容丢为None。不会直接返回A DrivingCommand或操纵车辆。

<a id="fn--speed-parameters"></a>

### `_speed_parameters`

源码位置：[car_control_A/high_level_command.py 第 203 行](../../../car_control_A/high_level_command.py#L203)。类型：`FunctionDef`。

```python
_speed_parameters(payload: Mapping[str, object], *, required: bool) -> dict[str, object]
```

读取target_speed_mps，required=False且None则空dict；其余须有限非负数，返回{speed:float,unit:m/s}。没有上限50m/s或道路限速检查，此处依赖其他边界。

<a id="fn--direction-parameters"></a>

### `_direction_parameters`

源码位置：[car_control_A/high_level_command.py 第 211 行](../../../car_control_A/high_level_command.py#L211)。类型：`FunctionDef`。

```python
_direction_parameters(action: str, prefix: str) -> dict[str, object]
```

去掉动作前缀并strip下划线，余串非空则写direction，否则空dict；不独立校验LEFT/RIGHT，调用方先按动作集合过滤。

<a id="fn--source-text"></a>

### `_source_text`

源码位置：[car_control_A/high_level_command.py 第 216 行](../../../car_control_A/high_level_command.py#L216)。类型：`FunctionDef`。

```python
_source_text(payload: Mapping[str, object], action: str) -> str
```

优先非空source_text，其次reason再reason_zh，组合action: reason；全缺时生成Qwen high-level action加动作名。用于审计，不重新解析自然语言意图。

<a id="fn--required-text"></a>

### `_required_text`

源码位置：[car_control_A/high_level_command.py 第 224 行](../../../car_control_A/high_level_command.py#L224)。类型：`FunctionDef`。

```python
_required_text(data: Mapping[str, object], name: str) -> str
```

要求exact str且strip后非空，返回strip结果；与voice_adapter同名helper保留原空白的行为不同。

<a id="fn--optional-text"></a>

### `_optional_text`

源码位置：[car_control_A/high_level_command.py 第 231 行](../../../car_control_A/high_level_command.py#L231)。类型：`FunctionDef`。

```python
_optional_text(data: Mapping[str, object], name: str) -> str | None
```

字段为非空str则strip返回，其余包括错误类型返回None；这是宽容可选元数据处理，不适用于必填ID。

<a id="fn--safe-text"></a>

### `_safe_text`

源码位置：[car_control_A/high_level_command.py 第 236 行](../../../car_control_A/high_level_command.py#L236)。类型：`FunctionDef`。

```python
_safe_text(value: object, default: str) -> str
```

非空str返回strip，其他取传入default，用于拒绝路径保留可审计身份；不生成UUID。

<a id="fn--confidence"></a>

### `_confidence`

源码位置：[car_control_A/high_level_command.py 第 240 行](../../../car_control_A/high_level_command.py#L240)。类型：`FunctionDef`。

```python
_confidence(data: Mapping[str, object]) -> float
```

优先confidence，键不存在才回intent_confidence，二者都缺默认0.0；显式None或坏数不回退，交有界校验报错。

<a id="fn--bounded-confidence"></a>

### `_bounded_confidence`

源码位置：[car_control_A/high_level_command.py 第 244 行](../../../car_control_A/high_level_command.py#L244)。类型：`FunctionDef`。

```python
_bounded_confidence(value: object) -> float
```

先要求有限非负数，再拒绝>1，返回float；不根据阈值自动设确认，后续DrivingCommand属性处理低置信。

<a id="fn--nonnegative-number"></a>

### `_nonnegative_number`

源码位置：[car_control_A/high_level_command.py 第 251 行](../../../car_control_A/high_level_command.py#L251)。类型：`FunctionDef`。

```python
_nonnegative_number(name: str, value: object) -> float
```

exact int/float且非bool，有限>=0，返回float；拒绝字符串数值和NaN/Infinity。

<a id="fn--positive-number"></a>

### `_positive_number`

源码位置：[car_control_A/high_level_command.py 第 260 行](../../../car_control_A/high_level_command.py#L260)。类型：`FunctionDef`。

```python
_positive_number(name: str, value: object) -> float
```

在有限非负数检查后拒绝0，返回float；用于TTL，单位秒，不读取timestamp_ns换算时限。

<a id="fn--optional-timestamp"></a>

### `_optional_timestamp`

源码位置：[car_control_A/high_level_command.py 第 267 行](../../../car_control_A/high_level_command.py#L267)。类型：`FunctionDef`。

```python
_optional_timestamp(data: Mapping[str, object], name: str) -> int | None
```

字段None/缺失返回None；否则须非负exact int（拒绝bool），原样返回纳秒值，不判断时间域或先后顺序。

<a id="fn--optional-timestamp-lenient"></a>

### `_optional_timestamp_lenient`

源码位置：[car_control_A/high_level_command.py 第 276 行](../../../car_control_A/high_level_command.py#L276)。类型：`FunctionDef`。

```python
_optional_timestamp_lenient(data: Mapping[str, object], name: str) -> int | None
```

调用严格timestamp helper，TypeError/ValueError转None；用于invalid envelope审计，防止诊断时间坏值遮蔽主错误。

<a id="fn--confirmation-requested"></a>

### `_confirmation_requested`

源码位置：[car_control_A/high_level_command.py 第 283 行](../../../car_control_A/high_level_command.py#L283)。类型：`FunctionDef`。

```python
_confirmation_requested(data: Mapping[str, object]) -> bool
```

合并requires_confirmation与confirm_required两个可选键，每个存在值须exact bool；返回any，全部缺失为False。一个False不能覆盖另一个True。

## 内部调用与异常路径

- `is_high_level_command` 调用：`isinstance`.
- `_speed_parameters` 调用：`_nonnegative_number`, `payload.get`.
- `_direction_parameters` 调用：`action.removeprefix`, `action.removeprefix(prefix).strip`.
- `_source_text` 调用：`_optional_text`.
- `_required_text` 调用：`ValueError`, `data.get`, `type`, `value.strip`.
- `_optional_text` 调用：`data.get`, `type`, `value.strip`.
- `_safe_text` 调用：`type`, `value.strip`.
- `_confidence` 调用：`_bounded_confidence`, `data.get`.
- `_bounded_confidence` 调用：`ValueError`, `_nonnegative_number`.
- `_nonnegative_number` 调用：`TypeError`, `ValueError`, `float`, `isinstance`, `math.isfinite`, `type`.
- `_positive_number` 调用：`ValueError`, `_nonnegative_number`.
- `_optional_timestamp` 调用：`ValueError`, `data.get`, `type`.
- `_optional_timestamp_lenient` 调用：`_optional_timestamp`.
- `_confirmation_requested` 调用：`TypeError`, `any`, `type`.
- `__init__` 调用：`_nonnegative_number`, `_positive_number`.
- `adapt` 调用：`','.join`, `FORBIDDEN_LOW_LEVEL_FIELDS.intersection`, `TypeError`, `_confidence`, `_confirmation_requested`, `_optional_text`, `_optional_timestamp`, `_positive_number`, `_required_text`, `_required_text(payload, 'action').upper`, `_source_text`, `errors.append`, `isinstance`, `payload.get`, `payload.keys`, `self._invalid_envelope`, `self._runtime_fields`, `sorted`, `warnings.append`.
- `_runtime_fields` 调用：`_direction_parameters`, `_speed_parameters`, `action.startswith`, `payload.get`, `warnings.append`.
- `_invalid_envelope` 调用：`_optional_timestamp_lenient`, `_safe_text`, `_source_text`, `payload.get`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `_bounded_confidence`，第 247 行：`ValueError('confidence must be <= 1.0')`。
- `_confirmation_requested`，第 291 行：`TypeError('requires_confirmation/confirm_required must be bool')`。
- `_nonnegative_number`，第 253 行：`TypeError(f'{name} must be an int or float')`。
- `_nonnegative_number`，第 256 行：`ValueError(f'{name} must be finite and non-negative')`。
- `_optional_timestamp`，第 272 行：`ValueError(f'{name} must be a non-negative int or null')`。
- `_positive_number`，第 263 行：`ValueError(f'{name} must be positive')`。
- `_required_text`，第 227 行：`ValueError(f'{name} must be a non-empty string')`。
- `adapt`，第 62 行：`TypeError('high-level command payload must be a mapping')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [car_control_A/__init__.py](../../../car_control_A/__init__.py)
- [car_control_A/tests/test_high_level_command.py](../../../car_control_A/tests/test_high_level_command.py)
- [integration/carla_runner.py](../../../integration/carla_runner.py)
- [integration/offline_replay.py](../../../integration/offline_replay.py)
- [integration/qwen_async.py](../../../integration/qwen_async.py)
- [integration/qwen_boundary.py](../../../integration/qwen_boundary.py)
- [integration/qwen_command_adapter.py](../../../integration/qwen_command_adapter.py)
- [integration/tests/test_qwen_async.py](../../../integration/tests/test_qwen_async.py)
- [tools/run_four_modal_full_chain.py](../../../tools/run_four_modal_full_chain.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-behavior.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

<a id="fn-car-control-a-high-level-command-py"></a>

### `car_control_A/high_level_command.py`

来源 SHA256：`c482598ce6cbf9fba96d5038e6c730cb2eb05d5977f6225c32aec9113fb9b0b7`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `HighLevelCommandAdapter.adapt` / 62 | `not isinstance(payload, Mapping)` | `raise TypeError('high-level command payload must be a mapping')` |
| `_required_text` / 227 | `type(value) is not str or not value.strip()` | `raise ValueError(f'{name} must be a non-empty string')` |
| `_bounded_confidence` / 247 | `result > 1.0` | `raise ValueError('confidence must be <= 1.0')` |
| `_nonnegative_number` / 253 | `type(value) not in (int, float) or isinstance(value, bool)` | `raise TypeError(f'{name} must be an int or float')` |
| `_nonnegative_number` / 256 | `not math.isfinite(result) or result < 0.0` | `raise ValueError(f'{name} must be finite and non-negative')` |
| `_positive_number` / 263 | `result <= 0.0` | `raise ValueError(f'{name} must be positive')` |
| `_optional_timestamp` / 272 | `type(value) is not int or value < 0` | `raise ValueError(f'{name} must be a non-negative int or null')` |
| `_confirmation_requested` / 291 | `type(value) is not bool` | `raise TypeError('requires_confirmation/confirm_required must be bool')` |
