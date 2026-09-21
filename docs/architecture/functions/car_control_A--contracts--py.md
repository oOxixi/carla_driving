# contracts：功能记录

上级模块：[模块说明](../modules/vehicle-behavior.md) · 实现：[car_control_A/contracts.py](../../../car_control_A/contracts.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [授权、确认、过期与停车保持](command-lifecycle.md)
- [前置条件锁存、步骤完成与重规划](maneuver-progress.md)

## 功能职责与范围

Versioned, CARLA-independent contracts shared by A and C.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `RuntimeVehicleState.frame: int`；默认：`未在声明处设置`。
- `RuntimeVehicleState.sim_time_s: float`；默认：`未在声明处设置`。
- `RuntimeVehicleState.speed_mps: float`；默认：`未在声明处设置`。
- `RuntimeVehicleState.x_m: float`；默认：`未在声明处设置`。
- `RuntimeVehicleState.y_m: float`；默认：`未在声明处设置`。
- `RuntimeVehicleState.z_m: float`；默认：`未在声明处设置`。
- `RuntimeVehicleState.yaw_deg: float`；默认：`未在声明处设置`。
- `RuntimeVehicleState.lane_id: str`；默认：`未在声明处设置`。
- `DrivingCommand.command_id: str`；默认：`未在声明处设置`。
- `DrivingCommand.received_at_s: float`；默认：`未在声明处设置`。
- `DrivingCommand.expires_at_s: float`；默认：`未在声明处设置`。
- `DrivingCommand.confidence: float`；默认：`未在声明处设置`。
- `DrivingCommand.action: str`；默认：`未在声明处设置`。
- `DrivingCommand.target_speed_mps: float | None`；默认：`None`。
- `DrivingCommand.is_ambiguous: bool`；默认：`False`。
- `DrivingCommand.confirmation_requested: bool`；默认：`False`。
- `TrafficConstraint.signal_state: SignalState`；默认：`未在声明处设置`。
- `TrafficConstraint.distance_to_stop_line_m: float | None`；默认：`未在声明处设置`。
- `TrafficConstraint.speed_limit_mps: float | None`；默认：`None`。
- `LongitudinalRequest.vehicle: RuntimeVehicleState`；默认：`未在声明处设置`。
- `LongitudinalRequest.requested_speed_mps: float`；默认：`未在声明处设置`。
- `LongitudinalRequest.path_curvature_per_m: float`；默认：`未在声明处设置`。
- `LongitudinalRequest.traffic: TrafficConstraint | None`；默认：`None`。
- `LongitudinalRequest.lead_distance_m: float | None`；默认：`None`。
- `LongitudinalRequest.closing_speed_mps: float | None`；默认：`None`。
- `ControlOutput.throttle: float`；默认：`未在声明处设置`。
- `ControlOutput.brake: float`；默认：`未在声明处设置`。
- `ControlOutput.steer: float`；默认：`0.0`。
- `RiskMetrics.ttc_s: float | None`；默认：`未在声明处设置`。
- `RiskMetrics.desired_gap_m: float`；默认：`未在声明处设置`。
- `RiskMetrics.emergency_brake_requested: bool`；默认：`未在声明处设置`。
- `LongitudinalOutput.control: ControlOutput`；默认：`未在声明处设置`。
- `LongitudinalOutput.target_accel_mps2: float`；默认：`未在声明处设置`。
- `LongitudinalOutput.target_speed_mps: float`；默认：`未在声明处设置`。
- `LongitudinalOutput.state: str`；默认：`未在声明处设置`。
- `LongitudinalOutput.reason: str`；默认：`未在声明处设置`。
- `LongitudinalOutput.risk: RiskMetrics`；默认：`未在声明处设置`。
- `ExecutionFeedback.command_id: str`；默认：`未在声明处设置`。
- `ExecutionFeedback.status: ExecutionStatus`；默认：`未在声明处设置`。
- `ExecutionFeedback.completed_at_s: float`；默认：`未在声明处设置`。
- `ExecutionFeedback.detail: str`；默认：`未在声明处设置`。

## 功能入口：输入、输出与实现说明

<a id="fn--number"></a>

### `_number`

源码位置：[car_control_A/contracts.py 第 23 行](../../../car_control_A/contracts.py#L23)。类型：`FunctionDef`。

```python
_number(name: str, value: object, *, minimum: float | None=None) -> float
```

仅接受exact int/float（因此拒绝bool），转float后要求有限；minimum非None则包含下界检查。返回标准float，不接受数字字符串，单位由字段定义。

<a id="fn--integer"></a>

### `_integer`

源码位置：[car_control_A/contracts.py 第 34 行](../../../car_control_A/contracts.py#L34)。类型：`FunctionDef`。

```python
_integer(name: str, value: object, *, minimum: int | None=None) -> int
```

要求exact int，拒绝bool；minimum非None则检查包含下界，返回原整数。用于frame等索引，不做自动取整。

<a id="fn--text"></a>

### `_text`

源码位置：[car_control_A/contracts.py 第 42 行](../../../car_control_A/contracts.py#L42)。类型：`FunctionDef`。

```python
_text(name: str, value: object) -> str
```

要求exact str且strip后非空，但返回原字符串而非strip结果；前后空白可保留在ID/action/lane_id中，调用方不能假定已规范化。

<a id="fn--boolean"></a>

### `_boolean`

源码位置：[car_control_A/contracts.py 第 48 行](../../../car_control_A/contracts.py#L48)。类型：`FunctionDef`。

```python
_boolean(name: str, value: object) -> bool
```

要求exact bool，拒绝0/1或字符串；返回原值，不进行truthy转换。

<a id="fn--payload"></a>

### `_payload`

源码位置：[car_control_A/contracts.py 第 54 行](../../../car_control_A/contracts.py#L54)。类型：`FunctionDef`。

```python
_payload(payload: object, fields: set[str]) -> dict[str, Any]
```

要求plain dict且键集恰等于指定fields加schema_version，未知/缺失键都报错；版本须exact str且为1.0。返回原dict，不复制；后续from_dict构造器才校验各字段。带默认值的dataclass字段在字典边界仍必须显式提供。

<a id="fn-signalstate"></a>

### `SignalState`

源码位置：[car_control_A/contracts.py 第 67 行](../../../car_control_A/contracts.py#L67)。类型：`ClassDef`。

UNKNOWN deliberately denotes an uncertain perception result.

<a id="fn-runtimevehiclestate"></a>

### `RuntimeVehicleState`

源码位置：[car_control_A/contracts.py 第 77 行](../../../car_control_A/contracts.py#L77)。类型：`ClassDef`。

冻结帧状态：frame、sim_time_s、speed_mps、x/y/z_m、yaw_deg、lane_id。坐标字段只校验有限数，不在此转换CARLA与canonical坐标系；速度是非负模值、yaw为度。

<a id="fn-runtimevehiclestate---post-init--"></a>

### `RuntimeVehicleState.__post_init__`

源码位置：[car_control_A/contracts.py 第 87 行](../../../car_control_A/contracts.py#L87)。类型：`FunctionDef`。

```python
RuntimeVehicleState.__post_init__(self) -> None
```

frame非负exact int；仿真秒和速度有限非负；位置/朝向有限可负；lane_id为非空字符串。通过object.__setattr__规范化数值，不连接CARLA。

<a id="fn-runtimevehiclestate-to-dict"></a>

### `RuntimeVehicleState.to_dict`

源码位置：[car_control_A/contracts.py 第 95 行](../../../car_control_A/contracts.py#L95)。类型：`FunctionDef`。

```python
RuntimeVehicleState.to_dict(self) -> dict[str, object]
```

导出全部帧字段加schema_version=1.0，单位不变；创建新顶层dict，不隐式增加采集时间或传感器来源。

<a id="fn-runtimevehiclestate-from-dict"></a>

### `RuntimeVehicleState.from_dict`

源码位置：[car_control_A/contracts.py 第 101 行](../../../car_control_A/contracts.py#L101)。类型：`FunctionDef`。

```python
RuntimeVehicleState.from_dict(cls, payload: object) -> RuntimeVehicleState
```

先严格检查全部键和版本，再传给构造器执行数值/文本校验；不忽略未知字段，不为缺失坐标补零。

<a id="fn-drivingcommand"></a>

### `DrivingCommand`

源码位置：[car_control_A/contracts.py 第 107 行](../../../car_control_A/contracts.py#L107)。类型：`ClassDef`。

A内部冻结命令，received/expires是仿真秒、target_speed_mps可None；action只要求非空文本，未在契约类限定枚举。不同于canonical JSON DrivingCommand，不能直接以同名互换。

<a id="fn-drivingcommand---post-init--"></a>

### `DrivingCommand.__post_init__`

源码位置：[car_control_A/contracts.py 第 117 行](../../../car_control_A/contracts.py#L117)。类型：`FunctionDef`。

```python
DrivingCommand.__post_init__(self) -> None
```

command_id/action非空；received/expires有限非负且expires>=received（允许相等）；confidence有限[0,1]；非空target_speed有限非负；两个确认标志须bool。只约束结构，不授予车辆执行权或限制最高车速。

<a id="fn-drivingcommand-is-expired-at"></a>

### `DrivingCommand.is_expired_at`

源码位置：[car_control_A/contracts.py 第 135 行](../../../car_control_A/contracts.py#L135)。类型：`FunctionDef`。

```python
DrivingCommand.is_expired_at(self, sim_time_s: float) -> bool
```

sim_time_s须有限非负，比较sim_time_s>=expires_at_s；到期边界包含相等，没有宽限期，也不检查是否早于received_at_s。

<a id="fn-drivingcommand-requires-confirmation"></a>

### `DrivingCommand.requires_confirmation`

源码位置：[car_control_A/contracts.py 第 141 行](../../../car_control_A/contracts.py#L141)。类型：`FunctionDef`。

```python
DrivingCommand.requires_confirmation(self) -> bool
```

confirmation_requested或is_ambiguous为真，或confidence严格小于LOW_CONFIDENCE_THRESHOLD则True；阈值导入自DEFAULT_STRATEGY.common.command_confidence_threshold，当前配置0.80。属性无状态，不因BehaviorFSM.confirm自动改变。

<a id="fn-drivingcommand-to-dict"></a>

### `DrivingCommand.to_dict`

源码位置：[car_control_A/contracts.py 第 144 行](../../../car_control_A/contracts.py#L144)。类型：`FunctionDef`。

```python
DrivingCommand.to_dict(self) -> dict[str, object]
```

输出版本及所有字段，包括target_speed_mps=None和False确认标志；不把expires秒换成deadline纳秒，也不映射action到canonical intent。

<a id="fn-drivingcommand-from-dict"></a>

### `DrivingCommand.from_dict`

源码位置：[car_control_A/contracts.py 第 151 行](../../../car_control_A/contracts.py#L151)。类型：`FunctionDef`。

```python
DrivingCommand.from_dict(cls, payload: object) -> DrivingCommand
```

要求全部8个数据字段加版本，即使可选字段有构造默认也不能在字典中省略；再由构造器校验。未知action文本可通过结构检查，执行支持需外层确认。

<a id="fn-trafficconstraint"></a>

### `TrafficConstraint`

源码位置：[car_control_A/contracts.py 第 157 行](../../../car_control_A/contracts.py#L157)。类型：`ClassDef`。

交通约束容器：SignalState枚举、可空停止线距离m、可空速度上限m/s；UNKNOWN代表不确定感知，不等于GREEN。

<a id="fn-trafficconstraint---post-init--"></a>

### `TrafficConstraint.__post_init__`

源码位置：[car_control_A/contracts.py 第 162 行](../../../car_control_A/contracts.py#L162)。类型：`FunctionDef`。

```python
TrafficConstraint.__post_init__(self) -> None
```

signal_state必须SignalState实例（直接传字符串不接受）；非空distance与speed_limit须有限非负。None保留未知，不补0或默认绿灯。

<a id="fn-trafficconstraint-to-dict"></a>

### `TrafficConstraint.to_dict`

源码位置：[car_control_A/contracts.py 第 170 行](../../../car_control_A/contracts.py#L170)。类型：`FunctionDef`。

```python
TrafficConstraint.to_dict(self) -> dict[str, object]
```

将枚举转字符串，保留两个可空字段并带版本；不推导是否必须停车，停车策略由消费者处理。

<a id="fn-trafficconstraint-from-dict"></a>

### `TrafficConstraint.from_dict`

源码位置：[car_control_A/contracts.py 第 175 行](../../../car_control_A/contracts.py#L175)。类型：`FunctionDef`。

```python
TrafficConstraint.from_dict(cls, payload: object) -> TrafficConstraint
```

plain dict/完整键/版本检查后，signal_state必须字符串并转换枚举；未知枚举抛ValueError，构造器继续检查距离/速度。

<a id="fn-longitudinalrequest"></a>

### `LongitudinalRequest`

源码位置：[car_control_A/contracts.py 第 187 行](../../../car_control_A/contracts.py#L187)。类型：`ClassDef`。

Frame-aligned input for C's longitudinal controller.

``closing_speed_mps = ego_speed_mps - lead_speed_mps``.  A positive value
means the ego vehicle is approaching the lead vehicle; zero or a negative
value must not trigger time-to-collision (TTC) braking calculations.

<a id="fn-longitudinalrequest---post-init--"></a>

### `LongitudinalRequest.__post_init__`

源码位置：[car_control_A/contracts.py 第 202 行](../../../car_control_A/contracts.py#L202)。类型：`FunctionDef`。

```python
LongitudinalRequest.__post_init__(self) -> None
```

vehicle须RuntimeVehicleState；requested_speed有限非负，curvature有限可有符号；traffic须TrafficConstraint或None。lead_distance_m与closing_speed_mps必须同时提供或同时None，距离非负、closing可负（ego-lead），正值才表示追近。

<a id="fn-longitudinalrequest-to-dict"></a>

### `LongitudinalRequest.to_dict`

源码位置：[car_control_A/contracts.py 第 215 行](../../../car_control_A/contracts.py#L215)。类型：`FunctionDef`。

```python
LongitudinalRequest.to_dict(self) -> dict[str, object]
```

递归序列化vehicle与可选traffic为各自带版本dict；保留前车距离/接近速度成对None，不计算TTC或目标加速度。

<a id="fn-longitudinalrequest-from-dict"></a>

### `LongitudinalRequest.from_dict`

源码位置：[car_control_A/contracts.py 第 222 行](../../../car_control_A/contracts.py#L222)。类型：`FunctionDef`。

```python
LongitudinalRequest.from_dict(cls, payload: object) -> LongitudinalRequest
```

严格检查顶层键，vehicle须plain dict、traffic须dict或None；递归各契约from_dict，再校验速度、曲率和前车字段配对，不接受任意对象代替嵌套载荷。

<a id="fn-controloutput"></a>

### `ControlOutput`

源码位置：[car_control_A/contracts.py 第 234 行](../../../car_control_A/contracts.py#L234)。类型：`ClassDef`。

冻结归一化控制量throttle/brake及默认steer=0.0；这个内部契约允许控制量，不代表高层模型接口也可输出它们。

<a id="fn-controloutput---post-init--"></a>

### `ControlOutput.__post_init__`

源码位置：[car_control_A/contracts.py 第 239 行](../../../car_control_A/contracts.py#L239)。类型：`FunctionDef`。

```python
ControlOutput.__post_init__(self) -> None
```

throttle/brake有限[0,1]，steer有限[-1,1]；油门和刹车不能同时>0，否则ValueError。允许二者都0；不检查车辆实际执行状态。

<a id="fn-controloutput-to-dict"></a>

### `ControlOutput.to_dict`

源码位置：[car_control_A/contracts.py 第 253 行](../../../car_control_A/contracts.py#L253)。类型：`FunctionDef`。

```python
ControlOutput.to_dict(self) -> dict[str, object]
```

返回版本与三个归一化浮点量；不转换为CARLA VehicleControl，不调用apply_control。

<a id="fn-controloutput-from-dict"></a>

### `ControlOutput.from_dict`

源码位置：[car_control_A/contracts.py 第 257 行](../../../car_control_A/contracts.py#L257)。类型：`FunctionDef`。

```python
ControlOutput.from_dict(cls, payload: object) -> ControlOutput
```

完整键和版本校验后构造，故字典里steer不能因dataclass默认0而省略；范围和互斥由构造器验证。

<a id="fn-riskmetrics"></a>

### `RiskMetrics`

源码位置：[car_control_A/contracts.py 第 263 行](../../../car_control_A/contracts.py#L263)。类型：`ClassDef`。

风险结果：可空ttc_s、期望间距desired_gap_m、emergency_brake_requested布尔值。ttc未知用None，不能用Infinity绕过严格数值边界。

<a id="fn-riskmetrics---post-init--"></a>

### `RiskMetrics.__post_init__`

源码位置：[car_control_A/contracts.py 第 268 行](../../../car_control_A/contracts.py#L268)。类型：`FunctionDef`。

```python
RiskMetrics.__post_init__(self) -> None
```

非空ttc有限非负，desired_gap有限非负，紧急制动请求须exact bool；并不保证ttc和期望间距符合某个安全模型。

<a id="fn-riskmetrics-to-dict"></a>

### `RiskMetrics.to_dict`

源码位置：[car_control_A/contracts.py 第 274 行](../../../car_control_A/contracts.py#L274)。类型：`FunctionDef`。

```python
RiskMetrics.to_dict(self) -> dict[str, object]
```

输出版本及三个字段，保留None；不自行计算TTC或安全制动强度。

<a id="fn-riskmetrics-from-dict"></a>

### `RiskMetrics.from_dict`

源码位置：[car_control_A/contracts.py 第 279 行](../../../car_control_A/contracts.py#L279)。类型：`FunctionDef`。

```python
RiskMetrics.from_dict(cls, payload: object) -> RiskMetrics
```

完整键与版本校验后构造；非有限ttc、负间距或非bool请求均拒绝，不自动修正风险值。

<a id="fn-longitudinaloutput"></a>

### `LongitudinalOutput`

源码位置：[car_control_A/contracts.py 第 285 行](../../../car_control_A/contracts.py#L285)。类型：`ClassDef`。

C纵向输出，组合ControlOutput、target_accel_mps2、target_speed_mps、state/reason与RiskMetrics；加速度可正负，目标速度是非负模值。

<a id="fn-longitudinaloutput---post-init--"></a>

### `LongitudinalOutput.__post_init__`

源码位置：[car_control_A/contracts.py 第 293 行](../../../car_control_A/contracts.py#L293)。类型：`FunctionDef`。

```python
LongitudinalOutput.__post_init__(self) -> None
```

control/risk必须对应契约实例；加速度有限可负，速度有限非负，state/reason非空文本。state不是此类强制的枚举，语义由C控制器定义。

<a id="fn-longitudinaloutput-to-dict"></a>

### `LongitudinalOutput.to_dict`

源码位置：[car_control_A/contracts.py 第 301 行](../../../car_control_A/contracts.py#L301)。类型：`FunctionDef`。

```python
LongitudinalOutput.to_dict(self) -> dict[str, object]
```

递归导出control/risk及版本，保留目标加速度、速度与解释字段；不是D仲裁后的最终执行证明。

<a id="fn-longitudinaloutput-from-dict"></a>

### `LongitudinalOutput.from_dict`

源码位置：[car_control_A/contracts.py 第 307 行](../../../car_control_A/contracts.py#L307)。类型：`FunctionDef`。

```python
LongitudinalOutput.from_dict(cls, payload: object) -> LongitudinalOutput
```

严格顶层字段和版本，control/risk须plain dict并递归解析；构造后再执行数值和文本校验，不接受已实例化对象代替字典载荷。

<a id="fn-executionstatus"></a>

### `ExecutionStatus`

源码位置：[car_control_A/contracts.py 第 315 行](../../../car_control_A/contracts.py#L315)。类型：`ClassDef`。

六个A内部终态枚举：SUCCEEDED/FAILED/REJECTED/EXPIRED/TIMED_OUT/SAFETY_OVERRIDE。不包含RECEIVED/EXECUTING/CONFIRMING/SUPERSEDED；与canonical反馈和ManeuverFSM状态集合不同。

<a id="fn-executionfeedback"></a>

### `ExecutionFeedback`

源码位置：[car_control_A/contracts.py 第 325 行](../../../car_control_A/contracts.py#L325)。类型：`ClassDef`。

冻结终态反馈，含command_id、ExecutionStatus、completed_at_s仿真秒、非空detail。只有终态，没有逐帧执行中反馈；事件发布/去重由FSM和运行入口负责。

<a id="fn-executionfeedback---post-init--"></a>

### `ExecutionFeedback.__post_init__`

源码位置：[car_control_A/contracts.py 第 331 行](../../../car_control_A/contracts.py#L331)。类型：`FunctionDef`。

```python
ExecutionFeedback.__post_init__(self) -> None
```

command_id/detail非空文本；status必须ExecutionStatus实例；completed_at_s有限非负秒。直接字符串状态需先from_dict转换枚举。

<a id="fn-executionfeedback-is-terminal"></a>

### `ExecutionFeedback.is_terminal`

源码位置：[car_control_A/contracts.py 第 339 行](../../../car_control_A/contracts.py#L339)。类型：`FunctionDef`。

```python
ExecutionFeedback.is_terminal(self) -> bool
```

恒为True，因为该类型枚举仅包含终态；不是通过当前车辆动作计算是否结束。

<a id="fn-executionfeedback-to-dict"></a>

### `ExecutionFeedback.to_dict`

源码位置：[car_control_A/contracts.py 第 342 行](../../../car_control_A/contracts.py#L342)。类型：`FunctionDef`。

```python
ExecutionFeedback.to_dict(self) -> dict[str, object]
```

输出版本，status转枚举值字符串，其余字段不变；没有canonical的terminal_reason/纳秒issued字段，跨边界需适配。

<a id="fn-executionfeedback-from-dict"></a>

### `ExecutionFeedback.from_dict`

源码位置：[car_control_A/contracts.py 第 347 行](../../../car_control_A/contracts.py#L347)。类型：`FunctionDef`。

```python
ExecutionFeedback.from_dict(cls, payload: object) -> ExecutionFeedback
```

plain dict完整键与版本检查，status须字符串且可转换到六终态枚举，然后构造校验ID/秒数/detail；未知或执行中状态拒绝。

## 内部调用与异常路径

- `_number` 调用：`TypeError`, `ValueError`, `float`, `math.isfinite`, `type`.
- `_integer` 调用：`TypeError`, `ValueError`, `type`.
- `_text` 调用：`ValueError`, `type`, `value.strip`.
- `_boolean` 调用：`TypeError`, `type`.
- `_payload` 调用：`TypeError`, `ValueError`, `set`, `sorted`, `type`.
- `__post_init__` 调用：`TypeError`, `ValueError`, `_boolean`, `_integer`, `_number`, `_text`, `getattr`, `isinstance`, `object.__setattr__`.
- `from_dict` 调用：`ControlOutput.from_dict`, `ExecutionStatus`, `RiskMetrics.from_dict`, `RuntimeVehicleState.from_dict`, `SignalState`, `TrafficConstraint.from_dict`, `TypeError`, `ValueError`, `_payload`, `cls`, `type`.
- `is_expired_at` 调用：`_number`.
- `to_dict` 调用：`self.control.to_dict`, `self.risk.to_dict`, `self.traffic.to_dict`, `self.vehicle.to_dict`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__post_init__`，第 124 行：`ValueError('expires_at_s must not precede received_at_s')`。
- `__post_init__`，第 126 行：`ValueError('confidence must be <= 1.0')`。
- `__post_init__`，第 164 行：`TypeError('signal_state must be SignalState')`。
- `__post_init__`，第 204 行：`TypeError('vehicle must be RuntimeVehicleState')`。
- `__post_init__`，第 208 行：`TypeError('traffic must be TrafficConstraint or None')`。
- `__post_init__`，第 210 行：`ValueError('lead_distance_m and closing_speed_mps must be provided together')`。
- `__post_init__`，第 244 行：`ValueError('throttle and brake must be <= 1.0')`。
- `__post_init__`，第 246 行：`ValueError('steer must be in [-1.0, 1.0]')`。
- `__post_init__`，第 248 行：`ValueError('throttle and brake are mutually exclusive')`。
- `__post_init__`，第 295 行：`TypeError('control and risk must use their declared contracts')`。
- `__post_init__`，第 334 行：`TypeError('status must be an ExecutionStatus')`。
- `_boolean`，第 50 行：`TypeError(f'{name} must be bool')`。
- `_integer`，第 36 行：`TypeError(f'{name} must be an int')`。
- `_integer`，第 38 行：`ValueError(f'{name} must be >= {minimum}')`。
- `_number`，第 25 行：`TypeError(f'{name} must be an int or float, not {type(value).__name__}')`。
- `_number`，第 28 行：`ValueError(f'{name} must be finite')`。
- `_number`，第 30 行：`ValueError(f'{name} must be >= {minimum}')`。
- `_payload`，第 56 行：`TypeError('payload must be a plain dict')`。
- `_payload`，第 61 行：`ValueError(f'payload fields mismatch; missing={sorted(missing)}, unknown={sorted(unknown)}')`。
- `_payload`，第 63 行：`ValueError(f"unsupported schema_version: {payload['schema_version']!r}")`。
- `_text`，第 44 行：`ValueError(f'{name} must be a non-empty string')`。
- `from_dict`，第 178 行：`TypeError('signal_state must be a string enum value')`。
- `from_dict`，第 182 行：`ValueError('signal_state is invalid')`。
- `from_dict`，第 225 行：`TypeError('vehicle must be an object')`。
- `from_dict`，第 227 行：`TypeError('traffic must be an object or null')`。
- `from_dict`，第 310 行：`TypeError('control and risk must be objects')`。
- `from_dict`，第 350 行：`TypeError('status must be a string enum value')`。
- `from_dict`，第 354 行：`ValueError('status is invalid')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [compat.py](../../../compat.py)
- [config/strategy.py](../../../config/strategy.py)

静态 import 消费者（含测试）：

- [car_control_A/__init__.py](../../../car_control_A/__init__.py)
- [car_control_A/behavior_fsm.py](../../../car_control_A/behavior_fsm.py)
- [car_control_A/tests/test_behavior_fsm.py](../../../car_control_A/tests/test_behavior_fsm.py)
- [car_control_A/tests/test_contracts.py](../../../car_control_A/tests/test_contracts.py)
- [car_control_A/watchdog.py](../../../car_control_A/watchdog.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-behavior.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

<a id="fn-car-control-a-contracts-py"></a>

### `car_control_A/contracts.py`

来源 SHA256：`ba5628ff0ac255061bc16f4bd59670ad02fbad4b82187cde578ddf801e3ba638`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `RuntimeVehicleState.frame` | `int` | `无声明默认；构造/赋值方提供` |
| `RuntimeVehicleState.sim_time_s` | `float` | `无声明默认；构造/赋值方提供` |
| `RuntimeVehicleState.speed_mps` | `float` | `无声明默认；构造/赋值方提供` |
| `RuntimeVehicleState.x_m` | `float` | `无声明默认；构造/赋值方提供` |
| `RuntimeVehicleState.y_m` | `float` | `无声明默认；构造/赋值方提供` |
| `RuntimeVehicleState.z_m` | `float` | `无声明默认；构造/赋值方提供` |
| `RuntimeVehicleState.yaw_deg` | `float` | `无声明默认；构造/赋值方提供` |
| `RuntimeVehicleState.lane_id` | `str` | `无声明默认；构造/赋值方提供` |
| `DrivingCommand.command_id` | `str` | `无声明默认；构造/赋值方提供` |
| `DrivingCommand.received_at_s` | `float` | `无声明默认；构造/赋值方提供` |
| `DrivingCommand.expires_at_s` | `float` | `无声明默认；构造/赋值方提供` |
| `DrivingCommand.confidence` | `float` | `无声明默认；构造/赋值方提供` |
| `DrivingCommand.action` | `str` | `无声明默认；构造/赋值方提供` |
| `DrivingCommand.target_speed_mps` | `float &#124; None` | `None` |
| `DrivingCommand.is_ambiguous` | `bool` | `False` |
| `DrivingCommand.confirmation_requested` | `bool` | `False` |
| `TrafficConstraint.signal_state` | `SignalState` | `无声明默认；构造/赋值方提供` |
| `TrafficConstraint.distance_to_stop_line_m` | `float &#124; None` | `无声明默认；构造/赋值方提供` |
| `TrafficConstraint.speed_limit_mps` | `float &#124; None` | `None` |
| `LongitudinalRequest.vehicle` | `RuntimeVehicleState` | `无声明默认；构造/赋值方提供` |
| `LongitudinalRequest.requested_speed_mps` | `float` | `无声明默认；构造/赋值方提供` |
| `LongitudinalRequest.path_curvature_per_m` | `float` | `无声明默认；构造/赋值方提供` |
| `LongitudinalRequest.traffic` | `TrafficConstraint &#124; None` | `None` |
| `LongitudinalRequest.lead_distance_m` | `float &#124; None` | `None` |
| `LongitudinalRequest.closing_speed_mps` | `float &#124; None` | `None` |
| `ControlOutput.throttle` | `float` | `无声明默认；构造/赋值方提供` |
| `ControlOutput.brake` | `float` | `无声明默认；构造/赋值方提供` |
| `ControlOutput.steer` | `float` | `0.0` |
| `RiskMetrics.ttc_s` | `float &#124; None` | `无声明默认；构造/赋值方提供` |
| `RiskMetrics.desired_gap_m` | `float` | `无声明默认；构造/赋值方提供` |
| `RiskMetrics.emergency_brake_requested` | `bool` | `无声明默认；构造/赋值方提供` |
| `LongitudinalOutput.control` | `ControlOutput` | `无声明默认；构造/赋值方提供` |
| `LongitudinalOutput.target_accel_mps2` | `float` | `无声明默认；构造/赋值方提供` |
| `LongitudinalOutput.target_speed_mps` | `float` | `无声明默认；构造/赋值方提供` |
| `LongitudinalOutput.state` | `str` | `无声明默认；构造/赋值方提供` |
| `LongitudinalOutput.reason` | `str` | `无声明默认；构造/赋值方提供` |
| `LongitudinalOutput.risk` | `RiskMetrics` | `无声明默认；构造/赋值方提供` |
| `ExecutionFeedback.command_id` | `str` | `无声明默认；构造/赋值方提供` |
| `ExecutionFeedback.status` | `ExecutionStatus` | `无声明默认；构造/赋值方提供` |
| `ExecutionFeedback.completed_at_s` | `float` | `无声明默认；构造/赋值方提供` |
| `ExecutionFeedback.detail` | `str` | `无声明默认；构造/赋值方提供` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `_number` / 25 | `type(value) not in (int, float)` | `raise TypeError(f'{name} must be an int or float, not {type(value).__name__}')` |
| `_number` / 28 | `not math.isfinite(result)` | `raise ValueError(f'{name} must be finite')` |
| `_number` / 30 | `minimum is not None and result < minimum` | `raise ValueError(f'{name} must be >= {minimum}')` |
| `_integer` / 36 | `type(value) is not int` | `raise TypeError(f'{name} must be an int')` |
| `_integer` / 38 | `minimum is not None and value < minimum` | `raise ValueError(f'{name} must be >= {minimum}')` |
| `_text` / 44 | `type(value) is not str or not value.strip()` | `raise ValueError(f'{name} must be a non-empty string')` |
| `_boolean` / 50 | `type(value) is not bool` | `raise TypeError(f'{name} must be bool')` |
| `_payload` / 56 | `type(payload) is not dict` | `raise TypeError('payload must be a plain dict')` |
| `_payload` / 61 | `actual != expected` | `raise ValueError(f'payload fields mismatch; missing={sorted(missing)}, unknown={sorted(unknown)}')` |
| `_payload` / 63 | `type(payload['schema_version']) is not str or payload['schema_version'] != CONTRACT_VERSION` | `raise ValueError(f"unsupported schema_version: {payload['schema_version']!r}")` |
| `DrivingCommand.__post_init__` / 124 | `expires < received` | `raise ValueError('expires_at_s must not precede received_at_s')` |
| `DrivingCommand.__post_init__` / 126 | `confidence > 1.0` | `raise ValueError('confidence must be <= 1.0')` |
| `TrafficConstraint.__post_init__` / 164 | `not isinstance(self.signal_state, SignalState)` | `raise TypeError('signal_state must be SignalState')` |
| `TrafficConstraint.from_dict` / 178 | `type(data['signal_state']) is not str` | `raise TypeError('signal_state must be a string enum value')` |
| `TrafficConstraint.from_dict` / 182 | `except ValueError` | `raise ValueError('signal_state is invalid') from error` |
| `LongitudinalRequest.__post_init__` / 204 | `not isinstance(self.vehicle, RuntimeVehicleState)` | `raise TypeError('vehicle must be RuntimeVehicleState')` |
| `LongitudinalRequest.__post_init__` / 208 | `self.traffic is not None and (not isinstance(self.traffic, TrafficConstraint))` | `raise TypeError('traffic must be TrafficConstraint or None')` |
| `LongitudinalRequest.__post_init__` / 210 | `(self.lead_distance_m is None) != (self.closing_speed_mps is None)` | `raise ValueError('lead_distance_m and closing_speed_mps must be provided together')` |
| `LongitudinalRequest.from_dict` / 225 | `type(data['vehicle']) is not dict` | `raise TypeError('vehicle must be an object')` |
| `LongitudinalRequest.from_dict` / 227 | `data['traffic'] is not None and type(data['traffic']) is not dict` | `raise TypeError('traffic must be an object or null')` |
| `ControlOutput.__post_init__` / 244 | `throttle > 1.0 or brake > 1.0` | `raise ValueError('throttle and brake must be <= 1.0')` |
| `ControlOutput.__post_init__` / 246 | `not -1.0 <= steer <= 1.0` | `raise ValueError('steer must be in [-1.0, 1.0]')` |
| `ControlOutput.__post_init__` / 248 | `throttle > 0.0 and brake > 0.0` | `raise ValueError('throttle and brake are mutually exclusive')` |
| `LongitudinalOutput.__post_init__` / 295 | `not isinstance(self.control, ControlOutput) or not isinstance(self.risk, RiskMetrics)` | `raise TypeError('control and risk must use their declared contracts')` |
| `LongitudinalOutput.from_dict` / 310 | `type(data['control']) is not dict or type(data['risk']) is not dict` | `raise TypeError('control and risk must be objects')` |
| `ExecutionFeedback.__post_init__` / 334 | `not isinstance(self.status, ExecutionStatus)` | `raise TypeError('status must be an ExecutionStatus')` |
| `ExecutionFeedback.from_dict` / 350 | `type(data['status']) is not str` | `raise TypeError('status must be a string enum value')` |
| `ExecutionFeedback.from_dict` / 354 | `except ValueError` | `raise ValueError('status is invalid') from error` |

### car_control_A/contracts.py 数值检查调用

这里保留校验函数的minimum/positive等参数原文；实际可达性由调用分支决定，函数本体异常仍需看对应helper。

| 行 | 校验调用 |
|---|---|
| 120 | `_number('received_at_s', self.received_at_s, minimum=0.0)` |
| 121 | `_number('expires_at_s', self.expires_at_s, minimum=0.0)` |
| 122 | `_number('confidence', self.confidence, minimum=0.0)` |
| 240 | `_number('throttle', self.throttle, minimum=0.0)` |
| 241 | `_number('brake', self.brake, minimum=0.0)` |
| 242 | `_number('steer', self.steer)` |
| 89 | `_number('sim_time_s', self.sim_time_s, minimum=0.0)` |
| 90 | `_number('speed_mps', self.speed_mps, minimum=0.0)` |
| 138 | `_number('sim_time_s', sim_time_s, minimum=0.0)` |
| 205 | `_number('requested_speed_mps', self.requested_speed_mps, minimum=0.0)` |
| 206 | `_number('path_curvature_per_m', self.path_curvature_per_m)` |
| 271 | `_number('desired_gap_m', self.desired_gap_m, minimum=0.0)` |
| 296 | `_number('target_accel_mps2', self.target_accel_mps2)` |
| 297 | `_number('target_speed_mps', self.target_speed_mps, minimum=0.0)` |
| 335 | `_number('completed_at_s', self.completed_at_s, minimum=0.0)` |
| 92 | `_number(name, getattr(self, name))` |
| 128 | `_number('target_speed_mps', self.target_speed_mps, minimum=0.0)` |
| 166 | `_number('distance_to_stop_line_m', self.distance_to_stop_line_m, minimum=0.0)` |
| 168 | `_number('speed_limit_mps', self.speed_limit_mps, minimum=0.0)` |
| 212 | `_number('lead_distance_m', self.lead_distance_m, minimum=0.0)` |
| 213 | `_number('closing_speed_mps', self.closing_speed_mps)` |
| 270 | `_number('ttc_s', self.ttc_s, minimum=0.0)` |
