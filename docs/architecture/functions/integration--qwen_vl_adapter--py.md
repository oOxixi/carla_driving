# qwen_vl_adapter：功能记录

上级模块：[模块说明](../modules/vehicle-planner.md) · 实现：[integration/qwen_vl_adapter.py](../../../integration/qwen_vl_adapter.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [异步等待、旧结果拒绝与多层命令ID](async-plan-dispatch.md)
- [计划可行性校验与内部步骤展开](plan-validation-compilation.md)

## 功能职责与范围

Production boundary between a local Qwen2.5-VL checkpoint and CARLA.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `QwenVLActionChoice.code: str`；默认：`未在声明处设置`。
- `QwenVLActionChoice.action: str`；默认：`未在声明处设置`。
- `QwenVLActionChoice.confidence: float`；默认：`未在声明处设置`。
- `QwenVLInferenceTrace.request_id: str`；默认：`未在声明处设置`。
- `QwenVLInferenceTrace.started_ns: int`；默认：`未在声明处设置`。
- `QwenVLInferenceTrace.completed_ns: int`；默认：`未在声明处设置`。
- `QwenVLInferenceTrace.image_path: str | None`；默认：`未在声明处设置`。
- `QwenVLInferenceTrace.raw_output: str`；默认：`未在声明处设置`。
- `QwenVLInferenceTrace.decision: Mapping[str, Any] | None`；默认：`未在声明处设置`。
- `QwenVLInferenceTrace.visual_preprocess: Mapping[str, Any] | None`；默认：`None`。
- `QwenVLInferenceTrace.target_grounding: Mapping[str, Any] | None`；默认：`None`。
- `QwenVLInferenceTrace.error: str | None`；默认：`None`。

## 功能入口：输入、输出与实现说明

<a id="fn-qwenvlgenerationbackend"></a>

### `QwenVLGenerationBackend`

源码位置：[integration/qwen_vl_adapter.py 第 23 行](../../../integration/qwen_vl_adapter.py#L23)。类型：`ClassDef`。

Minimal generation interface used by the strict adapter and tests.

<a id="fn-qwenvlgenerationbackend-generate"></a>

### `QwenVLGenerationBackend.generate`

源码位置：[integration/qwen_vl_adapter.py 第 26 行](../../../integration/qwen_vl_adapter.py#L26)。类型：`FunctionDef`。

```python
QwenVLGenerationBackend.generate(self, *, prompt: str, image_path: Path | None) -> str
```

Protocol 接口，无模型实现；约定 keyword-only prompt、image_path，返回模型文本。实现方的 I/O、耗时和异常由适配器包装，不能直接实例化此声明获得推理能力。

<a id="fn-qwenvlactionchoice"></a>

### `QwenVLActionChoice`

源码位置：[integration/qwen_vl_adapter.py 第 40 行](../../../integration/qwen_vl_adapter.py#L40)。类型：`ClassDef`。

One constrained model choice before deterministic Schema assembly.

<a id="fn-qwenvlactionchoice-from-code"></a>

### `QwenVLActionChoice.from_code`

源码位置：[integration/qwen_vl_adapter.py 第 48 行](../../../integration/qwen_vl_adapter.py#L48)。类型：`FunctionDef`。

```python
QwenVLActionChoice.from_code(cls, code: str, confidence: float) -> 'QwenVLActionChoice'
```

将 code 去空白并转大写，按 A–E 动作表查找，未知码抛 ValueError；confidence 交给 dataclass 检查，动作码不是自由文本动作名。

<a id="fn-qwenvlactionchoice---post-init--"></a>

### `QwenVLActionChoice.__post_init__`

源码位置：[integration/qwen_vl_adapter.py 第 56 行](../../../integration/qwen_vl_adapter.py#L56)。类型：`FunctionDef`。

```python
QwenVLActionChoice.__post_init__(self) -> None
```

校验动作码、有限 confidence∈[0,1] 以及动作码与 action 对应关系；不会检查目标存在性或场景安全，后续 assembly/boundary 负责这些步骤。

<a id="fn-qwenvlinferencetrace"></a>

### `QwenVLInferenceTrace`

源码位置：[integration/qwen_vl_adapter.py 第 78 行](../../../integration/qwen_vl_adapter.py#L78)。类型：`ClassDef`。

单次模型推理诊断快照，包含请求身份、开始/完成纳秒、image_path、原始输出、规范化决策、视觉元数据、grounding 与错误。仅记录最近一次，不是持久审计日志。

<a id="fn-qwenvlinferencetrace-latency-ms"></a>

### `QwenVLInferenceTrace.latency_ms`

源码位置：[integration/qwen_vl_adapter.py 第 90 行](../../../integration/qwen_vl_adapter.py#L90)。类型：`FunctionDef`。

```python
QwenVLInferenceTrace.latency_ms(self) -> float
```

(completed_ns-started_ns)/1e6，单位毫秒；不额外校验时间顺序，且不包含 StrictQwenVLAdapter 的路径解析和 prompt 构建前置工作。

<a id="fn-qwenvlinferencetrace-to-dict"></a>

### `QwenVLInferenceTrace.to_dict`

源码位置：[integration/qwen_vl_adapter.py 第 93 行](../../../integration/qwen_vl_adapter.py#L93)。类型：`FunctionDef`。

```python
QwenVLInferenceTrace.to_dict(self) -> dict[str, Any]
```

将 trace 导出字典并附 latency_ms，映射字段做顶层复制；不会写文件或保留多次历史。

<a id="fn-strictqwenvladapter"></a>

### `StrictQwenVLAdapter`

源码位置：[integration/qwen_vl_adapter.py 第 116 行](../../../integration/qwen_vl_adapter.py#L116)。类型：`ClassDef`。

Callable adapter suitable for ``AsyncQwenDecisionBridge``.

<a id="fn-strictqwenvladapter---init--"></a>

### `StrictQwenVLAdapter.__init__`

源码位置：[integration/qwen_vl_adapter.py 第 119 行](../../../integration/qwen_vl_adapter.py#L119)。类型：`FunctionDef`。

```python
StrictQwenVLAdapter.__init__(self, backend: QwenVLGenerationBackend, *, image_root: str | Path | None=None) -> None
```

backend 至少提供可调用 generate 或 generate_action；可选 image_root 展开并 resolve，建立 trace 锁，last_trace=None。构造适配器不自动加载模型，后端构造可能已加载。

<a id="fn-strictqwenvladapter-from-local-checkpoint"></a>

### `StrictQwenVLAdapter.from_local_checkpoint`

源码位置：[integration/qwen_vl_adapter.py 第 139 行](../../../integration/qwen_vl_adapter.py#L139)。类型：`FunctionDef`。

```python
StrictQwenVLAdapter.from_local_checkpoint(cls, model_path: str | Path, *, image_root: str | Path | None=None, max_new_tokens: int=48, device_map: str='auto', torch_dtype: str='auto', awq_backend: str='auto', min_pixels: int=64 * 28 * 28, max_pixels: int=64 * 28 * 28, crop_top_ratio: float=0.04, crop_bottom_ratio: float=0.08) -> 'StrictQwenVLAdapter'
```

Load a real local Qwen2.5-VL checkpoint without network fallback.

将max_new_tokens/device_map/torch_dtype/awq_backend/min_pixels/max_pixels/crop参数原样传给TransformersQwen25VLBackend，构造时立即本地加载模型，然后包装image_root。不是等待首次infer才加载，且无下载回退。

<a id="fn-strictqwenvladapter-last-trace"></a>

### `StrictQwenVLAdapter.last_trace`

源码位置：[integration/qwen_vl_adapter.py 第 168 行](../../../integration/qwen_vl_adapter.py#L168)。类型：`FunctionDef`。

```python
StrictQwenVLAdapter.last_trace(self) -> QwenVLInferenceTrace | None
```

锁内返回最近 trace 对象引用，没有运行记录时为 None；不是深复制，嵌套映射不可据此认为不可变。

<a id="fn-strictqwenvladapter-infer"></a>

### `StrictQwenVLAdapter.infer`

源码位置：[integration/qwen_vl_adapter.py 第 172 行](../../../integration/qwen_vl_adapter.py#L172)。类型：`FunctionDef`。

```python
StrictQwenVLAdapter.infer(self, context: QwenInputContext) -> dict[str, Any]
```

先解析 image_path/构造 prompt，再计时进入 try。优先 generate_action 分支组装离散动作，否则 generate 文本并校验；验证 target_track_id，执行确定性语义 grounding，finally 记录成功/失败 trace。路径和 prompt 的前置异常不会写新 trace。安全覆盖或显式语音速度补全应结合 trace 的 decision_source/grounding 区分于模型原始输出。

<a id="fn-strictqwenvladapter---call--"></a>

### `StrictQwenVLAdapter.__call__`

源码位置：[integration/qwen_vl_adapter.py 第 232 行](../../../integration/qwen_vl_adapter.py#L232)。类型：`FunctionDef`。

```python
StrictQwenVLAdapter.__call__(self, context: QwenInputContext) -> dict[str, Any]
```

直接委托 infer(context)，返回严格高层决策；不增加另一层线程、缓存或重试。

<a id="fn-strictqwenvladapter--resolve-image"></a>

### `StrictQwenVLAdapter._resolve_image`

源码位置：[integration/qwen_vl_adapter.py 第 235 行](../../../integration/qwen_vl_adapter.py#L235)。类型：`FunctionDef`。

```python
StrictQwenVLAdapter._resolve_image(self, rgb_ref: str | None) -> Path | None
```

rgb_ref=None 则无图；配置 image_root 时只允许根目录内的相对引用，禁止逃逸并要求文件存在。解析/文件缺失异常发生在本次 trace 计时前，不会被记录为模型推理错误。

<a id="fn-build-strict-qwen-prompt"></a>

### `build_strict_qwen_prompt`

源码位置：[integration/qwen_vl_adapter.py 第 254 行](../../../integration/qwen_vl_adapter.py#L254)。类型：`FunctionDef`。

```python
build_strict_qwen_prompt(context: QwenInputContext) -> str
```

Build a deterministic prompt whose output matches the frozen boundary.

将完整context.to_payload以allow_nan=False、sort_keys=True序列化进提示，要求5种高层动作及目标引用；提示约束不是实际执行校验，结果仍走validate_qwen_response。

<a id="fn--compact-choice-mapping"></a>

### `_compact_choice_mapping`

源码位置：[integration/qwen_vl_adapter.py 第 282 行](../../../integration/qwen_vl_adapter.py#L282)。类型：`FunctionDef`。

```python
_compact_choice_mapping(value: Mapping[str, Any], keys: tuple[str, ...]) -> dict[str, Any]
```

为离散动作 prompt 提取有限键的上下文子映射，只保留源映射中存在的键；不补默认字段，不等价于完整 PerceptionState 序列化。

<a id="fn-build-action-choice-prompt"></a>

### `build_action_choice_prompt`

源码位置：[integration/qwen_vl_adapter.py 第 289 行](../../../integration/qwen_vl_adapter.py#L289)。类型：`FunctionDef`。

```python
build_action_choice_prompt(context: QwenInputContext) -> str
```

Build the five-way prompt without dataset/provenance-only fields.

构造A=START/B=STOP/C=SLOW_DOWN/D=SET_SPEED/E=EMERGENCY_STOP的离散分类提示，只选场景/感知/安全中明列字段，不包含数据集provenance；后端返回动作码后由本地assembly补全速度和来源。

<a id="fn-assemble-action-choice"></a>

### `assemble_action_choice`

源码位置：[integration/qwen_vl_adapter.py 第 338 行](../../../integration/qwen_vl_adapter.py#L338)。类型：`FunctionDef`。

```python
assemble_action_choice(choice: QwenVLActionChoice, context: QwenInputContext, *, confidence_threshold: float=0.6) -> dict[str, Any]
```

Turn one model class into the existing strict high-level decision.

confidence_threshold默认0.60，范围[0,1]，与canonical0.8不同。顺序为确定性安全覆盖→模型低置信STOP待确认→visual_valid=False停车待确认→显式目标不唯一停车待确认→动作组装。C遇明确设置速度语法可改SET_SPEED并confidence至少0.90、来源VOICE_SPEED_GROUNDED；不覆盖模型STOP/EMERGENCY_STOP。D无法解析速度或>50m/s时STOP待确认。这里只组装，infer随后再边界校验和目标grounding。

<a id="fn--base-choice-decision"></a>

### `_base_choice_decision`

源码位置：[integration/qwen_vl_adapter.py 第 446 行](../../../integration/qwen_vl_adapter.py#L446)。类型：`FunctionDef`。

```python
_base_choice_decision(action: str, *, confidence: float, requires_confirmation: bool, source: str, visual_valid: object) -> dict[str, Any]
```

构造 action、float confidence、requires_confirmation、decision_source；visual_valid 仅在 exact bool 时带出。此辅助函数不独立校验置信度范围，也不生成目标速度/目标 ID。

<a id="fn--deterministic-safety-action"></a>

### `_deterministic_safety_action`

源码位置：[integration/qwen_vl_adapter.py 第 465 行](../../../integration/qwen_vl_adapter.py#L465)。类型：`FunctionDef`。

```python
_deterministic_safety_action(context: QwenInputContext) -> tuple[str, float] | None
```

根据碰撞/推荐紧急停车/TTC<=2 秒覆盖为 EMERGENCY_STOP（confidence=0.99）；红灯或 stop 推荐为 STOP（0.99），slow 推荐为 SLOW_DOWN（0.95）；无条件命中则 None。该覆盖来源于输入安全证据，不是额外模型推理。

<a id="fn--voice-target-speed-mps"></a>

### `_voice_target_speed_mps`

源码位置：[integration/qwen_vl_adapter.py 第 509 行](../../../integration/qwen_vl_adapter.py#L509)。类型：`FunctionDef`。

```python
_voice_target_speed_mps(command: str) -> float | None
```

从语音匹配数字+km/h/公里每小时或 m/s/每秒形式，以及支持的中文小于 100 数字；km/h 除以 3.6，结果统一 m/s。未匹配返回 None；这里只解析，不承担车辆最大速度约束。

<a id="fn--explicit-voice-set-speed-mps"></a>

### `_explicit_voice_set_speed_mps`

源码位置：[integration/qwen_vl_adapter.py 第 545 行](../../../integration/qwen_vl_adapter.py#L545)。类型：`FunctionDef`。

```python
_explicit_voice_set_speed_mps(command: str) -> float | None
```

Return a speed only for an unambiguous speed-setting instruction.

This deliberately excludes relative slow-down wording (for example,
"减速到每秒两米") because that remains an action C request rather than a
speed-set correction.  Safety and confidence checks live in
``assemble_action_choice`` and therefore always run before this helper.

<a id="fn--chinese-number-below-100"></a>

### `_chinese_number_below_100`

源码位置：[integration/qwen_vl_adapter.py 第 564 行](../../../integration/qwen_vl_adapter.py#L564)。类型：`FunctionDef`。

```python
_chinese_number_below_100(text: str) -> float
```

支持单字零至九（含〇/两）与十/二十/二十三形式，返回 float；长度/结构不支持时抛 ValueError，未知数字字形也可触发 KeyError，不处理百及以上。

<a id="fn--validate-target-reference"></a>

### `_validate_target_reference`

源码位置：[integration/qwen_vl_adapter.py 第 581 行](../../../integration/qwen_vl_adapter.py#L581)。类型：`FunctionDef`。

```python
_validate_target_reference(decision: Mapping[str, Any], context: QwenInputContext) -> None
```

响应无 target_track_id 时通过；有时要求该 ID 出现在 context.perception 的检测 track 集合，否则拒绝。它核对感知 track ID，不建立 scenario actor ID 到 track ID 的 alias。

<a id="fn--explicit-target-candidates"></a>

### `_explicit_target_candidates`

源码位置：[integration/qwen_vl_adapter.py 第 602 行](../../../integration/qwen_vl_adapter.py#L602)。类型：`FunctionDef`。

```python
_explicit_target_candidates(context: QwenInputContext) -> list[Mapping[str, Any]] | None
```

Resolve only high-confidence Chinese target descriptions.

只识别中文行人/车辆/前车及支持的关系描述；不适用返回None，适用但无候选返回空list。过滤数值confidence<0.5对象（缺失confidence不自动过滤）；距离约X米容差2m，最近/较近保留距最小值0.25m内对象，其余按left/right_adjacent、occluded、far_ahead、center_ahead关系匹配。它依赖perception.detected_objects，不建立scenario actor alias。

<a id="fn--ground-explicit-target"></a>

### `_ground_explicit_target`

源码位置：[integration/qwen_vl_adapter.py 第 688 行](../../../integration/qwen_vl_adapter.py#L688)。类型：`FunctionDef`。

```python
_ground_explicit_target(decision: Mapping[str, Any], context: QwenInputContext) -> tuple[dict[str, Any], dict[str, Any] | None]
```

Fuse Qwen action with a unique deterministic semantic target.

无适用描述时返回原决策副本和None；候选ID唯一时可直接补正target_track_id并记录MATCHED/CORRECTED_UNIQUE。无候选必须无target、动作STOP/EMERGENCY_STOP且requires_confirmation=True，否则抛错；多个候选必须无target且待确认，否则抛错。返回grounding证据含模型原target与候选列表，不等价于模型本身正确识别目标。

<a id="fn-transformersqwen25vlbackend"></a>

### `TransformersQwen25VLBackend`

源码位置：[integration/qwen_vl_adapter.py 第 741 行](../../../integration/qwen_vl_adapter.py#L741)。类型：`ClassDef`。

Lazy optional-dependency backend for a local Qwen2.5-VL checkpoint.

<a id="fn-transformersqwen25vlbackend---init--"></a>

### `TransformersQwen25VLBackend.__init__`

源码位置：[integration/qwen_vl_adapter.py 第 744 行](../../../integration/qwen_vl_adapter.py#L744)。类型：`FunctionDef`。

```python
TransformersQwen25VLBackend.__init__(self, model_path: str | Path, *, max_new_tokens: int=48, device_map: str='auto', torch_dtype: str='auto', awq_backend: str='auto', min_pixels: int=64 * 28 * 28, max_pixels: int=64 * 28 * 28, crop_top_ratio: float=0.04, crop_bottom_ratio: float=0.08) -> None
```

要求本地 checkpoint 目录存在，max_new_tokens 默认48且正整数；device_map/torch_dtype/awq_backend 默认 auto，像素下限/上限默认各50176（64×28²）；crop_top_ratio=.04、bottom=.08，各在[0,.5)且总和<.5。构造时导入依赖并以 local_files_only=True、trust_remote_code=True 加载 processor/config/model；AWQ 显式 backend 仅适用于 AWQ checkpoint，并兼容 visual/model.visual 跳过量化列表。

<a id="fn-transformersqwen25vlbackend-generate"></a>

### `TransformersQwen25VLBackend.generate`

源码位置：[integration/qwen_vl_adapter.py 第 843 行](../../../integration/qwen_vl_adapter.py#L843)。类型：`FunctionDef`。

```python
TransformersQwen25VLBackend.generate(self, *, prompt: str, image_path: Path | None) -> str
```

组装多模态消息、读取和裁剪道路 ROI、处理视觉信息并记录 visual metadata，输入移动到模型设备，在 inference_mode 中确定性 generate（不采样、启用 cache）。去掉输入 token 后 decode 首条输出并 strip，空输出报错；本类不提供工作线程取消或 wall timeout。

<a id="fn-crop-road-roi"></a>

### `crop_road_roi`

源码位置：[integration/qwen_vl_adapter.py 第 908 行](../../../integration/qwen_vl_adapter.py#L908)。类型：`FunctionDef`。

```python
crop_road_roi(image: Any, *, top_ratio: float=0.04, bottom_ratio: float=0.08) -> tuple[Any, dict[str, Any]]
```

Remove low-value sky/hood bands without changing horizontal geometry.

top_ratio=.04/bottom_ratio=.08，各有限范围[0,.5)且总和<.5；要求Pillow兼容size/crop、width>=1/height>=2。按round裁上下边、保持横向宽度，返回(cropped, metadata)，metadata含原尺寸、裁剪框、裁后尺寸和保留像素比例；空裁剪报错。

## 内部调用与异常路径

- `build_strict_qwen_prompt` 调用：`context.to_payload`, `json.dumps`.
- `build_action_choice_prompt` 调用：`_compact_choice_mapping`, `context.perception.get`, `dict`, `isinstance`, `json.dumps`.
- `assemble_action_choice` 调用：`TypeError`, `ValueError`, `_base_choice_decision`, `_deterministic_safety_action`, `_explicit_target_candidates`, `_explicit_voice_set_speed_mps`, `_voice_target_speed_mps`, `context.perception.get`, `context.safety_state.get`, `float`, `isinstance`, `item.get`, `len`, `max`, `str`, `str(context.safety_state.get('reason') or '').strip`, `str(context.safety_state.get('reason') or '').strip().lower`.
- `_base_choice_decision` 调用：`float`, `type`.
- `_deterministic_safety_action` 调用：`context.scene_state.get`, `float`, `isinstance`, `math.isfinite`, `perception.get`, `safety.get`, `str`, `str(perception.get('traffic_light', context.scene_state.get('traffic_light', ''))).strip`, `str(perception.get('traffic_light', context.scene_state.get('traffic_light', ''))).strip().upper`, `str(safety.get('recommended_action') or '').strip`, `str(safety.get('recommended_action') or '').strip().upper`, `type`.
- `_voice_target_speed_mps` 调用：`_CHINESE_SPEED_PREFIX_RE.search`, `_CHINESE_SPEED_SUFFIX_RE.search`, `_VOICE_SPEED_RE.search`, `_chinese_number_below_100`, `float`, `match.group`, `match.group('unit').lower`, `numeric_prefix.group`, `prefix.group`, `re.search`, `re.sub`, `suffix.group`.
- `_explicit_voice_set_speed_mps` 调用：`_SPEED_REDUCTION_INTENT_RE.search`, `_SPEED_SETTING_INTENT_RE.search`, `_voice_target_speed_mps`, `re.sub`.
- `_chinese_number_below_100` 调用：`ValueError`, `float`, `len`, `text.split`.
- `_validate_target_reference` 调用：`ValueError`, `context.perception.get`, `decision.get`, `isinstance`, `item.get`, `str`.
- `_explicit_target_candidates` 调用：`ValueError`, `abs`, `context.perception.get`, `distance_match.group`, `float`, `isinstance`, `item.get`, `len`, `math.isfinite`, `min`, `re.search`, `relation.startswith`, `relation_check`, `str`, `str(item.get('class', '')).lower`, `str(item.get('relation', '')).lower`, `type`.
- `_ground_explicit_target` 调用：`ValueError`, `_explicit_target_candidates`, `decision.get`, `dict`, `item.get`, `iter`, `len`, `next`, `sorted`, `str`.
- `crop_road_roi` 调用：`TypeError`, `ValueError`, `callable`, `float`, `getattr`, `hasattr`, `image.crop`, `int`, `isinstance`, `round`, `type`.
- `from_code` 调用：`ValueError`, `cls`, `str`, `str(code).strip`, `str(code).strip().upper`.
- `__post_init__` 调用：`ValueError`, `float`, `isinstance`, `math.isfinite`, `object.__setattr__`, `str`, `str(self.action).strip`, `str(self.action).strip().upper`, `str(self.code).strip`, `str(self.code).strip().upper`, `type`.
- `to_dict` 调用：`dict`.
- `__init__` 调用：`AutoConfig.from_pretrained`, `AutoProcessor.from_pretrained`, `FileNotFoundError`, `Lock`, `Path`, `Path(image_root).expanduser`, `Path(image_root).expanduser().resolve`, `Path(model_path).expanduser`, `Path(model_path).expanduser().resolve`, `Qwen2_5_VLForConditionalGeneration.from_pretrained`, `Qwen2_5_VLForConditionalGeneration.from_pretrained(str(checkpoint), torch_dtype=torch_dtype, device_map=device_map, trust_remote_code=True, local_files_only=True, **model_load_args).eval`, `RuntimeError`, `TypeError`, `ValueError`, `awq_config.get`, `callable`, `checkpoint.is_dir`, `dict`, `float`, `getattr`, `isinstance`, `list`, `quantization.get`, `skipped_modules.append`, `str`, `type`.
- `from_local_checkpoint` 调用：`TransformersQwen25VLBackend`, `cls`.
- `infer` 调用：`QwenVLInferenceTrace`, `TypeError`, `ValueError`, `_ground_explicit_target`, `_validate_target_reference`, `assemble_action_choice`, `build_action_choice_prompt`, `build_strict_qwen_prompt`, `callable`, `dict`, `generate_action`, `getattr`, `isinstance`, `raw.strip`, `repr`, `self._backend.generate`, `self._resolve_image`, `str`, `time.monotonic_ns`, `type`, `validate_qwen_response`.
- `__call__` 调用：`self.infer`.
- `_resolve_image` 调用：`(self._image_root / candidate).resolve`, `FileNotFoundError`, `Path`, `Path(rgb_ref).expanduser`, `ValueError`, `candidate.is_absolute`, `candidate.is_file`, `candidate.relative_to`, `candidate.resolve`.
- `generate` 调用：`RuntimeError`, `content.append`, `crop_road_roi`, `cropped_images.append`, `decoded[0].strip`, `inputs.to`, `len`, `metadata.append`, `next`, `self._model.generate`, `self._model.parameters`, `self._process_vision_info`, `self._processor`, `self._processor.apply_chat_template`, `self._processor.batch_decode`, `self._torch.inference_mode`, `str`, `zip`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__init__`，第 128 行：`TypeError('backend must provide generate(...) or generate_action(...)')`。
- `__init__`，第 759 行：`FileNotFoundError(f'Qwen checkpoint directory not found: {checkpoint}')`。
- `__init__`，第 761 行：`ValueError('max_new_tokens must be a positive integer')`。
- `__init__`，第 763 行：`ValueError('min_pixels must be an integer of at least 784')`。
- `__init__`，第 765 行：`ValueError('max_pixels must be an integer >= min_pixels')`。
- `__init__`，第 767 行：`ValueError('awq_backend must be auto/torch_awq/gemm/gemm_triton')`。
- `__init__`，第 779 行：`ValueError(f'{name} must be in [0, 0.5)')`。
- `__init__`，第 781 行：`ValueError('combined vertical crop must retain at least half the image')`。
- `__init__`，第 791 行：`RuntimeError('Qwen runtime requires torch, transformers, pillow and qwen-vl-utils')`。
- `__init__`，第 832 行：`ValueError('awq_backend override requires an AWQ checkpoint')`。
- `__post_init__`，第 60 行：`ValueError(f'unsupported Qwen action code: {code!r}')`。
- `__post_init__`，第 62 行：`ValueError(f'Qwen action code {code} must map to {_ACTION_BY_CODE[code]}')`。
- `__post_init__`，第 71 行：`ValueError('Qwen action confidence must be finite and in [0, 1]')`。
- `_chinese_number_below_100`，第 571 行：`ValueError(f'unsupported Chinese speed number: {text!r}')`。
- `_chinese_number_below_100`，第 575 行：`ValueError(f'unsupported Chinese speed number: {text!r}')`。
- `_explicit_target_candidates`，第 642 行：`ValueError('perception.detected_objects must be a list')`。
- `_ground_explicit_target`，第 708 行：`ValueError('explicit voice target is absent; decision must fail closed with STOP and requires_confirmation=true')`。
- `_ground_explicit_target`，第 730 行：`ValueError('explicit voice target is ambiguous; target must be omitted and requires_confirmation=true')`。
- `_resolve_image`，第 241 行：`ValueError('rgb_ref must be relative when image_root is configured')`。
- `_resolve_image`，第 246 行：`ValueError('rgb_ref escapes image_root')`。
- `_resolve_image`，第 250 行：`FileNotFoundError(f'Qwen RGB input not found: {candidate}')`。
- `_validate_target_reference`，第 590 行：`ValueError('perception.detected_objects must be a list')`。
- `_validate_target_reference`，第 597 行：`ValueError(f'Qwen target_track_id is not present in perception: {target!r}')`。
- `assemble_action_choice`，第 346 行：`TypeError('choice must be QwenVLActionChoice')`。
- `assemble_action_choice`，第 348 行：`TypeError('context must be QwenInputContext')`。
- `assemble_action_choice`，第 350 行：`ValueError('confidence_threshold must be in [0, 1]')`。
- `crop_road_roi`，第 924 行：`ValueError(f'{name} must be in [0, 0.5)')`。
- `crop_road_roi`，第 926 行：`ValueError('combined vertical crop must retain at least half the image')`。
- `crop_road_roi`，第 928 行：`TypeError('image must provide Pillow-compatible size and crop')`。
- `crop_road_roi`，第 931 行：`ValueError('image dimensions must be positive integers')`。
- `crop_road_roi`，第 935 行：`ValueError('crop ratios produced an empty image')`。
- `from_code`，第 53 行：`ValueError(f'unsupported Qwen action code: {normalized!r}')`。
- `generate`，第 904 行：`RuntimeError('Qwen returned no decoded output')`。
- `infer`，第 174 行：`TypeError('context must be QwenInputContext')`。
- `infer`，第 195 行：`TypeError('Qwen action backend must return QwenVLActionChoice')`。
- `infer`，第 205 行：`ValueError('Qwen backend returned an empty non-text response')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [integration/qwen_boundary.py](../../../integration/qwen_boundary.py)

静态 import 消费者（含测试）：

- [integration/__init__.py](../../../integration/__init__.py)
- [integration/carla_runner.py](../../../integration/carla_runner.py)
- [integration/qwen_remote_backend.py](../../../integration/qwen_remote_backend.py)
- [integration/tests/test_four_modal_full_chain_remote.py](../../../integration/tests/test_four_modal_full_chain_remote.py)
- [integration/tests/test_qwen_vl_adapter.py](../../../integration/tests/test_qwen_vl_adapter.py)
- [qwen_service/service.py](../../../qwen_service/service.py)
- [tools/qwen_remote_smoke.py](../../../tools/qwen_remote_smoke.py)
- [tools/run_four_modal_full_chain.py](../../../tools/run_four_modal_full_chain.py)
- [tools/run_long_stability.py](../../../tools/run_long_stability.py)
- [tools/run_qwen_batch_benchmark.py](../../../tools/run_qwen_batch_benchmark.py)
- [tools/run_qwen_carla_closed_loop.py](../../../tools/run_qwen_carla_closed_loop.py)
- [tools/run_qwen_latency_gate.py](../../../tools/run_qwen_latency_gate.py)
- [tools/run_qwen_vl_decision.py](../../../tools/run_qwen_vl_decision.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-planner.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

<a id="fn-integration-qwen-vl-adapter-py"></a>

### `integration/qwen_vl_adapter.py`

来源 SHA256：`57d03e867248896005caca3fd1bb55276c0a7e36b1944a93a8c27d0283180f22`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `QwenVLActionChoice.code` | `str` | `无声明默认；构造/赋值方提供` |
| `QwenVLActionChoice.action` | `str` | `无声明默认；构造/赋值方提供` |
| `QwenVLActionChoice.confidence` | `float` | `无声明默认；构造/赋值方提供` |
| `QwenVLInferenceTrace.request_id` | `str` | `无声明默认；构造/赋值方提供` |
| `QwenVLInferenceTrace.started_ns` | `int` | `无声明默认；构造/赋值方提供` |
| `QwenVLInferenceTrace.completed_ns` | `int` | `无声明默认；构造/赋值方提供` |
| `QwenVLInferenceTrace.image_path` | `str &#124; None` | `无声明默认；构造/赋值方提供` |
| `QwenVLInferenceTrace.raw_output` | `str` | `无声明默认；构造/赋值方提供` |
| `QwenVLInferenceTrace.decision` | `Mapping[str, Any] &#124; None` | `无声明默认；构造/赋值方提供` |
| `QwenVLInferenceTrace.visual_preprocess` | `Mapping[str, Any] &#124; None` | `None` |
| `QwenVLInferenceTrace.target_grounding` | `Mapping[str, Any] &#124; None` | `None` |
| `QwenVLInferenceTrace.error` | `str &#124; None` | `None` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `QwenVLActionChoice.from_code` / 53 | `except KeyError` | `raise ValueError(f'unsupported Qwen action code: {normalized!r}') from error` |
| `QwenVLActionChoice.__post_init__` / 60 | `code not in _ACTION_BY_CODE` | `raise ValueError(f'unsupported Qwen action code: {code!r}')` |
| `QwenVLActionChoice.__post_init__` / 62 | `action != _ACTION_BY_CODE[code]` | `raise ValueError(f'Qwen action code {code} must map to {_ACTION_BY_CODE[code]}')` |
| `QwenVLActionChoice.__post_init__` / 71 | `type(self.confidence) not in (int, float) or isinstance(self.confidence, bool) or (not math.isfinite(float(self.confidence))) or (not 0.0 <= float(self.confidence) <= 1.0)` | `raise ValueError('Qwen action confidence must be finite and in [0, 1]')` |
| `StrictQwenVLAdapter.__init__` / 128 | `not callable(getattr(backend, 'generate', None)) and (not callable(getattr(backend, 'generate_action', None)))` | `raise TypeError('backend must provide generate(...) or generate_action(...)')` |
| `StrictQwenVLAdapter.infer` / 174 | `not isinstance(context, QwenInputContext)` | `raise TypeError('context must be QwenInputContext')` |
| `StrictQwenVLAdapter.infer` / 195 | `callable(generate_action) AND not isinstance(choice, QwenVLActionChoice)` | `raise TypeError('Qwen action backend must return QwenVLActionChoice')` |
| `StrictQwenVLAdapter.infer` / 205 | `NOT (callable(generate_action)) AND type(raw) is not str or not raw.strip()` | `raise ValueError('Qwen backend returned an empty non-text response')` |
| `StrictQwenVLAdapter.infer` / 214 | `except Exception` | `raise` |
| `StrictQwenVLAdapter._resolve_image` / 241 | `self._image_root is not None AND candidate.is_absolute()` | `raise ValueError('rgb_ref must be relative when image_root is configured')` |
| `StrictQwenVLAdapter._resolve_image` / 246 | `self._image_root is not None AND except ValueError` | `raise ValueError('rgb_ref escapes image_root') from error` |
| `StrictQwenVLAdapter._resolve_image` / 250 | `not candidate.is_file()` | `raise FileNotFoundError(f'Qwen RGB input not found: {candidate}')` |
| `assemble_action_choice` / 346 | `not isinstance(choice, QwenVLActionChoice)` | `raise TypeError('choice must be QwenVLActionChoice')` |
| `assemble_action_choice` / 348 | `not isinstance(context, QwenInputContext)` | `raise TypeError('context must be QwenInputContext')` |
| `assemble_action_choice` / 350 | `not 0.0 <= float(confidence_threshold) <= 1.0` | `raise ValueError('confidence_threshold must be in [0, 1]')` |
| `_chinese_number_below_100` / 571 | `'十' not in text AND len(text) != 1 or text not in digits` | `raise ValueError(f'unsupported Chinese speed number: {text!r}')` |
| `_chinese_number_below_100` / 575 | `len(tens) > 1 or len(ones) > 1` | `raise ValueError(f'unsupported Chinese speed number: {text!r}')` |
| `_validate_target_reference` / 590 | `not isinstance(objects, list)` | `raise ValueError('perception.detected_objects must be a list')` |
| `_validate_target_reference` / 597 | `target not in available` | `raise ValueError(f'Qwen target_track_id is not present in perception: {target!r}')` |
| `_explicit_target_candidates` / 642 | `not isinstance(objects, list)` | `raise ValueError('perception.detected_objects must be a list')` |
| `_ground_explicit_target` / 708 | `not candidate_ids AND target is not None or decision['action'] not in {'STOP', 'EMERGENCY_STOP'} or (not decision['requires_confirmation'])` | `raise ValueError('explicit voice target is absent; decision must fail closed with STOP and requires_confirmation=true')` |
| `_ground_explicit_target` / 730 | `target is not None or not decision['requires_confirmation']` | `raise ValueError('explicit voice target is ambiguous; target must be omitted and requires_confirmation=true')` |
| `TransformersQwen25VLBackend.__init__` / 759 | `not checkpoint.is_dir()` | `raise FileNotFoundError(f'Qwen checkpoint directory not found: {checkpoint}')` |
| `TransformersQwen25VLBackend.__init__` / 761 | `type(max_new_tokens) is not int or max_new_tokens < 1` | `raise ValueError('max_new_tokens must be a positive integer')` |
| `TransformersQwen25VLBackend.__init__` / 763 | `type(min_pixels) is not int or min_pixels < 28 * 28` | `raise ValueError('min_pixels must be an integer of at least 784')` |
| `TransformersQwen25VLBackend.__init__` / 765 | `type(max_pixels) is not int or max_pixels < min_pixels` | `raise ValueError('max_pixels must be an integer >= min_pixels')` |
| `TransformersQwen25VLBackend.__init__` / 767 | `awq_backend not in {'auto', 'torch_awq', 'gemm', 'gemm_triton'}` | `raise ValueError('awq_backend must be auto/torch_awq/gemm/gemm_triton')` |
| `TransformersQwen25VLBackend.__init__` / 779 | `type(value) not in (int, float) or isinstance(value, bool) or (not 0.0 <= float(value) < 0.5)` | `raise ValueError(f'{name} must be in [0, 0.5)')` |
| `TransformersQwen25VLBackend.__init__` / 781 | `float(crop_top_ratio) + float(crop_bottom_ratio) >= 0.5` | `raise ValueError('combined vertical crop must retain at least half the image')` |
| `TransformersQwen25VLBackend.__init__` / 791 | `except ImportError` | `raise RuntimeError('Qwen runtime requires torch, transformers, pillow and qwen-vl-utils') from error` |
| `TransformersQwen25VLBackend.__init__` / 832 | `NOT (isinstance(quantization, Mapping) and quantization.get('quant_method') == 'awq') AND awq_backend != 'auto'` | `raise ValueError('awq_backend override requires an AWQ checkpoint')` |
| `TransformersQwen25VLBackend.generate` / 904 | `not decoded` | `raise RuntimeError('Qwen returned no decoded output')` |
| `crop_road_roi` / 924 | `type(value) not in (int, float) or isinstance(value, bool) or (not 0.0 <= float(value) < 0.5)` | `raise ValueError(f'{name} must be in [0, 0.5)')` |
| `crop_road_roi` / 926 | `float(top_ratio) + float(bottom_ratio) >= 0.5` | `raise ValueError('combined vertical crop must retain at least half the image')` |
| `crop_road_roi` / 928 | `not hasattr(image, 'size') or not callable(getattr(image, 'crop', None))` | `raise TypeError('image must provide Pillow-compatible size and crop')` |
| `crop_road_roi` / 931 | `type(width) is not int or type(height) is not int or width < 1 or (height < 2)` | `raise ValueError('image dimensions must be positive integers')` |
| `crop_road_roi` / 935 | `bottom <= top` | `raise ValueError('crop ratios produced an empty image')` |
