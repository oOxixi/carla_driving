# rgb_pipeline：功能记录

上级模块：[模块说明](../modules/vehicle-perception.md) · 实现：[perception/rgb_pipeline.py](../../../perception/rgb_pipeline.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [同帧感知、目标身份与来源](perception-authority.md)

## 功能职责与范围

Road ROI, low-rate detection, high-rate stable tracking and Top-K output.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `RGBPipelineConfig.roi_top_ratio: float`；默认：`0.2`。
- `RGBPipelineConfig.roi_bottom_ratio: float`；默认：`1.0`。
- `RGBPipelineConfig.input_width: int`；默认：`640`。
- `RGBPipelineConfig.input_height: int`；默认：`384`。
- `RGBPipelineConfig.detection_interval_frames: int`；默认：`3`。
- `RGBPipelineConfig.top_k: int`；默认：`12`。
- `RGBPipelineConfig.iou_match_threshold: float`；默认：`0.25`。
- `RGBPipelineConfig.max_track_age_frames: int`；默认：`6`。
- `RGBDetection.class_name: str`；默认：`未在声明处设置`。
- `RGBDetection.confidence: float`；默认：`未在声明处设置`。
- `RGBDetection.bbox_xyxy_norm: tuple[float, float, float, float]`；默认：`未在声明处设置`。
- `RGBTrack.track_id: str`；默认：`未在声明处设置`。
- `RGBTrack.class_name: str`；默认：`未在声明处设置`。
- `RGBTrack.confidence: float`；默认：`未在声明处设置`。
- `RGBTrack.bbox_xyxy_norm: tuple[float, float, float, float]`；默认：`未在声明处设置`。
- `RGBTrack.first_frame_id: int`；默认：`未在声明处设置`。
- `RGBTrack.last_frame_id: int`；默认：`未在声明处设置`。
- `RGBTrack.age_frames: int`；默认：`未在声明处设置`。
- `RGBTrack.detected_this_frame: bool`；默认：`未在声明处设置`。

## 功能入口：输入、输出与实现说明

### `RGBPipelineConfig`

源码位置：[perception/rgb_pipeline.py 第 15 行](../../../perception/rgb_pipeline.py#L15)。类型：`ClassDef`。

定义道路 ROI、网络输入尺寸、低频检测间隔、Top-K、IoU 匹配和 track 保留帧数。这里的 track 是纯图像框追踪，没有距离和三维速度。

### `RGBPipelineConfig.__post_init__`

源码位置：[perception/rgb_pipeline.py 第 25 行](../../../perception/rgb_pipeline.py#L25)。类型：`FunctionDef`。

```python
RGBPipelineConfig.__post_init__(self) -> None
```

要求 `0 <= roi_top < roi_bottom <= 1`；输入尺寸、检测间隔、Top-K和寿命为正整数，IoU阈值在 `[0,1]`。不检查网络尺寸是否满足某个具体模型步长。

### `RGBDetection`

源码位置：[perception/rgb_pipeline.py 第 36 行](../../../perception/rgb_pipeline.py#L36)。类型：`ClassDef`。

检测器回调的二维结果，框坐标是输入 ROI 内归一化 xyxy；`_normalize` 再映射到整图坐标。类别字符串不受固定词表限制。

### `RGBDetection.__post_init__`

源码位置：[perception/rgb_pipeline.py 第 41 行](../../../perception/rgb_pipeline.py#L41)。类型：`FunctionDef`。

```python
RGBDetection.__post_init__(self) -> None
```

类别必须非空，置信度为 `[0,1]` 有限数；框必须是长度4 tuple，各值有限且在 `[0,1]`、宽高为正。成功后置信度和框统一转 float。

### `RGBTrack`

源码位置：[perception/rgb_pipeline.py 第 58 行](../../../perception/rgb_pipeline.py#L58)。类型：`ClassDef`。

不可变图像 track 快照，记录稳定 `rgb-xxxxxx` ID、框、首次/最后检测帧、累计年龄以及本帧是否真正检测到。传播帧的 `last_frame_id` 保持最后检测帧。

### `_iou`

源码位置：[perception/rgb_pipeline.py 第 69 行](../../../perception/rgb_pipeline.py#L69)。类型：`FunctionDef`。

```python
_iou(first: tuple[float, ...], second: tuple[float, ...]) -> float
```

计算两个归一化 xyxy 框的交并比，交集负边长截0，分母下限 `1e-12`。调用者依赖 `RGBDetection` 已保证正面积。

### `RGBPipeline`

源码位置：[perception/rgb_pipeline.py 第 78 行](../../../perception/rgb_pipeline.py#L78)。类型：`ClassDef`。

Detector callback receives the resized ROI and returns normalized ROI boxes.

### `RGBPipeline.__init__`

源码位置：[perception/rgb_pipeline.py 第 81 行](../../../perception/rgb_pipeline.py#L81)。类型：`FunctionDef`。

```python
RGBPipeline.__init__(self, detector: Callable[[np.ndarray], Iterable[RGBDetection | Mapping[str, Any]]], *, config: RGBPipelineConfig | None=None, gpu_preprocess: Callable[[np.ndarray, int, int], np.ndarray] | None=None) -> None
```

要求 detector 可调用，接受可选 GPU 预处理器；初始化空 track、检测帧和逐帧延迟表。回调合同是接收 resize 后 ROI，返回 `RGBDetection` 或含三个必需键的 mapping。

### `RGBPipeline.process`

源码位置：[perception/rgb_pipeline.py 第 98 行](../../../perception/rgb_pipeline.py#L98)。类型：`FunctionDef`。

```python
RGBPipeline.process(self, image_rgb: np.ndarray, *, frame_id: int) -> tuple[RGBTrack, ...]
```

校验非空 HWC RGB 和非负帧号。到检测间隔时裁剪/缩放 ROI、调用 detector、映射整图并关联；中间帧只传播旧框。活动 track 按框底部、面积、置信度和ID排序，截到 Top-K；每次调用都记录完整处理耗时。函数未强制帧号单调，倒序帧会影响年龄/淘汰语义。

### `RGBPipeline.metrics`

源码位置：[perception/rgb_pipeline.py 第 125 行](../../../perception/rgb_pipeline.py#L125)。类型：`FunctionDef`。

```python
RGBPipeline.metrics(self) -> dict[str, Any]
```

从已累计的每帧延迟计算帧数、均值、nearest-rank式 p95、最大值、内部track数和检测间隔；无样本时三个延迟均为 None。内部track数可包含尚未输出的状态，不等同于当前 Top-K 数。

### `RGBPipeline._preprocess`

源码位置：[perception/rgb_pipeline.py 第 136 行](../../../perception/rgb_pipeline.py#L136)。类型：`FunctionDef`。

```python
RGBPipeline._preprocess(self, image: np.ndarray) -> tuple[np.ndarray, float, float]
```

按图像高度比例切 ROI，保证至少一行；优先调用注入的 GPU preprocess，否则用 Pillow 双线性缩放到配置尺寸。返回 resize 图、ROI 顶部比例和高度比例，供框映射；缺少 Pillow 时抛 RuntimeError。

### `RGBPipeline._normalize`

源码位置：[perception/rgb_pipeline.py 第 154 行](../../../perception/rgb_pipeline.py#L154)。类型：`FunctionDef`。

```python
RGBPipeline._normalize(item: RGBDetection | Mapping[str, Any], top_ratio: float, height_ratio: float) -> RGBDetection
```

mapping 输入通过 `class_name/confidence/bbox_xyxy_norm` 三键构造检测；x坐标保持，y坐标按 `top_ratio + roi_y * height_ratio` 映射到整图，再由 `RGBDetection` 二次验证。

### `RGBPipeline._associate`

源码位置：[perception/rgb_pipeline.py 第 168 行](../../../perception/rgb_pipeline.py#L168)。类型：`FunctionDef`。

```python
RGBPipeline._associate(self, detections: tuple[RGBDetection, ...], frame_id: int) -> None
```

检测按置信度/类别/框确定性排序，只与同类别未占用 track 比 IoU；达到阈值复用ID并按帧差增加年龄，否则分配新ID。未匹配旧track在寿命内保留、标记非本帧检测；最终用本轮 updated 表整体替换历史。

### `RGBPipeline._propagate`

源码位置：[perception/rgb_pipeline.py 第 202 行](../../../perception/rgb_pipeline.py#L202)。类型：`FunctionDef`。

```python
RGBPipeline._propagate(self, frame_id: int) -> None
```

非检测帧不做运动预测，只原样保留寿命内的框、年龄加1并置 `detected_this_frame=False`；超过 `last_frame_id` 最大年龄的 track 删除。

## 内部调用与异常路径

- `_iou` 调用：`max`, `min`.
- `__post_init__` 调用：`TypeError`, `ValueError`, `all`, `float`, `getattr`, `isinstance`, `len`, `math.isfinite`, `object.__setattr__`, `tuple`, `type`.
- `__init__` 调用：`RGBPipelineConfig`, `TypeError`, `callable`.
- `process` 调用：`ValueError`, `active.sort`, `np.asarray`, `self._associate`, `self._latencies_ms.append`, `self._normalize`, `self._preprocess`, `self._propagate`, `self._tracks.values`, `self.detector`, `time.perf_counter_ns`, `tuple`, `type`.
- `metrics` 调用：`len`, `math.ceil`, `max`, `min`, `sorted`, `sum`.
- `_preprocess` 调用：`Image.fromarray`, `Image.fromarray(roi.astype(np.uint8)).resize`, `RuntimeError`, `int`, `max`, `np.asarray`, `roi.astype`, `round`, `self.gpu_preprocess`.
- `_normalize` 调用：`RGBDetection`, `float`, `isinstance`, `str`, `tuple`.
- `_associate` 调用：`RGBTrack`, `_iou`, `max`, `replace`, `set`, `sorted`, `unmatched.remove`.
- `_propagate` 调用：`replace`, `self._tracks.items`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__init__`，第 89 行：`TypeError('detector must be callable')`。
- `__post_init__`，第 27 行：`ValueError('ROI ratios must satisfy 0 <= top < bottom <= 1')`。
- `__post_init__`，第 30 行：`ValueError(f'{name} must be a positive integer')`。
- `__post_init__`，第 32 行：`ValueError('iou_match_threshold must be in [0, 1]')`。
- `__post_init__`，第 43 行：`ValueError('class_name must be non-empty')`。
- `__post_init__`，第 45 行：`ValueError('confidence must be finite and in [0, 1]')`。
- `__post_init__`，第 47 行：`TypeError('bbox_xyxy_norm must be a tuple of four values')`。
- `__post_init__`，第 50 行：`ValueError('bbox coordinates must be finite and in [0, 1]')`。
- `__post_init__`，第 52 行：`ValueError('bbox must have positive area')`。
- `_preprocess`，第 147 行：`RuntimeError('Pillow is required for RGB preprocessing')`。
- `process`，第 102 行：`ValueError('image_rgb must have shape (H, W, 3)')`。
- `process`，第 104 行：`ValueError('frame_id must be non-negative')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [perception/__init__.py](../../../perception/__init__.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-perception.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `perception/rgb_pipeline.py`

来源 SHA256：`c242c9e10094fdc419264e1f7c31610d6466d04a6718db57a31c85d07146d67c`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `RGBPipelineConfig.roi_top_ratio` | `float` | `0.2` |
| `RGBPipelineConfig.roi_bottom_ratio` | `float` | `1.0` |
| `RGBPipelineConfig.input_width` | `int` | `640` |
| `RGBPipelineConfig.input_height` | `int` | `384` |
| `RGBPipelineConfig.detection_interval_frames` | `int` | `3` |
| `RGBPipelineConfig.top_k` | `int` | `12` |
| `RGBPipelineConfig.iou_match_threshold` | `float` | `0.25` |
| `RGBPipelineConfig.max_track_age_frames` | `int` | `6` |
| `RGBDetection.class_name` | `str` | `无声明默认；构造/赋值方提供` |
| `RGBDetection.confidence` | `float` | `无声明默认；构造/赋值方提供` |
| `RGBDetection.bbox_xyxy_norm` | `tuple[float, float, float, float]` | `无声明默认；构造/赋值方提供` |
| `RGBTrack.track_id` | `str` | `无声明默认；构造/赋值方提供` |
| `RGBTrack.class_name` | `str` | `无声明默认；构造/赋值方提供` |
| `RGBTrack.confidence` | `float` | `无声明默认；构造/赋值方提供` |
| `RGBTrack.bbox_xyxy_norm` | `tuple[float, float, float, float]` | `无声明默认；构造/赋值方提供` |
| `RGBTrack.first_frame_id` | `int` | `无声明默认；构造/赋值方提供` |
| `RGBTrack.last_frame_id` | `int` | `无声明默认；构造/赋值方提供` |
| `RGBTrack.age_frames` | `int` | `无声明默认；构造/赋值方提供` |
| `RGBTrack.detected_this_frame` | `bool` | `无声明默认；构造/赋值方提供` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `RGBPipelineConfig.__post_init__` / 27 | `not 0.0 <= self.roi_top_ratio < self.roi_bottom_ratio <= 1.0` | `raise ValueError('ROI ratios must satisfy 0 <= top < bottom <= 1')` |
| `RGBPipelineConfig.__post_init__` / 30 | `type(getattr(self, name)) is not int or getattr(self, name) < 1` | `raise ValueError(f'{name} must be a positive integer')` |
| `RGBPipelineConfig.__post_init__` / 32 | `not 0.0 <= self.iou_match_threshold <= 1.0` | `raise ValueError('iou_match_threshold must be in [0, 1]')` |
| `RGBDetection.__post_init__` / 43 | `type(self.class_name) is not str or not self.class_name` | `raise ValueError('class_name must be non-empty')` |
| `RGBDetection.__post_init__` / 45 | `type(self.confidence) not in (int, float) or isinstance(self.confidence, bool) or (not math.isfinite(float(self.confidence))) or (not 0 <= self.confidence <= 1)` | `raise ValueError('confidence must be finite and in [0, 1]')` |
| `RGBDetection.__post_init__` / 47 | `type(self.bbox_xyxy_norm) is not tuple or len(self.bbox_xyxy_norm) != 4` | `raise TypeError('bbox_xyxy_norm must be a tuple of four values')` |
| `RGBDetection.__post_init__` / 50 | `not all((math.isfinite(value) and 0 <= value <= 1 for value in box))` | `raise ValueError('bbox coordinates must be finite and in [0, 1]')` |
| `RGBDetection.__post_init__` / 52 | `box[2] <= box[0] or box[3] <= box[1]` | `raise ValueError('bbox must have positive area')` |
| `RGBPipeline.__init__` / 89 | `not callable(detector)` | `raise TypeError('detector must be callable')` |
| `RGBPipeline.process` / 102 | `image.ndim != 3 or image.shape[2] != 3 or image.shape[0] < 2 or (image.shape[1] < 2)` | `raise ValueError('image_rgb must have shape (H, W, 3)')` |
| `RGBPipeline.process` / 104 | `type(frame_id) is not int or frame_id < 0` | `raise ValueError('frame_id must be non-negative')` |
| `RGBPipeline._preprocess` / 147 | `NOT (self.gpu_preprocess is not None) AND except ImportError` | `raise RuntimeError('Pillow is required for RGB preprocessing') from error` |
