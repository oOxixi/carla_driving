# intent_classifier：功能记录

上级模块：[模块说明](../modules/support-voice.md) · 实现：[voice_group/vehicle_nlu/src/intent_classifier.py](../../../voice_group/vehicle_nlu/src/intent_classifier.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [ASR、NLU、复核与命令交付](voice-command-production.md)

## 功能职责与范围

intent_classifier

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `IntentResult.original_text: str`；默认：`未在声明处设置`。
- `IntentResult.normalized_text: str`；默认：`未在声明处设置`。
- `IntentResult.intent: str`；默认：`未在声明处设置`。
- `IntentResult.confidence: float`；默认：`未在声明处设置`。
- `IntentResult.status: str`；默认：`未在声明处设置`。
- `IntentResult.route: str`；默认：`未在声明处设置`。
- `IntentResult.reason: Optional[str]`；默认：`未在声明处设置`。
- `IntentResult.latency_ms: float`；默认：`未在声明处设置`。

## 功能入口：输入、输出与实现说明

### `IntentResult`

源码位置：[voice_group/vehicle_nlu/src/intent_classifier.py 第 10 行](../../../voice_group/vehicle_nlu/src/intent_classifier.py#L10)。类型：`ClassDef`。

B1意图识别结果。

### `_matches`

源码位置：[voice_group/vehicle_nlu/src/intent_classifier.py 第 27 行](../../../voice_group/vehicle_nlu/src/intent_classifier.py#L27)。类型：`FunctionDef`。

```python
_matches(text: str, patterns: list[str]) -> bool
```

判断文本是否匹配任意一个正则表达式。

### `_build_result`

源码位置：[voice_group/vehicle_nlu/src/intent_classifier.py 第 36 行](../../../voice_group/vehicle_nlu/src/intent_classifier.py#L36)。类型：`FunctionDef`。

```python
_build_result(*, original_text: str, normalized_text: str, intent: str, confidence: float, status: str, route: str, reason: Optional[str], start_time: float) -> dict
```

统一创建返回结果并统计耗时。

### `_matches_any_pattern`

源码位置：[voice_group/vehicle_nlu/src/intent_classifier.py 第 245 行](../../../voice_group/vehicle_nlu/src/intent_classifier.py#L245)。类型：`FunctionDef`。

```python
_matches_any_pattern(text: str, patterns: tuple[str, ...]) -> bool
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_is_terminal_emergency_stop`

源码位置：[voice_group/vehicle_nlu/src/intent_classifier.py 第 255 行](../../../voice_group/vehicle_nlu/src/intent_classifier.py#L255)。类型：`FunctionDef`。

```python
_is_terminal_emergency_stop(text: str) -> bool
```

True when avoidance is explicitly unavailable and STOP is terminal.

### `_compound_signal_names`

源码位置：[voice_group/vehicle_nlu/src/intent_classifier.py 第 270 行](../../../voice_group/vehicle_nlu/src/intent_classifier.py#L270)。类型：`FunctionDef`。

```python
_compound_signal_names(text: str) -> set[str]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_has_compound_signal_pair`

源码位置：[voice_group/vehicle_nlu/src/intent_classifier.py 第 280 行](../../../voice_group/vehicle_nlu/src/intent_classifier.py#L280)。类型：`FunctionDef`。

```python
_has_compound_signal_pair(names: set[str]) -> bool
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_has_vulnerable_speed_continuation`

源码位置：[voice_group/vehicle_nlu/src/intent_classifier.py 第 289 行](../../../voice_group/vehicle_nlu/src/intent_classifier.py#L289)。类型：`FunctionDef`。

```python
_has_vulnerable_speed_continuation(text: str, names: set[str]) -> bool
```

Detect context-dependent speed+continuation commands.

A generic sentence such as
    "减到40公里每小时再继续行驶"
remains a single speed command.

When the same construction is conditioned on a pedestrian/bus-stop
hazard, preserving the follow-on route semantics requires the planner.

### `_contains_multiple_actions`

源码位置：[voice_group/vehicle_nlu/src/intent_classifier.py 第 317 行](../../../voice_group/vehicle_nlu/src/intent_classifier.py#L317)。类型：`FunctionDef`。

```python
_contains_multiple_actions(text: str) -> bool
```

Return True when one utterance requires multiple high-level semantics.

Complex commands keep their full text for Qwen. Terminal emergency-stop
commands remain a single intent hint even when they describe avoidance as
unavailable; the independent safety layer still brakes while Qwen runs.

### `classify_intent`

源码位置：[voice_group/vehicle_nlu/src/intent_classifier.py 第 339 行](../../../voice_group/vehicle_nlu/src/intent_classifier.py#L339)。类型：`FunctionDef`。

```python
classify_intent(text: str) -> dict
```

将车控文本识别为一个意图。

当前支持：
    EMERGENCY_STOP
    PULL_OVER
    SET_SPEED
    AVOID_OBSTACLE
    CHANGE_LANE
    KEEP_LANE
    SPEED_UP
    SLOW_DOWN
    STOP
    UNKNOWN

## 内部调用与异常路径

- `_matches` 调用：`any`, `re.search`.
- `_build_result` 调用：`IntentResult`, `asdict`, `round`, `time.perf_counter`.
- `_matches_any_pattern` 调用：`any`, `re.search`.
- `_is_terminal_emergency_stop` 调用：`_matches_any_pattern`.
- `_compound_signal_names` 调用：`_COMPOUND_SIGNAL_PATTERNS.items`, `_matches_any_pattern`, `names.add`, `set`.
- `_has_compound_signal_pair` 调用：`any`, `pair.issubset`.
- `_has_vulnerable_speed_continuation` 调用：`_matches_any_pattern`.
- `_contains_multiple_actions` 调用：`_compound_signal_names`, `_has_compound_signal_pair`, `_has_vulnerable_speed_continuation`, `_is_terminal_emergency_stop`.
- `classify_intent` 调用：`_build_result`, `_contains_multiple_actions`, `_matches`, `normalize_text`, `time.perf_counter`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- 未发现显式 raise；不代表运行不会失败。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [voice_group/vehicle_nlu/src/normalizer.py](../../../voice_group/vehicle_nlu/src/normalizer.py)

静态 import 消费者（含测试）：

- [integration/tests/test_voice_compound_routing.py](../../../integration/tests/test_voice_compound_routing.py)
- [voice_group/vehicle_nlu/src/b1_service.py](../../../voice_group/vehicle_nlu/src/b1_service.py)

## 后续修改需要一起阅读

- [上级模块](../modules/support-voice.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `voice_group/vehicle_nlu/src/intent_classifier.py`

来源 SHA256：`fc8c1230295c83b6a8f5b66ca7354442c70257624ca4be162c73c5571c482d8a`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `IntentResult.original_text` | `str` | `无声明默认；构造/赋值方提供` |
| `IntentResult.normalized_text` | `str` | `无声明默认；构造/赋值方提供` |
| `IntentResult.intent` | `str` | `无声明默认；构造/赋值方提供` |
| `IntentResult.confidence` | `float` | `无声明默认；构造/赋值方提供` |
| `IntentResult.status` | `str` | `无声明默认；构造/赋值方提供` |
| `IntentResult.route` | `str` | `无声明默认；构造/赋值方提供` |
| `IntentResult.reason` | `Optional[str]` | `无声明默认；构造/赋值方提供` |
| `IntentResult.latency_ms` | `float` | `无声明默认；构造/赋值方提供` |
