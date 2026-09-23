# evaluate_voice_audio：功能记录

上级模块：[模块说明](../modules/support-tools.md) · 实现：[tools/evaluate_voice_audio.py](../../../tools/evaluate_voice_audio.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [维护工具的运行上下文和证据范围](environment-delivery.md)

## 功能职责与范围

Run the complete voice pipeline over a manifest and write audit evidence.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `_synthetic_noise_audio`

源码位置：[tools/evaluate_voice_audio.py 第 33 行](../../../tools/evaluate_voice_audio.py#L33)。类型：`FunctionDef`。

```python
_synthetic_noise_audio(audio_path: Path, snr_db: float, rng: np.random.Generator) -> np.ndarray
```

Load mono 16 kHz audio and add deterministic white noise at an SNR.

SNR is a digital signal ratio.  It is deliberately not described as dBA,
which requires calibrated acoustic playback and measurement.

### `_normalize_transcript`

源码位置：[tools/evaluate_voice_audio.py 第 60 行](../../../tools/evaluate_voice_audio.py#L60)。类型：`FunctionDef`。

```python
_normalize_transcript(value: str) -> str
```

【_normalize_transcript】把输入转换为维护工具的数据检查、生成、评测或证据处理使用的结构；只承诺函数体明确实现的字段、单位和规范化规则，未知值、缺字段及降级语义需与下游Schema一并核对。

### `_edit_distance`

源码位置：[tools/evaluate_voice_audio.py 第 65 行](../../../tools/evaluate_voice_audio.py#L65)。类型：`FunctionDef`。

```python
_edit_distance(left: str, right: str) -> int
```

【_edit_distance】根据紧邻签名和函数体完成维护工具的数据检查、生成、评测或证据处理中的局部职责；返回、状态、副作用和异常以本页下方调用/raise记录为边界，名称本身不增加额外保证。

### `_percentile`

源码位置：[tools/evaluate_voice_audio.py 第 81 行](../../../tools/evaluate_voice_audio.py#L81)。类型：`FunctionDef`。

```python
_percentile(values: list[float], percentile: float) -> float | None
```

【_percentile】根据紧邻签名和函数体完成维护工具的数据检查、生成、评测或证据处理中的局部职责；返回、状态、副作用和异常以本页下方调用/raise记录为边界，名称本身不增加额外保证。

### `_latency_stats`

源码位置：[tools/evaluate_voice_audio.py 第 97 行](../../../tools/evaluate_voice_audio.py#L97)。类型：`FunctionDef`。

```python
_latency_stats(values: list[float]) -> dict[str, float | int | None]
```

【_latency_stats】根据紧邻签名和函数体完成维护工具的数据检查、生成、评测或证据处理中的局部职责；返回、状态、副作用和异常以本页下方调用/raise记录为边界，名称本身不增加额外保证。

### `_summarize`

源码位置：[tools/evaluate_voice_audio.py 第 107 行](../../../tools/evaluate_voice_audio.py#L107)。类型：`FunctionDef`。

```python
_summarize(records: list[dict[str, Any]]) -> dict[str, Any]
```

【_summarize】根据紧邻签名和函数体完成维护工具的数据检查、生成、评测或证据处理中的局部职责；返回、状态、副作用和异常以本页下方调用/raise记录为边界，名称本身不增加额外保证。

### `_markdown_report`

源码位置：[tools/evaluate_voice_audio.py 第 191 行](../../../tools/evaluate_voice_audio.py#L191)。类型：`FunctionDef`。

```python
_markdown_report(report: dict[str, Any]) -> str
```

【_markdown_report】根据紧邻签名和函数体完成维护工具的数据检查、生成、评测或证据处理中的局部职责；返回、状态、副作用和异常以本页下方调用/raise记录为边界，名称本身不增加额外保证。

### `_git_state`

源码位置：[tools/evaluate_voice_audio.py 第 270 行](../../../tools/evaluate_voice_audio.py#L270)。类型：`FunctionDef`。

```python
_git_state() -> dict[str, Any]
```

【_git_state】根据紧邻签名和函数体完成维护工具的数据检查、生成、评测或证据处理中的局部职责；返回、状态、副作用和异常以本页下方调用/raise记录为边界，名称本身不增加额外保证。

### `main`

源码位置：[tools/evaluate_voice_audio.py 第 299 行](../../../tools/evaluate_voice_audio.py#L299)。类型：`FunctionDef`。

```python
main() -> int
```

【main】是维护工具的数据检查、生成、评测或证据处理的执行/命令入口；参数来自紧邻签名或本页CLI表，可能读取外部资源、写产物或启动服务，应以退出码、原始日志和固定输入身份判定结果。

## 内部调用与异常路径

- `_synthetic_noise_audio` 调用：`float`, `int`, `len`, `max`, `np.arange`, `np.asarray`, `np.clip`, `np.interp`, `np.interp(np.linspace(0, len(waveform), output_size, endpoint=False), np.arange(len(waveform)), waveform).astype`, `np.linspace`, `np.mean`, `np.sqrt`, `np.square`, `rng.normal`, `rng.normal(0.0, noise_rms, waveform.shape).astype`, `sf.read`, `waveform.mean`.
- `_normalize_transcript` 调用：`re.sub`, `unicodedata.normalize`, `unicodedata.normalize('NFKC', value).lower`.
- `_edit_distance` 调用：`current.append`, `enumerate`, `len`, `list`, `min`, `range`.
- `_percentile` 调用：`len`, `math.ceil`, `math.floor`, `round`, `sorted`.
- `_latency_stats` 调用：`_percentile`, `len`, `max`, `round`, `statistics.fmean`.
- `_summarize` 调用：`(record.get('asr_verification') or {}).get`, `_latency_stats`, `bool`, `float`, `len`, `max`, `record.get`, `record.get('latency', {}).get`, `round`, `sum`.
- `_markdown_report` 调用：`'\n'.join`, `len`, `lines.append`, `lines.extend`, `report.get`, `report['by_language'].items`.
- `_git_state` 调用：`bool`, `commit_result.stdout.strip`, `line.strip`, `status_result.stdout.splitlines`, `subprocess.run`.
- `main` 调用：`(args.audio_root or args.manifest.parent).resolve`, `_edit_distance`, `_git_state`, `_markdown_report`, `_normalize_transcript`, `_summarize`, `_synthetic_noise_audio`, `abs`, `all`, `argparse.ArgumentParser`, `args.calibration_log.is_file`, `args.calibration_log.resolve`, `args.manifest.read_text`, `args.manifest.resolve`, `args.output.parent.mkdir`, `args.output.with_suffix`, `args.output.with_suffix('.md').write_text`, `args.output.write_text`, `audio_to_command`, `by_language_records.items`, `by_language_records[record['language']].append`, `command.get`, `command.get('parameters', {}).get`, `datetime.now`, `datetime.now(timezone.utc).isoformat`, `defaultdict`, `enumerate`, `item.get`, `item.get('slots', {}).items`, `json.dumps`, `json.loads`, `len`, `np.random.default_rng`, `parser.add_argument`, `parser.error`, `parser.parse_args`, `preload_voice_models`, `print`, `record.get`, `record.update`, `records.append`, `sorted`, `str`, `sys.path.insert`, `type`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- 未发现显式 raise；不代表运行不会失败。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 301 行：`parser.add_argument('--manifest', type=Path, default=DEFAULT_MANIFEST)`。
- 第 302 行：`parser.add_argument('--audio-root', type=Path, help='Root containing the same relative audio paths as the manifest')`。
- 第 307 行：`parser.add_argument('--condition', choices=('clean', 'noise_50dba', 'synthetic_noise'), required=True)`。
- 第 312 行：`parser.add_argument('--noise-level-dba', type=float)`。
- 第 313 行：`parser.add_argument('--calibration-log', type=Path)`。
- 第 314 行：`parser.add_argument('--synthetic-snr-db', type=float, help='Digital white-noise SNR; never evidence of an absolute dBA level')`。
- 第 319 行：`parser.add_argument('--noise-seed', type=int, default=20260726)`。
- 第 320 行：`parser.add_argument('--output', type=Path, required=True)`。
- 第 321 行：`parser.add_argument('--limit', type=int, help='Smoke-test only; invalid for final evidence')`。
- 第 322 行：`parser.add_argument('--min-intent-accuracy', type=float)`。

## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [tools/calibrate_whisper_confidence.py](../../../tools/calibrate_whisper_confidence.py)
- [voice_group/tests/test_audio_evaluator.py](../../../voice_group/tests/test_audio_evaluator.py)

## 后续修改需要一起阅读

- [上级模块](../modules/support-tools.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `tools/evaluate_voice_audio.py`

来源 SHA256：`8429c0ed701ab073844032f6d213c983a209335cb732b218d556fdce4490fc67`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 301 | `'--manifest'` | `type=Path; default=DEFAULT_MANIFEST` |
| 302 | `'--audio-root'` | `type=Path; help='Root containing the same relative audio paths as the manifest'` |
| 307 | `'--condition'` | `choices=('clean', 'noise_50dba', 'synthetic_noise'); required=True` |
| 312 | `'--noise-level-dba'` | `type=float` |
| 313 | `'--calibration-log'` | `type=Path` |
| 314 | `'--synthetic-snr-db'` | `type=float; help='Digital white-noise SNR; never evidence of an absolute dBA level'` |
| 319 | `'--noise-seed'` | `type=int; default=20260726` |
| 320 | `'--output'` | `type=Path; required=True` |
| 321 | `'--limit'` | `type=int; help='Smoke-test only; invalid for final evidence'` |
| 322 | `'--min-intent-accuracy'` | `type=float` |
