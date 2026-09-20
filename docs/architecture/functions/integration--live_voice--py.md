# live_voice：功能记录

上级模块：[模块说明](../modules/vehicle-entry.md) · 实现：[integration/live_voice.py](../../../integration/live_voice.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [一帧控制的实际顺序与执行值](control-frame.md)

## 功能职责与范围

Continuous PulseAudio microphone input for the CARLA voice runner.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `LiveVoiceConfig.source: str`；默认：`'@DEFAULT_SOURCE@'`。
- `LiveVoiceConfig.sample_rate: int`；默认：`16000`。
- `LiveVoiceConfig.frame_ms: int`；默认：`20`。
- `LiveVoiceConfig.pre_roll_ms: int`；默认：`300`。
- `LiveVoiceConfig.end_silence_ms: int`；默认：`700`。
- `LiveVoiceConfig.max_utterance_s: float`；默认：`7.0`。
- `LiveVoiceConfig.min_voice_ms: int`；默认：`160`。
- `LiveVoiceConfig.min_rms: float`；默认：`0.003`。
- `LiveVoiceConfig.noise_ratio: float`；默认：`3.0`。
- `LiveVoiceConfig.trigger_frames: int`；默认：`3`。
- `LiveVoiceResult.command: dict[str, Any] | None`；默认：`未在声明处设置`。
- `LiveVoiceResult.duration_s: float`；默认：`未在声明处设置`。
- `LiveVoiceResult.error: str | None`；默认：`None`。

## 功能入口：输入、输出与实现说明

<a id="fn-livevoiceconfig"></a>

### `LiveVoiceConfig`

源码位置：[integration/live_voice.py 第 21 行](../../../integration/live_voice.py#L21)。类型：`ClassDef`。

麦克风/VAD配置：默认PulseAudio source、16kHz、20ms PCM帧、300ms预滚、700ms尾静音、最长7s、最少160ms有声、min_rms0.003、noise_ratio3、连续3帧触发。它允许配置其他正采样率，但下游音频管线接口按16kHz使用，不能认为改采样率会自动重采样。

<a id="fn-livevoiceconfig---post-init--"></a>

### `LiveVoiceConfig.__post_init__`

源码位置：[integration/live_voice.py 第 33 行](../../../integration/live_voice.py#L33)。类型：`FunctionDef`。

```python
LiveVoiceConfig.__post_init__(self) -> None
```

拒绝空source、非正sample_rate/frame_ms、不能整除1000的frame_ms、负预滚、非正尾静音/最长时长/最少有声时长、min_rms<=0、noise_ratio<=1和trigger_frames<1。这里主要是比较校验，没有严格int/finite或采样率必须16kHz的检查。

<a id="fn-livevoiceconfig-samples-per-frame"></a>

### `LiveVoiceConfig.samples_per_frame`

源码位置：[integration/live_voice.py 第 50 行](../../../integration/live_voice.py#L50)。类型：`FunctionDef`。

```python
LiveVoiceConfig.samples_per_frame(self) -> int
```

sample_rate*frame_ms//1000，整数下取整；默认320样本。代码未额外要求该乘积整除1000。

<a id="fn-livevoiceconfig-bytes-per-frame"></a>

### `LiveVoiceConfig.bytes_per_frame`

源码位置：[integration/live_voice.py 第 54 行](../../../integration/live_voice.py#L54)。类型：`FunctionDef`。

```python
LiveVoiceConfig.bytes_per_frame(self) -> int
```

samples_per_frame*2，假定单声道16位s16le；默认640字节，不适用于float PCM或双声道直接输入。

<a id="fn-energyvadsegmenter"></a>

### `EnergyVadSegmenter`

源码位置：[integration/live_voice.py 第 58 行](../../../integration/live_voice.py#L58)。类型：`ClassDef`。

Adaptive energy VAD for short push-free driving commands.

<a id="fn-energyvadsegmenter---init--"></a>

### `EnergyVadSegmenter.__init__`

源码位置：[integration/live_voice.py 第 61 行](../../../integration/live_voice.py#L61)。类型：`FunctionDef`。

```python
EnergyVadSegmenter.__init__(self, config: LiveVoiceConfig | None=None) -> None
```

缺config用默认；预滚至少保留1帧，噪声RMS历史长度为3秒。尾静音/最长/最少有声阈值换算帧数并至少1帧；初始化空片段、触发/静音/有声计数与未激活状态。

<a id="fn-energyvadsegmenter--rms"></a>

### `EnergyVadSegmenter._rms`

源码位置：[integration/live_voice.py 第 85 行](../../../integration/live_voice.py#L85)。类型：`FunctionDef`。

```python
EnergyVadSegmenter._rms(frame: bytes) -> float
```

将bytes按little-endian int16转float32并除32768，返回均方根；空输入返回0，不进行语音分类。异常PCM长度可能由numpy拒绝，feed先检查固定帧字节数。

<a id="fn-energyvadsegmenter--threshold"></a>

### `EnergyVadSegmenter._threshold`

源码位置：[integration/live_voice.py 第 92 行](../../../integration/live_voice.py#L92)。类型：`FunctionDef`。

```python
EnergyVadSegmenter._threshold(self) -> float
```

无噪声历史返回min_rms，否则max(min_rms,历史RMS中位数*noise_ratio)。仅非激活时低于阈值的帧更新噪声历史，进入片段后使用触发时冻结阈值。

<a id="fn-energyvadsegmenter-feed"></a>

### `EnergyVadSegmenter.feed`

源码位置：[integration/live_voice.py 第 101 行](../../../integration/live_voice.py#L101)。类型：`FunctionDef`。

```python
EnergyVadSegmenter.feed(self, frame: bytes) -> bytes | None
```

要求bytes数恰为bytes_per_frame，否则ValueError。未激活时积累预滚和连续高能帧，达到trigger_frames后激活；激活后统计有声/尾静音，尾静音到限或总长度到限结束。只有有声帧达到min_voice_frames才返回拼接PCM，否则None；结束均reset，不做识别。

<a id="fn-energyvadsegmenter-flush"></a>

### `EnergyVadSegmenter.flush`

源码位置：[integration/live_voice.py 第 138 行](../../../integration/live_voice.py#L138)。类型：`FunctionDef`。

```python
EnergyVadSegmenter.flush(self) -> bytes | None
```

流结束时输出仍激活且有声帧达标的剩余PCM；否则None。两种分支均重置片段状态；结果可能包含预滚/尾静音。

<a id="fn-energyvadsegmenter--reset-after-utterance"></a>

### `EnergyVadSegmenter._reset_after_utterance`

源码位置：[integration/live_voice.py 第 146 行](../../../integration/live_voice.py#L146)。类型：`FunctionDef`。

```python
EnergyVadSegmenter._reset_after_utterance(self) -> None
```

清激活标志、片段、触发/静音/有声计数及预滚；保留_noise_rms历史，因此下段仍采用已有背景噪声估计。

<a id="fn-livevoiceresult"></a>

### `LiveVoiceResult`

源码位置：[integration/live_voice.py 第 156 行](../../../integration/live_voice.py#L156)。类型：`ClassDef`。

识别结果：command为envelope或None，duration_s是PCM片段时长，error为诊断字符串或None。duration不是ASR推理耗时；队列溢出也用此对象报告。

<a id="fn-livevoicesource"></a>

### `LiveVoiceSource`

源码位置：[integration/live_voice.py 第 162 行](../../../integration/live_voice.py#L162)。类型：`ClassDef`。

Capture, segment, and recognize microphone commands asynchronously.

<a id="fn-livevoicesource---init--"></a>

### `LiveVoiceSource.__init__`

源码位置：[integration/live_voice.py 第 165 行](../../../integration/live_voice.py#L165)。类型：`FunctionDef`。

```python
LiveVoiceSource.__init__(self, config: LiveVoiceConfig | None=None) -> None
```

建立最大4段的音频队列、无界结果队列、停止Event及空进程/线程引用；不启动采集/模型。对象的停止标志和线程引用没有重置接口。

<a id="fn-livevoicesource-preload"></a>

### `LiveVoiceSource.preload`

源码位置：[integration/live_voice.py 第 174 行](../../../integration/live_voice.py#L174)。类型：`FunctionDef`。

```python
LiveVoiceSource.preload(self) -> dict[str, object]
```

延迟导入voice_group.pipeline.preload_voice_models并原样返回模型预热报告；不启动parec或线程，模型/依赖加载异常向调用方传播。

<a id="fn-livevoicesource-start"></a>

### `LiveVoiceSource.start`

源码位置：[integration/live_voice.py 第 179 行](../../../integration/live_voice.py#L179)。类型：`FunctionDef`。

```python
LiveVoiceSource.start(self) -> None
```

已有_capture_thread即RuntimeError。启动parec按source/rate采集s16le单声道raw，stdout管道、stderr丢弃；再启动capture和ASR两个daemon线程。系统需提供parec/PulseAudio；stop后引用未清，不能在同对象上再次start。

<a id="fn-livevoicesource-poll"></a>

### `LiveVoiceSource.poll`

源码位置：[integration/live_voice.py 第 207 行](../../../integration/live_voice.py#L207)。类型：`FunctionDef`。

```python
LiveVoiceSource.poll(self) -> tuple[LiveVoiceResult, ...]
```

循环get_nowait取尽当前结果，遇queue.Empty返回tuple。非阻塞，不等待下一段音频，不修改车辆状态；runner主线程负责处理command。

<a id="fn-livevoicesource-stop"></a>

### `LiveVoiceSource.stop`

源码位置：[integration/live_voice.py 第 215 行](../../../integration/live_voice.py#L215)。类型：`FunctionDef`。

```python
LiveVoiceSource.stop(self) -> None
```

设置停止Event；parec仍在运行则terminate并等2s，超时kill再等2s；尝试放None哨兵（满队列忽略），每个线程join最多3s。不保证所有已排队音频识别完成，也不把对象恢复为可重启状态。

<a id="fn-livevoicesource--capture-loop"></a>

### `LiveVoiceSource._capture_loop`

源码位置：[integration/live_voice.py 第 233 行](../../../integration/live_voice.py#L233)。类型：`FunctionDef`。

```python
LiveVoiceSource._capture_loop(self) -> None
```

拼接stdout短读为固定PCM帧并送VAD；片段结束后用monotonic_ns减片段时长估算开始时间，音频队列put最多等0.1s，满则输出丢段错误。异常记结果；finally仅在非stop状态尝试flush剩余片段，满队列静默丢掉尾段。

<a id="fn-livevoicesource--recognition-loop"></a>

### `LiveVoiceSource._recognition_loop`

源码位置：[integration/live_voice.py 第 276 行](../../../integration/live_voice.py#L276)。类型：`FunctionDef`。

```python
LiveVoiceSource._recognition_loop(self) -> None
```

延迟导入audio_to_command，按0.2s队列轮询取段，None哨兵退出；s16le转float32/32768，传估算t_audio_start_ns。每段异常变LiveVoiceResult.error后继续；模块import在循环try之外，导入失败不走每段错误包装。

## 内部调用与异常路径

- `__post_init__` 调用：`ValueError`.
- `__init__` 调用：`LiveVoiceConfig`, `deque`, `int`, `max`, `queue.Queue`, `threading.Event`.
- `_rms` 调用：`float`, `np.frombuffer`, `np.frombuffer(frame, dtype='<i2').astype`, `np.mean`, `np.sqrt`.
- `_threshold` 调用：`float`, `max`, `np.asarray`, `np.median`.
- `feed` 调用：`ValueError`, `b''.join`, `len`, `list`, `self._frames.append`, `self._noise_rms.append`, `self._pre_roll.append`, `self._reset_after_utterance`, `self._rms`, `self._threshold`.
- `flush` 调用：`b''.join`, `self._reset_after_utterance`.
- `_reset_after_utterance` 调用：`self._pre_roll.clear`.
- `preload` 调用：`preload_voice_models`.
- `start` 调用：`RuntimeError`, `self._asr_thread.start`, `self._capture_thread.start`, `subprocess.Popen`, `threading.Thread`.
- `poll` 调用：`results.append`, `self._results.get_nowait`, `tuple`.
- `stop` 调用：`process.kill`, `process.poll`, `process.terminate`, `process.wait`, `self._segments.put_nowait`, `self._stop.set`, `thread.join`.
- `_capture_loop` 调用：`EnergyVadSegmenter`, `LiveVoiceResult`, `bytearray`, `bytes`, `int`, `len`, `pending.clear`, `pending.extend`, `process.poll`, `process.stdout.read`, `segmenter.feed`, `segmenter.flush`, `self._results.put`, `self._segments.put`, `self._segments.put_nowait`, `self._stop.is_set`, `time.monotonic_ns`, `type`.
- `_recognition_loop` 调用：`LiveVoiceResult`, `audio_to_command`, `dict`, `len`, `np.frombuffer`, `np.frombuffer(pcm, dtype='<i2').astype`, `self._results.put`, `self._segments.get`, `self._stop.is_set`, `type`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__post_init__`，第 35 行：`ValueError('microphone source must be non-empty')`。
- `__post_init__`，第 37 行：`ValueError('sample rate and frame size must be positive')`。
- `__post_init__`，第 39 行：`ValueError('frame_ms must divide one second')`。
- `__post_init__`，第 41 行：`ValueError('pre-roll must be non-negative and end silence positive')`。
- `__post_init__`，第 43 行：`ValueError('utterance durations must be positive')`。
- `__post_init__`，第 45 行：`ValueError('VAD thresholds must be positive')`。
- `__post_init__`，第 47 行：`ValueError('trigger_frames must be positive')`。
- `feed`，第 103 行：`ValueError(f'expected {self.config.bytes_per_frame} PCM bytes, got {len(frame)}')`。
- `start`，第 181 行：`RuntimeError('live microphone is already running')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [voice_group/pipeline.py](../../../voice_group/pipeline.py)

静态 import 消费者（含测试）：

- [integration/carla_runner.py](../../../integration/carla_runner.py)
- [integration/tests/test_live_voice.py](../../../integration/tests/test_live_voice.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-entry.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

<a id="fn-integration-live-voice-py"></a>

### `integration/live_voice.py`

来源 SHA256：`af3fe7fed596da3fb2ff3553955eb9510eb525b5ff5999fd88900b7f799f9688`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `LiveVoiceConfig.source` | `str` | `'@DEFAULT_SOURCE@'` |
| `LiveVoiceConfig.sample_rate` | `int` | `16000` |
| `LiveVoiceConfig.frame_ms` | `int` | `20` |
| `LiveVoiceConfig.pre_roll_ms` | `int` | `300` |
| `LiveVoiceConfig.end_silence_ms` | `int` | `700` |
| `LiveVoiceConfig.max_utterance_s` | `float` | `7.0` |
| `LiveVoiceConfig.min_voice_ms` | `int` | `160` |
| `LiveVoiceConfig.min_rms` | `float` | `0.003` |
| `LiveVoiceConfig.noise_ratio` | `float` | `3.0` |
| `LiveVoiceConfig.trigger_frames` | `int` | `3` |
| `LiveVoiceResult.command` | `dict[str, Any] &#124; None` | `无声明默认；构造/赋值方提供` |
| `LiveVoiceResult.duration_s` | `float` | `无声明默认；构造/赋值方提供` |
| `LiveVoiceResult.error` | `str &#124; None` | `None` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `LiveVoiceConfig.__post_init__` / 35 | `not self.source` | `raise ValueError('microphone source must be non-empty')` |
| `LiveVoiceConfig.__post_init__` / 37 | `self.sample_rate <= 0 or self.frame_ms <= 0` | `raise ValueError('sample rate and frame size must be positive')` |
| `LiveVoiceConfig.__post_init__` / 39 | `1000 % self.frame_ms` | `raise ValueError('frame_ms must divide one second')` |
| `LiveVoiceConfig.__post_init__` / 41 | `self.pre_roll_ms < 0 or self.end_silence_ms <= 0` | `raise ValueError('pre-roll must be non-negative and end silence positive')` |
| `LiveVoiceConfig.__post_init__` / 43 | `self.max_utterance_s <= 0.0 or self.min_voice_ms <= 0` | `raise ValueError('utterance durations must be positive')` |
| `LiveVoiceConfig.__post_init__` / 45 | `self.min_rms <= 0.0 or self.noise_ratio <= 1.0` | `raise ValueError('VAD thresholds must be positive')` |
| `LiveVoiceConfig.__post_init__` / 47 | `self.trigger_frames < 1` | `raise ValueError('trigger_frames must be positive')` |
| `EnergyVadSegmenter.feed` / 103 | `len(frame) != self.config.bytes_per_frame` | `raise ValueError(f'expected {self.config.bytes_per_frame} PCM bytes, got {len(frame)}')` |
| `LiveVoiceSource.start` / 181 | `self._capture_thread is not None` | `raise RuntimeError('live microphone is already running')` |
