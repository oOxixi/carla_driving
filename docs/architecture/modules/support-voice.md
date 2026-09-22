# Voice recognition and command interpretation

## 开发维护先读：实际语义

以下功能页说明实现理由、分支、接口含义、改动联动与验证。先读这些内容，再按逐文件索引定位方法；不要用函数名推断业务语义。

- [ASR、NLU、复核与命令交付](../functions/voice-command-production.md)

Parent: [Support module](../modules/support.md).

## Functions and sources

- [pipeline.py](../../../voice_group/pipeline.py): production audio_to_command(audio, t_audio_start_ns=None), preload_voice_models and ASR/B1/B2/verification orchestration. Package import and directory-local CLI share this implementation.
- [asr_vad.py](../../../voice_group/asr_vad.py): SenseVoice, VAD, dialect LoRA, local model resolution, transcript cleanup. Model environment variables and caches own model lookup.
- [asr_cascade.py](../../../voice_group/asr_cascade.py): CascadeConfig, ConfidenceCalibrator, FasterWhisperVerifier; needs_verification selects review, semantic_signature compares command meaning, apply_verification and mark_verifier_unavailable handle disagreement or unavailable verification.
- [b1_service.py](../../../voice_group/vehicle_nlu/src/b1_service.py): process_asr_text uses normalizer and intent_classifier to produce intent/confidence.
- [parser.py](../../../voice_group/nlu_b2/parser.py): DrivingCommandParser/parse_command implements speed, direction, obstacle/target, route and relative speed slots, common safety checks and status. nlu_b2/cli.py exposes standalone parsing.

## Contract, ownership and failure

[INTERFACE.md](../../../voice_group/docs/INTERFACE.md) documents fields; interfaces consumer validation owns executable contract constraints. Output includes command_id/source_text/intent/parameters/status/confirm_required/errors/warnings. Preserve units and nullable confidence. Non-valid or confirmation-required commands must not become normal executable commands. Missing calibrated confidence is not measured high confidence.

[MODEL_MANIFEST.json](../../../voice_group/MODEL_MANIFEST.json) owns weight identity; lora_dialect is the production adapter. models/*_confidence.json contains small/tiny Whisper calibration. Preserve recognition, model-loading, verification-unavailable and disagreement provenance.

## Dependencies, validation and coordinated edits

Input comes from audio files/live capture; output feeds runtime/integration command routing. Run python -m pytest -q voice_group/tests for text and mocked boundary regression, tools/evaluate_voice_audio.py for actual audio and tools/verify_voice_weights.py for weights. test_samples/manifest.json owns sample membership; docs/evaluation distinguishes text, Windows, server and cascade evidence. 50 dBA claims require physical calibration evidence.

Changing intents/parameters requires checking B1, B2, interfaces, control routing, Qwen request generation, training labels and regression samples. Changing ASR weights requires manifest, calibration and audio evaluation updates. Text-only tests do not validate loaded GPU models.


## 模块接口与参数核对（2026-09-20）

audio_to_command(audio,t_audio_start_ns=None)返回命令dict；_text_to_command是文本路径，不能用文本测试证明音频模型加载成功。输出envelope需保留status、errors/warnings、confirm_required、confidence和参数单位。

### 参数语义与生效边界

CascadeConfig默认启用small/cuda/int8_float16，minimum_calibrated_confidence=0.9；calibration_path指向small校准文件。缺校准confidence不是高置信。复核不可用、识别分歧与模型不可加载是不同来源。

### 上下游与修改影响

模型权重由MODEL_MANIFEST管理；改意图/槽位需查voice/canonical adapter、Schema、模型请求、执行FSM和训练数据。实际50dBA能力需要物理校准，mock/text测试不提供此证据。

### [voice_group/pipeline.py](../../../voice_group/pipeline.py) 的入口与声明

```python
preload_voice_models() -> dict
audio_to_command(audio, t_audio_start_ns: int=None) -> dict
```

### [voice_group/asr_cascade.py](../../../voice_group/asr_cascade.py) 的入口与声明

```python
CascadeConfig.from_environment(cls) -> 'CascadeConfig'
ConfidenceCalibrator.__init__(self, path: Path) -> None
ConfidenceCalibrator.transform(self, raw_probability: float | None) -> float | None
FasterWhisperVerifier.__init__(self, config: CascadeConfig | None=None) -> None
FasterWhisperVerifier.warmup(self) -> None
FasterWhisperVerifier.transcribe(self, audio: Any) -> dict[str, Any]
needs_verification(command: dict[str, Any]) -> bool
semantic_signature(command: dict[str, Any]) -> tuple[Any, ...]
apply_verification(primary: dict[str, Any], verification: dict[str, Any], secondary: dict[str, Any], *, minimum_confidence: float) -> dict[str, Any]
mark_verifier_unavailable(command: dict[str, Any], error: Exception) -> dict[str, Any]
```

类级字段（含配置、输入输出和内部状态；仅声明默认，不是当前run生效配置）：

| 字段 | 类型 | 默认值/来源 |
|---|---|---|
| `CascadeConfig.enabled` | `bool` | `True` |
| `CascadeConfig.model_size` | `str` | `'small'` |
| `CascadeConfig.device` | `str` | `'cuda'` |
| `CascadeConfig.compute_type` | `str` | `'int8_float16'` |
| `CascadeConfig.minimum_calibrated_confidence` | `float` | `0.9` |
| `CascadeConfig.calibration_path` | `Path` | `Path(__file__).resolve().parent / 'models' / 'faster_whisper_small_confidence.json'` |

### [integration/voice_adapter.py](../../../integration/voice_adapter.py) 的入口与声明

```python
VoiceCommandAdapter.__init__(self, *, default_ttl_s: float=3.0, default_slow_speed_mps: float=2.0) -> None
VoiceCommandAdapter.adapt(self, envelope: Mapping[str, object], *, now_s: float) -> AdaptedVoiceCommand
```

类级字段（含配置、输入输出和内部状态；仅声明默认，不是当前run生效配置）：

| 字段 | 类型 | 默认值/来源 |
|---|---|---|
| `VoiceDiagnostic.code` | `str` | `无声明默认（构造/赋值方提供）` |
| `VoiceDiagnostic.message` | `str` | `无声明默认（构造/赋值方提供）` |
| `VoiceCommandMetadata.source_text` | `str` | `无声明默认（构造/赋值方提供）` |
| `VoiceCommandMetadata.intent` | `str` | `无声明默认（构造/赋值方提供）` |
| `VoiceCommandMetadata.parameters` | `dict[str, object]` | `无声明默认（构造/赋值方提供）` |
| `VoiceCommandMetadata.status` | `str` | `无声明默认（构造/赋值方提供）` |
| `VoiceCommandMetadata.ambiguity_type` | `str` | `无声明默认（构造/赋值方提供）` |
| `VoiceCommandMetadata.errors` | `tuple[VoiceDiagnostic, ...]` | `无声明默认（构造/赋值方提供）` |
| `VoiceCommandMetadata.warnings` | `tuple[VoiceDiagnostic, ...]` | `无声明默认（构造/赋值方提供）` |
| `VoiceCommandMetadata.t_audio_start_ns` | `int &#124; None` | `无声明默认（构造/赋值方提供）` |
| `VoiceCommandMetadata.t_asr_end_ns` | `int &#124; None` | `无声明默认（构造/赋值方提供）` |
| `VoiceCommandMetadata.t_intent_end_ns` | `int &#124; None` | `无声明默认（构造/赋值方提供）` |
| `AdaptedVoiceCommand.command` | `DrivingCommand` | `无声明默认（构造/赋值方提供）` |
| `AdaptedVoiceCommand.metadata` | `VoiceCommandMetadata` | `无声明默认（构造/赋值方提供）` |
| `AdaptedVoiceCommand.control_authorized` | `bool` | `True` |
| `AdaptedVoiceCommand.feedback` | `ExecutionFeedback &#124; None` | `None` |

以上为核心交接入口；模块内其余实现、CLI和资源的完整字段/拒绝条件见本页功能小文档索引。类型未声明的返回值不凭名称推断。当前代码基线fe1ba839，静态复核不证明实际CARLA/GPU/板端运行成功。

## 功能小文档完整索引

以下功能页分别记录实现入口、输入输出声明、内部调用、异常、配置和静态上下游；测试文件保留在源码索引中。

- [voice_group/asr_cascade.py](../functions/voice_group--asr_cascade--py.md)
- [voice_group/asr_vad.py](../functions/voice_group--asr_vad--py.md)
- [voice_group/nlu_b2/__init__.py](../functions/voice_group--nlu_b2--__init__--py.md)
- [voice_group/nlu_b2/cli.py](../functions/voice_group--nlu_b2--cli--py.md)
- [voice_group/nlu_b2/parser.py](../functions/voice_group--nlu_b2--parser--py.md)
- [voice_group/pipeline.py](../functions/voice_group--pipeline--py.md)
- [voice_group/requirements-whisper-gpu-windows.txt](../functions/voice_group--requirements-whisper-gpu-windows--txt.md)
- [voice_group/requirements.txt](../functions/voice_group--requirements--txt.md)
- [voice_group/vehicle_nlu/requirements.txt](../functions/voice_group--vehicle_nlu--requirements--txt.md)
- [voice_group/vehicle_nlu/src/__init__.py](../functions/voice_group--vehicle_nlu--src--__init__--py.md)
- [voice_group/vehicle_nlu/src/b1_service.py](../functions/voice_group--vehicle_nlu--src--b1_service--py.md)
- [voice_group/vehicle_nlu/src/intent_classifier.py](../functions/voice_group--vehicle_nlu--src--intent_classifier--py.md)
- [voice_group/vehicle_nlu/src/normalizer.py](../functions/voice_group--vehicle_nlu--src--normalizer--py.md)

## 诊断与维护交接

本模块证据：音频、ASR/NLU envelope、confidence/errors；关联同一输入。功能实现与上下游见本页原索引；跨模块回查[追踪矩阵](../TRACEABILITY.md)与[诊断入口](../DIAGNOSIS.md)。实际run必须核对版本，未执行的检查不视为已通过。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `voice_group/tests/test_asr_cascade.py`

来源 SHA256：`641f8a9b9922170b8953887a33b3c4eb6fcec70d4915f83b882246dca6ed6115`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `voice_group/tests/test_audio_evaluator.py`

来源 SHA256：`778f777355c485f468a502f19f651e1cd515e759ccafbb7ab55e57e216b79432`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `voice_group/tests/test_manifest_regression.py`

来源 SHA256：`cb5df982389f6d723bd6ddb566373251c995f92abcd12cac7739bfd822a1ff66`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `voice_group/tests/test_safety_boundary.py`

来源 SHA256：`81c9e872dad6d19c552cd4bdd7e778711f2595f9cafe8a91fe63ed857bb3c759`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `voice_group/tests/test_whisper_calibration.py`

来源 SHA256：`2fc960a6ea0772ee7b50f22d7a15a228501cc4cfe8e013b44cdc131d37e2e7a3`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。

### 环境覆盖

CascadeConfig.from_environment读取VOICE_CASCADE_ENABLED（1/true/yes/on为真）、VOICE_CASCADE_MODEL、VOICE_CASCADE_DEVICE、VOICE_CASCADE_COMPUTE_TYPE、VOICE_CASCADE_MIN_CONFIDENCE及VOICE_CASCADE_CALIBRATION。类默认不是部署事实；pipeline缓存配置，修改环境后需核对初始化时机。

## 第16模块逐入口精读结论（2026-09-22）

本轮按当前 `challenge` 基线 `4e41f990` 核对13份实现/依赖页和1份语义页，将50处泛用占位改成对应入口的输入、转换、状态、副作用和证据边界。这里只整理现有行为，没有改ASR、NLU或控制代码。

### 生产链与控制授权

实际链路为 `audio_to_command` → SenseVoice ASR → B1规范化/意图分类 → B2槽位与安全检查；仅当 `needs_verification` 命中时才调用 faster-whisper，再由 `apply_verification` 比较语义签名。输出仍是带 `status`、`confirm_required`、`errors/warnings` 和纳秒时间戳的命令 envelope；后续 `VoiceCommandAdapter` 才决定是否形成可执行 `DrivingCommand`。文本入口 `_text_to_command` 跳过音频解码、VAD、模型装载和声学置信度，不能作为音频全链证据。

### 状态、配置与失败语义

- ASR、cascade config 和 verifier 是进程级延迟缓存；环境变量在首次创建后修改不会自动重建对象。部署证据必须记录进程启动时环境，而不是事后读取当前shell。
- primary识别错误、需要复核、secondary不可用、两路语义不一致和B2拒绝是不同失败来源；不得把它们统一改写成普通低置信命令。
- `preload_voice_models` 只证明预热调用返回；生产身份仍需 `MODEL_MANIFEST.json`、本地权重hash和实际音频结果共同确认。
- 50 dBA、方言、噪声和端到端时延都依赖真实采集条件。文本样本、mock verifier或模型缓存存在不能替代声学校准证据。

### 修改联动与门禁

改意图、槽位、单位或确认规则时，至少同步核对B1/B2、voice/canonical adapter、Interface Schema、Qwen请求、A状态机和训练标签；改模型或置信度时同步模型manifest、校准文件、音频manifest与评测报告。最低门禁依次是文本/边界单测、权重核验、固定音频回放、噪声/方言分层报告，最后才是CARLA中的控制授权与终态。任何一级缺失都只能报告该级结果。
