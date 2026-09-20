# pipeline：功能记录

上级模块：[模块说明](../modules/support-voice.md) · 实现：[voice_group/pipeline.py](../../../voice_group/pipeline.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [ASR、NLU、复核与命令交付](voice-command-production.md)

## 功能职责与范围

语音组完整链路（交付版）—— A + B1 + B2 → DrivingCommand

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `_get_asr`

源码位置：[voice_group/pipeline.py 第 43 行](../../../voice_group/pipeline.py#L43)。类型：`FunctionDef`。

```python
_get_asr() -> 未声明返回类型
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_get_cascade_config`

源码位置：[voice_group/pipeline.py 第 54 行](../../../voice_group/pipeline.py#L54)。类型：`FunctionDef`。

```python
_get_cascade_config() -> 未声明返回类型
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_get_verifier`

源码位置：[voice_group/pipeline.py 第 61 行](../../../voice_group/pipeline.py#L61)。类型：`FunctionDef`。

```python
_get_verifier() -> 未声明返回类型
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `preload_voice_models`

源码位置：[voice_group/pipeline.py 第 68 行](../../../voice_group/pipeline.py#L68)。类型：`FunctionDef`。

```python
preload_voice_models() -> dict
```

Load both ASR models before timed command handling starts.

### `_text_to_command`

源码位置：[voice_group/pipeline.py 第 88 行](../../../voice_group/pipeline.py#L88)。类型：`FunctionDef`。

```python
_text_to_command(text: str, command_id: str, confidence=None) -> dict
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `audio_to_command`

源码位置：[voice_group/pipeline.py 第 103 行](../../../voice_group/pipeline.py#L103)。类型：`FunctionDef`。

```python
audio_to_command(audio, t_audio_start_ns: int=None) -> dict
```

车辆控制组主入口。
audio: 音频文件路径(str) 或 16kHz单声道 numpy 数组(实时流)。
t_audio_start_ns: 实时场景传入采音起始时刻(time.monotonic_ns)，更准。
返回 DrivingCommand dict。

## 内部调用与异常路径

- `_get_asr` 调用：`ASR`.
- `_get_cascade_config` 调用：`CascadeConfig.from_environment`.
- `_get_verifier` 调用：`FasterWhisperVerifier`, `_get_cascade_config`.
- `preload_voice_models` 调用：`_get_asr`, `_get_cascade_config`, `_get_verifier`, `_get_verifier().warmup`, `_text_to_command`, `round`, `time.monotonic_ns`.
- `_text_to_command` 调用：`b2.get`, `parse_command`, `process_asr_text`.
- `audio_to_command` 调用：`_get_asr`, `_get_cascade_config`, `_get_verifier`, `_get_verifier().transcribe`, `_text_to_command`, `apply_verification`, `asr.transcribe`, `b2.get`, `cmd.get`, `final_status.upper`, `mark_verifier_unavailable`, `needs_verification`, `parse_command`, `parsed_status.upper`, `process_asr_text`, `round`, `str`, `str(cmd.get('ambiguity_type', 'NONE')).upper`, `time.monotonic_ns`, `uuid.uuid4`, `verification.get`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- 未发现显式 raise；不代表运行不会失败。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [voice_group/asr_cascade.py](../../../voice_group/asr_cascade.py)
- [voice_group/asr_vad.py](../../../voice_group/asr_vad.py)
- [voice_group/nlu_b2/parser.py](../../../voice_group/nlu_b2/parser.py)
- [voice_group/vehicle_nlu/src/b1_service.py](../../../voice_group/vehicle_nlu/src/b1_service.py)

静态 import 消费者（含测试）：

- [integration/carla_runner.py](../../../integration/carla_runner.py)
- [integration/live_voice.py](../../../integration/live_voice.py)
- [tools/run_four_modal_full_chain.py](../../../tools/run_four_modal_full_chain.py)

## 后续修改需要一起阅读

- [上级模块](../modules/support-voice.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `voice_group/pipeline.py`

来源 SHA256：`2ba622d9270101dcf56ed276f018a90fdc8367f874c71304ff2e1a3236ead84b`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
