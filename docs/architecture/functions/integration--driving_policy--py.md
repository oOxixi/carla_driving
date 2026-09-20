# driving_policy：功能记录

上级模块：[模块说明](../modules/vehicle-entry.md) · 实现：[integration/driving_policy.py](../../../integration/driving_policy.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [一帧控制的实际顺序与执行值](control-frame.md)

## 功能职责与范围

Single validated policy source shared by perception and safety.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `DrivingPolicy.source_path: Path`；默认：`未在声明处设置`。
- `DrivingPolicy.perception: Mapping[str, object]`；默认：`未在声明处设置`。
- `DrivingPolicy.safety: Mapping[str, object]`；默认：`未在声明处设置`。

## 功能入口：输入、输出与实现说明

<a id="fn--number"></a>

### `_number`

源码位置：[integration/driving_policy.py 第 18 行](../../../integration/driving_policy.py#L18)。类型：`FunctionDef`。

```python
_number(values: Mapping[str, object], name: str, *, minimum: float=0.0) -> float
```

从mapping取name，精确接受int/float并拒绝bool；转float后必须有限且>=minimum（默认0）。缺键/非数抛TypeError，越界/NaN/Inf抛ValueError；返回归一化float。

<a id="fn-drivingpolicy"></a>

### `DrivingPolicy`

源码位置：[integration/driving_policy.py 第 29 行](../../../integration/driving_policy.py#L29)。类型：`ClassDef`。

保存解析后的source_path以及perception/safety两组mapping；冻结仅作用于dataclass字段，内部字典仍可变。perception_parameters和safety_config是从文件配置生成实际C/D参数的入口，不直接控制车辆。

<a id="fn-drivingpolicy-perception-parameters"></a>

### `DrivingPolicy.perception_parameters`

源码位置：[integration/driving_policy.py 第 34 行](../../../integration/driving_policy.py#L34)。类型：`FunctionDef`。

```python
DrivingPolicy.perception_parameters(self, *, visual_confidence_override: float | None=None) -> SafetyStateParameters
```

将perception键逐项交给_number，构造SafetyStateParameters。visual_confidence_override非None时直接float转换并替换文件阈值；VRU距离floor、时间窗、速度余量、反应时间及减速度依文件，减速度_number下限0.001。最终范围还受SafetyStateParameters构造校验。

<a id="fn-drivingpolicy-safety-config"></a>

### `DrivingPolicy.safety_config`

源码位置：[integration/driving_policy.py 第 62 行](../../../integration/driving_policy.py#L62)。类型：`FunctionDef`。

```python
DrivingPolicy.safety_config(self, *, route_deviation_override_m: float | None=None, stop_line_guard_override_m: float | None=None) -> SafetyConfig
```

从safety生成SafetyConfig：route_deviation_override_m和stop_line_guard_override_m非None时替代文件对应值；maximum_lane_offset=min(文件最大偏移,最终route deviation)。minimum_lane_offset和minimum_severe_route_deviation再与DEFAULT_STRATEGY对应下限取min。未显式传入的SafetyConfig字段沿用类默认，因此改policy不等于改全部D参数。

<a id="fn-load-driving-policy"></a>

### `load_driving_policy`

源码位置：[integration/driving_policy.py 第 102 行](../../../integration/driving_policy.py#L102)。类型：`FunctionDef`。

```python
load_driving_policy(path: str | Path | None=None) -> DrivingPolicy
```

path=None读取仓库config/driving_policy.json；显式路径expanduser并resolve。JSON根必须dict且schema_version恰为1.0，perception/safety必须dict。构造后立即调用两组参数方法验证默认装载路径，返回policy；不缓存、也不写文件。

## 内部调用与异常路径

- `_number` 调用：`TypeError`, `ValueError`, `float`, `isinstance`, `math.isfinite`, `type`, `values.get`.
- `load_driving_policy` 调用：`DrivingPolicy`, `Path`, `Path(path).expanduser`, `Path(path).expanduser().resolve`, `TypeError`, `ValueError`, `dict`, `isinstance`, `json.loads`, `policy.perception_parameters`, `policy.safety_config`, `raw.get`, `source.read_text`.
- `perception_parameters` 调用：`SafetyStateParameters`, `_number`, `float`.
- `safety_config` 调用：`SafetyConfig`, `_number`, `float`, `min`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `_number`，第 21 行：`TypeError(f'policy {name} must be a number')`。
- `_number`，第 24 行：`ValueError(f'policy {name} must be finite and >= {minimum}')`。
- `load_driving_policy`，第 106 行：`ValueError("driving policy schema_version must be '1.0'")`。
- `load_driving_policy`，第 109 行：`TypeError('driving policy perception and safety must be objects')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [car_control_C/safety_state.py](../../../car_control_C/safety_state.py)
- [car_control_D/safety_supervisor.py](../../../car_control_D/safety_supervisor.py)
- [config/strategy.py](../../../config/strategy.py)

静态 import 消费者（含测试）：

- [integration/carla_runner.py](../../../integration/carla_runner.py)
- [integration/tests/test_driving_policy.py](../../../integration/tests/test_driving_policy.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-entry.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

<a id="fn-integration-driving-policy-py"></a>

### `integration/driving_policy.py`

来源 SHA256：`628dd367f8071e2b4f36a3f78654885a464ee91177cfb8c8e0441a637b071026`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `DrivingPolicy.source_path` | `Path` | `无声明默认；构造/赋值方提供` |
| `DrivingPolicy.perception` | `Mapping[str, object]` | `无声明默认；构造/赋值方提供` |
| `DrivingPolicy.safety` | `Mapping[str, object]` | `无声明默认；构造/赋值方提供` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `_number` / 21 | `type(value) not in (int, float) or isinstance(value, bool)` | `raise TypeError(f'policy {name} must be a number')` |
| `_number` / 24 | `not math.isfinite(result) or result < minimum` | `raise ValueError(f'policy {name} must be finite and >= {minimum}')` |
| `load_driving_policy` / 106 | `not isinstance(raw, dict) or raw.get('schema_version') != '1.0'` | `raise ValueError("driving policy schema_version must be '1.0'")` |
| `load_driving_policy` / 109 | `not isinstance(perception, dict) or not isinstance(safety, dict)` | `raise TypeError('driving policy perception and safety must be objects')` |

### integration/driving_policy.py 数值检查调用

这里保留校验函数的minimum/positive等参数原文；实际可达性由调用分支决定，函数本体异常仍需看对应helper。

| 行 | 校验调用 |
|---|---|
| 70 | `_number(s, 'severe_route_deviation_m')` |
| 74 | `_number(s, 'maximum_lane_offset_m')` |
| 43 | `_number(p, 'caution_distance_floor_m')` |
| 44 | `_number(p, 'emergency_distance_floor_m')` |
| 45 | `_number(p, 'vru_caution_distance_floor_m')` |
| 46 | `_number(p, 'vru_emergency_distance_floor_m')` |
| 47 | `_number(p, 'vru_caution_speed_cap_mps')` |
| 48 | `_number(p, 'vru_caution_hold_s')` |
| 49 | `_number(p, 'caution_ttc_s')` |
| 50 | `_number(p, 'emergency_ttc_s')` |
| 51 | `_number(p, 'max_observation_gap_s')` |
| 52 | `_number(p, 'untracked_approach_speed_margin_mps')` |
| 55 | `_number(p, 'reaction_time_s')` |
| 56 | `_number(p, 'emergency_reaction_time_s')` |
| 57 | `_number(p, 'comfortable_deceleration_mps2', minimum=0.001)` |
| 58 | `_number(p, 'emergency_deceleration_mps2', minimum=0.001)` |
| 59 | `_number(p, 'range_uncertainty_buffer_m')` |
| 77 | `_number(s, 'minimum_front_distance_floor_m')` |
| 78 | `_number(s, 'low_ttc_s')` |
| 79 | `_number(s, 'caution_ttc_s')` |
| 94 | `_number(s, 'route_recovery_max_speed_mps')` |
| 95 | `_number(s, 'low_confidence_threshold')` |
| 96 | `_number(s, 'emergency_reaction_time_s')` |
| 97 | `_number(s, 'emergency_deceleration_mps2', minimum=0.001)` |
| 98 | `_number(s, 'range_uncertainty_buffer_m')` |
| 40 | `_number(p, 'visual_confidence_threshold')` |
| 81 | `_number(s, 'stop_line_guard_m')` |
