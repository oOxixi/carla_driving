# contracts：功能记录

上级模块：[模块说明](../modules/vehicle-perception.md) · 实现：[integration/contracts.py](../../../integration/contracts.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [同帧感知、目标身份与来源](perception-authority.md)

## 功能职责与范围

Small integration-only contracts shared by the runtime adapters.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `DetectedObject.class_id: int`；默认：`未在声明处设置`。
- `DetectedObject.class_name: str`；默认：`未在声明处设置`。
- `DetectedObject.confidence: float`；默认：`未在声明处设置`。
- `DetectedObject.bbox_xyxy_norm: tuple[float, float, float, float]`；默认：`未在声明处设置`。
- `DetectedObject.distance_m: float | None`；默认：`None`。
- `DetectedObject.track_id: str | None`；默认：`None`。
- `PerceptionFrame.frame: int`；默认：`未在声明处设置`。
- `PerceptionFrame.sim_time_s: float`；默认：`未在声明处设置`。
- `PerceptionFrame.lead_distance_m: float | None`；默认：`None`。
- `PerceptionFrame.lead_speed_mps: float | None`；默认：`None`。
- `PerceptionFrame.traffic_light: str`；默认：`'UNKNOWN'`。
- `PerceptionFrame.distance_to_stop_line_m: float | None`；默认：`None`。
- `PerceptionFrame.speed_limit_mps: float | None`；默认：`None`。
- `PerceptionFrame.lane_offset_m: float | None`；默认：`None`。
- `PerceptionFrame.route_deviation_m: float | None`；默认：`None`。
- `PerceptionFrame.collision: bool`；默认：`False`。
- `PerceptionFrame.red_light_violation: bool`；默认：`False`。
- `PerceptionFrame.lane_invasion: bool`；默认：`False`。
- `PerceptionFrame.detected_objects: tuple[DetectedObject, ...]`；默认：`()`。
- `FrameResult.vehicle: RuntimeVehicleState`；默认：`未在声明处设置`。
- `FrameResult.final_control: ControlOutput`；默认：`未在声明处设置`。
- `FrameResult.longitudinal: LongitudinalOutput | None`；默认：`未在声明处设置`。
- `FrameResult.safety_reason: str`；默认：`未在声明处设置`。
- `FrameResult.safety_override: bool`；默认：`未在声明处设置`。
- `FrameResult.feedback: tuple[ExecutionFeedback, ...]`；默认：`()`。
- `FrameResult.raw_control: Any | None`；默认：`None`。
- `FrameResult.lateral: LateralOutput | None`；默认：`None`。
- `FrameResult.safety_reason_category: str`；默认：`'NONE'`。

## 功能入口：输入、输出与实现说明

### `_finite_or_none`

源码位置：[integration/contracts.py 第 17 行](../../../integration/contracts.py#L17)。类型：`FunctionDef`。

```python
_finite_or_none(name: str, value: float | None) -> float | None
```

把 `None` 原样保留；其余值只接受非布尔的 `int/float` 且必须有限，成功后统一转为 `float`。类型、NaN 和无穷值都抛 `ValueError`；是否允许负数由调用该助手的字段再判断。

### `DetectedObject`

源码位置：[integration/contracts.py 第 26 行](../../../integration/contracts.py#L26)。类型：`ClassDef`。

One RGB road-user detection, optionally fused with a sensor distance.

### `DetectedObject.__post_init__`

源码位置：[integration/contracts.py 第 36 行](../../../integration/contracts.py#L36)。类型：`FunctionDef`。

```python
DetectedObject.__post_init__(self) -> None
```

冻结对象的构造门禁：`class_id` 必须为非负整数，类别名非空，置信度在 `[0,1]`；归一化框必须是长度4的 tuple、各坐标在 `[0,1]` 且宽高为正。距离可空但非空时须非负，track ID 可空但非空时必须是非空字符串；通过后置信度、框和距离被标准化为 float。

### `PerceptionFrame`

源码位置：[integration/contracts.py 第 66 行](../../../integration/contracts.py#L66)。类型：`ClassDef`。

Frame-aligned scene facts consumed by C and D.

The production CARLA bridge populates these values from frame-aligned
sensors and map-derived geometry.  Scenario truth must not enter this
control contract; it is retained only by the scoring/oracle stage.

### `PerceptionFrame.__post_init__`

源码位置：[integration/contracts.py 第 87 行](../../../integration/contracts.py#L87)。类型：`FunctionDef`。

```python
PerceptionFrame.__post_init__(self) -> None
```

校验控制侧一帧事实：帧号和仿真时间非负，距离/速度/偏移等可空数值必须有限，其中前车距离/速度、停止线距离和限速不得为负；灯态只允许四个枚举值，三个违规标记必须为 bool，目标必须是 `DetectedObject` tuple。该合同不携带来源，因此生产端还必须同时保留 `PerceptionSample.source_by_field`。

### `FrameResult`

源码位置：[integration/contracts.py 第 111 行](../../../integration/contracts.py#L111)。类型：`ClassDef`。

Auditable output of one control frame; only ``final_control`` reaches CARLA.

## 内部调用与异常路径

- `_finite_or_none` 调用：`ValueError`, `float`, `isinstance`, `math.isfinite`, `type`.
- `__post_init__` 调用：`TypeError`, `ValueError`, `_finite_or_none`, `any`, `enumerate`, `float`, `getattr`, `isinstance`, `len`, `math.isfinite`, `object.__setattr__`, `type`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__post_init__`，第 38 行：`ValueError('class_id must be a non-negative integer')`。
- `__post_init__`，第 40 行：`ValueError('class_name must be non-empty')`。
- `__post_init__`，第 42 行：`ValueError('confidence must be finite')`。
- `__post_init__`，第 44 行：`ValueError('confidence must be in [0, 1]')`。
- `__post_init__`，第 46 行：`TypeError('bbox_xyxy_norm must be a four-number tuple')`。
- `__post_init__`，第 52 行：`ValueError('normalized detection box values must be in [0, 1]')`。
- `__post_init__`，第 54 行：`ValueError('detection box must have positive width and height')`。
- `__post_init__`，第 59 行：`ValueError('distance_m must be non-negative')`。
- `__post_init__`，第 62 行：`ValueError('track_id must be a non-empty string or None')`。
- `__post_init__`，第 89 行：`ValueError('frame must be a non-negative integer')`。
- `__post_init__`，第 92 行：`ValueError('sim_time_s must be non-negative')`。
- `__post_init__`，第 97 行：`ValueError(f'{name} must be non-negative')`。
- `__post_init__`，第 100 行：`ValueError('traffic_light must be RED/YELLOW/GREEN/UNKNOWN')`。
- `__post_init__`，第 103 行：`TypeError(f'{name} must be bool')`。
- `__post_init__`，第 107 行：`TypeError('detected_objects must be a tuple of DetectedObject values')`。
- `_finite_or_none`，第 21 行：`ValueError(f'{name} must be a finite number or None')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [car_control_A/__init__.py](../../../car_control_A/__init__.py)
- [car_control_B/schemas.py](../../../car_control_B/schemas.py)

静态 import 消费者（含测试）：

- [integration/__init__.py](../../../integration/__init__.py)
- [integration/canonical_bridge.py](../../../integration/canonical_bridge.py)
- [integration/carla_perception.py](../../../integration/carla_perception.py)
- [integration/carla_runner.py](../../../integration/carla_runner.py)
- [integration/demo_offline.py](../../../integration/demo_offline.py)
- [integration/object_tracker.py](../../../integration/object_tracker.py)
- [integration/offline_replay.py](../../../integration/offline_replay.py)
- [integration/perception_bridge.py](../../../integration/perception_bridge.py)
- [integration/rgb_detector.py](../../../integration/rgb_detector.py)
- [integration/runtime_loop.py](../../../integration/runtime_loop.py)
- [integration/second_group_runtime.py](../../../integration/second_group_runtime.py)
- [integration/tests/test_canonical_bridge.py](../../../integration/tests/test_canonical_bridge.py)
- [integration/tests/test_carla_perception.py](../../../integration/tests/test_carla_perception.py)
- [integration/tests/test_carla_runner_helpers.py](../../../integration/tests/test_carla_runner_helpers.py)
- [integration/tests/test_object_tracker.py](../../../integration/tests/test_object_tracker.py)
- [integration/tests/test_perception_bridge.py](../../../integration/tests/test_perception_bridge.py)
- [integration/tests/test_rgb_detector.py](../../../integration/tests/test_rgb_detector.py)
- [integration/tests/test_scenario_evidence.py](../../../integration/tests/test_scenario_evidence.py)
- [integration/tests/test_second_group_runtime.py](../../../integration/tests/test_second_group_runtime.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-perception.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `integration/contracts.py`

来源 SHA256：`93a58ab38400950a32988cec1cdb65a15433f3731d2eee05494f788485fce10c`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `DetectedObject.class_id` | `int` | `无声明默认；构造/赋值方提供` |
| `DetectedObject.class_name` | `str` | `无声明默认；构造/赋值方提供` |
| `DetectedObject.confidence` | `float` | `无声明默认；构造/赋值方提供` |
| `DetectedObject.bbox_xyxy_norm` | `tuple[float, float, float, float]` | `无声明默认；构造/赋值方提供` |
| `DetectedObject.distance_m` | `float &#124; None` | `None` |
| `DetectedObject.track_id` | `str &#124; None` | `None` |
| `PerceptionFrame.frame` | `int` | `无声明默认；构造/赋值方提供` |
| `PerceptionFrame.sim_time_s` | `float` | `无声明默认；构造/赋值方提供` |
| `PerceptionFrame.lead_distance_m` | `float &#124; None` | `None` |
| `PerceptionFrame.lead_speed_mps` | `float &#124; None` | `None` |
| `PerceptionFrame.traffic_light` | `str` | `'UNKNOWN'` |
| `PerceptionFrame.distance_to_stop_line_m` | `float &#124; None` | `None` |
| `PerceptionFrame.speed_limit_mps` | `float &#124; None` | `None` |
| `PerceptionFrame.lane_offset_m` | `float &#124; None` | `None` |
| `PerceptionFrame.route_deviation_m` | `float &#124; None` | `None` |
| `PerceptionFrame.collision` | `bool` | `False` |
| `PerceptionFrame.red_light_violation` | `bool` | `False` |
| `PerceptionFrame.lane_invasion` | `bool` | `False` |
| `PerceptionFrame.detected_objects` | `tuple[DetectedObject, ...]` | `()` |
| `FrameResult.vehicle` | `RuntimeVehicleState` | `无声明默认；构造/赋值方提供` |
| `FrameResult.final_control` | `ControlOutput` | `无声明默认；构造/赋值方提供` |
| `FrameResult.longitudinal` | `LongitudinalOutput &#124; None` | `无声明默认；构造/赋值方提供` |
| `FrameResult.safety_reason` | `str` | `无声明默认；构造/赋值方提供` |
| `FrameResult.safety_override` | `bool` | `无声明默认；构造/赋值方提供` |
| `FrameResult.feedback` | `tuple[ExecutionFeedback, ...]` | `()` |
| `FrameResult.raw_control` | `Any &#124; None` | `None` |
| `FrameResult.lateral` | `LateralOutput &#124; None` | `None` |
| `FrameResult.safety_reason_category` | `str` | `'NONE'` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `_finite_or_none` / 21 | `type(value) not in (int, float) or isinstance(value, bool) or (not math.isfinite(float(value)))` | `raise ValueError(f'{name} must be a finite number or None')` |
| `DetectedObject.__post_init__` / 38 | `type(self.class_id) is not int or self.class_id < 0` | `raise ValueError('class_id must be a non-negative integer')` |
| `DetectedObject.__post_init__` / 40 | `type(self.class_name) is not str or not self.class_name` | `raise ValueError('class_name must be non-empty')` |
| `DetectedObject.__post_init__` / 42 | `type(self.confidence) not in (int, float) or not math.isfinite(float(self.confidence))` | `raise ValueError('confidence must be finite')` |
| `DetectedObject.__post_init__` / 44 | `not 0.0 <= float(self.confidence) <= 1.0` | `raise ValueError('confidence must be in [0, 1]')` |
| `DetectedObject.__post_init__` / 46 | `type(self.bbox_xyxy_norm) is not tuple or len(self.bbox_xyxy_norm) != 4` | `raise TypeError('bbox_xyxy_norm must be a four-number tuple')` |
| `DetectedObject.__post_init__` / 52 | `any((value is None or value < 0.0 or value > 1.0 for value in (x1, y1, x2, y2)))` | `raise ValueError('normalized detection box values must be in [0, 1]')` |
| `DetectedObject.__post_init__` / 54 | `x2 <= x1 or y2 <= y1` | `raise ValueError('detection box must have positive width and height')` |
| `DetectedObject.__post_init__` / 59 | `distance is not None and distance < 0.0` | `raise ValueError('distance_m must be non-negative')` |
| `DetectedObject.__post_init__` / 62 | `self.track_id is not None and (type(self.track_id) is not str or not self.track_id)` | `raise ValueError('track_id must be a non-empty string or None')` |
| `PerceptionFrame.__post_init__` / 89 | `type(self.frame) is not int or self.frame < 0` | `raise ValueError('frame must be a non-negative integer')` |
| `PerceptionFrame.__post_init__` / 92 | `sim_time is None or sim_time < 0` | `raise ValueError('sim_time_s must be non-negative')` |
| `PerceptionFrame.__post_init__` / 97 | `name in {'lead_distance_m', 'lead_speed_mps', 'distance_to_stop_line_m', 'speed_limit_mps'} and value is not None and (value < 0)` | `raise ValueError(f'{name} must be non-negative')` |
| `PerceptionFrame.__post_init__` / 100 | `self.traffic_light not in {'RED', 'YELLOW', 'GREEN', 'UNKNOWN'}` | `raise ValueError('traffic_light must be RED/YELLOW/GREEN/UNKNOWN')` |
| `PerceptionFrame.__post_init__` / 103 | `type(getattr(self, name)) is not bool` | `raise TypeError(f'{name} must be bool')` |
| `PerceptionFrame.__post_init__` / 107 | `type(self.detected_objects) is not tuple or any((not isinstance(item, DetectedObject) for item in self.detected_objects))` | `raise TypeError('detected_objects must be a tuple of DetectedObject values')` |
