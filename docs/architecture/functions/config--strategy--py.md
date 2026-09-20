# strategy：功能记录

上级模块：[模块说明](../modules/support-config-scenarios.md) · 实现：[config/strategy.py](../../../config/strategy.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [具体参数的装载和覆盖](policy-precedence.md)
- [场景配置与控制/评分分工](scenario-evidence-contract.md)

## 功能职责与范围

Single, strict configuration source for generalized control and safety.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `CommonStrategy.command_confidence_threshold: float`；默认：`未在声明处设置`。
- `CommonStrategy.standstill_speed_mps: float`；默认：`未在声明处设置`。
- `CommonStrategy.comfortable_decel_mps2: float`；默认：`未在声明处设置`。
- `CommonStrategy.max_decel_mps2: float`；默认：`未在声明处设置`。
- `CommonStrategy.hold_brake: float`；默认：`未在声明处设置`。
- `CommonStrategy.emergency_brake: float`；默认：`未在声明处设置`。
- `CommonStrategy.caution_ttc_s: float`；默认：`未在声明处设置`。
- `CommonStrategy.emergency_ttc_s: float`；默认：`未在声明处设置`。
- `SafetyDistanceStrategy.standstill_gap_m: float`；默认：`未在声明处设置`。
- `SafetyDistanceStrategy.reaction_time_s: float`；默认：`未在声明处设置`。
- `SafetyDistanceStrategy.emergency_reaction_time_s: float`；默认：`未在声明处设置`。
- `SafetyDistanceStrategy.sensor_base_margin_m: float`；默认：`未在声明处设置`。
- `SafetyDistanceStrategy.sensor_uncertainty_time_s: float`；默认：`未在声明处设置`。
- `SafetyDistanceStrategy.curvature_margin_gain: float`；默认：`未在声明处设置`。
- `SafetyDistanceStrategy.vru_distance_factor: float`；默认：`未在声明处设置`。
- `SafetyDistanceStrategy.vru_emergency_distance_factor: float`；默认：`未在声明处设置`。
- `SafetyDistanceStrategy.vru_minimum_emergency_distance_m: float`；默认：`未在声明处设置`。
- `SafetyDistanceStrategy.large_vehicle_distance_factor: float`；默认：`未在声明处设置`。
- `SafetyDistanceStrategy.unknown_actor_distance_factor: float`；默认：`未在声明处设置`。
- `SafetyDistanceStrategy.minimum_emergency_distance_m: float`；默认：`未在声明处设置`。
- `PerceptionSafetyStrategy.visual_confidence_threshold: float`；默认：`未在声明处设置`。
- `PerceptionSafetyStrategy.max_observation_gap_s: float`；默认：`未在声明处设置`。
- `PerceptionSafetyStrategy.vru_caution_speed_cap_mps: float`；默认：`未在声明处设置`。
- `PerceptionSafetyStrategy.vru_caution_hold_s: float`；默认：`未在声明处设置`。
- `LongitudinalStrategy.max_lateral_accel_mps2: float`；默认：`未在声明处设置`。
- `LongitudinalStrategy.command_accel_mps2: float`；默认：`未在声明处设置`。
- `LongitudinalStrategy.command_decel_mps2: float`；默认：`未在声明处设置`。
- `LongitudinalStrategy.max_accel_mps2: float`；默认：`未在声明处设置`。
- `LongitudinalStrategy.max_control_delta_per_s: float`；默认：`未在声明处设置`。
- `LongitudinalStrategy.creep_speed_mps: float`；默认：`未在声明处设置`。
- `LongitudinalStrategy.stop_hold_distance_m: float`；默认：`未在声明处设置`。
- `LongitudinalStrategy.pid_kp: float`；默认：`未在声明处设置`。
- `LongitudinalStrategy.pid_ki: float`；默认：`未在声明处设置`。
- `LongitudinalStrategy.pid_kd: float`；默认：`未在声明处设置`。
- `LongitudinalStrategy.pid_integral_limit: float`；默认：`未在声明处设置`。
- `LongitudinalStrategy.pid_target_step_reset_mps: float`；默认：`未在声明处设置`。
- `LateralStrategy.wheel_base_m: float`；默认：`未在声明处设置`。
- `LateralStrategy.base_lookahead_m: float`；默认：`未在声明处设置`。
- `LateralStrategy.speed_gain_s: float`；默认：`未在声明处设置`。
- `LateralStrategy.min_lookahead_m: float`；默认：`未在声明处设置`。
- `LateralStrategy.max_lookahead_m: float`；默认：`未在声明处设置`。
- `LateralStrategy.curvature_lookahead_gain: float`；默认：`未在声明处设置`。
- `LateralStrategy.error_lookahead_gain: float`；默认：`未在声明处设置`。
- `LateralStrategy.max_steer_angle_rad: float`；默认：`未在声明处设置`。
- `LateralStrategy.steer_gain: float`；默认：`未在声明处设置`。
- `LateralStrategy.max_steer: float`；默认：`未在声明处设置`。
- `LateralStrategy.min_steer_limit: float`；默认：`未在声明处设置`。
- `LateralStrategy.high_speed_steer_reduction_per_mps: float`；默认：`未在声明处设置`。
- `LateralStrategy.curvature_steer_gain: float`；默认：`未在声明处设置`。
- `LateralStrategy.base_steer_delta_per_step: float`；默认：`未在声明处设置`。
- `LateralStrategy.min_steer_delta_per_step: float`；默认：`未在声明处设置`。
- `LateralStrategy.max_steer_delta_per_step: float`；默认：`未在声明处设置`。
- `LateralStrategy.low_speed_steer_gain: float`；默认：`未在声明处设置`。
- `LateralStrategy.curvature_rate_gain: float`；默认：`未在声明处设置`。
- `LateralStrategy.error_rate_gain: float`；默认：`未在声明处设置`。
- `LateralStrategy.stanley_gain: float`；默认：`未在声明处设置`。
- `LateralStrategy.stanley_softening_speed_mps: float`；默认：`未在声明处设置`。
- `LateralStrategy.stanley_curvature_gain: float`；默认：`未在声明处设置`。
- `LateralStrategy.steer_sign: float`；默认：`未在声明处设置`。
- `SupervisorStrategy.stop_line_guard_m: float`；默认：`未在声明处设置`。
- `SupervisorStrategy.max_lane_offset_m: float`；默认：`未在声明处设置`。
- `SupervisorStrategy.minimum_lane_offset_m: float`；默认：`未在声明处设置`。
- `SupervisorStrategy.severe_route_deviation_m: float`；默认：`未在声明处设置`。
- `SupervisorStrategy.minimum_severe_route_deviation_m: float`；默认：`未在声明处设置`。
- `SupervisorStrategy.route_speed_sensitivity: float`；默认：`未在声明处设置`。
- `SupervisorStrategy.route_curvature_sensitivity: float`；默认：`未在声明处设置`。
- `SupervisorStrategy.route_recovery_max_speed_mps: float`；默认：`未在声明处设置`。
- `SupervisorStrategy.route_recovery_throttle: float`；默认：`未在声明处设置`。
- `SupervisorStrategy.route_recovery_steer_limit: float`；默认：`未在声明处设置`。
- `SupervisorStrategy.route_deviation_brake: float`；默认：`未在声明处设置`。
- `SupervisorStrategy.caution_brake: float`；默认：`未在声明处设置`。
- `SensorFaultStrategy.single_sensor_speed_cap_mps: float`；默认：`未在声明处设置`。
- `SensorFaultStrategy.speed_cap_tolerance_mps: float`；默认：`未在声明处设置`。
- `SensorFaultStrategy.speed_cap_base_brake: float`；默认：`未在声明处设置`。
- `SensorFaultStrategy.speed_cap_brake_gain: float`；默认：`未在声明处设置`。
- `StrategyConfig.schema_version: str`；默认：`未在声明处设置`。
- `StrategyConfig.common: CommonStrategy`；默认：`未在声明处设置`。
- `StrategyConfig.safety_distance: SafetyDistanceStrategy`；默认：`未在声明处设置`。
- `StrategyConfig.perception_safety: PerceptionSafetyStrategy`；默认：`未在声明处设置`。
- `StrategyConfig.longitudinal: LongitudinalStrategy`；默认：`未在声明处设置`。
- `StrategyConfig.lateral: LateralStrategy`；默认：`未在声明处设置`。
- `StrategyConfig.supervisor: SupervisorStrategy`；默认：`未在声明处设置`。
- `StrategyConfig.sensor_fault: SensorFaultStrategy`；默认：`未在声明处设置`。
- `SafetyDistanceEnvelope.caution_distance_m: float`；默认：`未在声明处设置`。
- `SafetyDistanceEnvelope.emergency_distance_m: float`；默认：`未在声明处设置`。
- `SafetyDistanceEnvelope.reaction_distance_m: float`；默认：`未在声明处设置`。
- `SafetyDistanceEnvelope.braking_distance_m: float`；默认：`未在声明处设置`。
- `SafetyDistanceEnvelope.sensor_margin_m: float`；默认：`未在声明处设置`。
- `SafetyDistanceEnvelope.curvature_multiplier: float`；默认：`未在声明处设置`。
- `SafetyDistanceEnvelope.actor_multiplier: float`；默认：`未在声明处设置`。
- `SafetyDistanceEnvelope.emergency_actor_multiplier: float`；默认：`未在声明处设置`。

## 功能入口：输入、输出与实现说明

### `_number`

源码位置：[config/strategy.py 第 21 行](../../../config/strategy.py#L21)。类型：`FunctionDef`。

```python
_number(name: str, value: object, *, minimum: float=0.0, maximum: float | None=None, positive: bool=False) -> float
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `CommonStrategy`

源码位置：[config/strategy.py 第 38 行](../../../config/strategy.py#L38)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `SafetyDistanceStrategy`

源码位置：[config/strategy.py 第 50 行](../../../config/strategy.py#L50)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `PerceptionSafetyStrategy`

源码位置：[config/strategy.py 第 66 行](../../../config/strategy.py#L66)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `LongitudinalStrategy`

源码位置：[config/strategy.py 第 74 行](../../../config/strategy.py#L74)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `LateralStrategy`

源码位置：[config/strategy.py 第 90 行](../../../config/strategy.py#L90)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `SupervisorStrategy`

源码位置：[config/strategy.py 第 117 行](../../../config/strategy.py#L117)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `SensorFaultStrategy`

源码位置：[config/strategy.py 第 133 行](../../../config/strategy.py#L133)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `StrategyConfig`

源码位置：[config/strategy.py 第 141 行](../../../config/strategy.py#L141)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_section`

源码位置：[config/strategy.py 第 155 行](../../../config/strategy.py#L155)。类型：`FunctionDef`。

```python
_section(name: str, payload: object, cls: type[T]) -> T
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `load_strategy_config`

源码位置：[config/strategy.py 第 175 行](../../../config/strategy.py#L175)。类型：`FunctionDef`。

```python
load_strategy_config(path: str | Path=DEFAULT_STRATEGY_PATH) -> StrategyConfig
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `_validate_relations`

源码位置：[config/strategy.py 第 208 行](../../../config/strategy.py#L208)。类型：`FunctionDef`。

```python
_validate_relations(config: StrategyConfig) -> None
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `SafetyDistanceEnvelope`

源码位置：[config/strategy.py 第 246 行](../../../config/strategy.py#L246)。类型：`ClassDef`。

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `SafetyDistanceEnvelope.to_dict`

源码位置：[config/strategy.py 第 256 行](../../../config/strategy.py#L256)。类型：`FunctionDef`。

```python
SafetyDistanceEnvelope.to_dict(self) -> dict[str, float]
```

源码未提供该入口的独立说明；名称和类型签名不能充分确定单位、异常或副作用，修改时须同时阅读函数体及下列调用关系。

### `dynamic_safety_distance`

源码位置：[config/strategy.py 第 267 行](../../../config/strategy.py#L267)。类型：`FunctionDef`。

```python
dynamic_safety_distance(*, ego_speed_mps: float, closing_speed_mps: float | None=None, curvature_per_m: float=0.0, actor_type: str | None=None, sensor_margin_scale: float=1.0, config: StrategyConfig=DEFAULT_STRATEGY) -> SafetyDistanceEnvelope
```

Return a kinematic, speed/curvature/sensor/actor-aware envelope.

## 内部调用与异常路径

- `_number` 调用：`TypeError`, `ValueError`, `float`, `math.isfinite`, `type`.
- `_section` 调用：`TypeError`, `ValueError`, `_number`, `cls`, `fields`, `payload.items`, `set`, `sorted`, `type`.
- `load_strategy_config` 调用：`Path`, `StrategyConfig`, `TypeError`, `ValueError`, `_section`, `_validate_relations`, `config_path.read_text`, `json.loads`, `set`, `sorted`, `type`.
- `_validate_relations` 调用：`ValueError`, `getattr`.
- `dynamic_safety_distance` 调用：`SafetyDistanceEnvelope`, `_number`, `abs`, `math.sqrt`, `max`, `min`, `str`, `str(actor_type or 'UNKNOWN').strip`, `str(actor_type or 'UNKNOWN').strip().upper`.
- `to_dict` 调用：`fields`, `float`, `getattr`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `_number`，第 24 行：`TypeError(f'{name} must be a number')`。
- `_number`，第 27 行：`ValueError(f'{name} must be finite')`。
- `_number`，第 29 行：`ValueError(f'{name} must be positive')`。
- `_number`，第 31 行：`ValueError(f'{name} must be >= {minimum}')`。
- `_number`，第 33 行：`ValueError(f'{name} must be <= {maximum}')`。
- `_section`，第 157 行：`TypeError(f'strategy section {name!r} must be an object')`。
- `_section`，第 161 行：`ValueError(f'strategy section {name!r} fields mismatch; missing={sorted(expected - actual)}, unknown={sorted(actual - expected)}')`。
- `_validate_relations`，第 211 行：`ValueError('comfortable_decel_mps2 must not exceed max_decel_mps2')`。
- `_validate_relations`，第 213 行：`ValueError('emergency_ttc_s must not exceed caution_ttc_s')`。
- `_validate_relations`，第 216 行：`ValueError(f'common.{name} must be <= 1.0')`。
- `_validate_relations`，第 219 行：`ValueError('perception_safety.visual_confidence_threshold must be <= 1.0')`。
- `_validate_relations`，第 222 行：`ValueError('lateral min_lookahead_m must not exceed max_lookahead_m')`。
- `_validate_relations`，第 224 行：`ValueError('lateral steer delta limits must contain the base value')`。
- `_validate_relations`，第 226 行：`ValueError('lateral min_steer_limit must not exceed max_steer')`。
- `_validate_relations`，第 228 行：`ValueError('lateral.steer_sign must be -1 or 1')`。
- `_validate_relations`，第 231 行：`ValueError('minimum lane offset must not exceed maximum lane offset')`。
- `_validate_relations`，第 233 行：`ValueError('minimum severe deviation must not exceed maximum severe deviation')`。
- `_validate_relations`，第 239 行：`ValueError(f'supervisor.{name} must be <= 1.0')`。
- `load_strategy_config`，第 180 行：`ValueError(f'strategy config must be valid JSON-compatible YAML: {error}')`。
- `load_strategy_config`，第 182 行：`TypeError('strategy config root must be an object')`。
- `load_strategy_config`，第 188 行：`ValueError(f'strategy config fields mismatch; missing={sorted(expected - set(payload))}, unknown={sorted(set(payload) - expected)}')`。
- `load_strategy_config`，第 193 行：`ValueError(f"unsupported strategy schema_version={payload['schema_version']!r}")`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [car_control_A/contracts.py](../../../car_control_A/contracts.py)
- [car_control_B/pure_pursuit.py](../../../car_control_B/pure_pursuit.py)
- [car_control_B/stanley.py](../../../car_control_B/stanley.py)
- [car_control_C/config.py](../../../car_control_C/config.py)
- [car_control_C/following_controller.py](../../../car_control_C/following_controller.py)
- [car_control_C/fusion_tracker.py](../../../car_control_C/fusion_tracker.py)
- [car_control_C/longitudinal_controller.py](../../../car_control_C/longitudinal_controller.py)
- [car_control_C/safety_state.py](../../../car_control_C/safety_state.py)
- [car_control_C/speed_pid.py](../../../car_control_C/speed_pid.py)
- [car_control_C/speed_planner.py](../../../car_control_C/speed_planner.py)
- [car_control_C/stop_controller.py](../../../car_control_C/stop_controller.py)
- [car_control_C/tests/test_strategy_generalization.py](../../../car_control_C/tests/test_strategy_generalization.py)
- [car_control_D/safety_supervisor.py](../../../car_control_D/safety_supervisor.py)
- [integration/carla_runner.py](../../../integration/carla_runner.py)
- [integration/driving_policy.py](../../../integration/driving_policy.py)
- [integration/scenario_evidence.py](../../../integration/scenario_evidence.py)
- [tools/validate_control_generalization.py](../../../tools/validate_control_generalization.py)

## 后续修改需要一起阅读

- [上级模块](../modules/support-config-scenarios.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `config/strategy.py`

来源 SHA256：`14428704c7aa41151bcff450e38aee514c9f0ec6c3f943ccb4646c9792f8085b`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `CommonStrategy.command_confidence_threshold` | `float` | `无声明默认；构造/赋值方提供` |
| `CommonStrategy.standstill_speed_mps` | `float` | `无声明默认；构造/赋值方提供` |
| `CommonStrategy.comfortable_decel_mps2` | `float` | `无声明默认；构造/赋值方提供` |
| `CommonStrategy.max_decel_mps2` | `float` | `无声明默认；构造/赋值方提供` |
| `CommonStrategy.hold_brake` | `float` | `无声明默认；构造/赋值方提供` |
| `CommonStrategy.emergency_brake` | `float` | `无声明默认；构造/赋值方提供` |
| `CommonStrategy.caution_ttc_s` | `float` | `无声明默认；构造/赋值方提供` |
| `CommonStrategy.emergency_ttc_s` | `float` | `无声明默认；构造/赋值方提供` |
| `SafetyDistanceStrategy.standstill_gap_m` | `float` | `无声明默认；构造/赋值方提供` |
| `SafetyDistanceStrategy.reaction_time_s` | `float` | `无声明默认；构造/赋值方提供` |
| `SafetyDistanceStrategy.emergency_reaction_time_s` | `float` | `无声明默认；构造/赋值方提供` |
| `SafetyDistanceStrategy.sensor_base_margin_m` | `float` | `无声明默认；构造/赋值方提供` |
| `SafetyDistanceStrategy.sensor_uncertainty_time_s` | `float` | `无声明默认；构造/赋值方提供` |
| `SafetyDistanceStrategy.curvature_margin_gain` | `float` | `无声明默认；构造/赋值方提供` |
| `SafetyDistanceStrategy.vru_distance_factor` | `float` | `无声明默认；构造/赋值方提供` |
| `SafetyDistanceStrategy.vru_emergency_distance_factor` | `float` | `无声明默认；构造/赋值方提供` |
| `SafetyDistanceStrategy.vru_minimum_emergency_distance_m` | `float` | `无声明默认；构造/赋值方提供` |
| `SafetyDistanceStrategy.large_vehicle_distance_factor` | `float` | `无声明默认；构造/赋值方提供` |
| `SafetyDistanceStrategy.unknown_actor_distance_factor` | `float` | `无声明默认；构造/赋值方提供` |
| `SafetyDistanceStrategy.minimum_emergency_distance_m` | `float` | `无声明默认；构造/赋值方提供` |
| `PerceptionSafetyStrategy.visual_confidence_threshold` | `float` | `无声明默认；构造/赋值方提供` |
| `PerceptionSafetyStrategy.max_observation_gap_s` | `float` | `无声明默认；构造/赋值方提供` |
| `PerceptionSafetyStrategy.vru_caution_speed_cap_mps` | `float` | `无声明默认；构造/赋值方提供` |
| `PerceptionSafetyStrategy.vru_caution_hold_s` | `float` | `无声明默认；构造/赋值方提供` |
| `LongitudinalStrategy.max_lateral_accel_mps2` | `float` | `无声明默认；构造/赋值方提供` |
| `LongitudinalStrategy.command_accel_mps2` | `float` | `无声明默认；构造/赋值方提供` |
| `LongitudinalStrategy.command_decel_mps2` | `float` | `无声明默认；构造/赋值方提供` |
| `LongitudinalStrategy.max_accel_mps2` | `float` | `无声明默认；构造/赋值方提供` |
| `LongitudinalStrategy.max_control_delta_per_s` | `float` | `无声明默认；构造/赋值方提供` |
| `LongitudinalStrategy.creep_speed_mps` | `float` | `无声明默认；构造/赋值方提供` |
| `LongitudinalStrategy.stop_hold_distance_m` | `float` | `无声明默认；构造/赋值方提供` |
| `LongitudinalStrategy.pid_kp` | `float` | `无声明默认；构造/赋值方提供` |
| `LongitudinalStrategy.pid_ki` | `float` | `无声明默认；构造/赋值方提供` |
| `LongitudinalStrategy.pid_kd` | `float` | `无声明默认；构造/赋值方提供` |
| `LongitudinalStrategy.pid_integral_limit` | `float` | `无声明默认；构造/赋值方提供` |
| `LongitudinalStrategy.pid_target_step_reset_mps` | `float` | `无声明默认；构造/赋值方提供` |
| `LateralStrategy.wheel_base_m` | `float` | `无声明默认；构造/赋值方提供` |
| `LateralStrategy.base_lookahead_m` | `float` | `无声明默认；构造/赋值方提供` |
| `LateralStrategy.speed_gain_s` | `float` | `无声明默认；构造/赋值方提供` |
| `LateralStrategy.min_lookahead_m` | `float` | `无声明默认；构造/赋值方提供` |
| `LateralStrategy.max_lookahead_m` | `float` | `无声明默认；构造/赋值方提供` |
| `LateralStrategy.curvature_lookahead_gain` | `float` | `无声明默认；构造/赋值方提供` |
| `LateralStrategy.error_lookahead_gain` | `float` | `无声明默认；构造/赋值方提供` |
| `LateralStrategy.max_steer_angle_rad` | `float` | `无声明默认；构造/赋值方提供` |
| `LateralStrategy.steer_gain` | `float` | `无声明默认；构造/赋值方提供` |
| `LateralStrategy.max_steer` | `float` | `无声明默认；构造/赋值方提供` |
| `LateralStrategy.min_steer_limit` | `float` | `无声明默认；构造/赋值方提供` |
| `LateralStrategy.high_speed_steer_reduction_per_mps` | `float` | `无声明默认；构造/赋值方提供` |
| `LateralStrategy.curvature_steer_gain` | `float` | `无声明默认；构造/赋值方提供` |
| `LateralStrategy.base_steer_delta_per_step` | `float` | `无声明默认；构造/赋值方提供` |
| `LateralStrategy.min_steer_delta_per_step` | `float` | `无声明默认；构造/赋值方提供` |
| `LateralStrategy.max_steer_delta_per_step` | `float` | `无声明默认；构造/赋值方提供` |
| `LateralStrategy.low_speed_steer_gain` | `float` | `无声明默认；构造/赋值方提供` |
| `LateralStrategy.curvature_rate_gain` | `float` | `无声明默认；构造/赋值方提供` |
| `LateralStrategy.error_rate_gain` | `float` | `无声明默认；构造/赋值方提供` |
| `LateralStrategy.stanley_gain` | `float` | `无声明默认；构造/赋值方提供` |
| `LateralStrategy.stanley_softening_speed_mps` | `float` | `无声明默认；构造/赋值方提供` |
| `LateralStrategy.stanley_curvature_gain` | `float` | `无声明默认；构造/赋值方提供` |
| `LateralStrategy.steer_sign` | `float` | `无声明默认；构造/赋值方提供` |
| `SupervisorStrategy.stop_line_guard_m` | `float` | `无声明默认；构造/赋值方提供` |
| `SupervisorStrategy.max_lane_offset_m` | `float` | `无声明默认；构造/赋值方提供` |
| `SupervisorStrategy.minimum_lane_offset_m` | `float` | `无声明默认；构造/赋值方提供` |
| `SupervisorStrategy.severe_route_deviation_m` | `float` | `无声明默认；构造/赋值方提供` |
| `SupervisorStrategy.minimum_severe_route_deviation_m` | `float` | `无声明默认；构造/赋值方提供` |
| `SupervisorStrategy.route_speed_sensitivity` | `float` | `无声明默认；构造/赋值方提供` |
| `SupervisorStrategy.route_curvature_sensitivity` | `float` | `无声明默认；构造/赋值方提供` |
| `SupervisorStrategy.route_recovery_max_speed_mps` | `float` | `无声明默认；构造/赋值方提供` |
| `SupervisorStrategy.route_recovery_throttle` | `float` | `无声明默认；构造/赋值方提供` |
| `SupervisorStrategy.route_recovery_steer_limit` | `float` | `无声明默认；构造/赋值方提供` |
| `SupervisorStrategy.route_deviation_brake` | `float` | `无声明默认；构造/赋值方提供` |
| `SupervisorStrategy.caution_brake` | `float` | `无声明默认；构造/赋值方提供` |
| `SensorFaultStrategy.single_sensor_speed_cap_mps` | `float` | `无声明默认；构造/赋值方提供` |
| `SensorFaultStrategy.speed_cap_tolerance_mps` | `float` | `无声明默认；构造/赋值方提供` |
| `SensorFaultStrategy.speed_cap_base_brake` | `float` | `无声明默认；构造/赋值方提供` |
| `SensorFaultStrategy.speed_cap_brake_gain` | `float` | `无声明默认；构造/赋值方提供` |
| `StrategyConfig.schema_version` | `str` | `无声明默认；构造/赋值方提供` |
| `StrategyConfig.common` | `CommonStrategy` | `无声明默认；构造/赋值方提供` |
| `StrategyConfig.safety_distance` | `SafetyDistanceStrategy` | `无声明默认；构造/赋值方提供` |
| `StrategyConfig.perception_safety` | `PerceptionSafetyStrategy` | `无声明默认；构造/赋值方提供` |
| `StrategyConfig.longitudinal` | `LongitudinalStrategy` | `无声明默认；构造/赋值方提供` |
| `StrategyConfig.lateral` | `LateralStrategy` | `无声明默认；构造/赋值方提供` |
| `StrategyConfig.supervisor` | `SupervisorStrategy` | `无声明默认；构造/赋值方提供` |
| `StrategyConfig.sensor_fault` | `SensorFaultStrategy` | `无声明默认；构造/赋值方提供` |
| `SafetyDistanceEnvelope.caution_distance_m` | `float` | `无声明默认；构造/赋值方提供` |
| `SafetyDistanceEnvelope.emergency_distance_m` | `float` | `无声明默认；构造/赋值方提供` |
| `SafetyDistanceEnvelope.reaction_distance_m` | `float` | `无声明默认；构造/赋值方提供` |
| `SafetyDistanceEnvelope.braking_distance_m` | `float` | `无声明默认；构造/赋值方提供` |
| `SafetyDistanceEnvelope.sensor_margin_m` | `float` | `无声明默认；构造/赋值方提供` |
| `SafetyDistanceEnvelope.curvature_multiplier` | `float` | `无声明默认；构造/赋值方提供` |
| `SafetyDistanceEnvelope.actor_multiplier` | `float` | `无声明默认；构造/赋值方提供` |
| `SafetyDistanceEnvelope.emergency_actor_multiplier` | `float` | `无声明默认；构造/赋值方提供` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `_number` / 24 | `type(value) not in (int, float)` | `raise TypeError(f'{name} must be a number')` |
| `_number` / 27 | `not math.isfinite(number)` | `raise ValueError(f'{name} must be finite')` |
| `_number` / 29 | `positive and number <= 0.0` | `raise ValueError(f'{name} must be positive')` |
| `_number` / 31 | `number < minimum` | `raise ValueError(f'{name} must be >= {minimum}')` |
| `_number` / 33 | `maximum is not None and number > maximum` | `raise ValueError(f'{name} must be <= {maximum}')` |
| `_section` / 157 | `type(payload) is not dict` | `raise TypeError(f'strategy section {name!r} must be an object')` |
| `_section` / 161 | `actual != expected` | `raise ValueError(f'strategy section {name!r} fields mismatch; missing={sorted(expected - actual)}, unknown={sorted(actual - expected)}')` |
| `load_strategy_config` / 180 | `except json.JSONDecodeError` | `raise ValueError(f'strategy config must be valid JSON-compatible YAML: {error}') from error` |
| `load_strategy_config` / 182 | `type(payload) is not dict` | `raise TypeError('strategy config root must be an object')` |
| `load_strategy_config` / 188 | `set(payload) != expected` | `raise ValueError(f'strategy config fields mismatch; missing={sorted(expected - set(payload))}, unknown={sorted(set(payload) - expected)}')` |
| `load_strategy_config` / 193 | `payload['schema_version'] != STRATEGY_SCHEMA_VERSION` | `raise ValueError(f"unsupported strategy schema_version={payload['schema_version']!r}")` |
| `_validate_relations` / 211 | `common.comfortable_decel_mps2 > common.max_decel_mps2` | `raise ValueError('comfortable_decel_mps2 must not exceed max_decel_mps2')` |
| `_validate_relations` / 213 | `common.emergency_ttc_s > common.caution_ttc_s` | `raise ValueError('emergency_ttc_s must not exceed caution_ttc_s')` |
| `_validate_relations` / 216 | `getattr(common, name) > 1.0` | `raise ValueError(f'common.{name} must be <= 1.0')` |
| `_validate_relations` / 219 | `perception.visual_confidence_threshold > 1.0` | `raise ValueError('perception_safety.visual_confidence_threshold must be <= 1.0')` |
| `_validate_relations` / 222 | `lateral.min_lookahead_m > lateral.max_lookahead_m` | `raise ValueError('lateral min_lookahead_m must not exceed max_lookahead_m')` |
| `_validate_relations` / 224 | `not lateral.min_steer_delta_per_step <= lateral.base_steer_delta_per_step <= lateral.max_steer_delta_per_step` | `raise ValueError('lateral steer delta limits must contain the base value')` |
| `_validate_relations` / 226 | `lateral.min_steer_limit > lateral.max_steer` | `raise ValueError('lateral min_steer_limit must not exceed max_steer')` |
| `_validate_relations` / 228 | `lateral.steer_sign not in {-1.0, 1.0}` | `raise ValueError('lateral.steer_sign must be -1 or 1')` |
| `_validate_relations` / 231 | `supervisor.minimum_lane_offset_m > supervisor.max_lane_offset_m` | `raise ValueError('minimum lane offset must not exceed maximum lane offset')` |
| `_validate_relations` / 233 | `supervisor.minimum_severe_route_deviation_m > supervisor.severe_route_deviation_m` | `raise ValueError('minimum severe deviation must not exceed maximum severe deviation')` |
| `_validate_relations` / 239 | `getattr(supervisor, name) > 1.0` | `raise ValueError(f'supervisor.{name} must be <= 1.0')` |

### config/strategy.py 数值检查调用

这里保留校验函数的minimum/positive等参数原文；实际可达性由调用分支决定，函数本体异常仍需看对应helper。

| 行 | 校验调用 |
|---|---|
| 277 | `_number('ego_speed_mps', ego_speed_mps)` |
| 282 | `_number('sensor_margin_scale', sensor_margin_scale)` |
| 166 | `_number(f'{name}.{key}', value, minimum=-1.0 if key == 'steer_sign' else 0.0)` |
| 281 | `_number('curvature_per_m', curvature_per_m, minimum=-math.inf)` |
| 278 | `_number('closing_speed_mps', closing_speed_mps, minimum=-math.inf)` |
