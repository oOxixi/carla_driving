# run_group1_voice_text_regression：功能记录

上级模块：[模块说明](../modules/support-tools.md) · 实现：[tools/run_group1_voice_text_regression.py](../../../tools/run_group1_voice_text_regression.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [维护工具的运行上下文和证据范围](environment-delivery.md)

## 功能职责与范围

Run deterministic Group 1 task 5 NLU/safety regression from a voice manifest.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `_write_json`

源码位置：[tools/run_group1_voice_text_regression.py 第 64 行](../../../tools/run_group1_voice_text_regression.py#L64)。类型：`FunctionDef`。

```python
_write_json(path: Path, payload: Any) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_git_state`

源码位置：[tools/run_group1_voice_text_regression.py 第 72 行](../../../tools/run_group1_voice_text_regression.py#L72)。类型：`FunctionDef`。

```python
_git_state() -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_percentile`

源码位置：[tools/run_group1_voice_text_regression.py 第 94 行](../../../tools/run_group1_voice_text_regression.py#L94)。类型：`FunctionDef`。

```python
_percentile(values: list[float], percentile: float) -> float | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_latency_stats`

源码位置：[tools/run_group1_voice_text_regression.py 第 107 行](../../../tools/run_group1_voice_text_regression.py#L107)。类型：`FunctionDef`。

```python
_latency_stats(values: list[float]) -> dict[str, float | int | None]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_run_text`

源码位置：[tools/run_group1_voice_text_regression.py 第 117 行](../../../tools/run_group1_voice_text_regression.py#L117)。类型：`FunctionDef`。

```python
_run_text(text: str, request_id: str, asr_confidence: float | None) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_slots_match`

源码位置：[tools/run_group1_voice_text_regression.py 第 127 行](../../../tools/run_group1_voice_text_regression.py#L127)。类型：`FunctionDef`。

```python
_slots_match(actual: dict[str, Any], expected: dict[str, Any]) -> bool
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_error_codes`

源码位置：[tools/run_group1_voice_text_regression.py 第 131 行](../../../tools/run_group1_voice_text_regression.py#L131)。类型：`FunctionDef`。

```python
_error_codes(command: dict[str, Any]) -> set[str]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_record`

源码位置：[tools/run_group1_voice_text_regression.py 第 135 行](../../../tools/run_group1_voice_text_regression.py#L135)。类型：`FunctionDef`。

```python
_record(item: dict[str, Any], asr_confidence: float) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_low_confidence_check`

源码位置：[tools/run_group1_voice_text_regression.py 第 179 行](../../../tools/run_group1_voice_text_regression.py#L179)。类型：`FunctionDef`。

```python
_low_confidence_check(item: dict[str, Any], low_confidence: float) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_run_safety_probe`

源码位置：[tools/run_group1_voice_text_regression.py 第 194 行](../../../tools/run_group1_voice_text_regression.py#L194)。类型：`FunctionDef`。

```python
_run_safety_probe(probe: dict[str, Any]) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_summarize`

源码位置：[tools/run_group1_voice_text_regression.py 第 208 行](../../../tools/run_group1_voice_text_regression.py#L208)。类型：`FunctionDef`。

```python
_summarize(records: list[dict[str, Any]]) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_grouped_summary`

源码位置：[tools/run_group1_voice_text_regression.py 第 240 行](../../../tools/run_group1_voice_text_regression.py#L240)。类型：`FunctionDef`。

```python
_grouped_summary(records: list[dict[str, Any]], key: str) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_markdown_report`

源码位置：[tools/run_group1_voice_text_regression.py 第 247 行](../../../tools/run_group1_voice_text_regression.py#L247)。类型：`FunctionDef`。

```python
_markdown_report(report: dict[str, Any]) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[tools/run_group1_voice_text_regression.py 第 306 行](../../../tools/run_group1_voice_text_regression.py#L306)。类型：`FunctionDef`。

```python
main() -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `_write_json` 调用：`json.dumps`, `path.parent.mkdir`, `path.write_text`.
- `_git_state` 调用：`bool`, `commit.stdout.strip`, `line.strip`, `status.stdout.splitlines`, `status.stdout.strip`, `subprocess.run`.
- `_percentile` 调用：`len`, `math.ceil`, `math.floor`, `round`, `sorted`.
- `_latency_stats` 调用：`_percentile`, `len`, `max`, `round`, `statistics.fmean`.
- `_run_text` 调用：`parse_command`, `process_asr_text`.
- `_slots_match` 调用：`actual.get`, `all`, `expected.items`.
- `_error_codes` 调用：`command.get`, `item.get`.
- `_record` 调用：`_run_text`, `_slots_match`, `b1.get`, `b2.get`, `expected_slots.get`, `isinstance`, `item.get`, `round`, `time.perf_counter`.
- `_low_confidence_check` 调用：`_error_codes`, `_run_text`, `b2.get`, `item.get`.
- `_run_safety_probe` 调用：`_error_codes`, `_run_text`, `b2.get`.
- `_summarize` 调用：`Counter`, `_latency_stats`, `dict`, `float`, `latency_values.items`, `len`, `record.get`, `record.get('latency', {}).get`, `round`, `sum`.
- `_grouped_summary` 调用：`_summarize`, `defaultdict`, `grouped.items`, `grouped[str(record.get(key))].append`, `record.get`, `sorted`, `str`.
- `_markdown_report` 调用：`'\n'.join`, `lines.append`, `lines.extend`.
- `main` 调用：`_git_state`, `_grouped_summary`, `_low_confidence_check`, `_markdown_report`, `_record`, `_run_safety_probe`, `_summarize`, `_write_json`, `all`, `argparse.ArgumentParser`, `args.manifest.read_text`, `args.manifest.resolve`, `args.output.with_suffix`, `args.output.with_suffix('.md').write_text`, `datetime.now`, `datetime.now(timezone.utc).isoformat`, `item.get`, `json.loads`, `len`, `parser.add_argument`, `parser.parse_args`, `print`, `round`, `str`, `sum`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- 未发现显式 raise；不代表运行不会失败。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 308 行：`parser.add_argument('--manifest', type=Path, default=DEFAULT_MANIFEST)`。
- 第 309 行：`parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)`。
- 第 310 行：`parser.add_argument('--asr-confidence', type=float, default=1.0)`。
- 第 311 行：`parser.add_argument('--low-asr-confidence', type=float, default=0.2)`。
- 第 312 行：`parser.add_argument('--min-intent-accuracy', type=float, default=0.98)`。
- 第 313 行：`parser.add_argument('--min-slot-accuracy', type=float, default=0.98)`。
- 第 314 行：`parser.add_argument('--limit', type=int)`。

## 上下游与关联验证

静态导入的项目内实现：

- [voice_group/nlu_b2/parser.py](../../../voice_group/nlu_b2/parser.py)
- [voice_group/vehicle_nlu/src/b1_service.py](../../../voice_group/vehicle_nlu/src/b1_service.py)

静态 import 消费者（含测试）：

- 未发现静态 import 消费者；命令行、间接注册、文件路径加载不在此清单内。

## 后续修改需要一起阅读

- [上级模块](../modules/support-tools.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `tools/run_group1_voice_text_regression.py`

来源 SHA256：`ab6d1ee2c5a0bc599c4dd2d9af41a3a7f7b50bdc2cbc207bacdd2c23f4065ccb`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 308 | `'--manifest'` | `type=Path; default=DEFAULT_MANIFEST` |
| 309 | `'--output'` | `type=Path; default=DEFAULT_OUTPUT` |
| 310 | `'--asr-confidence'` | `type=float; default=1.0` |
| 311 | `'--low-asr-confidence'` | `type=float; default=0.2` |
| 312 | `'--min-intent-accuracy'` | `type=float; default=0.98` |
| 313 | `'--min-slot-accuracy'` | `type=float; default=0.98` |
| 314 | `'--limit'` | `type=int` |
