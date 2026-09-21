# run_four_modal_full_chain：功能记录

上级模块：[模块说明](../modules/support-tools.md) · 实现：[tools/run_four_modal_full_chain.py](../../../tools/run_four_modal_full_chain.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [维护工具的运行上下文和证据范围](environment-delivery.md)

## 功能职责与范围

Evaluate frozen full-chain latency with separate accuracy input contracts.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `audio_to_command`

源码位置：[tools/run_four_modal_full_chain.py 第 43 行](../../../tools/run_four_modal_full_chain.py#L43)。类型：`FunctionDef`。

```python
audio_to_command(audio: str, t_audio_start_ns: int) -> dict[str, Any]
```

Load optional ASR dependencies only when a real evaluation is run.

### `preload_voice_models`

源码位置：[tools/run_four_modal_full_chain.py 第 50 行](../../../tools/run_four_modal_full_chain.py#L50)。类型：`FunctionDef`。

```python
preload_voice_models() -> dict[str, Any]
```

Keep unit tests independent of the optional ASR model package.

### `_provided_transcript_command`

源码位置：[tools/run_four_modal_full_chain.py 第 57 行](../../../tools/run_four_modal_full_chain.py#L57)。类型：`FunctionDef`。

```python
_provided_transcript_command(text: str, case_id: str) -> dict[str, Any]
```

Run the production NLU while explicitly bypassing unavailable ASR.

### `_sha256`

源码位置：[tools/run_four_modal_full_chain.py 第 66 行](../../../tools/run_four_modal_full_chain.py#L66)。类型：`FunctionDef`。

```python
_sha256(path: Path) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_resolve_reference`

源码位置：[tools/run_four_modal_full_chain.py 第 74 行](../../../tools/run_four_modal_full_chain.py#L74)。类型：`FunctionDef`。

```python
_resolve_reference(reference: str, *bases: Path) -> Path
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_load_jsonl`

源码位置：[tools/run_four_modal_full_chain.py 第 87 行](../../../tools/run_four_modal_full_chain.py#L87)。类型：`FunctionDef`。

```python
_load_jsonl(path: Path) -> list[dict[str, Any]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_load_latency_samples`

源码位置：[tools/run_four_modal_full_chain.py 第 98 行](../../../tools/run_four_modal_full_chain.py#L98)。类型：`FunctionDef`。

```python
_load_latency_samples(path: Path) -> list[dict[str, Any]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_raw_control`

源码位置：[tools/run_four_modal_full_chain.py 第 125 行](../../../tools/run_four_modal_full_chain.py#L125)。类型：`FunctionDef`。

```python
_raw_control(decision: dict[str, Any]) -> dict[str, float]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_context`

源码位置：[tools/run_four_modal_full_chain.py 第 134 行](../../../tools/run_four_modal_full_chain.py#L134)。类型：`FunctionDef`。

```python
_context(case: dict[str, Any], transcript: str, index: int) -> QwenInputContext
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_safety`

源码位置：[tools/run_four_modal_full_chain.py 第 156 行](../../../tools/run_four_modal_full_chain.py#L156)。类型：`FunctionDef`。

```python
_safety(decision: dict[str, Any] | None, transcript: str, case: dict[str, Any], *, watchdog_alerts: tuple[str, ...]=()) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_case_for_frame`

源码位置：[tools/run_four_modal_full_chain.py 第 198 行](../../../tools/run_four_modal_full_chain.py#L198)。类型：`FunctionDef`。

```python
_case_for_frame(cases: list[dict[str, Any]], cases_path: Path, frame_path: Path) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_make_qwen`

源码位置：[tools/run_four_modal_full_chain.py 第 215 行](../../../tools/run_four_modal_full_chain.py#L215)。类型：`FunctionDef`。

```python
_make_qwen(args: argparse.Namespace) -> tuple[StrictQwenVLAdapter, Any | None, dict[str, object]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_git_commit`

源码位置：[tools/run_four_modal_full_chain.py 第 239 行](../../../tools/run_four_modal_full_chain.py#L239)。类型：`FunctionDef`。

```python
_git_commit() -> str | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_run_one`

源码位置：[tools/run_four_modal_full_chain.py 第 248 行](../../../tools/run_four_modal_full_chain.py#L248)。类型：`FunctionDef`。

```python
_run_one(sample: dict[str, Any], case: dict[str, Any], qwen: Any, index: int, phase: str) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_asr_accuracy`

源码位置：[tools/run_four_modal_full_chain.py 第 313 行](../../../tools/run_four_modal_full_chain.py#L313)。类型：`FunctionDef`。

```python
_asr_accuracy(manifest_path: Path) -> tuple[dict[str, object], list[dict[str, Any]]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_multimodal_accuracy`

源码位置：[tools/run_four_modal_full_chain.py 第 349 行](../../../tools/run_four_modal_full_chain.py#L349)。类型：`FunctionDef`。

```python
_multimodal_accuracy(cases: list[dict[str, Any]], cases_path: Path, qwen: Any) -> tuple[dict[str, object], list[dict[str, Any]]]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_write_json`

源码位置：[tools/run_four_modal_full_chain.py 第 385 行](../../../tools/run_four_modal_full_chain.py#L385)。类型：`FunctionDef`。

```python
_write_json(path: Path, payload: object) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_append_raw`

源码位置：[tools/run_four_modal_full_chain.py 第 390 行](../../../tools/run_four_modal_full_chain.py#L390)。类型：`FunctionDef`。

```python
_append_raw(streams: tuple[Any, Any], record: dict[str, Any]) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_failed_latency_record`

源码位置：[tools/run_four_modal_full_chain.py 第 397 行](../../../tools/run_four_modal_full_chain.py#L397)。类型：`FunctionDef`。

```python
_failed_latency_record(sample: dict[str, Any], index: int, phase: str, exception: Exception) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `main`

源码位置：[tools/run_four_modal_full_chain.py 第 418 行](../../../tools/run_four_modal_full_chain.py#L418)。类型：`FunctionDef`。

```python
main() -> int
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `audio_to_command` 调用：`run_audio_to_command`.
- `preload_voice_models` 调用：`preload`.
- `_provided_transcript_command` 调用：`_text_to_command`, `command.get`.
- `_sha256` 调用：`digest.hexdigest`, `digest.update`, `hashlib.sha256`, `iter`, `path.open`, `stream.read`.
- `_resolve_reference` 调用：`(base / candidate).resolve`, `FileNotFoundError`, `Path`, `Path(reference).expanduser`, `candidate.is_absolute`, `candidate.is_file`, `candidate.resolve`, `path.is_file`.
- `_load_jsonl` 调用：`ValueError`, `any`, `isinstance`, `json.loads`, `line.strip`, `path.read_text`, `path.read_text(encoding='utf-8').splitlines`.
- `_load_latency_samples` 调用：`ValueError`, `_resolve_reference`, `_sha256`, `frame_hashes.add`, `isinstance`, `json.loads`, `len`, `normalized.append`, `path.read_text`, `payload.get`, `set`, `str`.
- `_context` 调用：`QwenInputContext`, `ValueError`, `dict`, `lidar.get`, `perception.get`, `scene_state.get`, `set`.
- `_safety` 调用：`HighLevelCommandAdapter`, `HighLevelCommandAdapter().adapt`, `SafetySupervisor`, `_raw_control`, `build_high_level_command`, `case['safety_state'].get`, `float`, `lidar.get`, `perception.get`, `result.to_dict`, `scene.get`, `str`, `str(perception.get('traffic_light', 'UNKNOWN')).upper`, `supervisor.arbitrate`.
- `_case_for_frame` 调用：`_resolve_reference`, `deepcopy`, `str`.
- `_make_qwen` 调用：`OpenAICompatibleQwenVLBackend`, `StrictQwenVLAdapter`, `StrictQwenVLAdapter.from_local_checkpoint`, `os.environ.get`, `resolve_qwen_profile`.
- `_git_commit` 调用：`subprocess.check_output`, `subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=_REPO_ROOT, text=True).strip`.
- `_run_one` 调用：`_context`, `_evaluate`, `_safety`, `audio_to_command`, `int`, `qwen`, `str`, `str(voice.get('source_text', '')).strip`, `time.monotonic_ns`, `type`, `voice.get`.
- `_asr_accuracy` 调用：`ValueError`, `_resolve_reference`, `audio_to_command`, `isinstance`, `json.loads`, `len`, `manifest_path.read_text`, `records.append`, `sample.get`, `str`, `sum`, `time.monotonic_ns`, `type`, `voice.get`.
- `_multimodal_accuracy` 调用：`_context`, `_evaluate`, `_resolve_reference`, `case.get`, `deepcopy`, `enumerate`, `len`, `qwen`, `records.append`, `str`, `sum`, `type`.
- `_write_json` 调用：`json.dumps`, `path.parent.mkdir`, `path.write_text`.
- `_append_raw` 调用：`json.dumps`, `stream.flush`, `stream.write`.
- `_failed_latency_record` 调用：`type`.
- `main` 调用：`FileNotFoundError`, `ValueError`, `_append_raw`, `_asr_accuracy`, `_case_for_frame`, `_failed_latency_record`, `_git_commit`, `_load_jsonl`, `_load_latency_samples`, `_make_qwen`, `_multimodal_accuracy`, `_run_one`, `_sha256`, `_write_json`, `argparse.ArgumentParser`, `args.asr_manifest.resolve`, `args.latency_manifest.resolve`, `args.multimodal_cases.resolve`, `asr_manifest.is_file`, `backend.add_argument`, `begin_run`, `datetime.now`, `datetime.now(timezone.utc).isoformat`, `evaluate_official_gates`, `evaluate_official_verdict`, `finish_run`, `float`, `len`, `os.environ.get`, `parser.add_argument`, `parser.add_mutually_exclusive_group`, `parser.parse_args`, `preload_voice_models`, `range`, `raw_path.open`, `raw_path.touch`, `records.append`, `remote_backend.close`, `root_raw_path.open`, `root_raw_path.touch`, `str`, `sum`, `summarize_latency`, `type`, `update_run_metadata`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `_asr_accuracy`，第 316 行：`ValueError('ASR manifest must be a JSON list')`。
- `_asr_accuracy`，第 320 行：`ValueError('ASR manifest entries must be objects')`。
- `_context`，第 140 行：`ValueError('case does not declare all four required modalities')`。
- `_context`，第 143 行：`ValueError('case has no valid hashed raw LiDAR evidence')`。
- `_load_jsonl`，第 94 行：`ValueError(f'{path} must contain JSON object rows')`。
- `_load_latency_samples`，第 102 行：`ValueError('latency manifest must contain exactly ten samples')`。
- `_load_latency_samples`，第 107 行：`ValueError('latency manifest samples must be objects')`。
- `_load_latency_samples`，第 113 行：`ValueError('latency manifest source hash mismatch')`。
- `_load_latency_samples`，第 115 行：`ValueError('latency manifest frames must have unique content')`。
- `_resolve_reference`，第 79 行：`FileNotFoundError(candidate)`。
- `_resolve_reference`，第 84 行：`FileNotFoundError(reference)`。
- `main`，第 456 行：`ValueError('--warmup must be non-negative and --measured positive')`。
- `main`，第 461 行：`ValueError('official evidence requires --warmup 5 and --measured 10; pass --diagnostic for any override')`。
- `main`，第 466 行：`ValueError('--scenario-completion-rate must be in [0, 1]')`。
- `main`，第 473 行：`FileNotFoundError(asr_manifest)`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 421 行：`backend.add_argument('--model-path', type=Path)`。
- 第 422 行：`backend.add_argument('--qwen-base-url')`。
- 第 423 行：`parser.add_argument('--profile', default='qwen3vl-2b-int4')`。
- 第 424 行：`parser.add_argument('--asr-manifest', type=Path, required=True)`。
- 第 425 行：`parser.add_argument('--multimodal-cases', type=Path, required=True)`。
- 第 426 行：`parser.add_argument('--latency-manifest', type=Path, required=True)`。
- 第 427 行：`parser.add_argument('--warmup', type=int, default=5)`。
- 第 428 行：`parser.add_argument('--measured', type=int, default=10)`。
- 第 429 行：`parser.add_argument('--diagnostic', action='store_true')`。
- 第 430 行：`parser.add_argument('--scenario-completion-rate', type=float)`。
- 第 431 行：`parser.add_argument('--hardware-label')`。
- 第 432 行：`parser.add_argument('--output', type=Path, required=True)`。

## 上下游与关联验证

静态导入的项目内实现：

- [car_control_A/high_level_command.py](../../../car_control_A/high_level_command.py)
- [car_control_D/__init__.py](../../../car_control_D/__init__.py)
- [integration/qwen_boundary.py](../../../integration/qwen_boundary.py)
- [integration/qwen_command_adapter.py](../../../integration/qwen_command_adapter.py)
- [integration/qwen_profiles.py](../../../integration/qwen_profiles.py)
- [integration/qwen_remote_backend.py](../../../integration/qwen_remote_backend.py)
- [integration/qwen_vl_adapter.py](../../../integration/qwen_vl_adapter.py)
- [integration/run_manifest.py](../../../integration/run_manifest.py)
- [tools/four_modal_metrics.py](../../../tools/four_modal_metrics.py)
- [tools/run_qwen_batch_benchmark.py](../../../tools/run_qwen_batch_benchmark.py)
- [voice_group/pipeline.py](../../../voice_group/pipeline.py)

静态 import 消费者（含测试）：

- [integration/tests/test_four_modal_full_chain_remote.py](../../../integration/tests/test_four_modal_full_chain_remote.py)
- [integration/tests/test_four_modal_provided_transcript.py](../../../integration/tests/test_four_modal_provided_transcript.py)
- [integration/tests/test_run_manifest.py](../../../integration/tests/test_run_manifest.py)

## 后续修改需要一起阅读

- [上级模块](../modules/support-tools.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `tools/run_four_modal_full_chain.py`

来源 SHA256：`34de295c1f99a2d6a07b1731f12b05440dd815fca18eb98df33fd6ffcbc37131`。


CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 421 | `'--model-path'` | `type=Path` |
| 422 | `'--qwen-base-url'` | `` |
| 423 | `'--profile'` | `default='qwen3vl-2b-int4'` |
| 424 | `'--asr-manifest'` | `type=Path; required=True` |
| 425 | `'--multimodal-cases'` | `type=Path; required=True` |
| 426 | `'--latency-manifest'` | `type=Path; required=True` |
| 427 | `'--warmup'` | `type=int; default=5` |
| 428 | `'--measured'` | `type=int; default=10` |
| 429 | `'--diagnostic'` | `action='store_true'` |
| 430 | `'--scenario-completion-rate'` | `type=float` |
| 431 | `'--hardware-label'` | `` |
| 432 | `'--output'` | `type=Path; required=True` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `_resolve_reference` / 79 | `candidate.is_absolute()` | `raise FileNotFoundError(candidate)` |
| `_resolve_reference` / 84 | `本地无直接if；检查上下文` | `raise FileNotFoundError(reference)` |
| `_load_jsonl` / 94 | `not rows or any((not isinstance(row, dict) for row in rows))` | `raise ValueError(f'{path} must contain JSON object rows')` |
| `_load_latency_samples` / 102 | `not isinstance(samples, list) or len(samples) != 10` | `raise ValueError('latency manifest must contain exactly ten samples')` |
| `_load_latency_samples` / 107 | `not isinstance(sample, dict)` | `raise ValueError('latency manifest samples must be objects')` |
| `_load_latency_samples` / 113 | `_sha256(audio) != audio_sha256 or _sha256(frame) != frame_sha256` | `raise ValueError('latency manifest source hash mismatch')` |
| `_load_latency_samples` / 115 | `frame_sha256 in frame_hashes` | `raise ValueError('latency manifest frames must have unique content')` |
| `_context` / 140 | `set(scene_state.get('modalities', {})) != required` | `raise ValueError('case does not declare all four required modalities')` |
| `_context` / 143 | `not lidar.get('valid') or not lidar.get('raw_sha256')` | `raise ValueError('case has no valid hashed raw LiDAR evidence')` |
| `_asr_accuracy` / 316 | `not isinstance(payload, list)` | `raise ValueError('ASR manifest must be a JSON list')` |
| `_asr_accuracy` / 320 | `not isinstance(sample, dict)` | `raise ValueError('ASR manifest entries must be objects')` |
| `main` / 456 | `args.warmup < 0 or args.measured <= 0` | `raise ValueError('--warmup must be non-negative and --measured positive')` |
| `main` / 461 | `not official_mode and (not args.diagnostic)` | `raise ValueError('official evidence requires --warmup 5 and --measured 10; pass --diagnostic for any override')` |
| `main` / 466 | `args.scenario_completion_rate is not None and (not 0.0 <= args.scenario_completion_rate <= 1.0)` | `raise ValueError('--scenario-completion-rate must be in [0, 1]')` |
| `main` / 473 | `not asr_manifest.is_file()` | `raise FileNotFoundError(asr_manifest)` |
| `main` / 587 | `except Exception` | `raise` |

### 环境参数读取位置

这里只记录源码表达式，不读取当前进程环境；缓存与覆盖关系需查调用时机。

| 来源/行 | 环境变量表达式 | 源码fallback |
|---|---|---|
| `tools/run_four_modal_full_chain.py:436` | `'DOCKER_IMAGE_DIGESTS'` | `''` |
| `tools/run_four_modal_full_chain.py:221` | `'QWEN_API_KEY'` | `凭据参数，不抄录值` |
| `tools/run_four_modal_full_chain.py:437` | `'HARDWARE_LABEL'` | `None（未传默认）` |
