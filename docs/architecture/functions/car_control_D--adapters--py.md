# adapters：功能记录

上级模块：[模块说明](../modules/vehicle-safety.md) · 实现：[car_control_D/adapters.py](../../../car_control_D/adapters.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [C/D分工与实时仲裁](longitudinal-safety-contract.md)
- [安全覆盖的生命周期影响](control-frame.md)

## 功能职责与范围

Adapters that accept dicts or A/C dataclasses and convert them to D views.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

本文件没有静态类字段声明。输入对象字段需结合所属模块指向的 Schema、类型定义和调用方读取。

## 功能入口：输入、输出与实现说明

### `_as_mapping`

源码位置：[car_control_D/adapters.py 第 11 行](../../../car_control_D/adapters.py#L11)。类型：`FunctionDef`。

```python
_as_mapping(obj: Any) -> Dict[str, Any]
```

把异构输入收敛为普通字典：`None` 返回空字典，`dict` 浅拷贝，dataclass 使用 `asdict`，带 `to_dict()` 的对象调用该方法；其余对象枚举公开、非 callable 属性。最后一种反射路径会执行属性 getter，异常不会在此吞掉，且嵌套可变值并非深拷贝。

### `optional_float`

源码位置：[car_control_D/adapters.py 第 23 行](../../../car_control_D/adapters.py#L23)。类型：`FunctionDef`。

```python
optional_float(value: Any) -> Optional[float]
```

将可选标量转换为有限 `float`；`None` 原样保留，布尔值、无法转换的值和 `NaN/Inf` 抛 `ValueError`。该函数不检查业务量纲或正负范围，距离、速度等限制由具体 adapter 继续执行。

### `_get`

源码位置：[car_control_D/adapters.py 第 34 行](../../../car_control_D/adapters.py#L34)。类型：`FunctionDef`。

```python
_get(d: Dict[str, Any], *names: str, default: Any=None) -> Any
```

按给定别名顺序返回 mapping 中第一个“存在的键”的值，否则返回 `default`。显式值 `None` 仍会命中，不会继续回退到后续别名；调用方随后决定是否允许 `None`。

### `adapt_control`

源码位置：[car_control_D/adapters.py 第 41 行](../../../car_control_D/adapters.py#L41)。类型：`FunctionDef`。

```python
adapt_control(obj: Any) -> ControlOutput
```

把 mapping/dataclass/对象的 `throttle`、`brake`、`steer` 转成 `ControlOutput`；缺失或 `None` 以 `0.0` 处理，非有限值和布尔值由 `optional_float` 拒绝。这里只做形状和数值转换，不检查控制范围或油门制动冲突，必须再经过 `validate_control`。

### `adapt_command`

源码位置：[car_control_D/adapters.py 第 50 行](../../../car_control_D/adapters.py#L50)。类型：`FunctionDef`。

```python
adapt_command(obj: Any) -> CommandView
```

将命令别名归一到 `CommandView`：字符串状态转大写，`confidence`/`intent_confidence` 互作后备，`parameters` 复制为字典，错误和警告复制为列表，缺失有效期取 5 秒。该入口不证明 intent、schema 或参数组合合法，后续由 `validate_command` 决定拒绝或告警。

### `adapt_vehicle_state`

源码位置：[car_control_D/adapters.py 第 75 行](../../../car_control_D/adapters.py#L75)。类型：`FunctionDef`。

```python
adapt_vehicle_state(obj: Any) -> VehicleStateView
```

把车辆状态及兼容别名转换成 `VehicleStateView`。速度、前向距离、停止线距离和传感器裕量不得为负，灯态被规范为大写且必须属于 `RED/YELLOW/GREEN/OFF/UNKNOWN`；其余坐标、偏移和曲率只要求有限。碰撞、闯灯和压线字段用 Python `bool()` 转换，字符串 `"false"` 因而会成为真值，调用者应传真实布尔量。

### `adapt_risk`

源码位置：[car_control_D/adapters.py 第 118 行](../../../car_control_D/adapters.py#L118)。类型：`FunctionDef`。

```python
adapt_risk(obj: Any) -> RiskView
```

把 TTC、期望间距和紧急制动标志转换成 `RiskView`，接受 `time_to_collision_s`/`safe_distance_m` 等别名。TTC 与间距允许缺失但不得为负，标志使用 `bool()`；本函数不验证风险值与车辆距离、速度是否物理一致。

## 内部调用与异常路径

- `_as_mapping` 调用：`asdict`, `callable`, `dict`, `dir`, `getattr`, `hasattr`, `is_dataclass`, `isinstance`, `k.startswith`, `obj.to_dict`.
- `optional_float` 调用：`ValueError`, `float`, `isinstance`, `math.isfinite`.
- `adapt_control` 调用：`ControlOutput`, `_as_mapping`, `_get`, `optional_float`.
- `adapt_command` 调用：`CommandView`, `_as_mapping`, `bool`, `d.get`, `dict`, `list`, `optional_float`, `str`, `str(d.get('ambiguity_type', 'NONE')).upper`, `str(d.get('intent', 'UNKNOWN')).upper`.
- `adapt_vehicle_state` 调用：`ValueError`, `VehicleStateView`, `_as_mapping`, `_get`, `bool`, `int`, `optional_float`, `str`, `str(_get(d, 'front_actor_type', 'object_class')).strip`, `str(_get(d, 'front_actor_type', 'object_class')).strip().upper`, `str(_get(d, 'traffic_light', 'signal_state', default='UNKNOWN')).upper`.
- `adapt_risk` 调用：`RiskView`, `_as_mapping`, `_get`, `bool`, `optional_float`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `adapt_vehicle_state`，第 79 行：`ValueError('traffic_light must be RED/YELLOW/GREEN/UNKNOWN')`。
- `adapt_vehicle_state`，第 85 行：`ValueError('speed_mps must be non-negative')`。
- `adapt_vehicle_state`，第 87 行：`ValueError('front_distance_m must be non-negative')`。
- `adapt_vehicle_state`，第 89 行：`ValueError('distance_to_stop_line_m must be non-negative')`。
- `adapt_vehicle_state`，第 91 行：`ValueError('sensor_margin_scale must be non-negative')`。
- `optional_float`，第 27 行：`ValueError('bool is not a float')`。
- `optional_float`，第 30 行：`ValueError('non-finite float')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [car_control_D/schemas.py](../../../car_control_D/schemas.py)

静态 import 消费者（含测试）：

- [car_control_D/safety_supervisor.py](../../../car_control_D/safety_supervisor.py)
- [car_control_D/tests/test_validators.py](../../../car_control_D/tests/test_validators.py)
- [car_control_D/validators.py](../../../car_control_D/validators.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-safety.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `car_control_D/adapters.py`

来源 SHA256：`251f39f53bc721d4a493bec44a46ff1a0ca34fc8c9b7ec7d65fef7a9924345ee`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `optional_float` / 27 | `isinstance(value, bool)` | `raise ValueError('bool is not a float')` |
| `optional_float` / 30 | `not math.isfinite(f)` | `raise ValueError('non-finite float')` |
| `adapt_vehicle_state` / 79 | `traffic_light not in {'RED', 'YELLOW', 'GREEN', 'UNKNOWN'}` | `raise ValueError('traffic_light must be RED/YELLOW/GREEN/UNKNOWN')` |
| `adapt_vehicle_state` / 85 | `speed_mps < 0.0` | `raise ValueError('speed_mps must be non-negative')` |
| `adapt_vehicle_state` / 87 | `front_distance_m is not None and front_distance_m < 0.0` | `raise ValueError('front_distance_m must be non-negative')` |
| `adapt_vehicle_state` / 89 | `stop_distance_m is not None and stop_distance_m < 0.0` | `raise ValueError('distance_to_stop_line_m must be non-negative')` |
| `adapt_vehicle_state` / 91 | `sensor_margin_scale is None or sensor_margin_scale < 0.0` | `raise ValueError('sensor_margin_scale must be non-negative')` |
