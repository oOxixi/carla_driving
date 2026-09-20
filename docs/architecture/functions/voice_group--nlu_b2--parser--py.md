# parser：功能记录

上级模块：[模块说明](../modules/support-voice.md) · 实现：[voice_group/nlu_b2/parser.py](../../../voice_group/nlu_b2/parser.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [ASR、NLU、复核与命令交付](voice-command-production.md)

## 功能职责与范围

Rule-based B2 parser for vehicle voice commands.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `ParserConfig.min_speed_kmh: int`；默认：`0`。
- `ParserConfig.max_speed_kmh: int`；默认：`80`。
- `ParserConfig.low_confidence_threshold: float`；默认：`0.6`。
- `ParserConfig.low_asr_confidence_threshold: float`；默认：`0.6`。
- `ParserConfig.default_pull_over_side: str`；默认：`'RIGHT'`。
- `ParseContext.request_id: Any | None`；默认：`未在声明处设置`。
- `ParseContext.original_text: str`；默认：`未在声明处设置`。
- `ParseContext.normalized_text: str`；默认：`未在声明处设置`。
- `ParseContext.intent: str`；默认：`未在声明处设置`。
- `ParseContext.intent_confidence: float`；默认：`未在声明处设置`。
- `ParseContext.asr_confidence: float | None`；默认：`None`。
- `ParseContext.b1_status: str | None`；默认：`None`。
- `ParseContext.route: str`；默认：`'qwen'`。
- `ParseContext.reason: str | None`；默认：`None`。
- `ParseContext.b1_latency_ms: float | None`；默认：`None`。
- `ParseContext.slots: dict[str, Any]`；默认：`field(default_factory=dict)`。
- `ParseContext.errors: list[dict[str, str]]`；默认：`field(default_factory=list)`。
- `ParseContext.warnings: list[dict[str, str]]`；默认：`field(default_factory=list)`。

## 功能入口：输入、输出与实现说明

### `ParserConfig`

源码位置：[voice_group/nlu_b2/parser.py 第 31 行](../../../voice_group/nlu_b2/parser.py#L31)。类型：`ClassDef`。

Runtime limits agreed with the vehicle-control side.

### `ParseContext`

源码位置：[voice_group/nlu_b2/parser.py 第 42 行](../../../voice_group/nlu_b2/parser.py#L42)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ParseContext.error`

源码位置：[voice_group/nlu_b2/parser.py 第 57 行](../../../voice_group/nlu_b2/parser.py#L57)。类型：`FunctionDef`。

```python
ParseContext.error(self, code: str, message: str) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ParseContext.warning`

源码位置：[voice_group/nlu_b2/parser.py 第 60 行](../../../voice_group/nlu_b2/parser.py#L60)。类型：`FunctionDef`。

```python
ParseContext.warning(self, code: str, message: str) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `CommandParser`

源码位置：[voice_group/nlu_b2/parser.py 第 64 行](../../../voice_group/nlu_b2/parser.py#L64)。类型：`ClassDef`。

Extract slots, validate them, and package executable commands.

### `CommandParser.__init__`

源码位置：[voice_group/nlu_b2/parser.py 第 67 行](../../../voice_group/nlu_b2/parser.py#L67)。类型：`FunctionDef`。

```python
CommandParser.__init__(self, config: ParserConfig | None=None) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `CommandParser.parse`

源码位置：[voice_group/nlu_b2/parser.py 第 83 行](../../../voice_group/nlu_b2/parser.py#L83)。类型：`FunctionDef`。

```python
CommandParser.parse(self, b1_result: dict[str, Any]) -> dict[str, Any]
```

Parse B1 output into the final JSON command consumed by D.

### `CommandParser._build_context`

源码位置：[voice_group/nlu_b2/parser.py 第 132 行](../../../voice_group/nlu_b2/parser.py#L132)。类型：`FunctionDef`。

```python
CommandParser._build_context(self, b1_result: dict[str, Any]) -> ParseContext
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `CommandParser._blocking_b1_error`

源码位置：[voice_group/nlu_b2/parser.py 第 160 行](../../../voice_group/nlu_b2/parser.py#L160)。类型：`FunctionDef`。

```python
CommandParser._blocking_b1_error(ctx: ParseContext) -> tuple[str, str] | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `CommandParser._handle_set_speed`

源码位置：[voice_group/nlu_b2/parser.py 第 169 行](../../../voice_group/nlu_b2/parser.py#L169)。类型：`FunctionDef`。

```python
CommandParser._handle_set_speed(self, ctx: ParseContext) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `CommandParser._handle_change_lane`

源码位置：[voice_group/nlu_b2/parser.py 第 177 行](../../../voice_group/nlu_b2/parser.py#L177)。类型：`FunctionDef`。

```python
CommandParser._handle_change_lane(self, ctx: ParseContext) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `CommandParser._handle_pull_over`

源码位置：[voice_group/nlu_b2/parser.py 第 187 行](../../../voice_group/nlu_b2/parser.py#L187)。类型：`FunctionDef`。

```python
CommandParser._handle_pull_over(self, ctx: ParseContext) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `CommandParser._handle_stop`

源码位置：[voice_group/nlu_b2/parser.py 第 199 行](../../../voice_group/nlu_b2/parser.py#L199)。类型：`FunctionDef`。

```python
CommandParser._handle_stop(self, ctx: ParseContext) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `CommandParser._handle_avoid_obstacle`

源码位置：[voice_group/nlu_b2/parser.py 第 202 行](../../../voice_group/nlu_b2/parser.py#L202)。类型：`FunctionDef`。

```python
CommandParser._handle_avoid_obstacle(self, ctx: ParseContext) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `CommandParser._handle_keep_lane`

源码位置：[voice_group/nlu_b2/parser.py 第 214 行](../../../voice_group/nlu_b2/parser.py#L214)。类型：`FunctionDef`。

```python
CommandParser._handle_keep_lane(self, ctx: ParseContext) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `CommandParser._handle_follow_route`

源码位置：[voice_group/nlu_b2/parser.py 第 217 行](../../../voice_group/nlu_b2/parser.py#L217)。类型：`FunctionDef`。

```python
CommandParser._handle_follow_route(self, ctx: ParseContext) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `CommandParser._handle_turn`

源码位置：[voice_group/nlu_b2/parser.py 第 225 行](../../../voice_group/nlu_b2/parser.py#L225)。类型：`FunctionDef`。

```python
CommandParser._handle_turn(self, ctx: ParseContext) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `CommandParser._handle_relative_speed`

源码位置：[voice_group/nlu_b2/parser.py 第 235 行](../../../voice_group/nlu_b2/parser.py#L235)。类型：`FunctionDef`。

```python
CommandParser._handle_relative_speed(self, ctx: ParseContext) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `CommandParser._validate_common_safety`

源码位置：[voice_group/nlu_b2/parser.py 第 280 行](../../../voice_group/nlu_b2/parser.py#L280)。类型：`FunctionDef`。

```python
CommandParser._validate_common_safety(self, ctx: ParseContext) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `CommandParser._status`

源码位置：[voice_group/nlu_b2/parser.py 第 295 行](../../../voice_group/nlu_b2/parser.py#L295)。类型：`FunctionDef`。

```python
CommandParser._status(ctx: ParseContext) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `parse_command`

源码位置：[voice_group/nlu_b2/parser.py 第 315 行](../../../voice_group/nlu_b2/parser.py#L315)。类型：`FunctionDef`。

```python
parse_command(b1_result: dict[str, Any], config: ParserConfig | None=None) -> dict[str, Any]
```

Convenience function for callers that do not need a parser instance.

### `_normalize_text`

源码位置：[voice_group/nlu_b2/parser.py 第 321 行](../../../voice_group/nlu_b2/parser.py#L321)。类型：`FunctionDef`。

```python
_normalize_text(text: str) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_extract_direction`

源码位置：[voice_group/nlu_b2/parser.py 第 333 行](../../../voice_group/nlu_b2/parser.py#L333)。类型：`FunctionDef`。

```python
_extract_direction(text: str) -> str | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_extract_speed`

源码位置：[voice_group/nlu_b2/parser.py 第 348 行](../../../voice_group/nlu_b2/parser.py#L348)。类型：`FunctionDef`。

```python
_extract_speed(text: str) -> int | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_extract_obstacle_target`

源码位置：[voice_group/nlu_b2/parser.py 第 359 行](../../../voice_group/nlu_b2/parser.py#L359)。类型：`FunctionDef`。

```python
_extract_obstacle_target(text: str) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_extract_target`

源码位置：[voice_group/nlu_b2/parser.py 第 375 行](../../../voice_group/nlu_b2/parser.py#L375)。类型：`FunctionDef`。

```python
_extract_target(text: str) -> str | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_chinese_number_to_int`

源码位置：[voice_group/nlu_b2/parser.py 第 386 行](../../../voice_group/nlu_b2/parser.py#L386)。类型：`FunctionDef`。

```python
_chinese_number_to_int(value: str) -> int | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_safe_float`

源码位置：[voice_group/nlu_b2/parser.py 第 412 行](../../../voice_group/nlu_b2/parser.py#L412)。类型：`FunctionDef`。

```python
_safe_float(value: Any, default: float) -> float
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_optional_float`

源码位置：[voice_group/nlu_b2/parser.py 第 419 行](../../../voice_group/nlu_b2/parser.py#L419)。类型：`FunctionDef`。

```python
_optional_float(value: Any) -> float | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_optional_lower`

源码位置：[voice_group/nlu_b2/parser.py 第 428 行](../../../voice_group/nlu_b2/parser.py#L428)。类型：`FunctionDef`。

```python
_optional_lower(value: Any) -> str | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `parse_command` 调用：`CommandParser`, `CommandParser(config).parse`.
- `_normalize_text` 调用：`normalized.replace`, `normalized.replace('公里/小时', 'KM/H').replace`, `normalized.replace('千米/小时', 'KM/H').replace`, `normalized.upper`, `normalized.upper().replace`, `re.sub`, `str.maketrans`, `text.translate`.
- `_extract_direction` 调用：`any`.
- `_extract_speed` 调用：`_chinese_number_to_int`, `arabic.group`, `chinese_match.group`, `int`, `re.search`.
- `_extract_target` 调用：`match.group`, `re.search`.
- `_chinese_number_to_int` 调用：`_chinese_number_to_int`, `digits.get`, `value.partition`.
- `_safe_float` 调用：`float`.
- `_optional_float` 调用：`float`.
- `_optional_lower` 调用：`str`, `str(value).strip`, `str(value).strip().lower`.
- `error` 调用：`self.errors.append`.
- `warning` 调用：`self.warnings.append`.
- `__init__` 调用：`ParserConfig`.
- `parse` 调用：`ctx.error`, `ctx.warning`, `round`, `self._blocking_b1_error`, `self._build_context`, `self._handlers[ctx.intent]`, `self._status`, `self._validate_common_safety`, `time.perf_counter`.
- `_build_context` 调用：`ParseContext`, `_normalize_text`, `_optional_float`, `_optional_lower`, `_safe_float`, `b1_result.get`, `str`, `str(b1_result.get('intent', '') or '').strip`, `str(b1_result.get('intent', '') or '').strip().upper`.
- `_handle_set_speed` 调用：`_extract_speed`, `ctx.error`.
- `_handle_change_lane` 调用：`_extract_direction`, `ctx.error`.
- `_handle_pull_over` 调用：`_extract_direction`, `ctx.error`, `ctx.warning`.
- `_handle_avoid_obstacle` 调用：`_extract_direction`, `_extract_obstacle_target`, `ctx.error`, `ctx.warning`.
- `_handle_follow_route` 调用：`_extract_target`, `ctx.warning`.
- `_handle_turn` 调用：`_extract_direction`, `ctx.error`.
- `_handle_relative_speed` 调用：`_extract_speed`, `any`, `ctx.warning`, `re.search`.
- `_validate_common_safety` 调用：`ctx.error`, `ctx.slots.get`, `isinstance`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- 未发现显式 raise；不代表运行不会失败。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [integration/tests/test_voice_qwen_semantic_coverage.py](../../../integration/tests/test_voice_qwen_semantic_coverage.py)
- [tools/evaluate_saved_asr_nlu.py](../../../tools/evaluate_saved_asr_nlu.py)
- [tools/run_group1_voice_onnx_benchmark.py](../../../tools/run_group1_voice_onnx_benchmark.py)
- [tools/run_group1_voice_text_regression.py](../../../tools/run_group1_voice_text_regression.py)
- [voice_group/nlu_b2/__init__.py](../../../voice_group/nlu_b2/__init__.py)
- [voice_group/nlu_b2/cli.py](../../../voice_group/nlu_b2/cli.py)
- [voice_group/pipeline.py](../../../voice_group/pipeline.py)
- [voice_group/tests/test_manifest_regression.py](../../../voice_group/tests/test_manifest_regression.py)
- [voice_group/tests/test_safety_boundary.py](../../../voice_group/tests/test_safety_boundary.py)

## 后续修改需要一起阅读

- [上级模块](../modules/support-voice.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `voice_group/nlu_b2/parser.py`

来源 SHA256：`41ce217b6f05795a14cc8fbbf8275561b732251630577e300ae69ded9a670eed`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `ParserConfig.min_speed_kmh` | `int` | `0` |
| `ParserConfig.max_speed_kmh` | `int` | `80` |
| `ParserConfig.low_confidence_threshold` | `float` | `0.6` |
| `ParserConfig.low_asr_confidence_threshold` | `float` | `0.6` |
| `ParserConfig.default_pull_over_side` | `str` | `'RIGHT'` |
| `ParseContext.request_id` | `Any &#124; None` | `无声明默认；构造/赋值方提供` |
| `ParseContext.original_text` | `str` | `无声明默认；构造/赋值方提供` |
| `ParseContext.normalized_text` | `str` | `无声明默认；构造/赋值方提供` |
| `ParseContext.intent` | `str` | `无声明默认；构造/赋值方提供` |
| `ParseContext.intent_confidence` | `float` | `无声明默认；构造/赋值方提供` |
| `ParseContext.asr_confidence` | `float &#124; None` | `None` |
| `ParseContext.b1_status` | `str &#124; None` | `None` |
| `ParseContext.route` | `str` | `'qwen'` |
| `ParseContext.reason` | `str &#124; None` | `None` |
| `ParseContext.b1_latency_ms` | `float &#124; None` | `None` |
| `ParseContext.slots` | `dict[str, Any]` | `field(default_factory=dict)` |
| `ParseContext.errors` | `list[dict[str, str]]` | `field(default_factory=list)` |
| `ParseContext.warnings` | `list[dict[str, str]]` | `field(default_factory=list)` |
