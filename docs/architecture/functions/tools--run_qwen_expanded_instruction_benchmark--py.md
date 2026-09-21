# run_qwen_expanded_instruction_benchmark：功能记录

上级模块：[模块说明](../modules/support-tools.md) · 实现：[tools/run_qwen_expanded_instruction_benchmark.py](../../../tools/run_qwen_expanded_instruction_benchmark.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [维护工具的运行上下文和证据范围](environment-delivery.md)

## 功能职责与范围

Evaluate Qwen on the frozen expanded CARLA language benchmark.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `build_case_prompt`

源码位置：[tools/run_qwen_expanded_instruction_benchmark.py 第 63 行](../../../tools/run_qwen_expanded_instruction_benchmark.py#L63)。类型：`FunctionDef`。

```python
build_case_prompt(record: dict[str, Any]) -> str
```

Build a prompt without exposing any evaluation label or category.

### `_percentile`

源码位置：[tools/run_qwen_expanded_instruction_benchmark.py 第 80 行](../../../tools/run_qwen_expanded_instruction_benchmark.py#L80)。类型：`FunctionDef`。

```python
_percentile(values: list[float], quantile: float) -> float | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_latency_summary`

源码位置：[tools/run_qwen_expanded_instruction_benchmark.py 第 95 行](../../../tools/run_qwen_expanded_instruction_benchmark.py#L95)。类型：`FunctionDef`。

```python
_latency_summary(values: list[float]) -> dict[str, float | int | None]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_group_metrics`

源码位置：[tools/run_qwen_expanded_instruction_benchmark.py 第 106 行](../../../tools/run_qwen_expanded_instruction_benchmark.py#L106)。类型：`FunctionDef`。

```python
_group_metrics(records: list[dict[str, Any]], field: str) -> dict[str, dict[str, float | int]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_input_integrity`

源码位置：[tools/run_qwen_expanded_instruction_benchmark.py 第 128 行](../../../tools/run_qwen_expanded_instruction_benchmark.py#L128)。类型：`FunctionDef`。

```python
_input_integrity(source_records: list[dict[str, Any]]) -> dict[str, int]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `summarize_records`

源码位置：[tools/run_qwen_expanded_instruction_benchmark.py 第 146 行](../../../tools/run_qwen_expanded_instruction_benchmark.py#L146)。类型：`FunctionDef`。

```python
summarize_records(records: list[dict[str, Any]]) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_extract_choice`

源码位置：[tools/run_qwen_expanded_instruction_benchmark.py 第 211 行](../../../tools/run_qwen_expanded_instruction_benchmark.py#L211)。类型：`FunctionDef`。

```python
_extract_choice(response: Any) -> tuple[str, float | None, list[dict[str, Any]]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_evaluate_one`

源码位置：[tools/run_qwen_expanded_instruction_benchmark.py 第 246 行](../../../tools/run_qwen_expanded_instruction_benchmark.py#L246)。类型：`AsyncFunctionDef`。

```python
_evaluate_one(*, client: Any, semaphore: asyncio.Semaphore, model: str, index: int, record: dict[str, Any], retries: int) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_select_records`

源码位置：[tools/run_qwen_expanded_instruction_benchmark.py 第 331 行](../../../tools/run_qwen_expanded_instruction_benchmark.py#L331)。类型：`FunctionDef`。

```python
_select_records(records: list[dict[str, Any]], *, categories: list[str], sample_per_category: int | None, limit: int | None) -> list[dict[str, Any]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_run`

源码位置：[tools/run_qwen_expanded_instruction_benchmark.py 第 359 行](../../../tools/run_qwen_expanded_instruction_benchmark.py#L359)。类型：`AsyncFunctionDef`。

```python
_run(args: argparse.Namespace) -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[tools/run_qwen_expanded_instruction_benchmark.py 第 505 行](../../../tools/run_qwen_expanded_instruction_benchmark.py#L505)。类型：`FunctionDef`。

```python
main() -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `build_case_prompt` 调用：`ValueError`, `instruction.strip`, `isinstance`, `json.dumps`, `record.get`.
- `_percentile` 调用：`len`, `math.ceil`, `math.floor`, `sorted`.
- `_latency_summary` 调用：`_percentile`, `len`, `max`, `statistics.fmean`.
- `_group_metrics` 调用：`defaultdict`, `groups[str(record[field])].append`, `len`, `sorted`, `str`, `sum`.
- `_input_integrity` 调用：`build_case_prompt`, `defaultdict`, `groups.values`, `groups[build_case_prompt(record)].append`, `len`, `sum`.
- `summarize_records` 调用：`ValueError`, `_group_metrics`, `_latency_summary`, `_percentile`, `by_category.values`, `confusion.items`, `counts.items`, `defaultdict`, `dict`, `float`, `len`, `record.get`, `sorted`, `statistics.fmean`, `str`, `sum`.
- `_extract_choice` 调用：`RuntimeError`, `alternatives.append`, `content.strip`, `content.strip().upper`, `float`, `getattr`, `isinstance`, `math.exp`, `max`, `min`, `str`, `str(getattr(alternative, 'token', '')).strip`, `str(getattr(alternative, 'token', '')).strip().upper`.
- `_evaluate_one` 调用：`_extract_choice`, `asyncio.sleep`, `build_case_prompt`, `client.chat.completions.create`, `list`, `range`, `record.get`, `str`, `time.perf_counter_ns`, `type`.
- `_select_records` 调用：`Counter`, `ValueError`, `record.get`, `sampled.append`, `str`.
- `_run` 调用：`''.join`, `AsyncOpenAI`, `RuntimeError`, `ValueError`, `_evaluate_one`, `_input_integrity`, `_select_records`, `args.base_url.rstrip`, `args.dataset.expanduser`, `args.dataset.expanduser().resolve`, `args.output.expanduser`, `args.output.expanduser().resolve`, `args.records_output.expanduser`, `args.records_output.expanduser().resolve`, `asyncio.Semaphore`, `asyncio.as_completed`, `asyncio.create_task`, `client.close`, `dataset_path.read_bytes`, `datetime.now`, `datetime.now(timezone.utc).isoformat`, `enumerate`, `hashlib.sha256`, `hashlib.sha256(source_bytes).hexdigest`, `int`, `isinstance`, `json.dumps`, `json.loads`, `len`, `os.environ.get`, `output.parent.mkdir`, `output.with_suffix`, `output.write_text`, `print`, `records_output.parent.mkdir`, `records_output.write_text`, `results.append`, `results.sort`, `set`, `str`, `sum`, `summarize_records`, `time.perf_counter_ns`.
- `main` 调用：`Path`, `_run`, `argparse.ArgumentParser`, `asyncio.run`, `getattr`, `name.replace`, `os.environ.get`, `parser.add_argument`, `parser.error`, `parser.parse_args`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `_extract_choice`，第 214 行：`RuntimeError('server returned no completion choices')`。
- `_extract_choice`，第 218 行：`RuntimeError('server returned an empty response')`。
- `_extract_choice`，第 221 行：`RuntimeError(f'server returned invalid action code: {code!r}')`。
- `_run`，第 363 行：`RuntimeError('install the optional client from requirements-qwen-client.txt')`。
- `_run`，第 371 行：`ValueError('dataset must be a non-empty JSON array')`。
- `_run`，第 375 行：`ValueError(f'dataset contains unsupported actions: {unknown_actions}')`。
- `_select_records`，第 355 行：`ValueError('record selection is empty')`。
- `build_case_prompt`，第 68 行：`ValueError('record template must be a non-empty string')`。
- `build_case_prompt`，第 70 行：`ValueError('record scene_constraints must be an object')`。
- `summarize_records`，第 150 行：`ValueError('records must not be empty')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 507 行：`parser.add_argument('--dataset', type=Path, default=Path('CARLA-Language-Benchmark/datasets/final_benchmark/CARLA_language_benchmark_v1_normalized.json'))`。
- 第 515 行：`parser.add_argument('--base-url', default=os.environ.get('QWEN_BASE_URL', 'http://127.0.0.1:8000/v1'))`。
- 第 519 行：`parser.add_argument('--model', default=os.environ.get('QWEN_MODEL', 'qwen2.5-vl'))`。
- 第 520 行：`parser.add_argument('--output', type=Path, required=True)`。
- 第 521 行：`parser.add_argument('--records-output', type=Path)`。
- 第 522 行：`parser.add_argument('--category', action='append', default=[])`。
- 第 523 行：`parser.add_argument('--sample-per-category', type=int)`。
- 第 524 行：`parser.add_argument('--limit', type=int)`。
- 第 525 行：`parser.add_argument('--concurrency', type=int, default=8)`。
- 第 526 行：`parser.add_argument('--timeout-s', type=float, default=20.0)`。
- 第 527 行：`parser.add_argument('--retries', type=int, default=1)`。
- 第 528 行：`parser.add_argument('--progress-every', type=int, default=100)`。
- 第 529 行：`parser.add_argument('--max-incorrect-examples', type=int, default=50)`。
- 第 530 行：`parser.add_argument('--server-gpu-name')`。
- 第 531 行：`parser.add_argument('--server-gpu-memory-mib', type=int)`。

## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [integration/tests/test_qwen_expanded_instruction_benchmark.py](../../../integration/tests/test_qwen_expanded_instruction_benchmark.py)

## 后续修改需要一起阅读

- [上级模块](../modules/support-tools.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `tools/run_qwen_expanded_instruction_benchmark.py`

来源 SHA256：`0bbf749c0d16307bfc6a17135f5e445c3d9a5969b0f7d72c23c91f71d13c30dd`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 507 | `'--dataset'` | `type=Path; default=Path('CARLA-Language-Benchmark/datasets/final_benchmark/CARLA_language_benchmark_v1_normalized.json')` |
| 515 | `'--base-url'` | `default=os.environ.get('QWEN_BASE_URL', 'http://127.0.0.1:8000/v1')` |
| 519 | `'--model'` | `default=os.environ.get('QWEN_MODEL', 'qwen2.5-vl')` |
| 520 | `'--output'` | `type=Path; required=True` |
| 521 | `'--records-output'` | `type=Path` |
| 522 | `'--category'` | `action='append'; default=[]` |
| 523 | `'--sample-per-category'` | `type=int` |
| 524 | `'--limit'` | `type=int` |
| 525 | `'--concurrency'` | `type=int; default=8` |
| 526 | `'--timeout-s'` | `type=float; default=20.0` |
| 527 | `'--retries'` | `type=int; default=1` |
| 528 | `'--progress-every'` | `type=int; default=100` |
| 529 | `'--max-incorrect-examples'` | `type=int; default=50` |
| 530 | `'--server-gpu-name'` | `` |
| 531 | `'--server-gpu-memory-mib'` | `type=int` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `build_case_prompt` / 68 | `not isinstance(instruction, str) or not instruction.strip()` | `raise ValueError('record template must be a non-empty string')` |
| `build_case_prompt` / 70 | `not isinstance(scene, dict)` | `raise ValueError('record scene_constraints must be an object')` |
| `summarize_records` / 150 | `not records` | `raise ValueError('records must not be empty')` |
| `_extract_choice` / 214 | `not choices` | `raise RuntimeError('server returned no completion choices')` |
| `_extract_choice` / 218 | `not isinstance(content, str) or not content.strip()` | `raise RuntimeError('server returned an empty response')` |
| `_extract_choice` / 221 | `code not in CODE_TO_ACTION` | `raise RuntimeError(f'server returned invalid action code: {code!r}')` |
| `_select_records` / 355 | `not selected` | `raise ValueError('record selection is empty')` |
| `_run` / 363 | `except ImportError` | `raise RuntimeError('install the optional client from requirements-qwen-client.txt') from error` |
| `_run` / 371 | `not isinstance(source_records, list) or not source_records` | `raise ValueError('dataset must be a non-empty JSON array')` |
| `_run` / 375 | `unknown_actions` | `raise ValueError(f'dataset contains unsupported actions: {unknown_actions}')` |

### 环境参数读取位置

这里只记录源码表达式，不读取当前进程环境；缓存与覆盖关系需查调用时机。

| 来源/行 | 环境变量表达式 | 源码fallback |
|---|---|---|
| `tools/run_qwen_expanded_instruction_benchmark.py:385` | `'QWEN_API_KEY'` | `凭据参数，不抄录值` |
| `tools/run_qwen_expanded_instruction_benchmark.py:517` | `'QWEN_BASE_URL'` | `'http://127.0.0.1:8000/v1'` |
| `tools/run_qwen_expanded_instruction_benchmark.py:519` | `'QWEN_MODEL'` | `'qwen2.5-vl'` |
