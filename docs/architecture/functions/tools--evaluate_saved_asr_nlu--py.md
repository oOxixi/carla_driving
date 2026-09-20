# evaluate_saved_asr_nlu：功能记录

上级模块：[模块说明](../modules/support-tools.md) · 实现：[tools/evaluate_saved_asr_nlu.py](../../../tools/evaluate_saved_asr_nlu.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [维护工具的运行上下文和证据范围](environment-delivery.md)

## 功能职责与范围

Re-evaluate saved ASR transcripts through the current NLU implementation.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `_percentile`

源码位置：[tools/evaluate_saved_asr_nlu.py 第 28 行](../../../tools/evaluate_saved_asr_nlu.py#L28)。类型：`FunctionDef`。

```python
_percentile(values: list[float], quantile: float) -> float | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `evaluate_saved_transcripts`

源码位置：[tools/evaluate_saved_asr_nlu.py 第 39 行](../../../tools/evaluate_saved_asr_nlu.py#L39)。类型：`FunctionDef`。

```python
evaluate_saved_transcripts(payload: dict[str, Any], *, warmup: int=20, latency_samples: int=50) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `evaluate_saved_transcripts.summary`

源码位置：[tools/evaluate_saved_asr_nlu.py 第 92 行](../../../tools/evaluate_saved_asr_nlu.py#L92)。类型：`FunctionDef`。

```python
evaluate_saved_transcripts.summary(stats: Counter[str]) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[tools/evaluate_saved_asr_nlu.py 第 119 行](../../../tools/evaluate_saved_asr_nlu.py#L119)。类型：`FunctionDef`。

```python
main() -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `_percentile` 调用：`len`, `math.ceil`, `math.floor`, `sorted`.
- `evaluate_saved_transcripts` 调用：`Counter`, `_percentile`, `all`, `by_language.items`, `defaultdict`, `dict`, `enumerate`, `expected_slots.items`, `failures.append`, `int`, `latency_ms.append`, `len`, `list`, `max`, `parse_command`, `payload.get`, `payload.get('overall', {}).get`, `process_asr_text`, `range`, `record.get`, `result['slots'].get`, `round`, `sorted`, `str`, `sum`, `summary`, `time.perf_counter_ns`.
- `main` 调用：`argparse.ArgumentParser`, `args.input.read_text`, `evaluate_saved_transcripts`, `json.dumps`, `json.loads`, `parser.add_argument`, `parser.parse_args`, `print`, `result.pop`.
- `summary` 调用：`round`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- 未发现显式 raise；不代表运行不会失败。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 121 行：`parser.add_argument('input', type=Path)`。
- 第 122 行：`parser.add_argument('--failures', action='store_true')`。
- 第 123 行：`parser.add_argument('--warmup', type=int, default=20)`。
- 第 124 行：`parser.add_argument('--latency-samples', type=int, default=50)`。

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

### `tools/evaluate_saved_asr_nlu.py`

来源 SHA256：`4bf34346f73402344383b066ad3e3d658764d189ce8529eb94dc3e709b6df15f`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 121 | `'input'` | `type=Path` |
| 122 | `'--failures'` | `action='store_true'` |
| 123 | `'--warmup'` | `type=int; default=20` |
| 124 | `'--latency-samples'` | `type=int; default=50` |
