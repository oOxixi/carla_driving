# run_group1_voice_onnx_benchmark：功能记录

上级模块：[模块说明](../modules/support-tools.md) · 实现：[tools/run_group1_voice_onnx_benchmark.py](../../../tools/run_group1_voice_onnx_benchmark.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [维护工具的运行上下文和证据范围](environment-delivery.md)

## 功能职责与范围

Benchmark the exported SenseVoice ONNX model on Group 1 voice data.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `_normalize_transcript`

源码位置：[tools/run_group1_voice_onnx_benchmark.py 第 51 行](../../../tools/run_group1_voice_onnx_benchmark.py#L51)。类型：`FunctionDef`。

```python
_normalize_transcript(value: str) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_edit_distance`

源码位置：[tools/run_group1_voice_onnx_benchmark.py 第 56 行](../../../tools/run_group1_voice_onnx_benchmark.py#L56)。类型：`FunctionDef`。

```python
_edit_distance(left: str, right: str) -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_slots_match`

源码位置：[tools/run_group1_voice_onnx_benchmark.py 第 72 行](../../../tools/run_group1_voice_onnx_benchmark.py#L72)。类型：`FunctionDef`。

```python
_slots_match(actual: dict[str, Any], expected: dict[str, Any]) -> bool
```

Match annotated slots without rejecting additional executable metadata.

### `_percentile`

源码位置：[tools/run_group1_voice_onnx_benchmark.py 第 78 行](../../../tools/run_group1_voice_onnx_benchmark.py#L78)。类型：`FunctionDef`。

```python
_percentile(values: list[float], percentile: float) -> float | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_latency_stats`

源码位置：[tools/run_group1_voice_onnx_benchmark.py 第 91 行](../../../tools/run_group1_voice_onnx_benchmark.py#L91)。类型：`FunctionDef`。

```python
_latency_stats(values: list[float]) -> dict[str, float | int | None]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_strip_and_correct`

源码位置：[tools/run_group1_voice_onnx_benchmark.py 第 101 行](../../../tools/run_group1_voice_onnx_benchmark.py#L101)。类型：`FunctionDef`。

```python
_strip_and_correct(text: str) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_git_state`

源码位置：[tools/run_group1_voice_onnx_benchmark.py 第 109 行](../../../tools/run_group1_voice_onnx_benchmark.py#L109)。类型：`FunctionDef`。

```python
_git_state() -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_write_json`

源码位置：[tools/run_group1_voice_onnx_benchmark.py 第 131 行](../../../tools/run_group1_voice_onnx_benchmark.py#L131)。类型：`FunctionDef`。

```python
_write_json(path: Path, payload: Any) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_write_markdown`

源码位置：[tools/run_group1_voice_onnx_benchmark.py 第 136 行](../../../tools/run_group1_voice_onnx_benchmark.py#L136)。类型：`FunctionDef`。

```python
_write_markdown(path: Path, report: dict[str, Any]) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `OnnxSenseVoice`

源码位置：[tools/run_group1_voice_onnx_benchmark.py 第 178 行](../../../tools/run_group1_voice_onnx_benchmark.py#L178)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `OnnxSenseVoice.__init__`

源码位置：[tools/run_group1_voice_onnx_benchmark.py 第 179 行](../../../tools/run_group1_voice_onnx_benchmark.py#L179)。类型：`FunctionDef`。

```python
OnnxSenseVoice.__init__(self, model_path: Path, base_model: Path, provider: str, language: str, use_itn: bool) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `OnnxSenseVoice.transcribe`

源码位置：[tools/run_group1_voice_onnx_benchmark.py 第 221 行](../../../tools/run_group1_voice_onnx_benchmark.py#L221)。类型：`FunctionDef`。

```python
OnnxSenseVoice.transcribe(self, audio_path: Path) -> tuple[str, dict[str, float]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `OnnxSenseVoice.warmup`

源码位置：[tools/run_group1_voice_onnx_benchmark.py 第 284 行](../../../tools/run_group1_voice_onnx_benchmark.py#L284)。类型：`FunctionDef`。

```python
OnnxSenseVoice.warmup(self, audio_root: Path, manifest: list[dict[str, Any]], rounds: int) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_run_item`

源码位置：[tools/run_group1_voice_onnx_benchmark.py 第 289 行](../../../tools/run_group1_voice_onnx_benchmark.py#L289)。类型：`FunctionDef`。

```python
_run_item(item: dict[str, Any], audio_root: Path, recognizer: OnnxSenseVoice) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_summarize`

源码位置：[tools/run_group1_voice_onnx_benchmark.py 第 337 行](../../../tools/run_group1_voice_onnx_benchmark.py#L337)。类型：`FunctionDef`。

```python
_summarize(records: list[dict[str, Any]], latency_samples: int) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[tools/run_group1_voice_onnx_benchmark.py 第 356 行](../../../tools/run_group1_voice_onnx_benchmark.py#L356)。类型：`FunctionDef`。

```python
main() -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `_normalize_transcript` 调用：`re.sub`, `unicodedata.normalize`, `unicodedata.normalize('NFKC', value).lower`.
- `_edit_distance` 调用：`current.append`, `enumerate`, `len`, `list`, `min`, `range`.
- `_slots_match` 调用：`actual.get`, `all`, `expected.items`.
- `_percentile` 调用：`len`, `math.ceil`, `math.floor`, `round`, `sorted`.
- `_latency_stats` 调用：`_percentile`, `len`, `max`, `round`, `statistics.fmean`.
- `_strip_and_correct` 调用：`_CORRECTION.items`, `_EMOJI.sub`, `_EMOJI.sub('', text).strip`, `_TAG.sub`, `text.replace`.
- `_git_state` 调用：`bool`, `commit.stdout.strip`, `line.strip`, `status.stdout.splitlines`, `status.stdout.strip`, `subprocess.run`.
- `_write_json` 调用：`json.dumps`, `path.parent.mkdir`, `path.write_text`.
- `_write_markdown` 调用：`'\n'.join`, `lines.append`, `lines.extend`, `path.write_text`.
- `_run_item` 调用：`_edit_distance`, `_normalize_transcript`, `_slots_match`, `b2.get`, `dict`, `item.get`, `len`, `parse_command`, `process_asr_text`, `recognizer.transcribe`, `round`, `str`, `time.perf_counter`.
- `_summarize` 调用：`_latency_stats`, `float`, `len`, `max`, `round`, `sum`.
- `main` 调用：`OnnxSenseVoice`, `_git_state`, `_run_item`, `_summarize`, `_write_json`, `_write_markdown`, `argparse.ArgumentParser`, `args.manifest.read_text`, `args.output.with_suffix`, `datetime.now`, `datetime.now(timezone.utc).isoformat`, `json.loads`, `parser.add_argument`, `parser.parse_args`, `print`, `process_asr_text`, `recognizer.warmup`, `sorted`, `str`.
- `__init__` 调用：`(base_model / 'tokens.json').read_text`, `AutoModel`, `int`, `isinstance`, `json.loads`, `len`, `next`, `ort.InferenceSession`, `ort.SessionOptions`, `self.session.get_inputs`, `str`.
- `transcribe` 调用：`''.join`, `_strip_and_correct`, `collapsed.append`, `feat_lens.cpu`, `feat_lens.cpu().numpy`, `feat_lens.cpu().numpy().astype`, `feats.cpu`, `feats.cpu().numpy`, `feats.cpu().numpy().astype`, `int`, `len`, `logits[0].argmax`, `logits[0].argmax(axis=-1).tolist`, `min`, `np.arange`, `np.array`, `np.asarray`, `np.interp`, `np.interp(np.linspace(0, len(waveform), output_size, endpoint=False), np.arange(len(waveform)), waveform).astype`, `np.linspace`, `rich_transcription_postprocess`, `round`, `self.frontend`, `self.session.run`, `sf.read`, `time.perf_counter`, `torch.from_numpy`, `torch.from_numpy(waveform).unsqueeze`, `torch.nn.functional.pad`, `torch.tensor`, `waveform.mean`.
- `warmup` 调用：`self.transcribe`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- 未发现显式 raise；不代表运行不会失败。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 358 行：`parser.add_argument('--manifest', type=Path, default=DEFAULT_MANIFEST)`。
- 第 359 行：`parser.add_argument('--audio-root', type=Path, default=DEFAULT_AUDIO_ROOT)`。
- 第 360 行：`parser.add_argument('--onnx-model', type=Path, default=DEFAULT_MODEL)`。
- 第 361 行：`parser.add_argument('--base-model', type=Path, default=SENSEVOICE_PATH)`。
- 第 362 行：`parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)`。
- 第 363 行：`parser.add_argument('--provider', default='CUDAExecutionProvider')`。
- 第 364 行：`parser.add_argument('--language', choices=sorted(_LANGUAGE_IDS), default='zh')`。
- 第 365 行：`parser.add_argument('--use-itn', action='store_true')`。
- 第 366 行：`parser.add_argument('--limit', type=int, default=50)`。
- 第 367 行：`parser.add_argument('--warmup', type=int, default=3)`。
- 第 368 行：`parser.add_argument('--latency-samples', type=int, default=50)`。

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

### `tools/run_group1_voice_onnx_benchmark.py`

来源 SHA256：`bebf8991ae869becaa21a35de99a1c81f7dc503284ad0d84b836f2bb4f30743e`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 358 | `'--manifest'` | `type=Path; default=DEFAULT_MANIFEST` |
| 359 | `'--audio-root'` | `type=Path; default=DEFAULT_AUDIO_ROOT` |
| 360 | `'--onnx-model'` | `type=Path; default=DEFAULT_MODEL` |
| 361 | `'--base-model'` | `type=Path; default=SENSEVOICE_PATH` |
| 362 | `'--output'` | `type=Path; default=DEFAULT_OUTPUT` |
| 363 | `'--provider'` | `default='CUDAExecutionProvider'` |
| 364 | `'--language'` | `choices=sorted(_LANGUAGE_IDS); default='zh'` |
| 365 | `'--use-itn'` | `action='store_true'` |
| 366 | `'--limit'` | `type=int; default=50` |
| 367 | `'--warmup'` | `type=int; default=3` |
| 368 | `'--latency-samples'` | `type=int; default=50` |
