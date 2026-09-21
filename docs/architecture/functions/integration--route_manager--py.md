# route_manager：功能记录

上级模块：[模块说明](../modules/vehicle-lateral.md) · 实现：[integration/route_manager.py](../../../integration/route_manager.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [路线、跟踪控制与完成里程](route-control-progress.md)

## 功能职责与范围

Destination-driven global route planning over CARLA map topology.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `RouteSample.x_m: float`；默认：`未在声明处设置`。
- `RouteSample.y_m: float`；默认：`未在声明处设置`。
- `RouteSample.z_m: float`；默认：`未在声明处设置`。
- `RouteSample.yaw_deg: float`；默认：`未在声明处设置`。
- `RouteSample.s_m: float`；默认：`未在声明处设置`。
- `RouteSample.road_id: int | None`；默认：`未在声明处设置`。
- `RouteSample.section_id: int | None`；默认：`未在声明处设置`。
- `RouteSample.lane_id: int | None`；默认：`未在声明处设置`。
- `RouteSample.is_junction: bool`；默认：`未在声明处设置`。
- `RouteSample.left_lane_id: int | None`；默认：`未在声明处设置`。
- `RouteSample.right_lane_id: int | None`；默认：`未在声明处设置`。
- `RouteValidation.total_length_m: float`；默认：`未在声明处设置`。
- `RouteValidation.point_count: int`；默认：`未在声明处设置`。
- `RouteValidation.maximum_gap_m: float`；默认：`未在声明处设置`。
- `RouteValidation.destination_error_m: float`；默认：`未在声明处设置`。
- `RouteValidation.repeated_sample_count: int`；默认：`未在声明处设置`。
- `RouteValidation.junction_count: int`；默认：`未在声明处设置`。
- `GlobalRoute.reference: RouteReference`；默认：`未在声明处设置`。
- `GlobalRoute.samples: tuple[RouteSample, ...]`；默认：`未在声明处设置`。
- `GlobalRoute.validation: RouteValidation`；默认：`未在声明处设置`。
- `GlobalRoute.start_xy_m: Point2D`；默认：`未在声明处设置`。
- `GlobalRoute.destination_xy_m: Point2D`；默认：`未在声明处设置`。
- `GlobalRoute.waypoints: tuple[Any, ...]`；默认：`field(repr=False, compare=False)`。
- `RouteState.route_s: float`；默认：`未在声明处设置`。
- `RouteState.route_progress: float`；默认：`未在声明处设置`。
- `RouteState.route_remaining_m: float`；默认：`未在声明处设置`。
- `RouteState.nearest_route_point: Point2D`；默认：`未在声明处设置`。
- `RouteState.cross_track_error_m: float`；默认：`未在声明处设置`。
- `RouteState.road_curvature: float`；默认：`未在声明处设置`。
- `RouteState.road_id: int | None`；默认：`未在声明处设置`。
- `RouteState.lane_id: int | None`；默认：`未在声明处设置`。
- `RouteState.lane_relation: str`；默认：`未在声明处设置`。
- `RouteState.left_lane_id: int | None`；默认：`未在声明处设置`。
- `RouteState.right_lane_id: int | None`；默认：`未在声明处设置`。
- `RouteState.nearest_index: int`；默认：`未在声明处设置`。
- `RouteState.reached_destination: bool`；默认：`未在声明处设置`。
- `RouteState.status: str`；默认：`未在声明处设置`。
- `RouteState.reason: str | None`；默认：`未在声明处设置`。
- `RouteState.requires_replan: bool`；默认：`未在声明处设置`。
- `RoutePlacement.route_s: float`；默认：`未在声明处设置`。
- `RoutePlacement.lane_relation: str`；默认：`未在声明处设置`。
- `RoutePlacement.x_m: float`；默认：`未在声明处设置`。
- `RoutePlacement.y_m: float`；默认：`未在声明处设置`。
- `RoutePlacement.z_m: float`；默认：`未在声明处设置`。
- `RoutePlacement.yaw_deg: float`；默认：`未在声明处设置`。
- `RoutePlacement.road_id: int | None`；默认：`未在声明处设置`。
- `RoutePlacement.lane_id: int | None`；默认：`未在声明处设置`。
- `LaneCorridorRequirement.requirement_id: str`；默认：`未在声明处设置`。
- `LaneCorridorRequirement.relation: str`；默认：`未在声明处设置`。
- `LaneCorridorRequirement.start_s_m: float`；默认：`未在声明处设置`。
- `LaneCorridorRequirement.end_s_m: float`；默认：`未在声明处设置`。
- `LaneCorridorRequirement.junction_free: bool`；默认：`False`。
- `SpeedWindowRequirement.requirement_id: str`；默认：`未在声明处设置`。
- `SpeedWindowRequirement.start_s_m: float`；默认：`未在声明处设置`。
- `SpeedWindowRequirement.end_s_m: float`；默认：`未在声明处设置`。
- `SpeedWindowRequirement.minimum_speed_kph: float`；默认：`未在声明处设置`。
- `SpeedWindowRequirement.max_lateral_accel_mps2: float`；默认：`2.0`。
- `SpeedWindowRequirement.lookahead_m: float`；默认：`45.0`。
- `RouteRecoveryPolicy.off_route_threshold_m: float`；默认：`6.0`。
- `RouteRecoveryPolicy.confirmation_s: float`；默认：`0.5`。
- `RouteRecoveryPolicy.cooldown_s: float`；默认：`5.0`。
- `RouteRecoveryPolicy.maximum_attempts: int`；默认：`3`。
- `RouteRecoveryDecision.status: str`；默认：`未在声明处设置`。
- `RouteRecoveryDecision.reason: str | None`；默认：`未在声明处设置`。
- `RouteRecoveryDecision.should_replan: bool`；默认：`未在声明处设置`。
- `RouteRecoveryDecision.attempt: int`；默认：`未在声明处设置`。
- `_TopologyEdge.index: int`；默认：`未在声明处设置`。
- `_TopologyEdge.entry: Any`；默认：`未在声明处设置`。
- `_TopologyEdge.exit: Any`；默认：`未在声明处设置`。
- `_TopologyEdge.waypoints: tuple[Any, ...]`；默认：`未在声明处设置`。
- `_TopologyEdge.length_m: float`；默认：`未在声明处设置`。
- `_LaneChangeTransition.source_edge_index: int`；默认：`未在声明处设置`。
- `_LaneChangeTransition.target_edge_index: int`；默认：`未在声明处设置`。
- `_LaneChangeTransition.side: str`；默认：`未在声明处设置`。
- `_LaneChangeTransition.candidates: tuple[tuple[Any, Any], ...]`；默认：`field(repr=False, compare=False)`。

## 功能入口：输入、输出与实现说明

### `RoutePlanningError`

源码位置：[integration/route_manager.py 第 31 行](../../../integration/route_manager.py#L31)。类型：`ClassDef`。

A route failure with a stable machine-readable reason code.

### `RoutePlanningError.__init__`

源码位置：[integration/route_manager.py 第 34 行](../../../integration/route_manager.py#L34)。类型：`FunctionDef`。

```python
RoutePlanningError.__init__(self, code: str, detail: str, *, context: Mapping[str, object] | None=None) -> None
```

保存稳定 `code`、人类可读 `detail` 和复制后的 context，并把异常消息格式化为 `CODE: detail`；调用方可按 code 分支而无需解析文本。

### `RouteSample`

源码位置：[integration/route_manager.py 第 48 行](../../../integration/route_manager.py#L48)。类型：`ClassDef`。

不可变拓扑采样，绑定世界姿态、全局弧长、道路/section/lane、junction 与左右邻道身份；是全局路线与场景放置/状态查询的对齐记录。

### `RouteSample.point_xy_m`

源码位置：[integration/route_manager.py 第 62 行](../../../integration/route_manager.py#L62)。类型：`FunctionDef`。

```python
RouteSample.point_xy_m(self) -> Point2D
```

返回采样的 `(x_m,y_m)` tuple，不包含 z、yaw 或车道身份。

### `RouteValidation`

源码位置：[integration/route_manager.py 第 67 行](../../../integration/route_manager.py#L67)。类型：`ClassDef`。

不可变规划质量记录：总长、点数、最大相邻间距、终点误差、重复采样数和进入 junction 次数。

### `RouteValidation.to_dict`

源码位置：[integration/route_manager.py 第 75 行](../../../integration/route_manager.py#L75)。类型：`FunctionDef`。

```python
RouteValidation.to_dict(self) -> dict[str, object]
```

按稳定字段名导出规划质量；只序列化当前值，不重新执行路线验证。

### `GlobalRoute`

源码位置：[integration/route_manager.py 第 87 行](../../../integration/route_manager.py#L87)。类型：`ClassDef`。

全局路线聚合：控制参考线、逐点拓扑样本、验证摘要、起终点坐标及不参与 repr/compare 的原始 waypoint；这些序列按索引共同演进。

### `GlobalRoute.total_length_m`

源码位置：[integration/route_manager.py 第 96 行](../../../integration/route_manager.py#L96)。类型：`FunctionDef`。

```python
GlobalRoute.total_length_m(self) -> float
```

直接返回 `validation.total_length_m`，不从 reference 重新累计。

### `RouteState`

源码位置：[integration/route_manager.py 第 101 行](../../../integration/route_manager.py#L101)。类型：`ClassDef`。

单帧路线状态，包含绝对弧长、比例、剩余距离、最近点/误差、道路车道关系、终点与重规划判定；它描述路线关系，不等于最终安全状态。

### `RouteState.to_dict`

源码位置：[integration/route_manager.py 第 119 行](../../../integration/route_manager.py#L119)。类型：`FunctionDef`。

```python
RouteState.to_dict(self) -> dict[str, object]
```

导出完整状态并把最近点 tuple 转为 JSON 友好的 list；reason 可为 None。

### `RoutePlacement`

源码位置：[integration/route_manager.py 第 141 行](../../../integration/route_manager.py#L141)。类型：`ClassDef`。

A map-valid placement resolved from route distance and lane relation.

### `LaneCorridorRequirement`

源码位置：[integration/route_manager.py 第 155 行](../../../integration/route_manager.py#L155)。类型：`ClassDef`。

Adjacent-lane topology that must exist over a mission-distance window.

### `LaneCorridorRequirement.__post_init__`

源码位置：[integration/route_manager.py 第 164 行](../../../integration/route_manager.py#L164)。类型：`FunctionDef`。

```python
LaneCorridorRequirement.__post_init__(self) -> None
```

规范化 relation（去掉 `_ADJACENT`）并限制为 LEFT/RIGHT，要求非空 id、有限且有序的非负 s 区间以及严格 bool 的 junction_free；在 frozen 对象中写回规范值。

### `LaneCorridorRequirement.from_mapping`

源码位置：[integration/route_manager.py 第 180 行](../../../integration/route_manager.py#L180)。类型：`FunctionDef`。

```python
LaneCorridorRequirement.from_mapping(cls, value: Mapping[str, object]) -> 'LaneCorridorRequirement'
```

从场景对象读取 id/phase_id、relation、起止 s 和 junction_free；缺失值按 0/False 补齐后交由构造校验，输入不是 Mapping 时拒绝。

### `SpeedWindowRequirement`

源码位置：[integration/route_manager.py 第 193 行](../../../integration/route_manager.py#L193)。类型：`ClassDef`。

Minimum physically supportable speed over a route-distance window.

### `SpeedWindowRequirement.__post_init__`

源码位置：[integration/route_manager.py 第 203 行](../../../integration/route_manager.py#L203)。类型：`FunctionDef`。

```python
SpeedWindowRequirement.__post_init__(self) -> None
```

把距离、最低速度、横向加速度和 lookahead 规范为 float，要求 id 非空、值有限、区间有序且速度/加速度/lookahead 为正。

### `SpeedWindowRequirement.from_mapping`

源码位置：[integration/route_manager.py 第 222 行](../../../integration/route_manager.py#L222)。类型：`FunctionDef`。

```python
SpeedWindowRequirement.from_mapping(cls, value: Mapping[str, object]) -> 'SpeedWindowRequirement'
```

从场景对象构造速度窗口，默认横向加速度 2.0 m/s²、lookahead 45 m；字段缺失产生的 0 值会由构造校验拒绝无效最低速度。

### `RouteRecoveryPolicy`

源码位置：[integration/route_manager.py 第 236 行](../../../integration/route_manager.py#L236)。类型：`ClassDef`。

Map-independent hysteresis for automatic off-route recovery.

### `RouteRecoveryPolicy.from_mapping`

源码位置：[integration/route_manager.py 第 245 行](../../../integration/route_manager.py#L245)。类型：`FunctionDef`。

```python
RouteRecoveryPolicy.from_mapping(cls, value: Mapping[str, object] | None) -> 'RouteRecoveryPolicy'
```

None 返回默认策略；Mapping 只允许四个恢复字段，拒绝未知键，并把值转换为 float/int 后交由策略校验。

### `RouteRecoveryPolicy.__post_init__`

源码位置：[integration/route_manager.py 第 265 行](../../../integration/route_manager.py#L265)。类型：`FunctionDef`。

```python
RouteRecoveryPolicy.__post_init__(self) -> None
```

要求阈值/确认/冷却为有限数，off-route 阈值大于 0、两个时长非负，maximum_attempts 为非负严格整数；在不可变实例中保存规范化 float。

### `RouteRecoveryDecision`

源码位置：[integration/route_manager.py 第 280 行](../../../integration/route_manager.py#L280)。类型：`ClassDef`。

不可变恢复决策，记录状态、可空 reason、本帧是否应重规划和累计尝试次数；决策本身不执行 replan。

### `RouteRecoveryTracker`

源码位置：[integration/route_manager.py 第 287 行](../../../integration/route_manager.py#L287)。类型：`ClassDef`。

Turn noisy per-frame deviation into deterministic recovery decisions.

### `RouteRecoveryTracker.__init__`

源码位置：[integration/route_manager.py 第 290 行](../../../integration/route_manager.py#L290)。类型：`FunctionDef`。

```python
RouteRecoveryTracker.__init__(self, policy: RouteRecoveryPolicy | None=None) -> None
```

采用传入或默认恢复策略，初始化偏离起始时刻、上次尝试时刻和尝试计数；时间基准由后续 sim_time_s 提供。

### `RouteRecoveryTracker.attempts`

源码位置：[integration/route_manager.py 第 297 行](../../../integration/route_manager.py#L297)。类型：`FunctionDef`。

```python
RouteRecoveryTracker.attempts(self) -> int
```

只读返回当前任务已触发的重规划次数。

### `RouteRecoveryTracker.observe`

源码位置：[integration/route_manager.py 第 300 行](../../../integration/route_manager.py#L300)。类型：`FunctionDef`。

```python
RouteRecoveryTracker.observe(self, route_state: RouteState, sim_time_s: float, *, recovery_suppressed: bool=False) -> RouteRecoveryDecision
```

将单帧 RouteState 和仿真时间转为带确认时长、冷却和次数上限的确定性决策；到达/回归/主动机动抑制会清除连续偏离计时，只有确认完成且未冷却/耗尽时增加 attempts 并返回 should_replan=True。

### `RouteRecoveryTracker.note_replan_succeeded`

源码位置：[integration/route_manager.py 第 360 行](../../../integration/route_manager.py#L360)。类型：`FunctionDef`。

```python
RouteRecoveryTracker.note_replan_succeeded(self) -> None
```

清除连续偏离起始时刻，但保留 attempts 和 cooldown 时间，因此成功一次不会恢复尝试额度。

### `RouteRecoveryTracker.reset_mission`

源码位置：[integration/route_manager.py 第 363 行](../../../integration/route_manager.py#L363)。类型：`FunctionDef`。

```python
RouteRecoveryTracker.reset_mission(self) -> None
```

清除偏离时刻、冷却时刻和尝试数，只应在新任务边界调用。

### `_TopologyEdge`

源码位置：[integration/route_manager.py 第 370 行](../../../integration/route_manager.py#L370)。类型：`ClassDef`。

内部不可变拓扑边，保存稳定索引、入口/出口 waypoint、采样 waypoint 序列和边长。

### `_LaneChangeTransition`

源码位置：[integration/route_manager.py 第 379 行](../../../integration/route_manager.py#L379)。类型：`ClassDef`。

内部合法变道连接，保存源/目标边、左右方向及候选 waypoint 对；候选不参与 repr/compare。

### `_BlendedWaypoint`

源码位置：[integration/route_manager.py 第 386 行](../../../integration/route_manager.py#L386)。类型：`ClassDef`。

Waypoint-shaped route sample used inside a smooth legal lane change.

### `_BlendedWaypoint.__init__`

源码位置：[integration/route_manager.py 第 389 行](../../../integration/route_manager.py#L389)。类型：`FunctionDef`。

```python
_BlendedWaypoint.__init__(self, source: Any, target: Any, *, x_m: float, y_m: float, z_m: float, yaw_deg: float, target_weight: float) -> None
```

在源/目标 waypoint 之间构造 waypoint 形状的平滑采样；位置/yaw 由调用方给定，target_weight 达 0.5 后采用目标车道身份，并保留基础 waypoint 供邻道查询。

### `_BlendedWaypoint.get_left_lane`

源码位置：[integration/route_manager.py 第 417 行](../../../integration/route_manager.py#L417)。类型：`FunctionDef`。

```python
_BlendedWaypoint.get_left_lane(self) -> Any | None
```

把左邻道查询转发给当前基础 waypoint；缺少可调用 getter 时返回 None。

### `_BlendedWaypoint.get_right_lane`

源码位置：[integration/route_manager.py 第 421 行](../../../integration/route_manager.py#L421)。类型：`FunctionDef`。

```python
_BlendedWaypoint.get_right_lane(self) -> Any | None
```

把右邻道查询转发给当前基础 waypoint；缺少可调用 getter 时返回 None。

### `_location`

源码位置：[integration/route_manager.py 第 426 行](../../../integration/route_manager.py#L426)。类型：`FunctionDef`。

```python
_location(value: Any) -> Any
```

兼容 actor/location/transform/waypoint：优先调用 `get_location()`，其次取 `transform.location`，再取 `location` 属性，最后把输入本身视为位置。

### `_transform`

源码位置：[integration/route_manager.py 第 435 行](../../../integration/route_manager.py#L435)。类型：`FunctionDef`。

```python
_transform(value: Any) -> Any | None
```

优先调用 `get_transform()`；否则仅当对象同时有 location 与 rotation 时返回对象本身，无法解析时返回 None。

### `_xy`

源码位置：[integration/route_manager.py 第 443 行](../../../integration/route_manager.py#L443)。类型：`FunctionDef`。

```python
_xy(value: Any) -> Point2D
```

经 `_location` 解析后把 x/y 转成 float tuple；缺字段或不可转换异常原样传播。

### `_distance`

源码位置：[integration/route_manager.py 第 448 行](../../../integration/route_manager.py#L448)。类型：`FunctionDef`。

```python
_distance(first: Any, second: Any) -> float
```

解析两个对象的二维坐标并返回欧氏距离，忽略 z。

### `_wrap_degrees`

源码位置：[integration/route_manager.py 第 452 行](../../../integration/route_manager.py#L452)。类型：`FunctionDef`。

```python
_wrap_degrees(angle: float) -> float
```

把角度规范到 `[-180,180)`，用于航向差和拓扑排序。

### `_yaw`

源码位置：[integration/route_manager.py 第 456 行](../../../integration/route_manager.py#L456)。类型：`FunctionDef`。

```python
_yaw(waypoint: Any) -> float
```

读取 `waypoint.transform.rotation.yaw` 并转为 float；只接受 waypoint 形态对象。

### `_is_driving_lane`

源码位置：[integration/route_manager.py 第 460 行](../../../integration/route_manager.py#L460)。类型：`FunctionDef`。

```python
_is_driving_lane(waypoint: Any | None) -> bool
```

None 返回 False；否则取 lane_type 枚举文本末段并大小写无关地与 DRIVING 比较，缺省 lane_type 按 Driving 处理。

### `_lane_identity`

源码位置：[integration/route_manager.py 第 467 行](../../../integration/route_manager.py#L467)。类型：`FunctionDef`。

```python
_lane_identity(waypoint: Any) -> tuple[int | None, int | None, int | None]
```

返回 `(road_id, section_id, lane_id)`，字段缺失以 None 表示；用于把 waypoint 归入同一拓扑车道。

### `_visit_key`

源码位置：[integration/route_manager.py 第 475 行](../../../integration/route_manager.py#L475)。类型：`FunctionDef`。

```python
_visit_key(waypoint: Any) -> tuple[object, ...]
```

优先用道路/section/lane 与四舍五入到 0.01 的 lane s 标识访问点；拓扑字段不足时退化为 0.01 m 的 x/y 与 0.1° yaw，供去重和覆盖路线访问计数。

### `_same_direction`

源码位置：[integration/route_manager.py 第 484 行](../../../integration/route_manager.py#L484)。类型：`FunctionDef`。

```python
_same_direction(first: Any, second: Any, tolerance_deg: float=60.0) -> bool
```

比较两个 waypoint 的环绕 yaw 差，绝对值不超过 tolerance（默认 60°）即视为同向。

### `_lane_change_allowed`

源码位置：[integration/route_manager.py 第 488 行](../../../integration/route_manager.py#L488)。类型：`FunctionDef`。

```python
_lane_change_allowed(waypoint: Any, side: str) -> bool
```

Read CARLA lane-marking permissions without importing the CARLA module.

### `_curvature`

源码位置：[integration/route_manager.py 第 509 行](../../../integration/route_manager.py#L509)。类型：`FunctionDef`。

```python
_curvature(points: Sequence[Point2D], index: int) -> float
```

在夹到内部范围的索引周围取三点，以三角形面积/边长计算无符号曲率；点不足或退化边返回 0。

### `RouteManager`

源码位置：[integration/route_manager.py 第 525 行](../../../integration/route_manager.py#L525)。类型：`ClassDef`。

Plan and query one global destination route for a CARLA map.

### `RouteManager.__init__`

源码位置：[integration/route_manager.py 第 528 行](../../../integration/route_manager.py#L528)。类型：`FunctionDef`。

```python
RouteManager.__init__(self, world_map: Any, *, sample_step_m: float=2.0, finish_radius_m: float=4.0, maximum_gap_m: float | None=None, maximum_expansions: int=50000, off_route_threshold_m: float=6.0) -> None
```

验证采样步长、终点半径、A* 展开上限和偏离阈值；maximum_gap 未提供时取 `max(5m, 3*sample_step)`。初始化惰性拓扑缓存与变道连接表，不读取场景特定 ID。

### `RouteManager.plan`

源码位置：[integration/route_manager.py 第 561 行](../../../integration/route_manager.py#L561)。类型：`FunctionDef`。

```python
RouteManager.plan(self, start: Any, destination: Any, target_speed_mps: float) -> GlobalRoute
```

把起终点投影为驾驶 waypoint，构建/复用拓扑图，以 A* 搜索边路径并组装 waypoint；若某条变道连接无法形成完整合法走廊，则屏蔽该连接后重新搜索，最终构造并验证 GlobalRoute。

### `RouteManager.plan_distance`

源码位置：[integration/route_manager.py 第 612 行](../../../integration/route_manager.py#L612)。类型：`FunctionDef`。

```python
RouteManager.plan_distance(self, start: Any, distance_m: float, target_speed_mps: float) -> GlobalRoute
```

Generate a topology-following coverage route of a requested length.

This mode is for distance-contract missions such as the 8 km competition
scene, where a shortest path to one destination cannot express the task.
Junction choices prefer unvisited legal topology and never introduce an
implicit lane change.

### `RouteManager.plan_distance_compatible`

源码位置：[integration/route_manager.py 第 693 行](../../../integration/route_manager.py#L693)。类型：`FunctionDef`。

```python
RouteManager.plan_distance_compatible(self, starts: Sequence[Any], distance_m: float, target_speed_mps: float, *, lane_corridors: Sequence[LaneCorridorRequirement]=(), speed_windows: Sequence[SpeedWindowRequirement]=()) -> tuple[int, GlobalRoute]
```

Select the first start whose route satisfies scene topology.

The caller owns deterministic candidate order. No town, scenario, or
spawn index is embedded here; compatibility is route-relative.

### `RouteManager.validate_compatibility`

源码位置：[integration/route_manager.py 第 739 行](../../../integration/route_manager.py#L739)。类型：`FunctionDef`。

```python
RouteManager.validate_compatibility(self, route: GlobalRoute, *, lane_corridors: Sequence[LaneCorridorRequirement]=(), speed_windows: Sequence[SpeedWindowRequirement]=()) -> None
```

Reject route/event combinations that are physically inconsistent.

### `RouteManager._validate_lane_corridor`

源码位置：[integration/route_manager.py 第 753 行](../../../integration/route_manager.py#L753)。类型：`FunctionDef`。

```python
RouteManager._validate_lane_corridor(self, route: GlobalRoute, cumulative: Sequence[float], requirement: LaneCorridorRequirement) -> None
```

把声明的 s 区间映射到 waypoint 索引，逐点要求指定左右邻道存在；区间超路线、邻道缺失或 junction_free 窗口触及 junction 时分别以稳定 RoutePlanningError code 拒绝。

### `RouteManager._validate_speed_window`

源码位置：[integration/route_manager.py 第 785 行](../../../integration/route_manager.py#L785)。类型：`FunctionDef`。

```python
RouteManager._validate_speed_window(self, route: GlobalRoute, cumulative: Sequence[float], requirement: SpeedWindowRequirement) -> None
```

在声明窗口内逐点查看未来 lookahead 的最大曲率，按 `sqrt(max_lateral_accel/curvature)` 估算可支持速度；窗口越界或低于 minimum_speed_kph 时拒绝。

### `RouteManager.state`

源码位置：[integration/route_manager.py 第 819 行](../../../integration/route_manager.py#L819)。类型：`FunctionDef`。

```python
RouteManager.state(self, route: GlobalRoute, x_m: float, y_m: float, *, previous_s_m: float | None=None, forward_window_m: float=80.0) -> RouteState
```

用 previous_s 和 80m 默认前向窗投影单调 route_s，解析最近路线姿态与车辆 map waypoint，判定 CURRENT/LEFT/RIGHT/UNKNOWN；同时计算剩余、端点误差和无符号 CTE，并以 finish_radius 与 off_route_threshold 产生到达、偏离和 replan 状态。

### `RouteManager.placement`

源码位置：[integration/route_manager.py 第 889 行](../../../integration/route_manager.py#L889)。类型：`FunctionDef`。

```python
RouteManager.placement(self, route: GlobalRoute, route_s: float, lane_relation: str='CURRENT') -> RoutePlacement
```

Resolve an actor/event pose using route distance plus lane relation.

### `RouteManager.local_reference`

源码位置：[integration/route_manager.py 第 924 行](../../../integration/route_manager.py#L924)。类型：`FunctionDef`。

```python
RouteManager.local_reference(self, route: GlobalRoute, route_s: float, target_speed_mps: float, *, lookbehind_m: float=8.0, lookahead_m: float=80.0) -> RouteReference
```

Return a bounded controller view while the global route stays authoritative.

### `RouteManager.mission_placement`

源码位置：[integration/route_manager.py 第 995 行](../../../integration/route_manager.py#L995)。类型：`FunctionDef`。

```python
RouteManager.mission_placement(self, route: GlobalRoute, mission_route_s: float, mission_progress_offset_m: float, lane_relation: str='CURRENT') -> RoutePlacement
```

Resolve an absolute mission ``route_s`` on the current replanned route.

### `RouteManager.replan`

源码位置：[integration/route_manager.py 第 1023 行](../../../integration/route_manager.py#L1023)。类型：`FunctionDef`。

```python
RouteManager.replan(self, current: Any, destination: Any, target_speed_mps: float) -> GlobalRoute
```

Rebuild a route from the current map pose after an off-route event.

### `RouteManager._project_xy_like`

源码位置：[integration/route_manager.py 第 1129 行](../../../integration/route_manager.py#L1129)。类型：`FunctionDef`。

```python
RouteManager._project_xy_like(self, sample_waypoint: Any, x_m: float, y_m: float) -> Any | None
```

尝试用 world_map.get_waypoint 将 x/y 投影到与样本相同的地图位置类型；无法构造 location、缺少 API 或投影异常时返回 None，而不把查询失败升级为规划错误。

### `RouteManager._future_novel_capacity`

源码位置：[integration/route_manager.py 第 1140 行](../../../integration/route_manager.py#L1140)。类型：`FunctionDef`。

```python
RouteManager._future_novel_capacity(self, waypoint: Any, visits: Mapping[tuple[object, ...], int], *, depth: int, branch_seen: frozenset[tuple[object, ...]]=frozenset()) -> int
```

从某 waypoint 递归查看有限 depth 的后继，按 visit 次数惩罚已走点并选择最大未来新颖容量；用于距离覆盖分支排序，不修改 visits。

### `RouteManager._project_endpoint`

源码位置：[integration/route_manager.py 第 1172 行](../../../integration/route_manager.py#L1172)。类型：`FunctionDef`。

```python
RouteManager._project_endpoint(self, value: Any, code: str) -> Any
```

把任意起终点解析为 location，并调用 map.get_waypoint 投影到驾驶车道；缺接口、调用失败、返回 None 或非 Driving 时转换为带指定 code 的 RoutePlanningError。

### `RouteManager._topology_graph`

源码位置：[integration/route_manager.py 第 1187 行](../../../integration/route_manager.py#L1187)。类型：`FunctionDef`。

```python
RouteManager._topology_graph(self) -> tuple[tuple[_TopologyEdge, ...], dict[int, tuple[int, ...]]]
```

首次调用读取 map topology、采样每条边、计算长度并建立 `_TopologyEdge`；随后连接自然后继与合法变道边并缓存。空拓扑或没有有效边时拒绝，后续调用复用缓存。

### `RouteManager._sample_edge`

源码位置：[integration/route_manager.py 第 1218 行](../../../integration/route_manager.py#L1218)。类型：`FunctionDef`。

```python
RouteManager._sample_edge(self, entry: Any, exit_waypoint: Any) -> tuple[Any, ...]
```

沿 entry.next(sample_step) 选择保持目标车道身份且同向、最接近 exit 的 waypoint，直到到达出口或步数上限；检测循环、断路和异常 gap，并确保出口加入采样。

### `RouteManager._connect_edges`

源码位置：[integration/route_manager.py 第 1258 行](../../../integration/route_manager.py#L1258)。类型：`FunctionDef`。

```python
RouteManager._connect_edges(self, edges: tuple[_TopologyEdge, ...]) -> dict[int, tuple[int, ...]]
```

按车道身份和端点邻近关系建立自然有向连接；再扫描非 junction waypoint 的车道线权限与连续邻道，验证可构造平滑变道连接后加入邻接表，并保留候选最多的同源目标 transition。

### `RouteManager._locate_edge`

源码位置：[integration/route_manager.py 第 1370 行](../../../integration/route_manager.py#L1370)。类型：`FunctionDef`。

```python
RouteManager._locate_edge(self, waypoint: Any, edges: tuple[_TopologyEdge, ...], code: str) -> _TopologyEdge
```

优先在同车道身份的边中按 waypoint 最小距离、入口 yaw 差和边索引排序，找不到同车道时回退全图；最近距离超过 maximum_gap 时按调用方 code 拒绝。

### `RouteManager._search`

源码位置：[integration/route_manager.py 第 1399 行](../../../integration/route_manager.py#L1399)。类型：`FunctionDef`。

```python
RouteManager._search(self, start_index: int, goal_index: int, destination: Any, edges: tuple[_TopologyEdge, ...], adjacency: Mapping[int, tuple[int, ...]], *, blocked_connections: set[tuple[int, int]] | frozenset[tuple[int, int]]=frozenset()) -> tuple[int, ...]
```

在拓扑边图上执行有展开上限的 A*；代价为边长并对变道加 25m 惩罚，可跳过 blocked_connections。无法到达目标边时抛 `ROUTE_UNREACHABLE`，成功时从 parents 回溯边索引序列。

### `RouteManager._assemble_waypoints`

源码位置：[integration/route_manager.py 第 1455 行](../../../integration/route_manager.py#L1455)。类型：`FunctionDef`。

```python
RouteManager._assemble_waypoints(self, edge_path: Sequence[int], start: Any, destination: Any, edges: tuple[_TopologyEdge, ...]) -> tuple[Any, ...]
```

按边路径裁起终点并去重采样；遇到变道边时在足够前进距离后选择可完成的合法平滑 connector。倒退序列、不可用变道或不足两个点使用稳定 code 失败。

### `RouteManager._build_lane_change_connector`

源码位置：[integration/route_manager.py 第 1557 行](../../../integration/route_manager.py#L1557)。类型：`FunctionDef`。

```python
RouteManager._build_lane_change_connector(self, transition: _LaneChangeTransition, source: Any) -> tuple[tuple[Any, ...], Any]
```

Build a smooth, permission-checked connector between parallel lanes.

### `RouteManager._build_global_route`

源码位置：[integration/route_manager.py 第 1627 行](../../../integration/route_manager.py#L1627)。类型：`FunctionDef`。

```python
RouteManager._build_global_route(self, waypoints: Sequence[Any], start: Any, destination: Any, target_speed_mps: float, *, allow_repeated_samples: bool=False) -> GlobalRoute
```

从 waypoint 生成点集、累计弧长、RouteSample 与验证摘要；拒绝过大 gap、非允许重复、非驾驶车道和终点误差。计算最大曲率、变道数与坐标指纹 route_id，并返回索引对齐的 GlobalRoute。

### `RouteManager._route_sample`

源码位置：[integration/route_manager.py 第 1710 行](../../../integration/route_manager.py#L1710)。类型：`FunctionDef`。

```python
RouteManager._route_sample(waypoint: Any, s_m: float) -> RouteSample
```

把单个 waypoint 与累计 s 转成 RouteSample，同时查询合法同向左右邻道 ID；保留 road/section/lane、junction、z 和 yaw。

### `RouteManager._adjacent_lane`

源码位置：[integration/route_manager.py 第 1729 行](../../../integration/route_manager.py#L1729)。类型：`FunctionDef`。

```python
RouteManager._adjacent_lane(waypoint: Any, side: str) -> Any | None
```

按 LEFT/RIGHT 调用相应邻道 getter，只返回 Driving 且与源 waypoint 同向的邻道，否则返回 None。

## 内部调用与异常路径

- `_location` 调用：`callable`, `getattr`, `hasattr`, `value.get_location`.
- `_transform` 调用：`callable`, `getattr`, `hasattr`, `value.get_transform`.
- `_xy` 调用：`_location`, `float`.
- `_distance` 调用：`_xy`, `math.dist`.
- `_wrap_degrees` 调用：`float`.
- `_yaw` 调用：`float`.
- `_is_driving_lane` 调用：`getattr`, `lane_type.upper`, `str`, `str(getattr(waypoint, 'lane_type', 'Driving')).split`.
- `_lane_identity` 调用：`getattr`.
- `_visit_key` 调用：`_lane_identity`, `_xy`, `_yaw`, `float`, `getattr`, `round`.
- `_same_direction` 调用：`_wrap_degrees`, `_yaw`, `abs`.
- `_lane_change_allowed` 调用：`bool`, `getattr`, `int`, `str`, `str(value).split`, `str(value).split('.')[-1].strip`, `str(value).split('.')[-1].strip().upper`.
- `_curvature` 调用：`abs`, `int`, `len`, `math.dist`, `max`, `min`.
- `__init__` 调用：`RouteRecoveryPolicy`, `SimpleNamespace`, `ValueError`, `dict`, `float`, `getattr`, `location_type`, `math.isfinite`, `max`, `setattr`, `str`, `super`, `super().__init__`, `type`.
- `to_dict` 调用：`list`.
- `__post_init__` 调用：`TypeError`, `ValueError`, `any`, `float`, `map`, `math.isfinite`, `object.__setattr__`, `str`, `str(self.relation).strip`, `str(self.relation).strip().upper`, `str(self.relation).strip().upper().removesuffix`, `tuple`, `type`.
- `from_mapping` 调用：`', '.join`, `TypeError`, `ValueError`, `cls`, `float`, `isinstance`, `set`, `set(value).difference`, `sorted`, `str`, `value.get`.
- `observe` 调用：`RouteRecoveryDecision`, `ValueError`, `float`, `math.isfinite`.
- `get_left_lane` 调用：`callable`, `getattr`, `getter`.
- `get_right_lane` 调用：`callable`, `getattr`, `getter`.
- `plan` 调用：`ValueError`, `blocked_connections.add`, `error.context.get`, `float`, `math.isfinite`, `self._assemble_waypoints`, `self._build_global_route`, `self._locate_edge`, `self._project_endpoint`, `self._search`, `self._topology_graph`, `set`, `type`.
- `plan_distance` 调用：`RoutePlanningError`, `ValueError`, `_distance`, `_is_driving_lane`, `_same_direction`, `_visit_key`, `_wrap_degrees`, `_yaw`, `abs`, `current.next`, `dict`, `float`, `math.ceil`, `math.isfinite`, `max`, `metadata.update`, `min`, `range`, `replace`, `self._build_global_route`, `self._future_novel_capacity`, `self._project_endpoint`, `tuple`, `visits.get`, `waypoints.append`.
- `plan_distance_compatible` 调用：`RoutePlanningError`, `ValueError`, `dict`, `enumerate`, `failures.append`, `len`, `replace`, `self.plan_distance`, `self.validate_compatibility`.
- `validate_compatibility` 调用：`cumulative_distances_m`, `self._validate_lane_corridor`, `self._validate_speed_window`.
- `_validate_lane_corridor` 调用：`RoutePlanningError`, `bisect_left`, `bool`, `getattr`, `len`, `min`, `range`, `requirement.relation.lower`, `self._adjacent_lane`.
- `_validate_speed_window` 调用：`RoutePlanningError`, `_curvature`, `bisect_left`, `len`, `math.sqrt`, `max`, `min`, `range`.
- `state` 调用：`RouteState`, `_curvature`, `bisect_left`, `cumulative_distances_m`, `float`, `getattr`, `len`, `math.dist`, `max`, `min`, `project_route_progress_m`, `route_pose_at_s`, `self._project_xy_like`.
- `placement` 调用：`RoutePlacement`, `RoutePlanningError`, `ValueError`, `_yaw`, `bisect_left`, `cumulative_distances_m`, `float`, `getattr`, `len`, `math.isfinite`, `max`, `min`, `relation.lower`, `self._adjacent_lane`, `str`, `str(lane_relation).strip`, `str(lane_relation).strip().upper`.
- `local_reference` 调用：`RoutePlanningError`, `RouteReference`, `ValueError`, `_curvature`, `any`, `cumulative_distances_m`, `deduplicated.append`, `dict`, `float`, `isinstance`, `len`, `math.dist`, `math.isfinite`, `max`, `metadata.update`, `min`, `points.append`, `points.extend`, `range`, `route_pose_at_s`, `tuple`, `type`, `zip`.
- `mission_placement` 调用：`RoutePlanningError`, `ValueError`, `float`, `math.isfinite`, `replace`, `self.placement`.
- `replan` 调用：`'|'.join`, `'|'.join((f'{x_m:.2f},{y_m:.2f}' for x_m, y_m in points)).encode`, `GlobalRoute`, `RoutePlanningError`, `RouteReference`, `_curvature`, `_xy`, `bisect_left`, `cumulative_distances_m`, `dict`, `enumerate`, `hashlib.sha256`, `hashlib.sha256(route_fingerprint).hexdigest`, `len`, `math.ceil`, `math.dist`, `max`, `min`, `range`, `replace`, `self.plan`, `tuple`, `zip`.
- `_project_xy_like` 调用：`float`, `getattr`, `self.world_map.get_waypoint`, `type`, `type(location)`.
- `_future_novel_capacity` 调用：`_is_driving_lane`, `_visit_key`, `frozenset`, `max`, `self._future_novel_capacity`, `tuple`, `visits.get`, `waypoint.next`.
- `_project_endpoint` 调用：`RoutePlanningError`, `_is_driving_lane`, `_location`, `_transform`, `_wrap_degrees`, `_yaw`, `abs`, `float`, `self.world_map.get_waypoint`.
- `_topology_graph` 调用：`RoutePlanningError`, `_TopologyEdge`, `_distance`, `_is_driving_lane`, `callable`, `edges.append`, `get_topology`, `getattr`, `isinstance`, `len`, `self._connect_edges`, `self._sample_edge`, `sum`, `tuple`, `zip`.
- `_sample_edge` 调用：`RoutePlanningError`, `_distance`, `_is_driving_lane`, `_lane_identity`, `_visit_key`, `_wrap_degrees`, `_yaw`, `abs`, `current.next`, `int`, `max`, `min`, `points.append`, `range`, `seen.add`, `tuple`.
- `_connect_edges` 调用：`_LaneChangeTransition`, `_distance`, `_is_driving_lane`, `_lane_change_allowed`, `_lane_identity`, `_same_direction`, `_visit_key`, `bool`, `by_lane.get`, `by_lane.setdefault`, `by_lane.setdefault(_lane_identity(edge.entry), []).append`, `edge.exit.next`, `getattr`, `keys.add`, `len`, `max`, `min`, `mutable.items`, `mutable[edge.index].add`, `mutable[source_index].add`, `self._adjacent_lane`, `self._build_lane_change_connector`, `self._lane_change_transitions.get`, `set`, `sorted`, `transition_candidates.items`, `transition_candidates.setdefault`, `transition_candidates.setdefault((edge.index, target.index, side), []).append`, `tuple`, `unique.append`.
- `_locate_edge` 调用：`RoutePlanningError`, `_distance`, `_lane_identity`, `_wrap_degrees`, `_yaw`, `abs`, `min`, `sorted`, `tuple`.
- `_search` 调用：`RoutePlanningError`, `_distance`, `adjacency.get`, `costs.get`, `frozenset`, `heapq.heappop`, `heapq.heappush`, `itertools.count`, `next`, `range`, `reversed`, `reversed_path.append`, `tuple`.
- `_assemble_waypoints` 调用：`RoutePlanningError`, `_distance`, `_visit_key`, `assembled.append`, `deduplicated.append`, `enumerate`, `len`, `math.ceil`, `max`, `min`, `outgoing.side.lower`, `range`, `self._build_lane_change_connector`, `self._lane_change_transitions.get`, `tuple`.
- `_build_lane_change_connector` 调用：`RoutePlanningError`, `_BlendedWaypoint`, `_distance`, `_is_driving_lane`, `_lane_change_allowed`, `_lane_identity`, `_same_direction`, `_wrap_degrees`, `_yaw`, `bool`, `connector.append`, `current.next`, `float`, `getattr`, `math.ceil`, `max`, `min`, `range`, `self._adjacent_lane`, `tuple`.
- `_build_global_route` 调用：`'|'.join`, `'|'.join((f'{x_m:.2f},{y_m:.2f}' for x_m, y_m in points)).encode`, `GlobalRoute`, `RoutePlanningError`, `RouteReference`, `RouteValidation`, `_curvature`, `_distance`, `_is_driving_lane`, `_visit_key`, `_xy`, `any`, `cumulative_distances_m`, `enumerate`, `getattr`, `hashlib.sha256`, `hashlib.sha256(route_fingerprint).hexdigest`, `len`, `math.dist`, `max`, `range`, `self._route_sample`, `set`, `sum`, `tuple`, `validation.to_dict`, `zip`.
- `_route_sample` 调用：`RouteManager._adjacent_lane`, `RouteSample`, `_yaw`, `bool`, `float`, `getattr`.
- `_adjacent_lane` 调用：`_is_driving_lane`, `_same_direction`, `callable`, `getattr`, `getter`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__init__`，第 539 行：`ValueError('sample_step_m must be finite and positive')`。
- `__init__`，第 541 行：`ValueError('finish_radius_m must be finite and positive')`。
- `__init__`，第 543 行：`ValueError('maximum_expansions must be a positive integer')`。
- `__init__`，第 553 行：`ValueError('off_route_threshold_m must be finite and positive')`。
- `__post_init__`，第 167 行：`ValueError('lane corridor requirement_id must be non-empty')`。
- `__post_init__`，第 169 行：`ValueError('lane corridor relation must be LEFT or RIGHT')`。
- `__post_init__`，第 172 行：`ValueError('lane corridor distances must be finite and ordered')`。
- `__post_init__`，第 174 行：`TypeError('lane corridor junction_free must be bool')`。
- `__post_init__`，第 209 行：`ValueError('speed window requirement_id must be non-empty')`。
- `__post_init__`，第 211 行：`ValueError('speed window values must be finite')`。
- `__post_init__`，第 214 行：`ValueError('speed window values are outside their valid range')`。
- `__post_init__`，第 270 行：`ValueError('off_route_threshold_m must be finite and positive')`。
- `__post_init__`，第 272 行：`ValueError('confirmation_s must be finite and non-negative')`。
- `__post_init__`，第 274 行：`ValueError('cooldown_s must be finite and non-negative')`。
- `__post_init__`，第 276 行：`ValueError('maximum_attempts must be a positive integer')`。
- `_assemble_waypoints`，第 1509 行：`RoutePlanningError('ROUTE_LANE_CHANGE_UNAVAILABLE', f'no complete legal {outgoing.side.lower()} lane-change corridor from edge {edge_index} to {outgoing.target_edge_index}', context={'source_edge_index': edge_index, 'target_edge_index': outgoing.target_edge_index})`。
- `_assemble_waypoints`，第 1523 行：`RoutePlanningError('ROUTE_LANE_CHANGE_SEQUENCE_INVALID', f'lane-change sequence reverses progress on edge {edge_index}', context={'source_edge_index': edge_index, 'target_edge_index': target_edge_index})`。
- `_assemble_waypoints`，第 1554 行：`RoutePlanningError('ROUTE_ENDED_EARLY', 'route contains fewer than two points')`。
- `_build_global_route`，第 1641 行：`RoutePlanningError('ROUTE_DISCONTINUOUS', f'maximum waypoint gap {maximum_gap:.2f} m exceeds {self.maximum_gap_m:.2f} m')`。
- `_build_global_route`，第 1648 行：`RoutePlanningError('ROUTE_LOOP_DETECTED', f'route repeats {repeated} waypoint samples')`。
- `_build_global_route`，第 1652 行：`RoutePlanningError('ROUTE_WRONG_LANE_TYPE', 'route contains a non-driving waypoint')`。
- `_build_global_route`，第 1657 行：`RoutePlanningError('ROUTE_ENDED_EARLY', f'destination error {destination_error:.2f} m exceeds finish radius')`。
- `_build_lane_change_connector`，第 1585 行：`RoutePlanningError('ROUTE_LANE_CHANGE_UNAVAILABLE', 'source lane ends before the lane change can complete')`。
- `_build_lane_change_connector`，第 1591 行：`RoutePlanningError('ROUTE_LANE_CHANGE_UNAVAILABLE', 'lane change would enter a junction')`。
- `_build_lane_change_connector`，第 1596 行：`RoutePlanningError('ROUTE_LANE_CHANGE_UNAVAILABLE', 'lane marking stops permitting the requested lane change')`。
- `_build_lane_change_connector`，第 1602 行：`RoutePlanningError('ROUTE_LANE_CHANGE_UNAVAILABLE', 'adjacent driving lane is not continuous through the transition')`。
- `_locate_edge`，第 1396 行：`RoutePlanningError(code, 'no topology edge matches the endpoint')`。
- `_project_endpoint`，第 1177 行：`RoutePlanningError(code, 'endpoint is not on a driving lane')`。
- `_project_endpoint`，第 1184 行：`RoutePlanningError(code, 'endpoint heading opposes the projected lane')`。
- `_sample_edge`，第 1248 行：`RoutePlanningError('ROUTE_LOOP_DETECTED', 'topology edge repeats a waypoint')`。
- `_search`，第 1444 行：`RoutePlanningError('ROUTE_UNREACHABLE', f'no topology path from edge {start_index} to edge {goal_index}')`。
- `_topology_graph`，第 1192 行：`RoutePlanningError('ROUTE_TOPOLOGY_UNAVAILABLE', 'map has no get_topology()')`。
- `_topology_graph`，第 1195 行：`RoutePlanningError('ROUTE_TOPOLOGY_UNAVAILABLE', 'map topology is empty')`。
- `_topology_graph`，第 1199 行：`RoutePlanningError('ROUTE_TOPOLOGY_INVALID', 'topology edge must be a pair')`。
- `_topology_graph`，第 1212 行：`RoutePlanningError('ROUTE_TOPOLOGY_INVALID', 'topology has no driving edges')`。
- `_validate_lane_corridor`，第 760 行：`RoutePlanningError('ROUTE_LANE_CORRIDOR_BEYOND_ROUTE', f'{requirement.requirement_id} ends beyond the route contract')`。
- `_validate_lane_corridor`，第 770 行：`RoutePlanningError('ROUTE_LANE_CORRIDOR_UNAVAILABLE', f'{requirement.requirement_id} has no legal {requirement.relation.lower()} lane at s={cumulative[index]:.2f}m')`。
- `_validate_lane_corridor`，第 779 行：`RoutePlanningError('ROUTE_LANE_CORRIDOR_CROSSES_JUNCTION', f'{requirement.requirement_id} reaches a junction at s={cumulative[index]:.2f}m')`。
- `_validate_speed_window`，第 792 行：`RoutePlanningError('ROUTE_SPEED_WINDOW_BEYOND_ROUTE', f'{requirement.requirement_id} ends beyond the route contract')`。
- `_validate_speed_window`，第 813 行：`RoutePlanningError('ROUTE_SPEED_WINDOW_INFEASIBLE', f'{requirement.requirement_id} supports at most {supported_mps * 3.6:.2f}km/h at s={cumulative[index]:.2f}m')`。
- `from_mapping`，第 182 行：`TypeError('route lane corridor must be an object')`。
- `from_mapping`，第 224 行：`TypeError('route speed window must be an object')`。
- `from_mapping`，第 249 行：`TypeError('route.recovery must be an object')`。
- `from_mapping`，第 255 行：`ValueError('unsupported route.recovery field(s): ' + ', '.join(sorted(unknown)))`。
- `local_reference`，第 941 行：`ValueError('local route reference values must be finite numbers')`。
- `local_reference`，第 943 行：`ValueError('target_speed_mps must be non-negative')`。
- `local_reference`，第 945 行：`ValueError('lookbehind_m must be non-negative and lookahead_m positive')`。
- `local_reference`，第 968 行：`RoutePlanningError('ROUTE_LOCAL_REFERENCE_EMPTY', f'cannot build a control window at route_s={center_s:.2f}')`。
- `mission_placement`，第 1006 行：`ValueError('mission route positions must be finite')`。
- `mission_placement`，第 1009 行：`RoutePlanningError('ROUTE_EVENT_ALREADY_PASSED', f'event s={mission_route_s:.2f} precedes active route origin s={mission_progress_offset_m:.2f}')`。
- `mission_placement`，第 1015 行：`RoutePlanningError('ROUTE_EVENT_BEYOND_ACTIVE_ROUTE', f'event local s={local_s:.2f} exceeds active route length {route.total_length_m:.2f}')`。
- `observe`，第 309 行：`ValueError('sim_time_s must be finite and non-negative')`。
- `placement`，第 897 行：`ValueError('route_s must be finite')`。
- `placement`，第 900 行：`ValueError('lane_relation must be LEFT, CURRENT or RIGHT')`。
- `placement`，第 908 行：`RoutePlanningError('ROUTE_LANE_UNAVAILABLE', f'no legal {relation.lower()} driving lane at route_s={clamped_s:.2f}')`。
- `plan`，第 568 行：`ValueError('target_speed_mps must be finite and non-negative')`。
- `plan_distance`，第 626 行：`ValueError('distance_m must be finite and positive')`。
- `plan_distance`，第 628 行：`ValueError('target_speed_mps must be finite and non-negative')`。
- `plan_distance`，第 648 行：`RoutePlanningError('ROUTE_ENDED_EARLY', f'coverage route ended at {accumulated_m:.2f} m before the {requested_distance_m:.2f} m contract')`。
- `plan_distance`，第 664 行：`RoutePlanningError('ROUTE_DISCONTINUOUS', f'coverage route step {step_length_m:.2f} m is invalid')`。
- `plan_distance`，第 673 行：`RoutePlanningError('ROUTE_ENDED_EARLY', f'coverage route reached only {accumulated_m:.2f} m of {requested_distance_m:.2f} m')`。
- `plan_distance_compatible`，第 708 行：`ValueError('at least one route start candidate is required')`。
- `plan_distance_compatible`，第 733 行：`RoutePlanningError('ROUTE_NO_COMPATIBLE_ANCHOR', f'none of {len(starts)} route starts satisfies the declared topology', context={'failures': failures})`。
- `replan`，第 1037 行：`RoutePlanningError('ROUTE_RECOVERY_CONNECTOR_UNSAFE', f'current pose is {connector_length_m:.2f} m from the replanned lane')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [car_control_A/routing.py](../../../car_control_A/routing.py)
- [integration/route_geometry.py](../../../integration/route_geometry.py)

静态 import 消费者（含测试）：

- [integration/carla_runner.py](../../../integration/carla_runner.py)
- [integration/route_planner.py](../../../integration/route_planner.py)
- [integration/tests/test_route_manager.py](../../../integration/tests/test_route_manager.py)
- [tools/validate_route_generalization.py](../../../tools/validate_route_generalization.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-lateral.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `integration/route_manager.py`

来源 SHA256：`b224ff2111f5b7a64f750deff29fed8e04fc37226e76bc1d820214b8c0ba24f6`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `RouteSample.x_m` | `float` | `无声明默认；构造/赋值方提供` |
| `RouteSample.y_m` | `float` | `无声明默认；构造/赋值方提供` |
| `RouteSample.z_m` | `float` | `无声明默认；构造/赋值方提供` |
| `RouteSample.yaw_deg` | `float` | `无声明默认；构造/赋值方提供` |
| `RouteSample.s_m` | `float` | `无声明默认；构造/赋值方提供` |
| `RouteSample.road_id` | `int &#124; None` | `无声明默认；构造/赋值方提供` |
| `RouteSample.section_id` | `int &#124; None` | `无声明默认；构造/赋值方提供` |
| `RouteSample.lane_id` | `int &#124; None` | `无声明默认；构造/赋值方提供` |
| `RouteSample.is_junction` | `bool` | `无声明默认；构造/赋值方提供` |
| `RouteSample.left_lane_id` | `int &#124; None` | `无声明默认；构造/赋值方提供` |
| `RouteSample.right_lane_id` | `int &#124; None` | `无声明默认；构造/赋值方提供` |
| `RouteValidation.total_length_m` | `float` | `无声明默认；构造/赋值方提供` |
| `RouteValidation.point_count` | `int` | `无声明默认；构造/赋值方提供` |
| `RouteValidation.maximum_gap_m` | `float` | `无声明默认；构造/赋值方提供` |
| `RouteValidation.destination_error_m` | `float` | `无声明默认；构造/赋值方提供` |
| `RouteValidation.repeated_sample_count` | `int` | `无声明默认；构造/赋值方提供` |
| `RouteValidation.junction_count` | `int` | `无声明默认；构造/赋值方提供` |
| `GlobalRoute.reference` | `RouteReference` | `无声明默认；构造/赋值方提供` |
| `GlobalRoute.samples` | `tuple[RouteSample, ...]` | `无声明默认；构造/赋值方提供` |
| `GlobalRoute.validation` | `RouteValidation` | `无声明默认；构造/赋值方提供` |
| `GlobalRoute.start_xy_m` | `Point2D` | `无声明默认；构造/赋值方提供` |
| `GlobalRoute.destination_xy_m` | `Point2D` | `无声明默认；构造/赋值方提供` |
| `GlobalRoute.waypoints` | `tuple[Any, ...]` | `field(repr=False, compare=False)` |
| `RouteState.route_s` | `float` | `无声明默认；构造/赋值方提供` |
| `RouteState.route_progress` | `float` | `无声明默认；构造/赋值方提供` |
| `RouteState.route_remaining_m` | `float` | `无声明默认；构造/赋值方提供` |
| `RouteState.nearest_route_point` | `Point2D` | `无声明默认；构造/赋值方提供` |
| `RouteState.cross_track_error_m` | `float` | `无声明默认；构造/赋值方提供` |
| `RouteState.road_curvature` | `float` | `无声明默认；构造/赋值方提供` |
| `RouteState.road_id` | `int &#124; None` | `无声明默认；构造/赋值方提供` |
| `RouteState.lane_id` | `int &#124; None` | `无声明默认；构造/赋值方提供` |
| `RouteState.lane_relation` | `str` | `无声明默认；构造/赋值方提供` |
| `RouteState.left_lane_id` | `int &#124; None` | `无声明默认；构造/赋值方提供` |
| `RouteState.right_lane_id` | `int &#124; None` | `无声明默认；构造/赋值方提供` |
| `RouteState.nearest_index` | `int` | `无声明默认；构造/赋值方提供` |
| `RouteState.reached_destination` | `bool` | `无声明默认；构造/赋值方提供` |
| `RouteState.status` | `str` | `无声明默认；构造/赋值方提供` |
| `RouteState.reason` | `str &#124; None` | `无声明默认；构造/赋值方提供` |
| `RouteState.requires_replan` | `bool` | `无声明默认；构造/赋值方提供` |
| `RoutePlacement.route_s` | `float` | `无声明默认；构造/赋值方提供` |
| `RoutePlacement.lane_relation` | `str` | `无声明默认；构造/赋值方提供` |
| `RoutePlacement.x_m` | `float` | `无声明默认；构造/赋值方提供` |
| `RoutePlacement.y_m` | `float` | `无声明默认；构造/赋值方提供` |
| `RoutePlacement.z_m` | `float` | `无声明默认；构造/赋值方提供` |
| `RoutePlacement.yaw_deg` | `float` | `无声明默认；构造/赋值方提供` |
| `RoutePlacement.road_id` | `int &#124; None` | `无声明默认；构造/赋值方提供` |
| `RoutePlacement.lane_id` | `int &#124; None` | `无声明默认；构造/赋值方提供` |
| `LaneCorridorRequirement.requirement_id` | `str` | `无声明默认；构造/赋值方提供` |
| `LaneCorridorRequirement.relation` | `str` | `无声明默认；构造/赋值方提供` |
| `LaneCorridorRequirement.start_s_m` | `float` | `无声明默认；构造/赋值方提供` |
| `LaneCorridorRequirement.end_s_m` | `float` | `无声明默认；构造/赋值方提供` |
| `LaneCorridorRequirement.junction_free` | `bool` | `False` |
| `SpeedWindowRequirement.requirement_id` | `str` | `无声明默认；构造/赋值方提供` |
| `SpeedWindowRequirement.start_s_m` | `float` | `无声明默认；构造/赋值方提供` |
| `SpeedWindowRequirement.end_s_m` | `float` | `无声明默认；构造/赋值方提供` |
| `SpeedWindowRequirement.minimum_speed_kph` | `float` | `无声明默认；构造/赋值方提供` |
| `SpeedWindowRequirement.max_lateral_accel_mps2` | `float` | `2.0` |
| `SpeedWindowRequirement.lookahead_m` | `float` | `45.0` |
| `RouteRecoveryPolicy.off_route_threshold_m` | `float` | `6.0` |
| `RouteRecoveryPolicy.confirmation_s` | `float` | `0.5` |
| `RouteRecoveryPolicy.cooldown_s` | `float` | `5.0` |
| `RouteRecoveryPolicy.maximum_attempts` | `int` | `3` |
| `RouteRecoveryDecision.status` | `str` | `无声明默认；构造/赋值方提供` |
| `RouteRecoveryDecision.reason` | `str &#124; None` | `无声明默认；构造/赋值方提供` |
| `RouteRecoveryDecision.should_replan` | `bool` | `无声明默认；构造/赋值方提供` |
| `RouteRecoveryDecision.attempt` | `int` | `无声明默认；构造/赋值方提供` |
| `_TopologyEdge.index` | `int` | `无声明默认；构造/赋值方提供` |
| `_TopologyEdge.entry` | `Any` | `无声明默认；构造/赋值方提供` |
| `_TopologyEdge.exit` | `Any` | `无声明默认；构造/赋值方提供` |
| `_TopologyEdge.waypoints` | `tuple[Any, ...]` | `无声明默认；构造/赋值方提供` |
| `_TopologyEdge.length_m` | `float` | `无声明默认；构造/赋值方提供` |
| `_LaneChangeTransition.source_edge_index` | `int` | `无声明默认；构造/赋值方提供` |
| `_LaneChangeTransition.target_edge_index` | `int` | `无声明默认；构造/赋值方提供` |
| `_LaneChangeTransition.side` | `str` | `无声明默认；构造/赋值方提供` |
| `_LaneChangeTransition.candidates` | `tuple[tuple[Any, Any], ...]` | `field(repr=False, compare=False)` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `LaneCorridorRequirement.__post_init__` / 167 | `not self.requirement_id` | `raise ValueError('lane corridor requirement_id must be non-empty')` |
| `LaneCorridorRequirement.__post_init__` / 169 | `relation not in {'LEFT', 'RIGHT'}` | `raise ValueError('lane corridor relation must be LEFT or RIGHT')` |
| `LaneCorridorRequirement.__post_init__` / 172 | `not math.isfinite(start) or not math.isfinite(end) or start < 0.0 or (end < start)` | `raise ValueError('lane corridor distances must be finite and ordered')` |
| `LaneCorridorRequirement.__post_init__` / 174 | `type(self.junction_free) is not bool` | `raise TypeError('lane corridor junction_free must be bool')` |
| `LaneCorridorRequirement.from_mapping` / 182 | `not isinstance(value, Mapping)` | `raise TypeError('route lane corridor must be an object')` |
| `SpeedWindowRequirement.__post_init__` / 209 | `not self.requirement_id` | `raise ValueError('speed window requirement_id must be non-empty')` |
| `SpeedWindowRequirement.__post_init__` / 211 | `any((not math.isfinite(item) for item in values))` | `raise ValueError('speed window values must be finite')` |
| `SpeedWindowRequirement.__post_init__` / 214 | `start < 0.0 or end < start or speed <= 0.0 or (lateral_accel <= 0.0) or (lookahead <= 0.0)` | `raise ValueError('speed window values are outside their valid range')` |
| `SpeedWindowRequirement.from_mapping` / 224 | `not isinstance(value, Mapping)` | `raise TypeError('route speed window must be an object')` |
| `RouteRecoveryPolicy.from_mapping` / 249 | `not isinstance(value, Mapping)` | `raise TypeError('route.recovery must be an object')` |
| `RouteRecoveryPolicy.from_mapping` / 255 | `unknown` | `raise ValueError('unsupported route.recovery field(s): ' + ', '.join(sorted(unknown)))` |
| `RouteRecoveryPolicy.__post_init__` / 270 | `not math.isfinite(float(self.off_route_threshold_m)) or self.off_route_threshold_m <= 0.0` | `raise ValueError('off_route_threshold_m must be finite and positive')` |
| `RouteRecoveryPolicy.__post_init__` / 272 | `not math.isfinite(float(self.confirmation_s)) or self.confirmation_s < 0.0` | `raise ValueError('confirmation_s must be finite and non-negative')` |
| `RouteRecoveryPolicy.__post_init__` / 274 | `not math.isfinite(float(self.cooldown_s)) or self.cooldown_s < 0.0` | `raise ValueError('cooldown_s must be finite and non-negative')` |
| `RouteRecoveryPolicy.__post_init__` / 276 | `type(self.maximum_attempts) is not int or self.maximum_attempts < 1` | `raise ValueError('maximum_attempts must be a positive integer')` |
| `RouteRecoveryTracker.observe` / 309 | `not math.isfinite(now_s) or now_s < 0.0` | `raise ValueError('sim_time_s must be finite and non-negative')` |
| `RouteManager.__init__` / 539 | `not math.isfinite(float(sample_step_m)) or sample_step_m <= 0.0` | `raise ValueError('sample_step_m must be finite and positive')` |
| `RouteManager.__init__` / 541 | `not math.isfinite(float(finish_radius_m)) or finish_radius_m <= 0.0` | `raise ValueError('finish_radius_m must be finite and positive')` |
| `RouteManager.__init__` / 543 | `type(maximum_expansions) is not int or maximum_expansions < 1` | `raise ValueError('maximum_expansions must be a positive integer')` |
| `RouteManager.__init__` / 553 | `not math.isfinite(float(off_route_threshold_m)) or off_route_threshold_m <= 0.0` | `raise ValueError('off_route_threshold_m must be finite and positive')` |
| `RouteManager.plan` / 568 | `not math.isfinite(float(target_speed_mps)) or target_speed_mps < 0.0` | `raise ValueError('target_speed_mps must be finite and non-negative')` |
| `RouteManager.plan` / 598 | `except RoutePlanningError AND error.code not in {'ROUTE_LANE_CHANGE_UNAVAILABLE', 'ROUTE_LANE_CHANGE_SEQUENCE_INVALID'}` | `raise` |
| `RouteManager.plan` / 602 | `except RoutePlanningError AND type(source_index) is not int or type(target_index) is not int` | `raise` |
| `RouteManager.plan` / 605 | `except RoutePlanningError AND connection in blocked_connections` | `raise` |
| `RouteManager.plan_distance` / 626 | `not math.isfinite(float(distance_m)) or distance_m <= 0.0` | `raise ValueError('distance_m must be finite and positive')` |
| `RouteManager.plan_distance` / 628 | `not math.isfinite(float(target_speed_mps)) or target_speed_mps < 0.0` | `raise ValueError('target_speed_mps must be finite and non-negative')` |
| `RouteManager.plan_distance` / 648 | `not candidates` | `raise RoutePlanningError('ROUTE_ENDED_EARLY', f'coverage route ended at {accumulated_m:.2f} m before the {requested_distance_m:.2f} m contract')` |
| `RouteManager.plan_distance` / 664 | `step_length_m <= 1e-06 or step_length_m > self.maximum_gap_m` | `raise RoutePlanningError('ROUTE_DISCONTINUOUS', f'coverage route step {step_length_m:.2f} m is invalid')` |
| `RouteManager.plan_distance` / 673 | `accumulated_m + 1e-09 < requested_distance_m` | `raise RoutePlanningError('ROUTE_ENDED_EARLY', f'coverage route reached only {accumulated_m:.2f} m of {requested_distance_m:.2f} m')` |
| `RouteManager.plan_distance_compatible` / 708 | `not starts` | `raise ValueError('at least one route start candidate is required')` |
| `RouteManager.plan_distance_compatible` / 733 | `本地无直接if；检查上下文` | `raise RoutePlanningError('ROUTE_NO_COMPATIBLE_ANCHOR', f'none of {len(starts)} route starts satisfies the declared topology', context={'failures': failures})` |
| `RouteManager._validate_lane_corridor` / 760 | `requirement.end_s_m > route.total_length_m + 1e-06` | `raise RoutePlanningError('ROUTE_LANE_CORRIDOR_BEYOND_ROUTE', f'{requirement.requirement_id} ends beyond the route contract')` |
| `RouteManager._validate_lane_corridor` / 770 | `adjacent is None` | `raise RoutePlanningError('ROUTE_LANE_CORRIDOR_UNAVAILABLE', f'{requirement.requirement_id} has no legal {requirement.relation.lower()} lane at s={cumulative[index]:.2f}m')` |
| `RouteManager._validate_lane_corridor` / 779 | `requirement.junction_free and (bool(getattr(source, 'is_junction', False)) or bool(getattr(adjacent, 'is_junction', False)))` | `raise RoutePlanningError('ROUTE_LANE_CORRIDOR_CROSSES_JUNCTION', f'{requirement.requirement_id} reaches a junction at s={cumulative[index]:.2f}m')` |
| `RouteManager._validate_speed_window` / 792 | `requirement.end_s_m > route.total_length_m + 1e-06` | `raise RoutePlanningError('ROUTE_SPEED_WINDOW_BEYOND_ROUTE', f'{requirement.requirement_id} ends beyond the route contract')` |
| `RouteManager._validate_speed_window` / 813 | `supported_mps + 1e-06 < minimum_mps` | `raise RoutePlanningError('ROUTE_SPEED_WINDOW_INFEASIBLE', f'{requirement.requirement_id} supports at most {supported_mps * 3.6:.2f}km/h at s={cumulative[index]:.2f}m')` |
| `RouteManager.placement` / 897 | `not math.isfinite(float(route_s))` | `raise ValueError('route_s must be finite')` |
| `RouteManager.placement` / 900 | `relation not in {'LEFT', 'CURRENT', 'RIGHT'}` | `raise ValueError('lane_relation must be LEFT, CURRENT or RIGHT')` |
| `RouteManager.placement` / 908 | `relation != 'CURRENT' AND waypoint is None` | `raise RoutePlanningError('ROUTE_LANE_UNAVAILABLE', f'no legal {relation.lower()} driving lane at route_s={clamped_s:.2f}')` |
| `RouteManager.local_reference` / 941 | `any((type(value) not in (int, float) or isinstance(value, bool) or (not math.isfinite(float(value))) for value in values))` | `raise ValueError('local route reference values must be finite numbers')` |
| `RouteManager.local_reference` / 943 | `target_speed_mps < 0.0` | `raise ValueError('target_speed_mps must be non-negative')` |
| `RouteManager.local_reference` / 945 | `lookbehind_m < 0.0 or lookahead_m <= 0.0` | `raise ValueError('lookbehind_m must be non-negative and lookahead_m positive')` |
| `RouteManager.local_reference` / 968 | `len(deduplicated) < 2` | `raise RoutePlanningError('ROUTE_LOCAL_REFERENCE_EMPTY', f'cannot build a control window at route_s={center_s:.2f}')` |
| `RouteManager.mission_placement` / 1006 | `not math.isfinite(float(mission_route_s)) or not math.isfinite(float(mission_progress_offset_m))` | `raise ValueError('mission route positions must be finite')` |
| `RouteManager.mission_placement` / 1009 | `local_s < -1e-06` | `raise RoutePlanningError('ROUTE_EVENT_ALREADY_PASSED', f'event s={mission_route_s:.2f} precedes active route origin s={mission_progress_offset_m:.2f}')` |
| `RouteManager.mission_placement` / 1015 | `local_s > route.total_length_m + 1e-06` | `raise RoutePlanningError('ROUTE_EVENT_BEYOND_ACTIVE_ROUTE', f'event local s={local_s:.2f} exceeds active route length {route.total_length_m:.2f}')` |
| `RouteManager.replan` / 1037 | `connector_length_m > max(self.maximum_gap_m, self.off_route_threshold_m * 2.0)` | `raise RoutePlanningError('ROUTE_RECOVERY_CONNECTOR_UNSAFE', f'current pose is {connector_length_m:.2f} m from the replanned lane')` |
| `RouteManager._project_endpoint` / 1177 | `not _is_driving_lane(waypoint)` | `raise RoutePlanningError(code, 'endpoint is not on a driving lane')` |
| `RouteManager._project_endpoint` / 1184 | `transform is not None AND heading_error > 90.0` | `raise RoutePlanningError(code, 'endpoint heading opposes the projected lane')` |
| `RouteManager._topology_graph` / 1192 | `not callable(get_topology)` | `raise RoutePlanningError('ROUTE_TOPOLOGY_UNAVAILABLE', 'map has no get_topology()')` |
| `RouteManager._topology_graph` / 1195 | `not raw` | `raise RoutePlanningError('ROUTE_TOPOLOGY_UNAVAILABLE', 'map topology is empty')` |
| `RouteManager._topology_graph` / 1199 | `not isinstance(pair, Sequence) or len(pair) != 2` | `raise RoutePlanningError('ROUTE_TOPOLOGY_INVALID', 'topology edge must be a pair')` |
| `RouteManager._topology_graph` / 1212 | `not edges` | `raise RoutePlanningError('ROUTE_TOPOLOGY_INVALID', 'topology has no driving edges')` |
| `RouteManager._sample_edge` / 1248 | `key in seen` | `raise RoutePlanningError('ROUTE_LOOP_DETECTED', 'topology edge repeats a waypoint')` |
| `RouteManager._locate_edge` / 1396 | `not ranked or ranked[0][0] > self.maximum_gap_m` | `raise RoutePlanningError(code, 'no topology edge matches the endpoint')` |
| `RouteManager._search` / 1444 | `not found` | `raise RoutePlanningError('ROUTE_UNREACHABLE', f'no topology path from edge {start_index} to edge {goal_index}')` |
| `RouteManager._assemble_waypoints` / 1509 | `outgoing is not None AND not connector` | `raise RoutePlanningError('ROUTE_LANE_CHANGE_UNAVAILABLE', f'no complete legal {outgoing.side.lower()} lane-change corridor from edge {edge_index} to {outgoing.target_edge_index}', context={'source_edge_index': edge_index, 'target_edge_index': outgoing.target_edge_index})` |
| `RouteManager._assemble_waypoints` / 1523 | `start_index > end_index` | `raise RoutePlanningError('ROUTE_LANE_CHANGE_SEQUENCE_INVALID', f'lane-change sequence reverses progress on edge {edge_index}', context={'source_edge_index': edge_index, 'target_edge_index': target_edge_index})` |
| `RouteManager._assemble_waypoints` / 1554 | `len(deduplicated) < 2` | `raise RoutePlanningError('ROUTE_ENDED_EARLY', 'route contains fewer than two points')` |
| `RouteManager._build_lane_change_connector` / 1585 | `index AND not candidates` | `raise RoutePlanningError('ROUTE_LANE_CHANGE_UNAVAILABLE', 'source lane ends before the lane change can complete')` |
| `RouteManager._build_lane_change_connector` / 1591 | `bool(getattr(current, 'is_junction', False))` | `raise RoutePlanningError('ROUTE_LANE_CHANGE_UNAVAILABLE', 'lane change would enter a junction')` |
| `RouteManager._build_lane_change_connector` / 1596 | `not _lane_change_allowed(current, transition.side)` | `raise RoutePlanningError('ROUTE_LANE_CHANGE_UNAVAILABLE', 'lane marking stops permitting the requested lane change')` |
| `RouteManager._build_lane_change_connector` / 1602 | `target is None or _lane_identity(target) != target_identity` | `raise RoutePlanningError('ROUTE_LANE_CHANGE_UNAVAILABLE', 'adjacent driving lane is not continuous through the transition')` |
| `RouteManager._build_global_route` / 1641 | `maximum_gap > self.maximum_gap_m` | `raise RoutePlanningError('ROUTE_DISCONTINUOUS', f'maximum waypoint gap {maximum_gap:.2f} m exceeds {self.maximum_gap_m:.2f} m')` |
| `RouteManager._build_global_route` / 1648 | `repeated and (not allow_repeated_samples)` | `raise RoutePlanningError('ROUTE_LOOP_DETECTED', f'route repeats {repeated} waypoint samples')` |
| `RouteManager._build_global_route` / 1652 | `any((not _is_driving_lane(item) for item in waypoints))` | `raise RoutePlanningError('ROUTE_WRONG_LANE_TYPE', 'route contains a non-driving waypoint')` |
| `RouteManager._build_global_route` / 1657 | `destination_error > self.finish_radius_m` | `raise RoutePlanningError('ROUTE_ENDED_EARLY', f'destination error {destination_error:.2f} m exceeds finish radius')` |
