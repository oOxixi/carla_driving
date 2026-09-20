# run_qwen_latency_gate：功能记录

上级模块：[模块说明](../modules/support-tools.md) · 实现：[tools/run_qwen_latency_gate.py](../../../tools/run_qwen_latency_gate.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [维护工具的运行上下文和证据范围](environment-delivery.md)

## 功能职责与范围

Run only the Qwen-VL latency gate; never starts a correctness suite.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `_percentile`

源码位置：[tools/run_qwen_latency_gate.py 第 26 行](../../../tools/run_qwen_latency_gate.py#L26)。类型：`FunctionDef`。

```python
_percentile(values: list[float], quantile: float) -> float
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `summarize_latency_gate`

源码位置：[tools/run_qwen_latency_gate.py 第 39 行](../../../tools/run_qwen_latency_gate.py#L39)。类型：`FunctionDef`。

```python
summarize_latency_gate(latencies_ms: list[float], *, threshold_ms: float) -> dict[str, object]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `latency_gate_exit_code`

源码位置：[tools/run_qwen_latency_gate.py 第 70 行](../../../tools/run_qwen_latency_gate.py#L70)。类型：`FunctionDef`。

```python
latency_gate_exit_code(report: Mapping[str, object]) -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_context`

源码位置：[tools/run_qwen_latency_gate.py 第 79 行](../../../tools/run_qwen_latency_gate.py#L79)。类型：`FunctionDef`。

```python
_context(image_name: str, index: int) -> QwenInputContext
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_gpu_snapshot`

源码位置：[tools/run_qwen_latency_gate.py 第 99 行](../../../tools/run_qwen_latency_gate.py#L99)。类型：`FunctionDef`。

```python
_gpu_snapshot() -> dict[str, object]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_write_report`

源码位置：[tools/run_qwen_latency_gate.py 第 126 行](../../../tools/run_qwen_latency_gate.py#L126)。类型：`FunctionDef`。

```python
_write_report(path: Path, report: Mapping[str, Any]) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[tools/run_qwen_latency_gate.py 第 134 行](../../../tools/run_qwen_latency_gate.py#L134)。类型：`FunctionDef`。

```python
main() -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `_percentile` 调用：`len`, `math.ceil`, `math.floor`, `sorted`.
- `summarize_latency_gate` 调用：`ValueError`, `_percentile`, `any`, `float`, `isinstance`, `len`, `math.isfinite`, `max`, `statistics.fmean`, `type`.
- `latency_gate_exit_code` 调用：`ValueError`, `report.get`.
- `_context` 调用：`QwenInputContext`.
- `_gpu_snapshot` 调用：`completed.stdout.strip`, `completed.stdout.strip().splitlines`, `completed.stdout.strip().splitlines()[0].split`, `first[0].strip`, `first[1].strip`, `first[2].strip`, `first[3].strip`, `float`, `len`, `subprocess.run`.
- `_write_report` 调用：`json.dumps`, `path.parent.mkdir`, `path.write_text`.
- `main` 调用：`OpenAICompatibleQwenVLBackend`, `StrictQwenVLAdapter`, `_context`, `_gpu_snapshot`, `_write_report`, `adapter.infer`, `argparse.ArgumentParser`, `args.image.expanduser`, `args.image.expanduser().resolve`, `backend.close`, `datetime.now`, `datetime.now(timezone.utc).isoformat`, `image.is_file`, `json.dumps`, `latencies_ms.append`, `latency_gate_exit_code`, `os.environ.get`, `parser.add_argument`, `parser.error`, `parser.parse_args`, `print`, `range`, `report.update`, `str`, `summarize_latency_gate`, `time.perf_counter_ns`, `type`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `latency_gate_exit_code`，第 76 行：`ValueError(f'unsupported latency gate status: {status!r}')`。
- `summarize_latency_gate`，第 45 行：`ValueError('latencies_ms must not be empty')`。
- `summarize_latency_gate`，第 52 行：`ValueError('threshold_ms must be finite and positive')`。
- `summarize_latency_gate`，第 55 行：`ValueError('latencies_ms must contain finite non-negative values')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 136 行：`parser.add_argument('--base-url', default=os.environ.get('QWEN_BASE_URL', 'http://127.0.0.1:8002/v1'))`。
- 第 139 行：`parser.add_argument('--model', default=os.environ.get('QWEN_MODEL', DEFAULT_QWEN_MODEL))`。
- 第 142 行：`parser.add_argument('--model-revision', default=DEFAULT_QWEN_REVISION)`。
- 第 143 行：`parser.add_argument('--image', type=Path, required=True)`。
- 第 144 行：`parser.add_argument('--output', type=Path, required=True)`。
- 第 145 行：`parser.add_argument('--warmups', type=int, default=5)`。
- 第 146 行：`parser.add_argument('--measurements', type=int, default=10)`。
- 第 147 行：`parser.add_argument('--threshold-ms', type=float, default=300.0)`。
- 第 148 行：`parser.add_argument('--timeout-s', type=float, default=2.0)`。
- 第 149 行：`parser.add_argument('--inference-gpu-name', help='GPU on the inference server when --base-url is remote.')`。
- 第 153 行：`parser.add_argument('--inference-gpu-memory-mib', type=float, help='Total memory of the remote inference GPU.')`。
- 第 158 行：`parser.add_argument('--inference-gpu-source', default='operator-supplied remote nvidia-smi snapshot')`。

## 上下游与关联验证

静态导入的项目内实现：

- [integration/qwen_boundary.py](../../../integration/qwen_boundary.py)
- [integration/qwen_remote_backend.py](../../../integration/qwen_remote_backend.py)
- [integration/qwen_vl_adapter.py](../../../integration/qwen_vl_adapter.py)

静态 import 消费者（含测试）：

- [integration/tests/test_qwen_latency_gate.py](../../../integration/tests/test_qwen_latency_gate.py)

## 后续修改需要一起阅读

- [上级模块](../modules/support-tools.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `tools/run_qwen_latency_gate.py`

来源 SHA256：`e885962925c57b47454ce3b152622821a577926853f76dd76c1420f723e8c8f0`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 136 | `'--base-url'` | `default=os.environ.get('QWEN_BASE_URL', 'http://127.0.0.1:8002/v1')` |
| 139 | `'--model'` | `default=os.environ.get('QWEN_MODEL', DEFAULT_QWEN_MODEL)` |
| 142 | `'--model-revision'` | `default=DEFAULT_QWEN_REVISION` |
| 143 | `'--image'` | `type=Path; required=True` |
| 144 | `'--output'` | `type=Path; required=True` |
| 145 | `'--warmups'` | `type=int; default=5` |
| 146 | `'--measurements'` | `type=int; default=10` |
| 147 | `'--threshold-ms'` | `type=float; default=300.0` |
| 148 | `'--timeout-s'` | `type=float; default=2.0` |
| 149 | `'--inference-gpu-name'` | `help='GPU on the inference server when --base-url is remote.'` |
| 153 | `'--inference-gpu-memory-mib'` | `type=float; help='Total memory of the remote inference GPU.'` |
| 158 | `'--inference-gpu-source'` | `default='operator-supplied remote nvidia-smi snapshot'` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `summarize_latency_gate` / 45 | `not latencies_ms` | `raise ValueError('latencies_ms must not be empty')` |
| `summarize_latency_gate` / 52 | `type(threshold_ms) not in (int, float) or isinstance(threshold_ms, bool) or (not math.isfinite(float(threshold_ms))) or (float(threshold_ms) <= 0.0)` | `raise ValueError('threshold_ms must be finite and positive')` |
| `summarize_latency_gate` / 55 | `any((not math.isfinite(value) or value < 0.0 for value in values))` | `raise ValueError('latencies_ms must contain finite non-negative values')` |
| `latency_gate_exit_code` / 76 | `本地无直接if；检查上下文` | `raise ValueError(f'unsupported latency gate status: {status!r}')` |

### 环境参数读取位置

这里只记录源码表达式，不读取当前进程环境；缓存与覆盖关系需查调用时机。

| 来源/行 | 环境变量表达式 | 源码fallback |
|---|---|---|
| `tools/run_qwen_latency_gate.py:136` | `'QWEN_BASE_URL'` | `'http://127.0.0.1:8002/v1'` |
| `tools/run_qwen_latency_gate.py:140` | `'QWEN_MODEL'` | `DEFAULT_QWEN_MODEL` |
| `tools/run_qwen_latency_gate.py:171` | `'QWEN_API_KEY'` | `凭据参数，不抄录值` |
