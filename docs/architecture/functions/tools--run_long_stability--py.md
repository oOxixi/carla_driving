# run_long_stability：功能记录

上级模块：[模块说明](../modules/support-tools.md) · 实现：[tools/run_long_stability.py](../../../tools/run_long_stability.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [维护工具的运行上下文和证据范围](environment-delivery.md)

## 功能职责与范围

Run a wall-clock CARLA sensor soak with GPU and periodic Qwen evidence.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `_percentile`

源码位置：[tools/run_long_stability.py 第 22 行](../../../tools/run_long_stability.py#L22)。类型：`FunctionDef`。

```python
_percentile(values: list[float], quantile: float) -> float | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_gpu_sample`

源码位置：[tools/run_long_stability.py 第 33 行](../../../tools/run_long_stability.py#L33)。类型：`FunctionDef`。

```python
_gpu_sample(gpu_index: int) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_monitor_gpu`

源码位置：[tools/run_long_stability.py 第 63 行](../../../tools/run_long_stability.py#L63)。类型：`FunctionDef`。

```python
_monitor_gpu(stop: threading.Event, records: list[dict[str, Any]], errors: list[str], *, gpu_index: int, interval_s: float) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_qwen_context`

源码位置：[tools/run_long_stability.py 第 79 行](../../../tools/run_long_stability.py#L79)。类型：`FunctionDef`。

```python
_qwen_context(image_ref: str, index: int) -> QwenInputContext
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_run_qwen_periodically`

源码位置：[tools/run_long_stability.py 第 111 行](../../../tools/run_long_stability.py#L111)。类型：`FunctionDef`。

```python
_run_qwen_periodically(stop: threading.Event, records: list[dict[str, Any]], adapter: StrictQwenVLAdapter, *, image_ref: str, interval_s: float, timeout_budget_s: float) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[tools/run_long_stability.py 第 159 行](../../../tools/run_long_stability.py#L159)。类型：`FunctionDef`。

```python
main() -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `_percentile` 调用：`int`, `len`, `min`, `sorted`.
- `_gpu_sample` 调用：`ValueError`, `completed.stdout.strip`, `completed.stdout.strip().split`, `datetime.now`, `datetime.now(timezone.utc).isoformat`, `field.strip`, `float`, `int`, `len`, `subprocess.run`.
- `_monitor_gpu` 调用：`_gpu_sample`, `errors.append`, `records.append`, `stop.is_set`, `stop.wait`, `type`.
- `_qwen_context` 调用：`QwenInputContext`, `float`.
- `_run_qwen_periodically` 调用：`_qwen_context`, `adapter`, `datetime.now`, `datetime.now(timezone.utc).isoformat`, `decision.get`, `records.append`, `stop.is_set`, `stop.wait`, `str`, `time.monotonic`, `type`.
- `main` 调用：`OpenAICompatibleQwenVLBackend`, `Path`, `StrictQwenVLAdapter`, `StrictQwenVLAdapter.from_local_checkpoint`, `ValueError`, `_percentile`, `all`, `argparse.ArgumentParser`, `args.output.parent.mkdir`, `args.output.write_text`, `asdict`, `bool`, `datetime.now`, `datetime.now(timezone.utc).isoformat`, `float`, `json.dumps`, `len`, `max`, `monitor.join`, `monitor.start`, `parser.add_argument`, `parser.parse_args`, `print`, `qwen_worker.join`, `qwen_worker.start`, `record.get`, `resolve_qwen_profile`, `run_sensor_probe`, `statistics.fmean`, `stop.set`, `str`, `sum`, `threading.Event`, `threading.Thread`, `time.monotonic`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `_gpu_sample`，第 50 行：`ValueError(f'unexpected nvidia-smi output: {completed.stdout!r}')`。
- `main`，第 176 行：`ValueError('duration-minutes must be positive')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 161 行：`parser.add_argument('--output', required=True, type=Path)`。
- 第 162 行：`parser.add_argument('--duration-minutes', type=float, default=30.0)`。
- 第 163 行：`parser.add_argument('--host', default='127.0.0.1')`。
- 第 164 行：`parser.add_argument('--port', type=int, default=2000)`。
- 第 165 行：`parser.add_argument('--gpu-index', type=int, default=0)`。
- 第 166 行：`parser.add_argument('--gpu-sample-seconds', type=float, default=5.0)`。
- 第 167 行：`parser.add_argument('--qwen-model', required=True)`。
- 第 168 行：`parser.add_argument('--qwen-base-url')`。
- 第 169 行：`parser.add_argument('--qwen-profile', default='qwen3vl-2b-int4')`。
- 第 170 行：`parser.add_argument('--qwen-image-root', required=True, type=Path)`。
- 第 171 行：`parser.add_argument('--qwen-image-ref', required=True)`。
- 第 172 行：`parser.add_argument('--qwen-interval-seconds', type=float, default=300.0)`。
- 第 173 行：`parser.add_argument('--qwen-timeout-budget-seconds', type=float, default=10.0)`。

## 上下游与关联验证

静态导入的项目内实现：

- [integration/qwen_boundary.py](../../../integration/qwen_boundary.py)
- [integration/qwen_profiles.py](../../../integration/qwen_profiles.py)
- [integration/qwen_remote_backend.py](../../../integration/qwen_remote_backend.py)
- [integration/qwen_vl_adapter.py](../../../integration/qwen_vl_adapter.py)
- [integration/sensor_stability.py](../../../integration/sensor_stability.py)

静态 import 消费者（含测试）：

- 未发现静态 import 消费者；命令行、间接注册、文件路径加载不在此清单内。

## 后续修改需要一起阅读

- [上级模块](../modules/support-tools.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `tools/run_long_stability.py`

来源 SHA256：`c24ebdf7cfef1c6f81fb6f98d20758f2a7c71da8d67ab30c406a7a0b4128ef3c`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 161 | `'--output'` | `required=True; type=Path` |
| 162 | `'--duration-minutes'` | `type=float; default=30.0` |
| 163 | `'--host'` | `default='127.0.0.1'` |
| 164 | `'--port'` | `type=int; default=2000` |
| 165 | `'--gpu-index'` | `type=int; default=0` |
| 166 | `'--gpu-sample-seconds'` | `type=float; default=5.0` |
| 167 | `'--qwen-model'` | `required=True` |
| 168 | `'--qwen-base-url'` | `` |
| 169 | `'--qwen-profile'` | `default='qwen3vl-2b-int4'` |
| 170 | `'--qwen-image-root'` | `required=True; type=Path` |
| 171 | `'--qwen-image-ref'` | `required=True` |
| 172 | `'--qwen-interval-seconds'` | `type=float; default=300.0` |
| 173 | `'--qwen-timeout-budget-seconds'` | `type=float; default=10.0` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `_gpu_sample` / 50 | `len(fields) != 7` | `raise ValueError(f'unexpected nvidia-smi output: {completed.stdout!r}')` |
| `main` / 176 | `args.duration_minutes <= 0` | `raise ValueError('duration-minutes must be positive')` |
