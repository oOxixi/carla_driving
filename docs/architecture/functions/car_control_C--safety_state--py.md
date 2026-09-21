# safety_state：功能记录

上级模块：[模块说明](../modules/vehicle-longitudinal.md) · 实现：[car_control_C/safety_state.py](../../../car_control_C/safety_state.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [目标速度、跟车风险与D交接](longitudinal-safety-contract.md)

## 功能职责与范围

Auditable RGB/LiDAR safety-state fusion for member C.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `VisualObservation.frame: int`；默认：`未在声明处设置`。
- `VisualObservation.valid: bool`；默认：`未在声明处设置`。
- `VisualObservation.object_class: str | None`；默认：`None`。
- `VisualObservation.confidence: float | None`；默认：`None`。
- `VisualObservation.source: str`；默认：`'RGB_DETECTOR'`。
- `SafetyStateParameters.visual_confidence_threshold: float`；默认：`DEFAULT_STRATEGY.perception_safety.visual_confidence_threshold`。
- `SafetyStateParameters.caution_distance_m: float`；默认：`10.0`。
- `SafetyStateParameters.emergency_distance_m: float`；默认：`5.0`。
- `SafetyStateParameters.vru_caution_distance_m: float`；默认：`25.0`。
- `SafetyStateParameters.vru_emergency_distance_m: float`；默认：`8.0`。
- `SafetyStateParameters.vru_caution_speed_cap_mps: float`；默认：`DEFAULT_STRATEGY.perception_safety.vru_caution_speed_cap_mps`。
- `SafetyStateParameters.vru_caution_hold_s: float`；默认：`DEFAULT_STRATEGY.perception_safety.vru_caution_hold_s`。
- `SafetyStateParameters.caution_ttc_s: float`；默认：`DEFAULT_STRATEGY.common.caution_ttc_s`。
- `SafetyStateParameters.emergency_ttc_s: float`；默认：`DEFAULT_STRATEGY.common.emergency_ttc_s`。
- `SafetyStateParameters.max_observation_gap_s: float`；默认：`DEFAULT_STRATEGY.perception_safety.max_observation_gap_s`。
- `SafetyStateParameters.untracked_approach_speed_margin_mps: float`；默认：`5.0`。
- `SafetyStateParameters.max_temporal_closing_speed_mps: float`；默认：`40.0`。
- `SafetyStateParameters.temporal_closing_confirmation_tolerance_mps: float`；默认：`5.0`。
- `SafetyStateParameters.reaction_time_s: float`；默认：`0.7`。
- `SafetyStateParameters.emergency_reaction_time_s: float`；默认：`0.35`。
- `SafetyStateParameters.comfortable_deceleration_mps2: float`；默认：`3.5`。
- `SafetyStateParameters.emergency_deceleration_mps2: float`；默认：`6.0`。
- `SafetyStateParameters.range_uncertainty_buffer_m: float`；默认：`1.0`。
- `SafetyStateParameters.full_brake: float`；默认：`DEFAULT_STRATEGY.common.emergency_brake`。
- `SafetyStateSummary.frame: int`；默认：`未在声明处设置`。
- `SafetyStateSummary.sim_time_s: float`；默认：`未在声明处设置`。
- `SafetyStateSummary.front_distance_m: float | None`；默认：`未在声明处设置`。
- `SafetyStateSummary.closing_speed_mps: float | None`；默认：`未在声明处设置`。
- `SafetyStateSummary.ttc_s: float | None`；默认：`未在声明处设置`。
- `SafetyStateSummary.object_class: str | None`；默认：`未在声明处设置`。
- `SafetyStateSummary.object_confidence: float | None`；默认：`未在声明处设置`。
- `SafetyStateSummary.visual_valid: bool`；默认：`未在声明处设置`。
- `SafetyStateSummary.lidar_valid: bool`；默认：`未在声明处设置`。
- `SafetyStateSummary.fused_valid: bool`；默认：`未在声明处设置`。
- `SafetyStateSummary.fusion_mode: str`；默认：`未在声明处设置`。
- `SafetyStateSummary.recommended_action: str`；默认：`未在声明处设置`。
- `SafetyStateSummary.recommended_speed_cap_mps: float | None`；默认：`未在声明处设置`。
- `SafetyStateSummary.dynamic_caution_distance_m: float | None`；默认：`未在声明处设置`。
- `SafetyStateSummary.dynamic_emergency_distance_m: float | None`；默认：`未在声明处设置`。
- `SafetyStateSummary.safety_distance_components: Mapping[str, float]`；默认：`未在声明处设置`。
- `SafetyStateSummary.reason: str`；默认：`未在声明处设置`。
- `SafetyStateSummary.source_by_field: Mapping[str, str]`；默认：`未在声明处设置`。

## 功能入口：输入、输出与实现说明

### `_optional_non_negative`

源码位置：[car_control_C/safety_state.py 第 25 行](../../../car_control_C/safety_state.py#L25)。类型：`FunctionDef`。

```python
_optional_non_negative(name: str, value: float | None) -> float | None
```

保留 `None` 表示测量缺失；非空值委托公共 `finite` 校验为有限非负浮点数，不把缺失转换成零。

### `_source`

源码位置：[car_control_C/safety_state.py 第 31 行](../../../car_control_C/safety_state.py#L31)。类型：`FunctionDef`。

```python
_source(name: str, value: object) -> str
```

要求 exact string 且去空白后非空，返回 strip 后来源；用于证据来源字段，拒绝数字等可字符串化对象。

### `VisualObservation`

源码位置：[car_control_C/safety_state.py 第 38 行](../../../car_control_C/safety_state.py#L38)。类型：`ClassDef`。

One upstream RGB semantic result for an exact control frame.

``valid=False`` requires the semantic fields to be absent.  This makes an
unavailable/failed detector distinguishable from a confident UNKNOWN
classification and prevents C from inventing visual evidence.

### `VisualObservation.__post_init__`

源码位置：[car_control_C/safety_state.py 第 52 行](../../../car_control_C/safety_state.py#L52)。类型：`FunctionDef`。

```python
VisualObservation.__post_init__(self) -> None
```

校验非负整数 frame、exact bool valid 和非空来源。无效观察必须同时没有类别/置信度；有效观察必须有非空类别和 `[0,1]` 置信度，并把类别标准化为大写。

### `VisualObservation.unavailable`

源码位置：[car_control_C/safety_state.py 第 69 行](../../../car_control_C/safety_state.py#L69)。类型：`FunctionDef`。

```python
VisualObservation.unavailable(cls, frame: int, *, source: str='RGB_DETECTOR_UNAVAILABLE') -> 'VisualObservation'
```

构造 `valid=False` 且无语义字段的显式缺失观察，默认来源 `RGB_DETECTOR_UNAVAILABLE`；用于区分检测器不可用和有效 UNKNOWN 分类。

### `SafetyStateParameters`

源码位置：[car_control_C/safety_state.py 第 74 行](../../../car_control_C/safety_state.py#L74)。类型：`ClassDef`。

C-side perception policy; distance thresholds are computed per frame.

### `SafetyStateParameters.__post_init__`

源码位置：[car_control_C/safety_state.py 第 104 行](../../../car_control_C/safety_state.py#L104)。类型：`FunctionDef`。

```python
SafetyStateParameters.__post_init__(self) -> None
```

校验置信阈值 `[0,1]`、其余距离/时间/减速度参数严格为正、full brake 在 `(0,1]`；同时约束普通紧急距离不大于 caution、VRU 紧急距离不低于普通值且不超过 VRU caution、紧急 TTC 不大于 caution TTC。

### `SafetyStateSummary`

源码位置：[car_control_C/safety_state.py 第 129 行](../../../car_control_C/safety_state.py#L129)。类型：`ClassDef`。

Serializable C output for Qwen/D/logging and on-site monitoring.

### `SafetyStateSummary.fail_closed`

源码位置：[car_control_C/safety_state.py 第 152 行](../../../car_control_C/safety_state.py#L152)。类型：`FunctionDef`。

```python
SafetyStateSummary.fail_closed(self) -> bool
```

只在 `recommended_action` 为 `FULL_BRAKE` 或 `EMERGENCY_BRAKE` 时为真；`SLOW_DOWN` 即使带速度 cap 也不算 fail-closed。

### `SafetyStateSummary.to_dict`

源码位置：[car_control_C/safety_state.py 第 155 行](../../../car_control_C/safety_state.py#L155)。类型：`FunctionDef`。

```python
SafetyStateSummary.to_dict(self) -> dict[str, object]
```

把全部融合字段序列化为版本 `1.0` 字典，并复制只读安全距离组成与来源映射；保留 `None` 表示缺失测量/未计算包络。

### `ConservativeSensorFusion`

源码位置：[car_control_C/safety_state.py 第 179 行](../../../car_control_C/safety_state.py#L179)。类型：`ClassDef`。

Fuse exact-frame RGB semantics with front LiDAR range conservatively.

### `ConservativeSensorFusion.__init__`

源码位置：[car_control_C/safety_state.py 第 188 行](../../../car_control_C/safety_state.py#L188)。类型：`FunctionDef`。

```python
ConservativeSensorFusion.__init__(self, parameters: SafetyStateParameters | None=None) -> None
```

保存策略并初始化上一帧/时间/距离、待确认时序接近速度和 VRU caution 截止时间。实例有 episode 状态，不能跨重生复用而不 reset。

### `ConservativeSensorFusion.reset`

源码位置：[car_control_C/safety_state.py 第 196 行](../../../car_control_C/safety_state.py#L196)。类型：`FunctionDef`。

```python
ConservativeSensorFusion.reset(self) -> None
```

清除全部时序历史和 VRU 保守保持窗口；不会修改参数。

### `ConservativeSensorFusion.update`

源码位置：[car_control_C/safety_state.py 第 203 行](../../../car_control_C/safety_state.py#L203)。类型：`FunctionDef`。

```python
ConservativeSensorFusion.update(self, *, frame: int, sim_time_s: float, ego_speed_mps: float, front_distance_m: float | None, lidar_valid: bool, visual: VisualObservation | None=None, lead_speed_mps: float | None=None, road_curvature_per_m: float=0.0, sensor_margin_scale: float=1.0, lidar_source: str='LIDAR_FRONT_CORRIDOR', lead_speed_source: str='LEAD_TRACKER') -> SafetyStateSummary
```

要求 frame/time 严格递增、RGB/LiDAR 同帧，并禁止无效 LiDAR 携带量测。优先用对齐 lead speed 算接近速度；无速度时对距离差分做物理上限和连续两次确认。随后生成动态安全距离，按 LiDAR 缺失、RGB 无距离危险、TTC/距离、VRU 保持依次决定 FULL_BRAKE/EMERGENCY_BRAKE/SLOW_DOWN/KEEP_SPEED，并记录每字段来源。

### `ConservativeSensorFusion.fail_closed_control`

源码位置：[car_control_C/safety_state.py 第 396 行](../../../car_control_C/safety_state.py#L396)。类型：`FunctionDef`。

```python
ConservativeSensorFusion.fail_closed_control(self) -> ControlOutput
```

返回 `ControlOutput(throttle=0, brake=full_brake)`；它只是 C 侧可提交的原始制动，最终仍应进入 D 仲裁和事件记录。

### `ConservativeSensorFusion._range_action`

源码位置：[car_control_C/safety_state.py 第 399 行](../../../car_control_C/safety_state.py#L399)。类型：`FunctionDef`。

```python
ConservativeSensorFusion._range_action(self, distance_m: float, ttc_s: float | None, mode: str, *, envelope: object, object_class: str | None=None) -> tuple[str, str, str]
```

要求动态包络非空，以配置 floor 和包络较大值作为 caution/emergency 距离；判定优先级为紧急 TTC、紧急距离、caution TTC、caution 距离、包络外 KEEP_SPEED，并为 VRU 紧急距离使用专用 reason。

## 内部调用与异常路径

- `_optional_non_negative` 调用：`finite`.
- `_source` 调用：`ValueError`, `type`, `value.strip`.
- `__post_init__` 调用：`TypeError`, `ValueError`, `_source`, `finite`, `getattr`, `object.__setattr__`, `self.object_class.strip`, `self.object_class.strip().upper`, `type`.
- `unavailable` 调用：`cls`.
- `to_dict` 调用：`dict`.
- `__init__` 调用：`SafetyStateParameters`.
- `update` 调用：`MappingProxyType`, `SafetyStateSummary`, `TypeError`, `ValueError`, `VisualObservation.unavailable`, `_optional_non_negative`, `_source`, `abs`, `bool`, `dynamic_safety_distance`, `envelope.to_dict`, `finite`, `max`, `min`, `self._range_action`, `type`.
- `fail_closed_control` 调用：`ControlOutput`.
- `_range_action` 调用：`ValueError`, `float`, `getattr`, `max`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__post_init__`，第 54 行：`ValueError('frame must be a non-negative integer')`。
- `__post_init__`，第 56 行：`TypeError('valid must be bool')`。
- `__post_init__`，第 60 行：`ValueError('invalid visual observations must not carry semantic values')`。
- `__post_init__`，第 63 行：`ValueError('a valid visual observation needs object_class')`。
- `__post_init__`，第 119 行：`ValueError('emergency_distance_m must not exceed caution_distance_m')`。
- `__post_init__`，第 121 行：`ValueError('vru_emergency_distance_m must be at least emergency_distance_m')`。
- `__post_init__`，第 123 行：`ValueError('vru_caution_distance_m must be at least vru_emergency_distance_m')`。
- `__post_init__`，第 125 行：`ValueError('emergency_ttc_s must not exceed caution_ttc_s')`。
- `_range_action`，第 409 行：`ValueError('a range action requires a dynamic safety envelope')`。
- `_source`，第 33 行：`ValueError(f'{name} must be a non-empty string')`。
- `update`，第 219 行：`ValueError('frame must be a non-negative integer')`。
- `update`，第 227 行：`TypeError('lidar_valid must be bool')`。
- `update`，第 229 行：`ValueError('fusion frames must be strictly increasing; call reset() for a new episode')`。
- `update`，第 231 行：`ValueError('sim_time_s must be strictly increasing; call reset() for a new episode')`。
- `update`，第 233 行：`ValueError('an invalid LiDAR observation must not carry range or lead speed')`。
- `update`，第 235 行：`ValueError('lead_speed_mps requires front_distance_m')`。
- `update`，第 239 行：`ValueError('visual and LiDAR observations must use the same frame')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [car_control_A/__init__.py](../../../car_control_A/__init__.py)
- [car_control_C/validation.py](../../../car_control_C/validation.py)
- [config/strategy.py](../../../config/strategy.py)

静态 import 消费者（含测试）：

- [car_control_C/__init__.py](../../../car_control_C/__init__.py)
- [integration/driving_policy.py](../../../integration/driving_policy.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-longitudinal.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `car_control_C/safety_state.py`

来源 SHA256：`e51e4859fb9715f89cd5f5a56c66bd98a4b3dbb455c4cff75c356fc8d4b3f3fb`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `VisualObservation.frame` | `int` | `无声明默认；构造/赋值方提供` |
| `VisualObservation.valid` | `bool` | `无声明默认；构造/赋值方提供` |
| `VisualObservation.object_class` | `str &#124; None` | `None` |
| `VisualObservation.confidence` | `float &#124; None` | `None` |
| `VisualObservation.source` | `str` | `'RGB_DETECTOR'` |
| `SafetyStateParameters.visual_confidence_threshold` | `float` | `DEFAULT_STRATEGY.perception_safety.visual_confidence_threshold` |
| `SafetyStateParameters.caution_distance_m` | `float` | `10.0` |
| `SafetyStateParameters.emergency_distance_m` | `float` | `5.0` |
| `SafetyStateParameters.vru_caution_distance_m` | `float` | `25.0` |
| `SafetyStateParameters.vru_emergency_distance_m` | `float` | `8.0` |
| `SafetyStateParameters.vru_caution_speed_cap_mps` | `float` | `DEFAULT_STRATEGY.perception_safety.vru_caution_speed_cap_mps` |
| `SafetyStateParameters.vru_caution_hold_s` | `float` | `DEFAULT_STRATEGY.perception_safety.vru_caution_hold_s` |
| `SafetyStateParameters.caution_ttc_s` | `float` | `DEFAULT_STRATEGY.common.caution_ttc_s` |
| `SafetyStateParameters.emergency_ttc_s` | `float` | `DEFAULT_STRATEGY.common.emergency_ttc_s` |
| `SafetyStateParameters.max_observation_gap_s` | `float` | `DEFAULT_STRATEGY.perception_safety.max_observation_gap_s` |
| `SafetyStateParameters.untracked_approach_speed_margin_mps` | `float` | `5.0` |
| `SafetyStateParameters.max_temporal_closing_speed_mps` | `float` | `40.0` |
| `SafetyStateParameters.temporal_closing_confirmation_tolerance_mps` | `float` | `5.0` |
| `SafetyStateParameters.reaction_time_s` | `float` | `0.7` |
| `SafetyStateParameters.emergency_reaction_time_s` | `float` | `0.35` |
| `SafetyStateParameters.comfortable_deceleration_mps2` | `float` | `3.5` |
| `SafetyStateParameters.emergency_deceleration_mps2` | `float` | `6.0` |
| `SafetyStateParameters.range_uncertainty_buffer_m` | `float` | `1.0` |
| `SafetyStateParameters.full_brake` | `float` | `DEFAULT_STRATEGY.common.emergency_brake` |
| `SafetyStateSummary.frame` | `int` | `无声明默认；构造/赋值方提供` |
| `SafetyStateSummary.sim_time_s` | `float` | `无声明默认；构造/赋值方提供` |
| `SafetyStateSummary.front_distance_m` | `float &#124; None` | `无声明默认；构造/赋值方提供` |
| `SafetyStateSummary.closing_speed_mps` | `float &#124; None` | `无声明默认；构造/赋值方提供` |
| `SafetyStateSummary.ttc_s` | `float &#124; None` | `无声明默认；构造/赋值方提供` |
| `SafetyStateSummary.object_class` | `str &#124; None` | `无声明默认；构造/赋值方提供` |
| `SafetyStateSummary.object_confidence` | `float &#124; None` | `无声明默认；构造/赋值方提供` |
| `SafetyStateSummary.visual_valid` | `bool` | `无声明默认；构造/赋值方提供` |
| `SafetyStateSummary.lidar_valid` | `bool` | `无声明默认；构造/赋值方提供` |
| `SafetyStateSummary.fused_valid` | `bool` | `无声明默认；构造/赋值方提供` |
| `SafetyStateSummary.fusion_mode` | `str` | `无声明默认；构造/赋值方提供` |
| `SafetyStateSummary.recommended_action` | `str` | `无声明默认；构造/赋值方提供` |
| `SafetyStateSummary.recommended_speed_cap_mps` | `float &#124; None` | `无声明默认；构造/赋值方提供` |
| `SafetyStateSummary.dynamic_caution_distance_m` | `float &#124; None` | `无声明默认；构造/赋值方提供` |
| `SafetyStateSummary.dynamic_emergency_distance_m` | `float &#124; None` | `无声明默认；构造/赋值方提供` |
| `SafetyStateSummary.safety_distance_components` | `Mapping[str, float]` | `无声明默认；构造/赋值方提供` |
| `SafetyStateSummary.reason` | `str` | `无声明默认；构造/赋值方提供` |
| `SafetyStateSummary.source_by_field` | `Mapping[str, str]` | `无声明默认；构造/赋值方提供` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `_source` / 33 | `type(value) is not str or not value.strip()` | `raise ValueError(f'{name} must be a non-empty string')` |
| `VisualObservation.__post_init__` / 54 | `type(self.frame) is not int or self.frame < 0` | `raise ValueError('frame must be a non-negative integer')` |
| `VisualObservation.__post_init__` / 56 | `type(self.valid) is not bool` | `raise TypeError('valid must be bool')` |
| `VisualObservation.__post_init__` / 60 | `not self.valid AND self.object_class is not None or self.confidence is not None` | `raise ValueError('invalid visual observations must not carry semantic values')` |
| `VisualObservation.__post_init__` / 63 | `type(self.object_class) is not str or not self.object_class.strip()` | `raise ValueError('a valid visual observation needs object_class')` |
| `SafetyStateParameters.__post_init__` / 119 | `self.emergency_distance_m > self.caution_distance_m` | `raise ValueError('emergency_distance_m must not exceed caution_distance_m')` |
| `SafetyStateParameters.__post_init__` / 121 | `self.vru_emergency_distance_m < self.emergency_distance_m` | `raise ValueError('vru_emergency_distance_m must be at least emergency_distance_m')` |
| `SafetyStateParameters.__post_init__` / 123 | `self.vru_caution_distance_m < self.vru_emergency_distance_m` | `raise ValueError('vru_caution_distance_m must be at least vru_emergency_distance_m')` |
| `SafetyStateParameters.__post_init__` / 125 | `self.emergency_ttc_s > self.caution_ttc_s` | `raise ValueError('emergency_ttc_s must not exceed caution_ttc_s')` |
| `ConservativeSensorFusion.update` / 219 | `type(frame) is not int or frame < 0` | `raise ValueError('frame must be a non-negative integer')` |
| `ConservativeSensorFusion.update` / 227 | `type(lidar_valid) is not bool` | `raise TypeError('lidar_valid must be bool')` |
| `ConservativeSensorFusion.update` / 229 | `self._previous_frame is not None and frame <= self._previous_frame` | `raise ValueError('fusion frames must be strictly increasing; call reset() for a new episode')` |
| `ConservativeSensorFusion.update` / 231 | `self._previous_time_s is not None and sim_time_s <= self._previous_time_s` | `raise ValueError('sim_time_s must be strictly increasing; call reset() for a new episode')` |
| `ConservativeSensorFusion.update` / 233 | `not lidar_valid and (front_distance_m is not None or lead_speed_mps is not None)` | `raise ValueError('an invalid LiDAR observation must not carry range or lead speed')` |
| `ConservativeSensorFusion.update` / 235 | `front_distance_m is None and lead_speed_mps is not None` | `raise ValueError('lead_speed_mps requires front_distance_m')` |
| `ConservativeSensorFusion.update` / 239 | `visual.frame != frame` | `raise ValueError('visual and LiDAR observations must use the same frame')` |
| `ConservativeSensorFusion._range_action` / 409 | `envelope is None` | `raise ValueError('a range action requires a dynamic safety envelope')` |

### car_control_C/safety_state.py 数值检查调用

这里保留校验函数的minimum/positive等参数原文；实际可达性由调用分支决定，函数本体异常仍需看对应helper。

| 行 | 校验调用 |
|---|---|
| 28 | `finite(name, value, minimum=0.0)` |
| 64 | `finite('confidence', self.confidence, minimum=0.0, maximum=1.0)` |
| 105 | `finite('visual_confidence_threshold', self.visual_confidence_threshold, minimum=0.0, maximum=1.0)` |
| 117 | `finite('full_brake', self.full_brake, positive=True, maximum=1.0)` |
| 220 | `finite('sim_time_s', sim_time_s, minimum=0.0)` |
| 221 | `finite('ego_speed_mps', ego_speed_mps, minimum=0.0)` |
| 222 | `_optional_non_negative('front_distance_m', front_distance_m)` |
| 223 | `_optional_non_negative('lead_speed_mps', lead_speed_mps)` |
| 224 | `finite('road_curvature_per_m', road_curvature_per_m)` |
| 225 | `finite('sensor_margin_scale', sensor_margin_scale, minimum=0.0)` |
| 116 | `finite(name, getattr(self, name), positive=True)` |
