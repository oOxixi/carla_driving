# asr_cascade：功能记录

上级模块：[模块说明](../modules/support-voice.md) · 实现：[voice_group/asr_cascade.py](../../../voice_group/asr_cascade.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [ASR、NLU、复核与命令交付](voice-command-production.md)

## 功能职责与范围

Conditional faster-whisper verification for safety-critical voice commands.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `CascadeConfig.enabled: bool`；默认：`True`。
- `CascadeConfig.model_size: str`；默认：`'small'`。
- `CascadeConfig.device: str`；默认：`'cuda'`。
- `CascadeConfig.compute_type: str`；默认：`'int8_float16'`。
- `CascadeConfig.minimum_calibrated_confidence: float`；默认：`0.9`。
- `CascadeConfig.calibration_path: Path`；默认：`Path(__file__).resolve().parent / 'models' / 'faster_whisper_small_confidence.json'`。

## 功能入口：输入、输出与实现说明

### `_add_nvidia_dll_directories`

源码位置：[voice_group/asr_cascade.py 第 34 行](../../../voice_group/asr_cascade.py#L34)。类型：`FunctionDef`。

```python
_add_nvidia_dll_directories() -> None
```

Expose pip-installed NVIDIA runtime DLLs to CTranslate2 on Windows.

### `CascadeConfig`

源码位置：[voice_group/asr_cascade.py 第 52 行](../../../voice_group/asr_cascade.py#L52)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `CascadeConfig.from_environment`

源码位置：[voice_group/asr_cascade.py 第 65 行](../../../voice_group/asr_cascade.py#L65)。类型：`FunctionDef`。

```python
CascadeConfig.from_environment(cls) -> 'CascadeConfig'
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ConfidenceCalibrator`

源码位置：[voice_group/asr_cascade.py 第 87 行](../../../voice_group/asr_cascade.py#L87)。类型：`ClassDef`。

Apply a stored Platt calibration without inventing a fallback score.

### `ConfidenceCalibrator.__init__`

源码位置：[voice_group/asr_cascade.py 第 90 行](../../../voice_group/asr_cascade.py#L90)。类型：`FunctionDef`。

```python
ConfidenceCalibrator.__init__(self, path: Path) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `ConfidenceCalibrator.transform`

源码位置：[voice_group/asr_cascade.py 第 99 行](../../../voice_group/asr_cascade.py#L99)。类型：`FunctionDef`。

```python
ConfidenceCalibrator.transform(self, raw_probability: float | None) -> float | None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `FasterWhisperVerifier`

源码位置：[voice_group/asr_cascade.py 第 111 行](../../../voice_group/asr_cascade.py#L111)。类型：`ClassDef`。

Lazy faster-whisper adapter; model loading occurs only on first trigger.

### `FasterWhisperVerifier.__init__`

源码位置：[voice_group/asr_cascade.py 第 114 行](../../../voice_group/asr_cascade.py#L114)。类型：`FunctionDef`。

```python
FasterWhisperVerifier.__init__(self, config: CascadeConfig | None=None) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `FasterWhisperVerifier._get_model`

源码位置：[voice_group/asr_cascade.py 第 120 行](../../../voice_group/asr_cascade.py#L120)。类型：`FunctionDef`。

```python
FasterWhisperVerifier._get_model(self) -> 未声明返回类型
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `FasterWhisperVerifier.warmup`

源码位置：[voice_group/asr_cascade.py 第 136 行](../../../voice_group/asr_cascade.py#L136)。类型：`FunctionDef`。

```python
FasterWhisperVerifier.warmup(self) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `FasterWhisperVerifier.transcribe`

源码位置：[voice_group/asr_cascade.py 第 166 行](../../../voice_group/asr_cascade.py#L166)。类型：`FunctionDef`。

```python
FasterWhisperVerifier.transcribe(self, audio: Any) -> dict[str, Any]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `needs_verification`

源码位置：[voice_group/asr_cascade.py 第 221 行](../../../voice_group/asr_cascade.py#L221)。类型：`FunctionDef`。

```python
needs_verification(command: dict[str, Any]) -> bool
```

Verify commands where a second model can change a control decision.

UNKNOWN commands are already rejected by the primary parser, while STOP
commands must take the fast safe path. Running Whisper for either class
adds latency without improving the control decision.

### `semantic_signature`

源码位置：[voice_group/asr_cascade.py 第 236 行](../../../voice_group/asr_cascade.py#L236)。类型：`FunctionDef`。

```python
semantic_signature(command: dict[str, Any]) -> tuple[Any, ...]
```

Return only fields whose disagreement can change vehicle behaviour.

Free-form target wording is deliberately excluded. For obstacle avoidance,
for example, ``障碍物`` versus the homophone ``帐碍物`` must not block an
otherwise identical left/right manoeuvre.

### `apply_verification`

源码位置：[voice_group/asr_cascade.py 第 261 行](../../../voice_group/asr_cascade.py#L261)。类型：`FunctionDef`。

```python
apply_verification(primary: dict[str, Any], verification: dict[str, Any], secondary: dict[str, Any], *, minimum_confidence: float) -> dict[str, Any]
```

Attach audit data and gate execution when the two semantics disagree.

### `mark_verifier_unavailable`

源码位置：[voice_group/asr_cascade.py 第 322 行](../../../voice_group/asr_cascade.py#L322)。类型：`FunctionDef`。

```python
mark_verifier_unavailable(command: dict[str, Any], error: Exception) -> dict[str, Any]
```

Fail into the confirmation gate rather than silently bypass verification.

## 内部调用与异常路径

- `_add_nvidia_dll_directories` 调用：`Path`, `_DLL_DIRECTORY_HANDLES.append`, `directories.append`, `directory.is_dir`, `hasattr`, `os.add_dll_directory`, `os.environ.get`, `os.pathsep.join`, `str`.
- `needs_verification` 调用：`_NUMBER.search`, `bool`, `command.get`, `str`, `str(command.get('intent', '')).upper`.
- `semantic_signature` 调用：`command.get`, `parameters.get`, `str`, `str(command.get('intent', '')).upper`.
- `apply_verification` 调用：`dict`, `output.get`, `primary.get`, `secondary.get`, `semantic_signature`, `str`, `str(primary.get('intent', '')).upper`, `verification.get`.
- `mark_verifier_unavailable` 调用：`dict`, `output.get`, `type`.
- `from_environment` 调用：`Path`, `cls`, `float`, `os.getenv`, `os.getenv('VOICE_CASCADE_ENABLED', '1').strip`, `os.getenv('VOICE_CASCADE_ENABLED', '1').strip().lower`, `str`.
- `__init__` 调用：`CascadeConfig.from_environment`, `ConfidenceCalibrator`, `ValueError`, `json.loads`, `path.is_file`, `path.read_text`, `payload.get`.
- `transform` 调用：`float`, `math.exp`, `math.log`, `max`, `min`, `round`.
- `_get_model` 调用：`RuntimeError`, `WhisperModel`, `_add_nvidia_dll_directories`.
- `warmup` 调用：`list`, `model.transcribe`, `np.zeros`, `self._get_model`.
- `transcribe` 调用：`''.join`, `''.join((segment.text for segment in realized)).strip`, `OpenCC`, `OpenCC('t2s').convert`, `float`, `getattr`, `len`, `list`, `round`, `self._calibrator.transform`, `self._get_model`, `self._get_model().transcribe`, `sum`, `time.monotonic_ns`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__init__`，第 96 行：`ValueError(f'unsupported confidence calibration: {path}')`。
- `_get_model`，第 126 行：`RuntimeError('faster-whisper is not installed; install voice_group requirements')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [tools/calibrate_whisper_confidence.py](../../../tools/calibrate_whisper_confidence.py)
- [voice_group/pipeline.py](../../../voice_group/pipeline.py)
- [voice_group/tests/test_asr_cascade.py](../../../voice_group/tests/test_asr_cascade.py)

## 后续修改需要一起阅读

- [上级模块](../modules/support-voice.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `voice_group/asr_cascade.py`

来源 SHA256：`066b3cb4eb6aeac109bcf535bca05472a7930e5e7d3e7eeab7da1f800bd77cad`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `CascadeConfig.enabled` | `bool` | `True` |
| `CascadeConfig.model_size` | `str` | `'small'` |
| `CascadeConfig.device` | `str` | `'cuda'` |
| `CascadeConfig.compute_type` | `str` | `'int8_float16'` |
| `CascadeConfig.minimum_calibrated_confidence` | `float` | `0.9` |
| `CascadeConfig.calibration_path` | `Path` | `Path(__file__).resolve().parent / 'models' / 'faster_whisper_small_confidence.json'` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `ConfidenceCalibrator.__init__` / 96 | `path.is_file() AND payload.get('method') != 'platt_logit'` | `raise ValueError(f'unsupported confidence calibration: {path}')` |
| `FasterWhisperVerifier._get_model` / 126 | `self._model is None AND except ImportError` | `raise RuntimeError('faster-whisper is not installed; install voice_group requirements') from error` |

### 环境参数读取位置

这里只记录源码表达式，不读取当前进程环境；缓存与覆盖关系需查调用时机。

| 来源/行 | 环境变量表达式 | 源码fallback |
|---|---|---|
| `voice_group/asr_cascade.py:47` | `'PATH'` | `''` |
| `voice_group/asr_cascade.py:69` | `'VOICE_CASCADE_MODEL'` | `'small'` |
| `voice_group/asr_cascade.py:70` | `'VOICE_CASCADE_DEVICE'` | `'cuda'` |
| `voice_group/asr_cascade.py:71` | `'VOICE_CASCADE_COMPUTE_TYPE'` | `'int8_float16'` |
| `voice_group/asr_cascade.py:76` | `'VOICE_CASCADE_MIN_CONFIDENCE'` | `'0.90'` |
| `voice_group/asr_cascade.py:79` | `'VOICE_CASCADE_CALIBRATION'` | `str(cls.calibration_path)` |
| `voice_group/asr_cascade.py:66` | `'VOICE_CASCADE_ENABLED'` | `'1'` |
