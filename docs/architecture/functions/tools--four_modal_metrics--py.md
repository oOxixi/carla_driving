# four_modal_metrics：功能记录

上级模块：[模块说明](../modules/support-tools.md) · 实现：[tools/four_modal_metrics.py](../../../tools/four_modal_metrics.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [维护工具的运行上下文和证据范围](environment-delivery.md)

## 功能职责与范围

Metric policy for the four-modal real-model benchmark.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `summarize_latency`

源码位置：[tools/four_modal_metrics.py 第 11 行](../../../tools/four_modal_metrics.py#L11)。类型：`FunctionDef`。

```python
summarize_latency(values: list[float]) -> dict[str, float]
```

Return the fixed, nearest-rank timing summary used by gates.

### `summarize_latency.percentile`

源码位置：[tools/four_modal_metrics.py 第 17 行](../../../tools/four_modal_metrics.py#L17)。类型：`FunctionDef`。

```python
summarize_latency.percentile(quantile: float) -> float
```

【summarize_latency.percentile】根据紧邻签名和函数体完成维护工具的数据检查、生成、评测或证据处理中的局部职责；返回、状态、副作用和异常以本页下方调用/raise记录为边界，名称本身不增加额外保证。

### `evaluate_official_gates`

源码位置：[tools/four_modal_metrics.py 第 30 行](../../../tools/four_modal_metrics.py#L30)。类型：`FunctionDef`。

```python
evaluate_official_gates(metrics: dict[str, object]) -> dict[str, object]
```

Apply latency gates before the accuracy and stability phases.

### `evaluate_official_verdict`

源码位置：[tools/four_modal_metrics.py 第 51 行](../../../tools/four_modal_metrics.py#L51)。类型：`FunctionDef`。

```python
evaluate_official_verdict(metrics: dict[str, object], accuracy: dict[str, object], *, scenario_completion: float | None) -> dict[str, object]
```

Aggregate only measured official thresholds without inventing scenarios.

### `_percentile`

源码位置：[tools/four_modal_metrics.py 第 107 行](../../../tools/four_modal_metrics.py#L107)。类型：`FunctionDef`。

```python
_percentile(values: list[float], quantile: float) -> float | None
```

【_percentile】根据紧邻签名和函数体完成维护工具的数据检查、生成、评测或证据处理中的局部职责；返回、状态、副作用和异常以本页下方调用/raise记录为边界，名称本身不增加额外保证。

### `_latency`

源码位置：[tools/four_modal_metrics.py 第 118 行](../../../tools/four_modal_metrics.py#L118)。类型：`FunctionDef`。

```python
_latency(values: list[float]) -> dict[str, float | None]
```

【_latency】根据紧邻签名和函数体完成维护工具的数据检查、生成、评测或证据处理中的局部职责；返回、状态、副作用和异常以本页下方调用/raise记录为边界，名称本身不增加额外保证。

### `_is_safety_fault`

源码位置：[tools/four_modal_metrics.py 第 128 行](../../../tools/four_modal_metrics.py#L128)。类型：`FunctionDef`。

```python
_is_safety_fault(record: dict[str, Any]) -> bool
```

【_is_safety_fault】根据紧邻签名和函数体完成维护工具的数据检查、生成、评测或证据处理中的局部职责；返回、状态、副作用和异常以本页下方调用/raise记录为边界，名称本身不增加额外保证。

### `_contract_pass`

源码位置：[tools/four_modal_metrics.py 第 132 行](../../../tools/four_modal_metrics.py#L132)。类型：`FunctionDef`。

```python
_contract_pass(record: dict[str, Any]) -> bool
```

【_contract_pass】根据紧邻签名和函数体完成维护工具的数据检查、生成、评测或证据处理中的局部职责；返回、状态、副作用和异常以本页下方调用/raise记录为边界，名称本身不增加额外保证。

### `_raw_target_ok`

源码位置：[tools/four_modal_metrics.py 第 138 行](../../../tools/four_modal_metrics.py#L138)。类型：`FunctionDef`。

```python
_raw_target_ok(record: dict[str, Any]) -> bool
```

【_raw_target_ok】从参数、文件、环境或缓存解析维护工具的数据检查、生成、评测或证据处理所需输入；路径优先级、默认值和缺失处理以函数体为准，读取成功不自动证明内容身份正确。

### `_asr_exact`

源码位置：[tools/four_modal_metrics.py 第 149 行](../../../tools/four_modal_metrics.py#L149)。类型：`FunctionDef`。

```python
_asr_exact(record: dict[str, Any]) -> bool
```

【_asr_exact】根据紧邻签名和函数体完成维护工具的数据检查、生成、评测或证据处理中的局部职责；返回、状态、副作用和异常以本页下方调用/raise记录为边界，名称本身不增加额外保证。

### `summarize_records`

源码位置：[tools/four_modal_metrics.py 第 156 行](../../../tools/four_modal_metrics.py#L156)。类型：`FunctionDef`。

```python
summarize_records(records: list[dict[str, Any]]) -> dict[str, Any]
```

Separate answerable perception from deliberate safety fault injection.

### `summarize_records.ratio`

源码位置：[tools/four_modal_metrics.py 第 163 行](../../../tools/four_modal_metrics.py#L163)。类型：`FunctionDef`。

```python
summarize_records.ratio(subset: list[dict[str, Any]], predicate: Callable[[dict[str, Any]], bool]) -> float | None
```

【summarize_records.ratio】生成或记录维护工具的数据检查、生成、评测或证据处理的文件/元数据；执行前要核对目标路径与覆盖行为，执行后以内容哈希、返回码和消费方复核，不能仅以文件存在判定通过。

## 内部调用与异常路径

- `summarize_latency` 调用：`ValueError`, `len`, `math.ceil`, `min`, `percentile`, `sorted`, `statistics.fmean`.
- `evaluate_official_gates` 调用：`ValueError`, `float`, `isinstance`.
- `evaluate_official_verdict` 调用：`ValueError`, `accuracy.get`, `asr.get`, `float`, `gates.items`, `isinstance`, `multimodal.get`.
- `_percentile` 调用：`int`, `len`, `min`, `sorted`.
- `_latency` 调用：`_percentile`, `max`, `statistics.fmean`.
- `_is_safety_fault` 调用：`bool`, `record.get`, `record.get('expected', {}).get`.
- `_contract_pass` 调用：`_is_safety_fault`, `bool`.
- `_raw_target_ok` 调用：`(record.get('decision') or {}).get`, `grounding.get`, `record.get`, `record.get('expected', {}).get`.
- `_asr_exact` 调用：`bool`, `normalize`, `re.sub`, `record.get`, `str`.
- `summarize_records` 调用：`(record.get('target_grounding') or {}).get`, `Counter`, `ValueError`, `_is_safety_fault`, `_latency`, `bool`, `dict`, `float`, `len`, `predicate`, `ratio`, `record.get`, `record.get('voice_command', {}).get`, `sorted`, `sum`.
- `percentile` 调用：`len`, `math.ceil`, `min`.
- `ratio` 调用：`bool`, `len`, `predicate`, `sum`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `evaluate_official_gates`，第 34 行：`ValueError('end_to_end_ms must be a timing summary')`。
- `evaluate_official_verdict`，第 61 行：`ValueError('timing summaries must be dictionaries')`。
- `evaluate_official_verdict`，第 65 行：`ValueError('accuracy must include ASR and multimodal summaries')`。
- `summarize_latency`，第 15 行：`ValueError('latency sample list is empty')`。
- `summarize_records`，第 159 行：`ValueError('records must not be empty')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [integration/tests/test_qwen_four_modal_stress_set.py](../../../integration/tests/test_qwen_four_modal_stress_set.py)
- [tools/finalize_four_modal_report.py](../../../tools/finalize_four_modal_report.py)
- [tools/run_four_modal_full_chain.py](../../../tools/run_four_modal_full_chain.py)

## 后续修改需要一起阅读

- [上级模块](../modules/support-tools.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `tools/four_modal_metrics.py`

来源 SHA256：`6f0ac44b85735e5fefb5280bdb3592d0a335785548c40897eb90e14498335771`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `summarize_latency` / 15 | `not ordered` | `raise ValueError('latency sample list is empty')` |
| `evaluate_official_gates` / 34 | `not isinstance(end_to_end, dict)` | `raise ValueError('end_to_end_ms must be a timing summary')` |
| `evaluate_official_verdict` / 61 | `not isinstance(instruction, dict) or not isinstance(end_to_end, dict)` | `raise ValueError('timing summaries must be dictionaries')` |
| `evaluate_official_verdict` / 65 | `not isinstance(asr, dict) or not isinstance(multimodal, dict)` | `raise ValueError('accuracy must include ASR and multimodal summaries')` |
| `summarize_records` / 159 | `not records` | `raise ValueError('records must not be empty')` |
