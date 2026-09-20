# qwen_image_stager：功能记录

上级模块：[模块说明](../modules/vehicle-planner.md) · 实现：[integration/qwen_image_stager.py](../../../integration/qwen_image_stager.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [异步等待、旧结果拒绝与多层命令ID](async-plan-dispatch.md)
- [计划可行性校验与内部步骤展开](plan-validation-compilation.md)

## 功能职责与范围

Stage CARLA RGB snapshots from A's slow worker, never the control thread.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

<a id="fn-qwenimagestager"></a>

### `QwenImageStager`

源码位置：[integration/qwen_image_stager.py 第 15 行](../../../integration/qwen_image_stager.py#L15)。类型：`ClassDef`。

在帧线程保存传感器 measurement 引用，把 JPEG 编码推迟至模型工作线程。stage 不落盘；prepare_request 消费一次缓存后落盘并改写 rgb_ref。它不承担传感器同步或图像文件清理。

<a id="fn-qwenimagestager---init--"></a>

### `QwenImageStager.__init__`

源码位置：[integration/qwen_image_stager.py 第 16 行](../../../integration/qwen_image_stager.py#L16)。类型：`FunctionDef`。

```python
QwenImageStager.__init__(self, image_root: str | Path, *, ref_prefix: str='artifacts/qwen_live') -> None
```

image_root resolve 为绝对目录；ref_prefix 默认 artifacts/qwen_live，统一为 POSIX 相对路径并拒绝绝对路径和 ..。预热 Pillow/JPEG 编码，建立锁和 command_id 缓存；实际文件目录在 prepare_request 创建。

<a id="fn-qwenimagestager-stage"></a>

### `QwenImageStager.stage`

源码位置：[integration/qwen_image_stager.py 第 37 行](../../../integration/qwen_image_stager.py#L37)。类型：`FunctionDef`。

```python
QwenImageStager.stage(self, command_id: str, measurement: Any, *, frame_id: int) -> str
```

要求非空 command_id 与非负整数 frame_id，生成带 command_id 哈希的图像引用，锁内保存 measurement 引用；相同 command_id 会覆盖旧缓存。不编码、不复制像素，也不验证 measurement.frame 与 frame_id 一致，调用方负责帧对齐。

<a id="fn-qwenimagestager-stage-multiview"></a>

### `QwenImageStager.stage_multiview`

源码位置：[integration/qwen_image_stager.py 第 48 行](../../../integration/qwen_image_stager.py#L48)。类型：`FunctionDef`。

```python
QwenImageStager.stage_multiview(self, command_id: str, measurements: Mapping[str, Any], *, frame_id: int) -> str
```

Stage an exact-frame four-camera montage for one Qwen request.

The fixed layout is front/left on the first row and right/rear on the
second row.  It keeps the frozen single-image model contract while
ensuring the official S2/S3 Qwen request actually contains all four
camera views instead of merely logging their presence.

实际只校验四键rgb_front/rgb_left/rgb_right/rgb_rear齐全、command_id非空和frame_id为非负整数；没有比较各measurement.frame。保存四个measurement引用而非图像副本，相同command_id覆盖旧capture；所谓exact-frame依赖调用方已完成对齐。

<a id="fn-qwenimagestager-discard"></a>

### `QwenImageStager.discard`

源码位置：[integration/qwen_image_stager.py 第 79 行](../../../integration/qwen_image_stager.py#L79)。类型：`FunctionDef`。

```python
QwenImageStager.discard(self, command_id: str) -> None
```

锁内移除 command_id 的待编码缓存，不存在时无操作；不删除已经写出的 JPEG 文件。

<a id="fn-qwenimagestager-prepare-request"></a>

### `QwenImageStager.prepare_request`

源码位置：[integration/qwen_image_stager.py 第 83 行](../../../integration/qwen_image_stager.py#L83)。类型：`FunctionDef`。

```python
QwenImageStager.prepare_request(self, request: Mapping[str, Any]) -> Mapping[str, Any]
```

按 command_id 原子 pop 缓存，无缓存则返回 request 顶层副本。检查输出路径仍位于 image_root，创建目录；单视图黑底补边缩放到 224×224，多视图将 front/left/right/rear 各 fit 到 112×112 后拼图，JPEG quality=75。返回更新 rgb_ref 的请求；缓存先移除，编码/写盘失败不能自动重试同一缓存，文件不会自动回收。

<a id="fn-qwenimagestager--measurement-image"></a>

### `QwenImageStager._measurement_image`

源码位置：[integration/qwen_image_stager.py 第 130 行](../../../integration/qwen_image_stager.py#L130)。类型：`FunctionDef`。

```python
QwenImageStager._measurement_image(self, measurement: Any) -> Any
```

有 CARLA raw_data/width/height 时按 BGRA 字节解码为 RGB；否则调用 carla_rgb_array 再转 Pillow 图像。错误尺寸或无效 measurement 的解码异常向上传播。

## 内部调用与异常路径

- `__init__` 调用：`Image.init`, `Image.new`, `Image.new('RGB', (1, 1)).save`, `Lock`, `Path`, `Path(image_root).expanduser`, `Path(image_root).expanduser().resolve`, `PurePosixPath`, `RuntimeError`, `ValueError`, `io.BytesIO`, `prefix.is_absolute`, `str`, `str(ref_prefix).replace`.
- `stage` 调用：`ValueError`, `command_id.encode`, `hashlib.sha256`, `hashlib.sha256(command_id.encode('utf-8')).hexdigest`, `str`, `type`.
- `stage_multiview` 调用：`ValueError`, `command_id.encode`, `hashlib.sha256`, `hashlib.sha256(command_id.encode('utf-8')).hexdigest`, `str`, `type`.
- `discard` 调用：`self._captures.pop`.
- `prepare_request` 调用：`(self.image_root / Path(reference)).resolve`, `Image.new`, `ImageOps.fit`, `ImageOps.pad`, `Path`, `ValueError`, `dict`, `getattr`, `image.paste`, `image.save`, `isinstance`, `request.get`, `self._captures.pop`, `self._measurement_image`, `str`, `target.parent.mkdir`, `target.relative_to`.
- `_measurement_image` 调用：`Image.fromarray`, `Image.frombuffer`, `Image.frombuffer('RGBA', (width, height), raw, 'raw', 'BGRA', 0, 1).convert`, `bytes`, `carla_rgb_array`, `getattr`, `isinstance`, `type`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__init__`，第 20 行：`RuntimeError('Pillow is required to stage Qwen RGB images')`。
- `__init__`，第 24 行：`ValueError('ref_prefix must be a safe relative path')`。
- `prepare_request`，第 94 行：`ValueError('staged Qwen image escapes image_root')`。
- `stage`，第 39 行：`ValueError('command_id must be a non-empty string')`。
- `stage`，第 41 行：`ValueError('frame_id must be a non-negative integer')`。
- `stage_multiview`，第 63 行：`ValueError('command_id must be a non-empty string')`。
- `stage_multiview`，第 65 行：`ValueError('frame_id must be a non-negative integer')`。
- `stage_multiview`，第 69 行：`ValueError(f'multiview measurements missing sensors: {missing}')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [integration/rgb_detector.py](../../../integration/rgb_detector.py)

静态 import 消费者（含测试）：

- [integration/carla_runner.py](../../../integration/carla_runner.py)
- [integration/tests/test_qwen_image_stager.py](../../../integration/tests/test_qwen_image_stager.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-planner.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

<a id="fn-integration-qwen-image-stager-py"></a>

### `integration/qwen_image_stager.py`

来源 SHA256：`d07359abf70bda0538e297e6ad9770764e5c36e520b43920d7a820beb1fe9901`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `QwenImageStager.__init__` / 20 | `except ImportError` | `raise RuntimeError('Pillow is required to stage Qwen RGB images') from error` |
| `QwenImageStager.__init__` / 24 | `prefix.is_absolute() or '..' in prefix.parts` | `raise ValueError('ref_prefix must be a safe relative path')` |
| `QwenImageStager.stage` / 39 | `type(command_id) is not str or not command_id` | `raise ValueError('command_id must be a non-empty string')` |
| `QwenImageStager.stage` / 41 | `type(frame_id) is not int or frame_id < 0` | `raise ValueError('frame_id must be a non-negative integer')` |
| `QwenImageStager.stage_multiview` / 63 | `type(command_id) is not str or not command_id` | `raise ValueError('command_id must be a non-empty string')` |
| `QwenImageStager.stage_multiview` / 65 | `type(frame_id) is not int or frame_id < 0` | `raise ValueError('frame_id must be a non-negative integer')` |
| `QwenImageStager.stage_multiview` / 69 | `missing` | `raise ValueError(f'multiview measurements missing sensors: {missing}')` |
| `QwenImageStager.prepare_request` / 94 | `except ValueError` | `raise ValueError('staged Qwen image escapes image_root') from error` |
