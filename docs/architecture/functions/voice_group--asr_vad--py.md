# asr_vad：功能记录

上级模块：[模块说明](../modules/support-voice.md) · 实现：[voice_group/asr_vad.py](../../../voice_group/asr_vad.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [ASR、NLU、复核与命令交付](voice-command-production.md)

## 功能职责与范围

ASR + VAD 模块（A 的最终交付，含语音活动检测）—— 东风智能驾驶语音项目

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `_env_flag`

源码位置：[voice_group/asr_vad.py 第 32 行](../../../voice_group/asr_vad.py#L32)。类型：`FunctionDef`。

```python
_env_flag(name, default=True) -> 未声明返回类型
```

【_env_flag】根据紧邻签名和函数体完成语音识别、复核或命令解释中的局部职责；返回、状态、副作用和异常以本页下方调用/raise记录为边界，名称本身不增加额外保证。

### `_strip`

源码位置：[voice_group/asr_vad.py 第 39 行](../../../voice_group/asr_vad.py#L39)。类型：`FunctionDef`。

```python
_strip(t) -> 未声明返回类型
```

【_strip】根据紧邻签名和函数体完成语音识别、复核或命令解释中的局部职责；返回、状态、副作用和异常以本页下方调用/raise记录为边界，名称本身不增加额外保证。

### `_corr`

源码位置：[voice_group/asr_vad.py 第 44 行](../../../voice_group/asr_vad.py#L44)。类型：`FunctionDef`。

```python
_corr(t) -> 未声明返回类型
```

【_corr】根据紧邻签名和函数体完成语音识别、复核或命令解释中的局部职责；返回、状态、副作用和异常以本页下方调用/raise记录为边界，名称本身不增加额外保证。

### `_local_model_or_id`

源码位置：[voice_group/asr_vad.py 第 49 行](../../../voice_group/asr_vad.py#L49)。类型：`FunctionDef`。

```python
_local_model_or_id(environment_name: str, cache_name: str, model_id: str) -> 未声明返回类型
```

Prefer an explicit/local ModelScope snapshot for offline startup.

### `ASR`

源码位置：[voice_group/asr_vad.py 第 71 行](../../../voice_group/asr_vad.py#L71)。类型：`ClassDef`。

【ASR】定义语音识别、复核或命令解释所需的对象边界；类字段、构造校验和方法才是完整合同，实例化本身不代表外部资源或运行门禁已通过。

### `ASR.__init__`

源码位置：[voice_group/asr_vad.py 第 72 行](../../../voice_group/asr_vad.py#L72)。类型：`FunctionDef`。

```python
ASR.__init__(self, device=DEVICE, lora_dir=LORA_DIR) -> 未声明返回类型
```

【ASR.__init__】按签名接收依赖并建立语音识别、复核或命令解释的实例状态；实际拒绝条件、缓存和资源所有权以函数体及下方调用/raise记录为准。

### `ASR._load`

源码位置：[voice_group/asr_vad.py 第 134 行](../../../voice_group/asr_vad.py#L134)。类型：`FunctionDef`。

```python
ASR._load(self, audio) -> 未声明返回类型
```

【ASR._load】从参数、文件、环境或缓存解析语音识别、复核或命令解释所需输入；路径优先级、默认值和缺失处理以函数体为准，读取成功不自动证明内容身份正确。

### `ASR.transcribe`

源码位置：[voice_group/asr_vad.py 第 147 行](../../../voice_group/asr_vad.py#L147)。类型：`FunctionDef`。

```python
ASR.transcribe(self, audio, correct=True, t_audio_start_ns=None) -> 未声明返回类型
```

【ASR.transcribe】消费签名中的输入并执行语音识别、复核或命令解释的核心推理路径；返回结构、置信度、超时和降级来源必须随结果保留，模型未加载或远端不可达不得记为成功。

## 内部调用与异常路径

- `_env_flag` 调用：`os.getenv`, `value.strip`, `value.strip().lower`.
- `_strip` 调用：`_EMOJI.sub`, `_EMOJI.sub('', t).strip`, `re.sub`.
- `_corr` 调用：`CORRECTION.items`, `t.replace`.
- `_local_model_or_id` 调用：`FileNotFoundError`, `Path`, `Path(configured).expanduser`, `Path.home`, `cached.is_dir`, `os.getenv`, `path.is_dir`, `str`.
- `__init__` 调用：`AutoModel`, `FileNotFoundError`, `Path`, `PeftModel.from_pretrained`, `PeftModel.from_pretrained(self.am.model, str(lora_path)).to`, `RuntimeError`, `_env_flag`, `_local_model_or_id`, `lora_path.is_dir`, `np.zeros`, `os.getenv`, `self.am.generate`, `self.am.model.eval`, `str`.
- `_load` 调用：`int`, `isinstance`, `len`, `np.arange`, `np.asarray`, `np.interp`, `np.interp(np.linspace(0, len(wav), n, endpoint=False), np.arange(len(wav)), wav).astype`, `np.linspace`, `sf.read`, `wav.mean`.
- `transcribe` 调用：`_corr`, `_strip`, `int`, `max`, `res[0].get`, `rich_transcription_postprocess`, `round`, `self._load`, `self.am.generate`, `self.vad.generate`, `time.monotonic_ns`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__init__`，第 94 行：`RuntimeError('peft is required when VOICE_USE_LORA=1; set VOICE_USE_LORA=0 to run the base SenseVoice model in environments without peft')`。
- `__init__`，第 108 行：`FileNotFoundError(f'local LoRA directory not found: {lora_path}')`。
- `_local_model_or_id`，第 55 行：`FileNotFoundError(f'{environment_name} does not point to a model directory: {path}')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [voice_group/pipeline.py](../../../voice_group/pipeline.py)

## 后续修改需要一起阅读

- [上级模块](../modules/support-voice.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `voice_group/asr_vad.py`

来源 SHA256：`e195cdaf6cf240c999cb81d36526f49a7243de347d902fa6699aadb98cdc39a6`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `_local_model_or_id` / 55 | `configured AND not path.is_dir()` | `raise FileNotFoundError(f'{environment_name} does not point to a model directory: {path}')` |
| `ASR.__init__` / 94 | `use_lora AND except ImportError` | `raise RuntimeError('peft is required when VOICE_USE_LORA=1; set VOICE_USE_LORA=0 to run the base SenseVoice model in environments without peft') from error` |
| `ASR.__init__` / 108 | `use_lora AND not lora_path.is_dir()` | `raise FileNotFoundError(f'local LoRA directory not found: {lora_path}')` |

### 环境参数读取位置

这里只记录源码表达式，不读取当前进程环境；缓存与覆盖关系需查调用时机。

| 来源/行 | 环境变量表达式 | 源码fallback |
|---|---|---|
| `voice_group/asr_vad.py:33` | `name` | `None（未传默认）` |
| `voice_group/asr_vad.py:51` | `environment_name` | `None（未传默认）` |
| `voice_group/asr_vad.py:75` | `'VOICE_ASR_LANGUAGE'` | `'auto'` |
