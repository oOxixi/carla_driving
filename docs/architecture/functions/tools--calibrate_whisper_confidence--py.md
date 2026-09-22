# calibrate_whisper_confidence：功能记录

上级模块：[模块说明](../modules/support-tools.md) · 实现：[tools/calibrate_whisper_confidence.py](../../../tools/calibrate_whisper_confidence.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [维护工具的运行上下文和证据范围](environment-delivery.md)

## 功能职责与范围

Fit and evaluate a provisional faster-whisper confidence calibration.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `normalize`

源码位置：[tools/calibrate_whisper_confidence.py 第 32 行](../../../tools/calibrate_whisper_confidence.py#L32)。类型：`FunctionDef`。

```python
normalize(value: str) -> str
```

【normalize】把输入转换为维护工具的数据检查、生成、评测或证据处理使用的结构；只承诺函数体明确实现的字段、单位和规范化规则，未知值、缺字段及降级语义需与下游Schema一并核对。

### `sigmoid`

源码位置：[tools/calibrate_whisper_confidence.py 第 37 行](../../../tools/calibrate_whisper_confidence.py#L37)。类型：`FunctionDef`。

```python
sigmoid(values: np.ndarray) -> np.ndarray
```

【sigmoid】根据紧邻签名和函数体完成维护工具的数据检查、生成、评测或证据处理中的局部职责；返回、状态、副作用和异常以本页下方调用/raise记录为边界，名称本身不增加额外保证。

### `fit_platt`

源码位置：[tools/calibrate_whisper_confidence.py 第 42 行](../../../tools/calibrate_whisper_confidence.py#L42)。类型：`FunctionDef`。

```python
fit_platt(raw_probabilities: list[float], labels: list[bool], *, regularization: float=1.0) -> tuple[float, float]
```

【fit_platt】根据紧邻签名和函数体完成维护工具的数据检查、生成、评测或证据处理中的局部职责；返回、状态、副作用和异常以本页下方调用/raise记录为边界，名称本身不增加额外保证。

### `calibrate`

源码位置：[tools/calibrate_whisper_confidence.py 第 66 行](../../../tools/calibrate_whisper_confidence.py#L66)。类型：`FunctionDef`。

```python
calibrate(raw_probability: float, intercept: float, slope: float) -> float
```

【calibrate】根据紧邻签名和函数体完成维护工具的数据检查、生成、评测或证据处理中的局部职责；返回、状态、副作用和异常以本页下方调用/raise记录为边界，名称本身不增加额外保证。

### `metrics`

源码位置：[tools/calibrate_whisper_confidence.py 第 76 行](../../../tools/calibrate_whisper_confidence.py#L76)。类型：`FunctionDef`。

```python
metrics(probabilities: list[float], labels: list[bool]) -> dict
```

【metrics】根据紧邻签名和函数体完成维护工具的数据检查、生成、评测或证据处理中的局部职责；返回、状态、副作用和异常以本页下方调用/raise记录为边界，名称本身不增加额外保证。

### `main`

源码位置：[tools/calibrate_whisper_confidence.py 第 98 行](../../../tools/calibrate_whisper_confidence.py#L98)。类型：`FunctionDef`。

```python
main() -> int
```

【main】是维护工具的数据检查、生成、评测或证据处理的执行/命令入口；参数来自紧邻签名或本页CLI表，可能读取外部资源、写产物或启动服务，应以退出码、原始日志和固定输入身份判定结果。

## 内部调用与异常路径

- `normalize` 调用：`re.sub`, `unicodedata.normalize`, `unicodedata.normalize('NFKC', value).lower`.
- `sigmoid` 调用：`np.clip`, `np.exp`.
- `fit_platt` 调用：`float`, `np.abs`, `np.asarray`, `np.clip`, `np.column_stack`, `np.diag`, `np.linalg.solve`, `np.log`, `np.max`, `np.maximum`, `np.ones_like`, `np.zeros`, `range`, `sigmoid`.
- `calibrate` 调用：`float`, `math.log`, `np.asarray`, `np.clip`, `sigmoid`.
- `metrics` 调用：`float`, `int`, `len`, `np.any`, `np.asarray`, `np.mean`, `round`, `target.sum`, `values.mean`, `values[target == 0].mean`, `values[target == 1].mean`.
- `main` 调用：`CascadeConfig`, `FasterWhisperVerifier`, `Path`, `RuntimeError`, `_synthetic_noise_audio`, `argparse.ArgumentParser`, `args.evidence.parent.mkdir`, `args.evidence.write_text`, `args.languages.split`, `args.manifest.read_text`, `args.manifest.resolve`, `args.output.parent.mkdir`, `args.output.write_text`, `calibrate`, `conditions.append`, `datetime.now`, `datetime.now(timezone.utc).isoformat`, `enumerate`, `fit_platt`, `json.dumps`, `json.loads`, `len`, `metrics`, `normalize`, `np.random.default_rng`, `parser.add_argument`, `parser.parse_args`, `print`, `records.append`, `round`, `sorted`, `str`, `value.strip`, `verifier.transcribe`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `main`，第 155 行：`RuntimeError(f'missing word probability for {audio_path}')`。
- `main`，第 196 行：`RuntimeError('validation split contains no ASR errors; calibration is not auditable')`。
- `main`，第 200 行：`RuntimeError('raw word probability does not rank correctness; refusing calibration')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 100 行：`parser.add_argument('--manifest', type=Path, default=DEFAULT_MANIFEST)`。
- 第 101 行：`parser.add_argument('--output', type=Path, required=True)`。
- 第 102 行：`parser.add_argument('--evidence', type=Path, required=True)`。
- 第 103 行：`parser.add_argument('--model', default='small')`。
- 第 104 行：`parser.add_argument('--device', default='cuda')`。
- 第 105 行：`parser.add_argument('--compute-type', default='int8_float16')`。
- 第 106 行：`parser.add_argument('--languages', help='Comma-separated manifest language labels used for calibration')`。
- 第 110 行：`parser.add_argument('--include-snr-db', type=float, default=10.0)`。
- 第 111 行：`parser.add_argument('--seed', type=int, default=20260726)`。
- 第 112 行：`parser.add_argument('--limit', type=int)`。

## 上下游与关联验证

静态导入的项目内实现：

- [tools/evaluate_voice_audio.py](../../../tools/evaluate_voice_audio.py)
- [voice_group/asr_cascade.py](../../../voice_group/asr_cascade.py)

静态 import 消费者（含测试）：

- [voice_group/tests/test_whisper_calibration.py](../../../voice_group/tests/test_whisper_calibration.py)

## 后续修改需要一起阅读

- [上级模块](../modules/support-tools.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `tools/calibrate_whisper_confidence.py`

来源 SHA256：`ad0272ef1c4b6bde6cffe25d8e0773414ee7a112a7d67943a2f5fe966a13dde0`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 100 | `'--manifest'` | `type=Path; default=DEFAULT_MANIFEST` |
| 101 | `'--output'` | `type=Path; required=True` |
| 102 | `'--evidence'` | `type=Path; required=True` |
| 103 | `'--model'` | `default='small'` |
| 104 | `'--device'` | `default='cuda'` |
| 105 | `'--compute-type'` | `default='int8_float16'` |
| 106 | `'--languages'` | `help='Comma-separated manifest language labels used for calibration'` |
| 110 | `'--include-snr-db'` | `type=float; default=10.0` |
| 111 | `'--seed'` | `type=int; default=20260726` |
| 112 | `'--limit'` | `type=int` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `main` / 155 | `raw is None` | `raise RuntimeError(f'missing word probability for {audio_path}')` |
| `main` / 196 | `validation_metrics['incorrect'] == 0` | `raise RuntimeError('validation split contains no ASR errors; calibration is not auditable')` |
| `main` / 200 | `slope <= 0` | `raise RuntimeError('raw word probability does not rank correctness; refusing calibration')` |
