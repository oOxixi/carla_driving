# schemas：功能记录

上级模块：[模块说明](../modules/vehicle-safety.md) · 实现：[car_control_D/schemas.py](../../../car_control_D/schemas.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [C/D分工与实时仲裁](longitudinal-safety-contract.md)
- [安全覆盖的生命周期影响](control-frame.md)

## 功能职责与范围

Shared data structures for D: safety arbitration, scoring and evidence.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `ControlOutput.throttle: float`；默认：`未在声明处设置`。
- `ControlOutput.brake: float`；默认：`未在声明处设置`。
- `ControlOutput.steer: float`；默认：`0.0`。
- `CommandView.schema_version: str`；默认：`未在声明处设置`。
- `CommandView.command_id: str`；默认：`未在声明处设置`。
- `CommandView.source_text: str`；默认：`未在声明处设置`。
- `CommandView.intent: str`；默认：`未在声明处设置`。
- `CommandView.parameters: Dict[str, Any]`；默认：`field(default_factory=dict)`。
- `CommandView.asr_confidence: Optional[float]`；默认：`None`。
- `CommandView.intent_confidence: float`；默认：`1.0`。
- `CommandView.status: str`；默认：`'valid'`。
- `CommandView.ambiguity_type: str`；默认：`'NONE'`。
- `CommandView.confirm_required: bool`；默认：`False`。
- `CommandView.errors: List[str]`；默认：`field(default_factory=list)`。
- `CommandView.warnings: List[str]`；默认：`field(default_factory=list)`。
- `CommandView.confidence: float`；默认：`1.0`。
- `CommandView.t_audio_start_ns: Optional[int]`；默认：`None`。
- `CommandView.t_asr_end_ns: Optional[int]`；默认：`None`。
- `CommandView.t_intent_end_ns: Optional[int]`；默认：`None`。
- `CommandView.valid_duration_s: float`；默认：`5.0`。
- `VehicleStateView.frame: int`；默认：`0`。
- `VehicleStateView.sim_time_s: float`；默认：`0.0`。
- `VehicleStateView.speed_mps: float`；默认：`0.0`。
- `VehicleStateView.x_m: float`；默认：`0.0`。
- `VehicleStateView.y_m: float`；默认：`0.0`。
- `VehicleStateView.z_m: float`；默认：`0.0`。
- `VehicleStateView.yaw_deg: float`；默认：`0.0`。
- `VehicleStateView.lane_id: int`；默认：`0`。
- `VehicleStateView.front_distance_m: Optional[float]`；默认：`None`。
- `VehicleStateView.distance_to_stop_line_m: Optional[float]`；默认：`None`。
- `VehicleStateView.traffic_light: str`；默认：`'UNKNOWN'`。
- `VehicleStateView.lane_offset_m: Optional[float]`；默认：`None`。
- `VehicleStateView.route_deviation_m: Optional[float]`；默认：`None`。
- `VehicleStateView.road_curvature_per_m: float`；默认：`0.0`。
- `VehicleStateView.front_actor_type: Optional[str]`；默认：`None`。
- `VehicleStateView.sensor_margin_scale: float`；默认：`1.0`。
- `VehicleStateView.collision: bool`；默认：`False`。
- `VehicleStateView.red_light_violation: bool`；默认：`False`。
- `VehicleStateView.lane_invasion: bool`；默认：`False`。
- `RiskView.ttc_s: Optional[float]`；默认：`None`。
- `RiskView.desired_gap_m: Optional[float]`；默认：`None`。
- `RiskView.emergency_brake_requested: bool`；默认：`False`。
- `SafetyDecision.final_control: ControlOutput`；默认：`未在声明处设置`。
- `SafetyDecision.safety_override: bool`；默认：`未在声明处设置`。
- `SafetyDecision.reason: str`；默认：`'NONE'`。
- `SafetyDecision.risk_metrics: Dict[str, Any]`；默认：`field(default_factory=dict)`。
- `SafetyDecision.raw_control: Optional[ControlOutput]`；默认：`None`。
- `SafetyDecision.reason_category: str`；默认：`'NONE'`。
- `ValidationResult.valid: bool`；默认：`未在声明处设置`。
- `ValidationResult.errors: List[str]`；默认：`field(default_factory=list)`。
- `ValidationResult.warnings: List[str]`；默认：`field(default_factory=list)`。
- `ScenarioResult.scenario_id: str`；默认：`未在声明处设置`。
- `ScenarioResult.difficulty: str`；默认：`未在声明处设置`。
- `ScenarioResult.status: str`；默认：`未在声明处设置`。
- `ScenarioResult.collision_count: int`；默认：`0`。
- `ScenarioResult.red_light_violation_count: int`；默认：`0`。
- `ScenarioResult.route_deviation_count: int`；默认：`0`。
- `ScenarioResult.unfinished_task_count: int`；默认：`0`。
- `ScenarioResult.safety_override_count: int`；默认：`0`。
- `ScenarioResult.command_count: int`；默认：`0`。
- `ScenarioResult.e2e_latency_ms: Optional[float]`；默认：`None`。
- `ScenarioResult.events: List[Dict[str, Any]]`；默认：`field(default_factory=list)`。

## 功能入口：输入、输出与实现说明

### `ControlOutput`

源码位置：[car_control_D/schemas.py 第 38 行](../../../car_control_D/schemas.py#L38)。类型：`ClassDef`。

冻结的三轴控制值容器：油门、制动和转向（默认 0）。构造本身不限制类型、有限性、范围或油门制动冲突；边界由 adapter/validator/supervisor 执行。

### `ControlOutput.to_dict`

源码位置：[car_control_D/schemas.py 第 43 行](../../../car_control_D/schemas.py#L43)。类型：`FunctionDef`。

```python
ControlOutput.to_dict(self) -> Dict[str, Any]
```

用 `asdict` 返回三个控制字段的普通字典，不做归一化或再次验证。

### `CommandView`

源码位置：[car_control_D/schemas.py 第 48 行](../../../car_control_D/schemas.py#L48)。类型：`ClassDef`。

D 仲裁使用的冻结命令视图，包含 schema/ID/原文/intent、参数、两类置信度、歧义/确认、错误告警、语音阶段纳秒时间和有效秒数。内部 list/dict 仍可变；直接构造不验证 intent、置信范围或时间顺序。

### `CommandView.to_dict`

源码位置：[car_control_D/schemas.py 第 67 行](../../../car_control_D/schemas.py#L67)。类型：`FunctionDef`。

```python
CommandView.to_dict(self) -> Dict[str, Any]
```

递归复制为普通字典，包括 parameters、errors 和 warnings；不附加版本升级或字段别名。

### `VehicleStateView`

源码位置：[car_control_D/schemas.py 第 72 行](../../../car_control_D/schemas.py#L72)。类型：`ClassDef`。

D 使用的冻结车辆状态投影，速度/坐标/距离单位为 m、m/s、仿真秒，曲率为 1/m；同时携带灯态、路线/车道偏差、前车类型、传感器裕量和三类安全事实。默认表示静止且大部分风险量缺测，不表示传感器已健康。

### `VehicleStateView.to_dict`

源码位置：[car_control_D/schemas.py 第 93 行](../../../car_control_D/schemas.py#L93)。类型：`FunctionDef`。

```python
VehicleStateView.to_dict(self) -> Dict[str, Any]
```

通过 `asdict` 输出当前所有车辆状态字段；不标注测量来源、置信度或缺测原因。

### `RiskView`

源码位置：[car_control_D/schemas.py 第 98 行](../../../car_control_D/schemas.py#L98)。类型：`ClassDef`。

冻结风险摘要，TTC 单位秒、期望间距单位米，并可请求紧急制动。两个数值可为 `None`；直接构造不校验负数、有限性或与车辆状态一致性。

### `RiskView.to_dict`

源码位置：[car_control_D/schemas.py 第 103 行](../../../car_control_D/schemas.py#L103)。类型：`FunctionDef`。

```python
RiskView.to_dict(self) -> Dict[str, Any]
```

返回风险字段普通字典，保留 `None`，不派生风险等级。

### `SafetyDecision`

源码位置：[car_control_D/schemas.py 第 108 行](../../../car_control_D/schemas.py#L108)。类型：`ClassDef`。

冻结的仲裁结果，包含最终控制、是否覆盖、原因/类别、风险指标及可选原始控制。`risk_metrics` 仍是可变字典；直接构造不能保证 override 与 reason/control 一致，应优先由 supervisor 生成。

### `SafetyDecision.to_dict`

源码位置：[car_control_D/schemas.py 第 116 行](../../../car_control_D/schemas.py#L116)。类型：`FunctionDef`。

```python
SafetyDecision.to_dict(self) -> Dict[str, Any]
```

用 `asdict` 递归展开嵌套 `ControlOutput` 和风险指标，返回可序列化性仍取决于调用方放入 metrics 的值。

### `ValidationResult`

源码位置：[car_control_D/schemas.py 第 122 行](../../../car_control_D/schemas.py#L122)。类型：`ClassDef`。

冻结的校验摘要，区分布尔 valid、错误和告警；内部列表仍可变。约定上告警不使 valid 变假，但 dataclass 本身不强制 valid 与 errors 一致。

### `ValidationResult.to_dict`

源码位置：[car_control_D/schemas.py 第 127 行](../../../car_control_D/schemas.py#L127)。类型：`FunctionDef`。

```python
ValidationResult.to_dict(self) -> Dict[str, Any]
```

递归复制 valid/errors/warnings 为普通字典，不改变校验结论。

### `ScenarioResult`

源码位置：[car_control_D/schemas.py 第 132 行](../../../car_control_D/schemas.py#L132)。类型：`ClassDef`。

可变的开发计分输入，保存场景身份、难度、状态、各事件/命令计数、可选端到端毫秒和事件列表。构造不限制状态枚举、非负计数或身份格式，不等于正式场景结果 schema。

### `ScenarioResult.to_dict`

源码位置：[car_control_D/schemas.py 第 145 行](../../../car_control_D/schemas.py#L145)。类型：`FunctionDef`。

```python
ScenarioResult.to_dict(self) -> Dict[str, Any]
```

用 `asdict` 递归复制场景结果及事件列表；不计算得分、不验证终态或冻结运行 provenance。

## 内部调用与异常路径

- `to_dict` 调用：`asdict`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- 未发现显式 raise；不代表运行不会失败。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- 无可直接解析的项目内 import；脚本/Schema 的消费者由模块文档补充。

静态 import 消费者（含测试）：

- [car_control_D/__init__.py](../../../car_control_D/__init__.py)
- [car_control_D/adapters.py](../../../car_control_D/adapters.py)
- [car_control_D/control_runtime.py](../../../car_control_D/control_runtime.py)
- [car_control_D/safety_supervisor.py](../../../car_control_D/safety_supervisor.py)
- [car_control_D/validators.py](../../../car_control_D/validators.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-safety.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `car_control_D/schemas.py`

来源 SHA256：`a4bd560ee89db4744cceef73ce98cb007ce3c849d0d795e0842d2a3103b54105`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `ControlOutput.throttle` | `float` | `无声明默认；构造/赋值方提供` |
| `ControlOutput.brake` | `float` | `无声明默认；构造/赋值方提供` |
| `ControlOutput.steer` | `float` | `0.0` |
| `CommandView.schema_version` | `str` | `无声明默认；构造/赋值方提供` |
| `CommandView.command_id` | `str` | `无声明默认；构造/赋值方提供` |
| `CommandView.source_text` | `str` | `无声明默认；构造/赋值方提供` |
| `CommandView.intent` | `str` | `无声明默认；构造/赋值方提供` |
| `CommandView.parameters` | `Dict[str, Any]` | `field(default_factory=dict)` |
| `CommandView.asr_confidence` | `Optional[float]` | `None` |
| `CommandView.intent_confidence` | `float` | `1.0` |
| `CommandView.status` | `str` | `'valid'` |
| `CommandView.ambiguity_type` | `str` | `'NONE'` |
| `CommandView.confirm_required` | `bool` | `False` |
| `CommandView.errors` | `List[str]` | `field(default_factory=list)` |
| `CommandView.warnings` | `List[str]` | `field(default_factory=list)` |
| `CommandView.confidence` | `float` | `1.0` |
| `CommandView.t_audio_start_ns` | `Optional[int]` | `None` |
| `CommandView.t_asr_end_ns` | `Optional[int]` | `None` |
| `CommandView.t_intent_end_ns` | `Optional[int]` | `None` |
| `CommandView.valid_duration_s` | `float` | `5.0` |
| `VehicleStateView.frame` | `int` | `0` |
| `VehicleStateView.sim_time_s` | `float` | `0.0` |
| `VehicleStateView.speed_mps` | `float` | `0.0` |
| `VehicleStateView.x_m` | `float` | `0.0` |
| `VehicleStateView.y_m` | `float` | `0.0` |
| `VehicleStateView.z_m` | `float` | `0.0` |
| `VehicleStateView.yaw_deg` | `float` | `0.0` |
| `VehicleStateView.lane_id` | `int` | `0` |
| `VehicleStateView.front_distance_m` | `Optional[float]` | `None` |
| `VehicleStateView.distance_to_stop_line_m` | `Optional[float]` | `None` |
| `VehicleStateView.traffic_light` | `str` | `'UNKNOWN'` |
| `VehicleStateView.lane_offset_m` | `Optional[float]` | `None` |
| `VehicleStateView.route_deviation_m` | `Optional[float]` | `None` |
| `VehicleStateView.road_curvature_per_m` | `float` | `0.0` |
| `VehicleStateView.front_actor_type` | `Optional[str]` | `None` |
| `VehicleStateView.sensor_margin_scale` | `float` | `1.0` |
| `VehicleStateView.collision` | `bool` | `False` |
| `VehicleStateView.red_light_violation` | `bool` | `False` |
| `VehicleStateView.lane_invasion` | `bool` | `False` |
| `RiskView.ttc_s` | `Optional[float]` | `None` |
| `RiskView.desired_gap_m` | `Optional[float]` | `None` |
| `RiskView.emergency_brake_requested` | `bool` | `False` |
| `SafetyDecision.final_control` | `ControlOutput` | `无声明默认；构造/赋值方提供` |
| `SafetyDecision.safety_override` | `bool` | `无声明默认；构造/赋值方提供` |
| `SafetyDecision.reason` | `str` | `'NONE'` |
| `SafetyDecision.risk_metrics` | `Dict[str, Any]` | `field(default_factory=dict)` |
| `SafetyDecision.raw_control` | `Optional[ControlOutput]` | `None` |
| `SafetyDecision.reason_category` | `str` | `'NONE'` |
| `ValidationResult.valid` | `bool` | `无声明默认；构造/赋值方提供` |
| `ValidationResult.errors` | `List[str]` | `field(default_factory=list)` |
| `ValidationResult.warnings` | `List[str]` | `field(default_factory=list)` |
| `ScenarioResult.scenario_id` | `str` | `无声明默认；构造/赋值方提供` |
| `ScenarioResult.difficulty` | `str` | `无声明默认；构造/赋值方提供` |
| `ScenarioResult.status` | `str` | `无声明默认；构造/赋值方提供` |
| `ScenarioResult.collision_count` | `int` | `0` |
| `ScenarioResult.red_light_violation_count` | `int` | `0` |
| `ScenarioResult.route_deviation_count` | `int` | `0` |
| `ScenarioResult.unfinished_task_count` | `int` | `0` |
| `ScenarioResult.safety_override_count` | `int` | `0` |
| `ScenarioResult.command_count` | `int` | `0` |
| `ScenarioResult.e2e_latency_ms` | `Optional[float]` | `None` |
| `ScenarioResult.events` | `List[Dict[str, Any]]` | `field(default_factory=list)` |
