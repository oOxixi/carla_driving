# qwen_remote_backend：功能记录

上级模块：[模块说明](../modules/vehicle-planner.md) · 实现：[integration/qwen_remote_backend.py](../../../integration/qwen_remote_backend.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [异步等待、旧结果拒绝与多层命令ID](async-plan-dispatch.md)
- [计划可行性校验与内部步骤展开](plan-validation-compilation.md)

## 功能职责与范围

qwen_remote_backend

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

<a id="fn-openaicompatibleqwenvlbackend"></a>

### `OpenAICompatibleQwenVLBackend`

源码位置：[integration/qwen_remote_backend.py 第 18 行](../../../integration/qwen_remote_backend.py#L18)。类型：`ClassDef`。

Ask a vLLM-compatible Qwen3-VL endpoint for one action code.

Final Schema assembly, target grounding and safety overrides stay in the
repository-owned strict adapter rather than autoregressive model output.

<a id="fn-openaicompatibleqwenvlbackend---init--"></a>

### `OpenAICompatibleQwenVLBackend.__init__`

源码位置：[integration/qwen_remote_backend.py 第 25 行](../../../integration/qwen_remote_backend.py#L25)。类型：`FunctionDef`。

```python
OpenAICompatibleQwenVLBackend.__init__(self, *, base_url: str, profile: QwenModelProfile | None=None, api_key: str='local-offline', timeout_s: float=30.0, max_tokens: int=1, model: str | None=None, image_max_side: int | None=None, jpeg_quality: int=75, client: Any | None=None) -> None
```

解析 model/profile 并要求模型 ID 与 profile 一致；image_max_side 也须符合 profile，JPEG quality 限 1–95。默认 HTTP timeout_s=30、max_tokens=1；可注入 client，否则构建 OpenAI client（max_retries=0）。构造不代表服务健康检查通过。

<a id="fn-openaicompatibleqwenvlbackend-generate-action"></a>

### `OpenAICompatibleQwenVLBackend.generate_action`

源码位置：[integration/qwen_remote_backend.py 第 81 行](../../../integration/qwen_remote_backend.py#L81)。类型：`FunctionDef`。

```python
OpenAICompatibleQwenVLBackend.generate_action(self, *, prompt: str, image_path: Path | None, context: QwenInputContext) -> QwenVLActionChoice
```

prompt 必须非空，context 必须为 QwenInputContext；可选图像转换为 data URL，与文字发给 chat.completions。temperature=0，要求 A–E 单 token、logprobs 和 top_logprobs；响应为空/非法动作/无有效 logprob 均报错。返回带概率置信度的 QwenVLActionChoice，不返回 ManeuverPlan。

<a id="fn-openaicompatibleqwenvlbackend--image-to-data-url"></a>

### `OpenAICompatibleQwenVLBackend._image_to_data_url`

源码位置：[integration/qwen_remote_backend.py 第 153 行](../../../integration/qwen_remote_backend.py#L153)。类型：`FunctionDef`。

```python
OpenAICompatibleQwenVLBackend._image_to_data_url(self, image_path: Path, context: QwenInputContext) -> str
```

打开输入图像并转换 RGB，按 context 中目标框生成 overview+focus 拼图，编码 JPEG 后返回 base64 data URL；读取/解码错误向上传播，不将原路径发送给远端读取。

<a id="fn-openaicompatibleqwenvlbackend-close"></a>

### `OpenAICompatibleQwenVLBackend.close`

源码位置：[integration/qwen_remote_backend.py 第 195 行](../../../integration/qwen_remote_backend.py#L195)。类型：`FunctionDef`。

```python
OpenAICompatibleQwenVLBackend.close(self) -> None
```

若注入或自建 client 有可调用 close 则调用；不额外管理远端服务生命周期。

<a id="fn--first-token-confidence"></a>

### `_first_token_confidence`

源码位置：[integration/qwen_remote_backend.py 第 201 行](../../../integration/qwen_remote_backend.py#L201)。类型：`FunctionDef`。

```python
_first_token_confidence(choice: object, expected_code: str) -> float
```

从首个生成 token 的 logprob 计算 exp(logprob)，优先与归一化动作码匹配，否则使用首 token。缺失/非数值/NaN 报错，负无穷得到 0；结果限制到 [0,1]。它是动作 token 概率，不等于场景识别准确率。

<a id="fn--scene-focus-montage"></a>

### `_scene_focus_montage`

源码位置：[integration/qwen_remote_backend.py 第 228 行](../../../integration/qwen_remote_backend.py#L228)。类型：`FunctionDef`。

```python
_scene_focus_montage(image: Any, detected_objects: object, *, size: int, image_ops: Any) -> Any
```

上部约 56.25% 高度放完整场景缩略图，下部放最多两个目标局部裁剪；无有效目标时使用道路区域作为 fallback。输出方形 RGB 拼图，改变此布局需同步 prompt/profile 和视觉回归。

<a id="fn--focus-regions"></a>

### `_focus_regions`

源码位置：[integration/qwen_remote_backend.py 第 273 行](../../../integration/qwen_remote_backend.py#L273)。类型：`FunctionDef`。

```python
_focus_regions(image: Any, detected_objects: object) -> list[Any]
```

从检测对象中选合法归一化 bbox，按距离排序取最多两个并加约 12% 边缘；无框返回空列表，由_scene_focus_montage裁剪下方道路区域。不是对所有 track 的完整视觉输入保证。

<a id="fn--valid-focus-count"></a>

### `_valid_focus_count`

源码位置：[integration/qwen_remote_backend.py 第 316 行](../../../integration/qwen_remote_backend.py#L316)。类型：`FunctionDef`。

```python
_valid_focus_count(detected_objects: object) -> int
```

统计合法 bbox 数并上限截为 2，供拼图布局选择；不检查目标 ID 是否满足执行 grounding 合约。

<a id="fn--normalized-box"></a>

### `_normalized_box`

源码位置：[integration/qwen_remote_backend.py 第 330 行](../../../integration/qwen_remote_backend.py#L330)。类型：`FunctionDef`。

```python
_normalized_box(value: object) -> tuple[float, float, float, float] | None
```

接受四个有限数值（拒绝 bool），要求 0<=x1<x2<=1、0<=y1<y2<=1；不合法返回 None，合法返回 float tuple，不修复反向/越界框。

## 内部调用与异常路径

- `_first_token_confidence` 调用：`RuntimeError`, `float`, `getattr`, `isinstance`, `math.exp`, `math.isfinite`, `math.isnan`, `max`, `min`, `next`, `str`, `str(getattr(entry, 'token', '')).strip`, `str(getattr(entry, 'token', '')).strip().upper`, `type`.
- `_scene_focus_montage` 调用：`Image.new`, `_focus_regions`, `canvas.paste`, `enumerate`, `image.crop`, `image_ops.contain`, `image_ops.fit`, `len`, `round`.
- `_focus_regions` 调用：`_normalized_box`, `float`, `image.crop`, `isinstance`, `item.get`, `math.ceil`, `math.floor`, `math.isfinite`, `max`, `min`, `ranked.append`, `ranked.sort`, `regions.append`, `type`.
- `_valid_focus_count` 调用：`_normalized_box`, `isinstance`, `item.get`, `min`, `sum`.
- `_normalized_box` 调用：`any`, `float`, `isinstance`, `len`, `math.isfinite`, `type`.
- `__init__` 调用：`OpenAI`, `RuntimeError`, `ValueError`, `base_url.rstrip`, `base_url.strip`, `get_qwen_profile_by_model`, `resolve_qwen_profile`.
- `generate_action` 调用：`QwenVLActionChoice.from_code`, `RuntimeError`, `TypeError`, `ValueError`, `_first_token_confidence`, `content.append`, `getattr`, `isinstance`, `prompt.strip`, `self._client.chat.completions.create`, `self._image_to_data_url`, `text.strip`, `text.strip().upper`.
- `_image_to_data_url` 调用：`FileNotFoundError`, `Image.open`, `Path`, `Path(image_path).expanduser`, `Path(image_path).expanduser().resolve`, `RuntimeError`, `_scene_focus_montage`, `_valid_focus_count`, `base64.b64encode`, `base64.b64encode(buffer.getvalue()).decode`, `buffer.getvalue`, `context.perception.get`, `image.convert`, `image.save`, `io.BytesIO`, `path.is_file`.
- `close` 调用：`callable`, `close`, `getattr`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__init__`，第 39 行：`ValueError('base_url must not be empty')`。
- `__init__`，第 41 行：`ValueError('timeout_s must be positive')`。
- `__init__`，第 43 行：`ValueError('max_tokens must be 1 for constrained action choice')`。
- `__init__`，第 45 行：`ValueError('jpeg_quality must be in [1, 95]')`。
- `__init__`，第 53 行：`ValueError('model must match the selected Qwen profile')`。
- `__init__`，第 55 行：`ValueError('image_max_side must match the selected Qwen profile')`。
- `__init__`，第 61 行：`RuntimeError('remote Qwen requires the optional openai client; install requirements-qwen-client.txt')`。
- `_first_token_confidence`，第 205 行：`RuntimeError('Qwen server returned no token logprobs')`。
- `_first_token_confidence`，第 220 行：`RuntimeError('Qwen server returned an invalid token logprob')`。
- `_first_token_confidence`，第 224 行：`RuntimeError('Qwen server returned an invalid token logprob')`。
- `_image_to_data_url`，第 161 行：`RuntimeError('remote Qwen image encoding requires Pillow')`。
- `_image_to_data_url`，第 166 行：`FileNotFoundError(f'Qwen image not found: {path}')`。
- `generate_action`，第 89 行：`ValueError('prompt must be a non-empty string')`。
- `generate_action`，第 91 行：`TypeError('context must be QwenInputContext')`。
- `generate_action`，第 140 行：`RuntimeError('Qwen server returned no completion choices')`。
- `generate_action`，第 144 行：`RuntimeError('Qwen server returned an empty response')`。
- `generate_action`，第 151 行：`RuntimeError(f'Qwen server returned invalid action code: {code!r}')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [integration/qwen_boundary.py](../../../integration/qwen_boundary.py)
- [integration/qwen_profiles.py](../../../integration/qwen_profiles.py)
- [integration/qwen_vl_adapter.py](../../../integration/qwen_vl_adapter.py)

静态 import 消费者（含测试）：

- [integration/carla_runner.py](../../../integration/carla_runner.py)
- [integration/tests/test_qwen_remote_backend.py](../../../integration/tests/test_qwen_remote_backend.py)
- [tools/qwen_remote_smoke.py](../../../tools/qwen_remote_smoke.py)
- [tools/run_four_modal_full_chain.py](../../../tools/run_four_modal_full_chain.py)
- [tools/run_long_stability.py](../../../tools/run_long_stability.py)
- [tools/run_qwen_latency_gate.py](../../../tools/run_qwen_latency_gate.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-planner.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

<a id="fn-integration-qwen-remote-backend-py"></a>

### `integration/qwen_remote_backend.py`

来源 SHA256：`ae267dcbe507f8fddbd3aa4765c533c0a74765759d0ec0e240425dc55126faba`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `OpenAICompatibleQwenVLBackend.__init__` / 39 | `not base_url.strip()` | `raise ValueError('base_url must not be empty')` |
| `OpenAICompatibleQwenVLBackend.__init__` / 41 | `timeout_s <= 0` | `raise ValueError('timeout_s must be positive')` |
| `OpenAICompatibleQwenVLBackend.__init__` / 43 | `max_tokens != 1` | `raise ValueError('max_tokens must be 1 for constrained action choice')` |
| `OpenAICompatibleQwenVLBackend.__init__` / 45 | `not 1 <= jpeg_quality <= 95` | `raise ValueError('jpeg_quality must be in [1, 95]')` |
| `OpenAICompatibleQwenVLBackend.__init__` / 53 | `model is not None and model != self.profile.model` | `raise ValueError('model must match the selected Qwen profile')` |
| `OpenAICompatibleQwenVLBackend.__init__` / 55 | `image_max_side is not None and image_max_side != self.profile.image_max_side` | `raise ValueError('image_max_side must match the selected Qwen profile')` |
| `OpenAICompatibleQwenVLBackend.__init__` / 61 | `client is None AND except ImportError` | `raise RuntimeError('remote Qwen requires the optional openai client; install requirements-qwen-client.txt') from error` |
| `OpenAICompatibleQwenVLBackend.generate_action` / 89 | `not isinstance(prompt, str) or not prompt.strip()` | `raise ValueError('prompt must be a non-empty string')` |
| `OpenAICompatibleQwenVLBackend.generate_action` / 91 | `not isinstance(context, QwenInputContext)` | `raise TypeError('context must be QwenInputContext')` |
| `OpenAICompatibleQwenVLBackend.generate_action` / 140 | `not choices` | `raise RuntimeError('Qwen server returned no completion choices')` |
| `OpenAICompatibleQwenVLBackend.generate_action` / 144 | `not isinstance(text, str) or not text.strip()` | `raise RuntimeError('Qwen server returned an empty response')` |
| `OpenAICompatibleQwenVLBackend.generate_action` / 151 | `except ValueError` | `raise RuntimeError(f'Qwen server returned invalid action code: {code!r}') from error` |
| `OpenAICompatibleQwenVLBackend._image_to_data_url` / 161 | `except ImportError` | `raise RuntimeError('remote Qwen image encoding requires Pillow') from error` |
| `OpenAICompatibleQwenVLBackend._image_to_data_url` / 166 | `not path.is_file()` | `raise FileNotFoundError(f'Qwen image not found: {path}')` |
| `_first_token_confidence` / 205 | `not entries` | `raise RuntimeError('Qwen server returned no token logprobs')` |
| `_first_token_confidence` / 220 | `type(value) not in (int, float) or isinstance(value, bool) or math.isnan(float(value))` | `raise RuntimeError('Qwen server returned an invalid token logprob')` |
| `_first_token_confidence` / 224 | `not math.isfinite(float(value))` | `raise RuntimeError('Qwen server returned an invalid token logprob')` |
