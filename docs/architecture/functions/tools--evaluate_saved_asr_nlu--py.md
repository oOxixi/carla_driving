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

【_percentile】根据紧邻签名和函数体完成维护工具的数据检查、生成、评测或证据处理中的局部职责；返回、状态、副作用和异常以本页下方调用/raise记录为边界，名称本身不增加额外保证。

### `evaluate_saved_transcripts`

源码位置：[tools/evaluate_saved_asr_nlu.py 第 39 行](../../../tools/evaluate_saved_asr_nlu.py#L39)。类型：`FunctionDef`。

```python
evaluate_saved_transcripts(payload: dict[str, Any], *, warmup: int=20, latency_samples: int=50) -> dict[str, Any]
```

【evaluate_saved_transcripts】生成或记录维护工具的数据检查、生成、评测或证据处理的文件/元数据；执行前要核对目标路径与覆盖行为，执行后以内容哈希、返回码和消费方复核，不能仅以文件存在判定通过。

### `evaluate_saved_transcripts.summary`

源码位置：[tools/evaluate_saved_asr_nlu.py 第 92 行](../../../tools/evaluate_saved_asr_nlu.py#L92)。类型：`FunctionDef`。

```python
evaluate_saved_transcripts.summary(stats: Counter[str]) -> dict[str, Any]
```

【evaluate_saved_transcripts.summary】生成或记录维护工具的数据检查、生成、评测或证据处理的文件/元数据；执行前要核对目标路径与覆盖行为，执行后以内容哈希、返回码和消费方复核，不能仅以文件存在判定通过。

### `main`

源码位置：[tools/evaluate_saved_asr_nlu.py 第 119 行](../../../tools/evaluate_saved_asr_nlu.py#L119)。类型：`FunctionDef`。

```python
main() -> None
```

【main】是维护工具的数据检查、生成、评测或证据处理的执行/命令入口；参数来自紧邻签名或本页CLI表，可能读取外部资源、写产物或启动服务，应以退出码、原始日志和固定输入身份判定结果。

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

来源 SHA256：`6e9e2c9127f2ee83d810b402653ed90d29e0538c7039d62b2512c27d04eada5e`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 121 | `'input'` | `type=Path` |
| 122 | `'--failures'` | `action='store_true'` |
| 123 | `'--warmup'` | `type=int; default=20` |
| 124 | `'--latency-samples'` | `type=int; default=50` |
