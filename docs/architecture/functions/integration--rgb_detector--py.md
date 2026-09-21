# rgb_detector：功能记录

上级模块：[模块说明](../modules/vehicle-perception.md) · 实现：[integration/rgb_detector.py](../../../integration/rgb_detector.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [同帧感知、目标身份与来源](perception-authority.md)

## 功能职责与范围

Dependency-light ONNX object detection for frame-aligned CARLA RGB images.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `_Letterbox.scale: float`；默认：`未在声明处设置`。
- `_Letterbox.pad_x: float`；默认：`未在声明处设置`。
- `_Letterbox.pad_y: float`；默认：`未在声明处设置`。
- `_Letterbox.original_width: int`；默认：`未在声明处设置`。
- `_Letterbox.original_height: int`；默认：`未在声明处设置`。

## 功能入口：输入、输出与实现说明

### `OnnxDetectionError`

源码位置：[integration/rgb_detector.py 第 29 行](../../../integration/rgb_detector.py#L29)。类型：`ClassDef`。

Model, preprocessing or inference failure that must fail closed.

### `_Letterbox`

源码位置：[integration/rgb_detector.py 第 34 行](../../../integration/rgb_detector.py#L34)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `carla_rgb_array`

源码位置：[integration/rgb_detector.py 第 42 行](../../../integration/rgb_detector.py#L42)。类型：`FunctionDef`。

```python
carla_rgb_array(measurement: Any) -> np.ndarray
```

Convert a CARLA BGRA payload (or a test RGB array) to uint8 RGB.

### `_resize_rgb`

源码位置：[integration/rgb_detector.py 第 60 行](../../../integration/rgb_detector.py#L60)。类型：`FunctionDef`。

```python
_resize_rgb(image: np.ndarray, width: int, height: int) -> np.ndarray
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_letterbox`

源码位置：[integration/rgb_detector.py 第 68 行](../../../integration/rgb_detector.py#L68)。类型：`FunctionDef`。

```python
_letterbox(image: np.ndarray, input_width: int, input_height: int) -> tuple[np.ndarray, _Letterbox]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_box_iou`

源码位置：[integration/rgb_detector.py 第 84 行](../../../integration/rgb_detector.py#L84)。类型：`FunctionDef`。

```python
_box_iou(box: Sequence[float], boxes: np.ndarray) -> np.ndarray
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_class_aware_nms`

源码位置：[integration/rgb_detector.py 第 95 行](../../../integration/rgb_detector.py#L95)。类型：`FunctionDef`。

```python
_class_aware_nms(boxes: np.ndarray, scores: np.ndarray, class_ids: np.ndarray, iou_threshold: float) -> list[int]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `OnnxYoloDetector`

源码位置：[integration/rgb_detector.py 第 112 行](../../../integration/rgb_detector.py#L112)。类型：`ClassDef`。

Ultralytics-style ONNX road-user detector with auditable postprocessing.

### `OnnxYoloDetector.__init__`

源码位置：[integration/rgb_detector.py 第 115 行](../../../integration/rgb_detector.py#L115)。类型：`FunctionDef`。

```python
OnnxYoloDetector.__init__(self, model_path: str | Path, *, confidence_threshold: float=0.35, iou_threshold: float=0.45, input_size: int=640, providers: Sequence[str]=('CPUExecutionProvider',), session: Any | None=None) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `OnnxYoloDetector.detect_measurement`

源码位置：[integration/rgb_detector.py 第 156 行](../../../integration/rgb_detector.py#L156)。类型：`FunctionDef`。

```python
OnnxYoloDetector.detect_measurement(self, measurement: Any) -> tuple[DetectedObject, ...]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `OnnxYoloDetector.detect_rgb`

源码位置：[integration/rgb_detector.py 第 159 行](../../../integration/rgb_detector.py#L159)。类型：`FunctionDef`。

```python
OnnxYoloDetector.detect_rgb(self, image_rgb: np.ndarray) -> tuple[DetectedObject, ...]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `OnnxYoloDetector._decode`

源码位置：[integration/rgb_detector.py 第 172 行](../../../integration/rgb_detector.py#L172)。类型：`FunctionDef`。

```python
OnnxYoloDetector._decode(self, output: np.ndarray, transform: _Letterbox) -> tuple[DetectedObject, ...]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `driving_corridor_detections`

源码位置：[integration/rgb_detector.py 第 228 行](../../../integration/rgb_detector.py#L228)。类型：`FunctionDef`。

```python
driving_corridor_detections(detections: Iterable[DetectedObject], *, center_min: float=0.35, center_max: float=0.65, minimum_bottom: float=0.3) -> tuple[DetectedObject, ...]
```

Select plausible ego-lane road users without pretending to segment lanes.

The front camera has a 100 degree horizontal field of view, so the former
20--80 percent gate covered adjacent lanes as well as the ego lane.  That
made a pedestrian who had completed a crossing remain a permanent visual
fail-closed obstacle even though LiDAR correctly reported an empty front
corridor.  The central 30 percent is the conservative ego-path region;
side detections remain in ``PerceptionFrame.detected_objects`` for Qwen and
audit, but no longer request longitudinal emergency braking by themselves.

## 内部调用与异常路径

- `carla_rgb_array` 调用：`ValueError`, `bgra.reshape`, `getattr`, `hasattr`, `image.astype`, `np.asarray`, `np.frombuffer`, `type`.
- `_resize_rgb` 调用：`Image.fromarray`, `Image.fromarray(image, mode='RGB').resize`, `OnnxDetectionError`, `np.asarray`.
- `_letterbox` 调用：`_Letterbox`, `_resize_rgb`, `canvas.astype`, `float`, `int`, `max`, `min`, `np.ascontiguousarray`, `np.full`, `np.transpose`, `round`.
- `_box_iou` 调用：`float`, `max`, `np.maximum`, `np.minimum`.
- `_class_aware_nms` 调用：`_box_iou`, `float`, `int`, `keep.append`, `np.argsort`, `np.flatnonzero`, `np.unique`, `sorted`.
- `driving_corridor_detections` 调用：`selected.append`, `tuple`.
- `__init__` 调用：`FileNotFoundError`, `OnnxDetectionError`, `Path`, `ValueError`, `float`, `int`, `len`, `list`, `ort.InferenceSession`, `self.model_path.is_file`, `session.get_inputs`, `str`, `tuple`, `type`.
- `detect_measurement` 调用：`carla_rgb_array`, `self.detect_rgb`.
- `detect_rgb` 调用：`OnnxDetectionError`, `ValueError`, `_letterbox`, `image.astype`, `np.asarray`, `self._decode`, `self._session.run`.
- `_decode` 调用：`DetectedObject`, `OnnxDetectionError`, `_class_aware_nms`, `detections.append`, `float`, `int`, `len`, `np.arange`, `np.argmax`, `np.argmax(class_scores, axis=1).astype`, `np.array`, `np.clip`, `np.empty_like`, `np.isfinite`, `np.squeeze`, `rows[:, -80:].astype`, `rows[:, 4].astype`, `rows[:, 5].astype`, `rows[:, :4].astype`, `tuple`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__init__`，第 127 行：`FileNotFoundError(f'ONNX detector model not found: {self.model_path}')`。
- `__init__`，第 129 行：`ValueError('confidence_threshold must be in (0, 1]')`。
- `__init__`，第 131 行：`ValueError('iou_threshold must be in (0, 1]')`。
- `__init__`，第 133 行：`ValueError('input_size must be an integer >= 32')`。
- `__init__`，第 138 行：`OnnxDetectionError('onnxruntime is required when --rgb-detector-model is configured')`。
- `__init__`，第 144 行：`OnnxDetectionError(f'failed to load ONNX model: {error}')`。
- `__init__`，第 148 行：`OnnxDetectionError('detector ONNX model must expose exactly one image input')`。
- `_decode`，第 175 行：`OnnxDetectionError(f'unsupported detector output shape: {output.shape}')`。
- `_decode`，第 196 行：`OnnxDetectionError(f'unsupported detector output columns: {rows.shape[1]}')`。
- `_resize_rgb`，第 64 行：`OnnxDetectionError('Pillow is required for ONNX detector preprocessing')`。
- `carla_rgb_array`，第 47 行：`ValueError('rgb_array must have shape (H, W, 3)')`。
- `carla_rgb_array`，第 53 行：`ValueError('CARLA RGB payload requires raw_data, width and height')`。
- `carla_rgb_array`，第 56 行：`ValueError('CARLA RGB raw_data size does not match width/height BGRA layout')`。
- `detect_rgb`，第 162 行：`ValueError('image_rgb must have shape (H, W, 3)')`。
- `detect_rgb`，第 167 行：`OnnxDetectionError(f'ONNX inference failed: {error}')`。
- `detect_rgb`，第 169 行：`OnnxDetectionError('ONNX detector returned no outputs')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [integration/contracts.py](../../../integration/contracts.py)

静态 import 消费者（含测试）：

- [integration/carla_perception.py](../../../integration/carla_perception.py)
- [integration/carla_runner.py](../../../integration/carla_runner.py)
- [integration/offline_replay.py](../../../integration/offline_replay.py)
- [integration/qwen_image_stager.py](../../../integration/qwen_image_stager.py)
- [integration/tests/test_rgb_detector.py](../../../integration/tests/test_rgb_detector.py)
- [tools/replay_acceptance.py](../../../tools/replay_acceptance.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-perception.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `integration/rgb_detector.py`

来源 SHA256：`34f6e960280ed43e803e16a2be9b772e74e8bbc34ae0a31bdcead073109d7440`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `_Letterbox.scale` | `float` | `无声明默认；构造/赋值方提供` |
| `_Letterbox.pad_x` | `float` | `无声明默认；构造/赋值方提供` |
| `_Letterbox.pad_y` | `float` | `无声明默认；构造/赋值方提供` |
| `_Letterbox.original_width` | `int` | `无声明默认；构造/赋值方提供` |
| `_Letterbox.original_height` | `int` | `无声明默认；构造/赋值方提供` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `carla_rgb_array` / 47 | `hasattr(measurement, 'rgb_array') AND image.ndim != 3 or image.shape[2] != 3` | `raise ValueError('rgb_array must have shape (H, W, 3)')` |
| `carla_rgb_array` / 53 | `raw is None or type(width) is not int or type(height) is not int or (width < 1) or (height < 1)` | `raise ValueError('CARLA RGB payload requires raw_data, width and height')` |
| `carla_rgb_array` / 56 | `bgra.size != width * height * 4` | `raise ValueError('CARLA RGB raw_data size does not match width/height BGRA layout')` |
| `_resize_rgb` / 64 | `except ImportError` | `raise OnnxDetectionError('Pillow is required for ONNX detector preprocessing') from error` |
| `OnnxYoloDetector.__init__` / 127 | `session is None and (not self.model_path.is_file())` | `raise FileNotFoundError(f'ONNX detector model not found: {self.model_path}')` |
| `OnnxYoloDetector.__init__` / 129 | `not 0.0 < confidence_threshold <= 1.0` | `raise ValueError('confidence_threshold must be in (0, 1]')` |
| `OnnxYoloDetector.__init__` / 131 | `not 0.0 < iou_threshold <= 1.0` | `raise ValueError('iou_threshold must be in (0, 1]')` |
| `OnnxYoloDetector.__init__` / 133 | `type(input_size) is not int or input_size < 32` | `raise ValueError('input_size must be an integer >= 32')` |
| `OnnxYoloDetector.__init__` / 138 | `session is None AND except ImportError` | `raise OnnxDetectionError('onnxruntime is required when --rgb-detector-model is configured') from error` |
| `OnnxYoloDetector.__init__` / 144 | `session is None AND except Exception` | `raise OnnxDetectionError(f'failed to load ONNX model: {error}') from error` |
| `OnnxYoloDetector.__init__` / 148 | `len(inputs) != 1` | `raise OnnxDetectionError('detector ONNX model must expose exactly one image input')` |
| `OnnxYoloDetector.detect_rgb` / 162 | `image.ndim != 3 or image.shape[2] != 3 or image.shape[0] < 1 or (image.shape[1] < 1)` | `raise ValueError('image_rgb must have shape (H, W, 3)')` |
| `OnnxYoloDetector.detect_rgb` / 167 | `except Exception` | `raise OnnxDetectionError(f'ONNX inference failed: {error}') from error` |
| `OnnxYoloDetector.detect_rgb` / 169 | `not outputs` | `raise OnnxDetectionError('ONNX detector returned no outputs')` |
| `OnnxYoloDetector._decode` / 175 | `rows.ndim != 2` | `raise OnnxDetectionError(f'unsupported detector output shape: {output.shape}')` |
| `OnnxYoloDetector._decode` / 196 | `NOT (rows.shape[1] == 6) AND NOT (rows.shape[1] in {84, 85})` | `raise OnnxDetectionError(f'unsupported detector output columns: {rows.shape[1]}')` |
