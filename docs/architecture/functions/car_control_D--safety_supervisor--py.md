# safety_supervisor：功能记录

上级模块：[模块说明](../modules/vehicle-safety.md) · 实现：[car_control_D/safety_supervisor.py](../../../car_control_D/safety_supervisor.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [C/D分工与实时仲裁](longitudinal-safety-contract.md)
- [安全覆盖的生命周期影响](control-frame.md)

## 功能职责与范围

Final safety arbitration for D.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `SafetyConfig.min_front_distance_m: float`；默认：`DEFAULT_STRATEGY.safety_distance.minimum_emergency_distance_m`。
- `SafetyConfig.low_ttc_s: float`；默认：`DEFAULT_STRATEGY.common.emergency_ttc_s`。
- `SafetyConfig.caution_ttc_s: float`；默认：`DEFAULT_STRATEGY.common.caution_ttc_s`。
- `SafetyConfig.stop_line_guard_m: float`；默认：`DEFAULT_STRATEGY.supervisor.stop_line_guard_m`。
- `SafetyConfig.max_lane_offset_m: float`；默认：`DEFAULT_STRATEGY.supervisor.max_lane_offset_m`。
- `SafetyConfig.minimum_lane_offset_m: float`；默认：`DEFAULT_STRATEGY.supervisor.minimum_lane_offset_m`。
- `SafetyConfig.severe_route_deviation_m: float`；默认：`DEFAULT_STRATEGY.supervisor.severe_route_deviation_m`。
- `SafetyConfig.minimum_severe_route_deviation_m: float`；默认：`DEFAULT_STRATEGY.supervisor.minimum_severe_route_deviation_m`。
- `SafetyConfig.route_speed_sensitivity: float`；默认：`DEFAULT_STRATEGY.supervisor.route_speed_sensitivity`。
- `SafetyConfig.route_curvature_sensitivity: float`；默认：`DEFAULT_STRATEGY.supervisor.route_curvature_sensitivity`。
- `SafetyConfig.route_recovery_max_speed_mps: float`；默认：`DEFAULT_STRATEGY.supervisor.route_recovery_max_speed_mps`。
- `SafetyConfig.route_recovery_throttle: float`；默认：`DEFAULT_STRATEGY.supervisor.route_recovery_throttle`。
- `SafetyConfig.route_recovery_steer_limit: float`；默认：`DEFAULT_STRATEGY.supervisor.route_recovery_steer_limit`。
- `SafetyConfig.route_deviation_brake: float`；默认：`DEFAULT_STRATEGY.supervisor.route_deviation_brake`。
- `SafetyConfig.low_confidence_threshold: float`；默认：`DEFAULT_STRATEGY.common.command_confidence_threshold`。
- `SafetyConfig.hold_brake: float`；默认：`DEFAULT_STRATEGY.common.hold_brake`。
- `SafetyConfig.emergency_brake: float`；默认：`DEFAULT_STRATEGY.common.emergency_brake`。
- `SafetyConfig.caution_brake: float`；默认：`DEFAULT_STRATEGY.supervisor.caution_brake`。
- `SafetyConfig.standstill_speed_mps: float`；默认：`DEFAULT_STRATEGY.common.standstill_speed_mps`。
- `SafetyConfig.emergency_reaction_time_s: float`；默认：`0.35`。
- `SafetyConfig.emergency_deceleration_mps2: float`；默认：`6.0`。
- `SafetyConfig.range_uncertainty_buffer_m: float`；默认：`1.0`。

## 功能入口：输入、输出与实现说明

### `SafetyConfig`

源码位置：[car_control_D/safety_supervisor.py 第 19 行](../../../car_control_D/safety_supervisor.py#L19)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `SafetyConfig.__post_init__`

源码位置：[car_control_D/safety_supervisor.py 第 47 行](../../../car_control_D/safety_supervisor.py#L47)。类型：`FunctionDef`。

```python
SafetyConfig.__post_init__(self) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `SafetySupervisor`

源码位置：[car_control_D/safety_supervisor.py 第 85 行](../../../car_control_D/safety_supervisor.py#L85)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `SafetySupervisor.__init__`

源码位置：[car_control_D/safety_supervisor.py 第 86 行](../../../car_control_D/safety_supervisor.py#L86)。类型：`FunctionDef`。

```python
SafetySupervisor.__init__(self, config: Optional[SafetyConfig]=None) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `SafetySupervisor.arbitrate`

源码位置：[car_control_D/safety_supervisor.py 第 89 行](../../../car_control_D/safety_supervisor.py#L89)。类型：`FunctionDef`。

```python
SafetySupervisor.arbitrate(self, raw_control: Any, vehicle_state: Any=None, command: Any=None, risk: Any=None, watchdog_alerts: Optional[Iterable[str]]=None) -> SafetyDecision
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `SafetySupervisor.arbitrate.category`

源码位置：[car_control_D/safety_supervisor.py 第 170 行](../../../car_control_D/safety_supervisor.py#L170)。类型：`FunctionDef`。

```python
SafetySupervisor.arbitrate.category(reason: str) -> str
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `SafetySupervisor.arbitrate.stop`

源码位置：[car_control_D/safety_supervisor.py 第 189 行](../../../car_control_D/safety_supervisor.py#L189)。类型：`FunctionDef`。

```python
SafetySupervisor.arbitrate.stop(reason: str, brake: Optional[float]=None, steer: float=0.0) -> SafetyDecision
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `SafetySupervisor.arbitrate.caution`

源码位置：[car_control_D/safety_supervisor.py 第 199 行](../../../car_control_D/safety_supervisor.py#L199)。类型：`FunctionDef`。

```python
SafetySupervisor.arbitrate.caution(reason: str) -> SafetyDecision
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `SafetySupervisor.arbitrate.recover_route`

源码位置：[car_control_D/safety_supervisor.py 第 209 行](../../../car_control_D/safety_supervisor.py#L209)。类型：`FunctionDef`。

```python
SafetySupervisor.arbitrate.recover_route() -> SafetyDecision
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

## 内部调用与异常路径

- `__post_init__` 调用：`ValueError`, `any`, `float`, `getattr`, `math.isfinite`, `type`, `values.values`.
- `__init__` 调用：`SafetyConfig`.
- `arbitrate` 调用：`'_'.join`, `'_'.join(control_result.errors).upper`, `'_'.join(control_result.errors).upper().replace`, `CommandView`, `ControlOutput`, `RiskView`, `SafetyDecision`, `VehicleStateView`, `abs`, `adapt_command`, `adapt_control`, `adapt_risk`, `adapt_vehicle_state`, `alert.strip`, `any`, `category`, `caution`, `cmd.to_dict`, `distance_envelope.to_dict`, `dynamic_safety_distance`, `list`, `max`, `min`, `reason.startswith`, `recover_route`, `stop`, `tuple`, `type`, `validate_command`, `validate_control`.
- `category` 调用：`any`, `reason.startswith`.
- `stop` 调用：`ControlOutput`, `SafetyDecision`, `category`.
- `caution` 调用：`ControlOutput`, `SafetyDecision`, `category`, `max`, `min`.
- `recover_route` 调用：`ControlOutput`, `SafetyDecision`, `max`, `min`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__post_init__`，第 56 行：`ValueError('all safety configuration values must be finite numbers')`。
- `__post_init__`，第 66 行：`ValueError('safety distances, times and speeds must be non-negative')`。
- `__post_init__`，第 68 行：`ValueError('emergency_deceleration_mps2 must be positive')`。
- `__post_init__`，第 70 行：`ValueError('low_ttc_s must not exceed caution_ttc_s')`。
- `__post_init__`，第 72 行：`ValueError('max_lane_offset_m must not exceed severe_route_deviation_m')`。
- `__post_init__`，第 74 行：`ValueError('minimum_lane_offset_m must not exceed max_lane_offset_m')`。
- `__post_init__`，第 76 行：`ValueError('minimum severe deviation must not exceed severe route deviation')`。
- `__post_init__`，第 82 行：`ValueError('control and confidence configuration values must be in [0, 1]')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [car_control_D/adapters.py](../../../car_control_D/adapters.py)
- [car_control_D/schemas.py](../../../car_control_D/schemas.py)
- [car_control_D/validators.py](../../../car_control_D/validators.py)
- [config/strategy.py](../../../config/strategy.py)

静态 import 消费者（含测试）：

- [car_control_D/__init__.py](../../../car_control_D/__init__.py)
- [car_control_D/benchmark.py](../../../car_control_D/benchmark.py)
- [car_control_D/control_runtime.py](../../../car_control_D/control_runtime.py)
- [car_control_D/demo_fake_integration.py](../../../car_control_D/demo_fake_integration.py)
- [car_control_D/tests/test_safety_supervisor.py](../../../car_control_D/tests/test_safety_supervisor.py)
- [integration/driving_policy.py](../../../integration/driving_policy.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-safety.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `car_control_D/safety_supervisor.py`

来源 SHA256：`cef680cc734c4bca97f2aac0bfc9ba11af671113f2465252094bebdabbb95596`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `SafetyConfig.min_front_distance_m` | `float` | `DEFAULT_STRATEGY.safety_distance.minimum_emergency_distance_m` |
| `SafetyConfig.low_ttc_s` | `float` | `DEFAULT_STRATEGY.common.emergency_ttc_s` |
| `SafetyConfig.caution_ttc_s` | `float` | `DEFAULT_STRATEGY.common.caution_ttc_s` |
| `SafetyConfig.stop_line_guard_m` | `float` | `DEFAULT_STRATEGY.supervisor.stop_line_guard_m` |
| `SafetyConfig.max_lane_offset_m` | `float` | `DEFAULT_STRATEGY.supervisor.max_lane_offset_m` |
| `SafetyConfig.minimum_lane_offset_m` | `float` | `DEFAULT_STRATEGY.supervisor.minimum_lane_offset_m` |
| `SafetyConfig.severe_route_deviation_m` | `float` | `DEFAULT_STRATEGY.supervisor.severe_route_deviation_m` |
| `SafetyConfig.minimum_severe_route_deviation_m` | `float` | `DEFAULT_STRATEGY.supervisor.minimum_severe_route_deviation_m` |
| `SafetyConfig.route_speed_sensitivity` | `float` | `DEFAULT_STRATEGY.supervisor.route_speed_sensitivity` |
| `SafetyConfig.route_curvature_sensitivity` | `float` | `DEFAULT_STRATEGY.supervisor.route_curvature_sensitivity` |
| `SafetyConfig.route_recovery_max_speed_mps` | `float` | `DEFAULT_STRATEGY.supervisor.route_recovery_max_speed_mps` |
| `SafetyConfig.route_recovery_throttle` | `float` | `DEFAULT_STRATEGY.supervisor.route_recovery_throttle` |
| `SafetyConfig.route_recovery_steer_limit` | `float` | `DEFAULT_STRATEGY.supervisor.route_recovery_steer_limit` |
| `SafetyConfig.route_deviation_brake` | `float` | `DEFAULT_STRATEGY.supervisor.route_deviation_brake` |
| `SafetyConfig.low_confidence_threshold` | `float` | `DEFAULT_STRATEGY.common.command_confidence_threshold` |
| `SafetyConfig.hold_brake` | `float` | `DEFAULT_STRATEGY.common.hold_brake` |
| `SafetyConfig.emergency_brake` | `float` | `DEFAULT_STRATEGY.common.emergency_brake` |
| `SafetyConfig.caution_brake` | `float` | `DEFAULT_STRATEGY.supervisor.caution_brake` |
| `SafetyConfig.standstill_speed_mps` | `float` | `DEFAULT_STRATEGY.common.standstill_speed_mps` |
| `SafetyConfig.emergency_reaction_time_s` | `float` | `0.35` |
| `SafetyConfig.emergency_deceleration_mps2` | `float` | `6.0` |
| `SafetyConfig.range_uncertainty_buffer_m` | `float` | `1.0` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `SafetyConfig.__post_init__` / 56 | `any((type(value) not in (int, float) or not math.isfinite(float(value)) for value in values.values()))` | `raise ValueError('all safety configuration values must be finite numbers')` |
| `SafetyConfig.__post_init__` / 66 | `any((float(values[name]) < 0.0 for name in ('min_front_distance_m', 'low_ttc_s', 'caution_ttc_s', 'stop_line_guard_m', 'max_lane_offset_m', 'minimum_lane_offset_m', 'severe_route_deviation_m', 'minimum_severe_route_deviation_m', 'route_speed_sensitivity', 'route_curvature_sensitivity', 'route_recovery_max_speed_mps', 'standstill_speed_mps', 'emergency_reaction_time_s', 'emergency_deceleration_mps2', 'range_uncertainty_buffer_m')))` | `raise ValueError('safety distances, times and speeds must be non-negative')` |
| `SafetyConfig.__post_init__` / 68 | `self.emergency_deceleration_mps2 <= 0.0` | `raise ValueError('emergency_deceleration_mps2 must be positive')` |
| `SafetyConfig.__post_init__` / 70 | `self.low_ttc_s > self.caution_ttc_s` | `raise ValueError('low_ttc_s must not exceed caution_ttc_s')` |
| `SafetyConfig.__post_init__` / 72 | `self.max_lane_offset_m > self.severe_route_deviation_m` | `raise ValueError('max_lane_offset_m must not exceed severe_route_deviation_m')` |
| `SafetyConfig.__post_init__` / 74 | `self.minimum_lane_offset_m > self.max_lane_offset_m` | `raise ValueError('minimum_lane_offset_m must not exceed max_lane_offset_m')` |
| `SafetyConfig.__post_init__` / 76 | `self.minimum_severe_route_deviation_m > self.severe_route_deviation_m` | `raise ValueError('minimum severe deviation must not exceed severe route deviation')` |
| `SafetyConfig.__post_init__` / 82 | `any((not 0.0 <= float(values[name]) <= 1.0 for name in ('route_recovery_throttle', 'route_recovery_steer_limit', 'low_confidence_threshold', 'hold_brake', 'emergency_brake', 'caution_brake')))` | `raise ValueError('control and confidence configuration values must be in [0, 1]')` |
