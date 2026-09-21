# Route geometry and lateral control

## 开发维护先读：实际语义

以下功能页说明实现理由、分支、接口含义、改动联动与验证。先读这些内容，再按逐文件索引定位方法；不要用函数名推断业务语义。

- [路线、跟踪控制与完成里程](../functions/route-control-progress.md)
- [路线与横向控制专题精读](../../modules/04_ROUTE_AND_LATERAL_CONTROL.md)

[Vehicle module](../modules/vehicle.md)

## Responsibility, contracts and failure behavior

LateralController.step consumes VehiclePose and RouteReference and returns LateralOutput; steer is normalized. CARLA local positive y and positive steer point right. Canonical perception y points left and requires explicit conversion. PurePursuit and Stanley are alternatives; lane_change generates transitions. RouteManager and planning_stage prepare/maintain routes. RouteProgressTracker measures route projection; DistanceCoverageTracker measures actual distance while rejecting teleport jumps. Their acceptance semantics differ.


## 第4模块逐项精读：生产接线与参数索引

本模块有两层路线实现。`RouteManager` 持有 CARLA 拓扑、任务全局弧长和重规划语义；`route_planner.py` 还提供验收场景的有界局部路线与变道构造。生产 runner 的终点/距离合同走 `RouteManager`，`build_destination_route_reference()` 只是兼容委托入口。Pure Pursuit 是生产横向控制器；Stanley 有独立实现和测试，但当前没有自动降级接线。

### 全局路线与恢复入口

| 入口 / 参数 | 声明默认或生产来源 | 单位与实际作用 |
|---|---|---|
| `RouteManager.sample_step_m` | `2.0`；runner 传 `spec.route_resample_interval_m` | m；拓扑边采样、连接和局部窗最小长度 |
| `finish_radius_m` | `4.0`；runner 传 `spec.finish_radius_m` | m；需同时满足端点误差和剩余里程条件 |
| `maximum_gap_m` | `None` → `max(5.0, 3*sample_step_m)` | m；相邻 waypoint/连接最大允许间距 |
| `maximum_expansions` | `50_000` | A* 最大展开次数，不是路线点上限 |
| `off_route_threshold_m` | `6.0` | m；未到终点且 CTE 超阈值时要求重规划 |
| `state.previous_s_m` | `None` | m；传上一帧值才能在交叉/回环保持单调进度 |
| `state.forward_window_m` | `80.0` | m；投影候选的最大前向弧长窗 |
| `local_reference.lookbehind_m/lookahead_m` | `8.0 / 80.0` | m；从全局路线裁给控制器的局部窗口 |
| `RouteRecoveryPolicy` | `6m / 0.5s / 5s / 3次` | 偏离阈值、确认时长、冷却和任务内尝试上限 |

`plan()` 生成起点到终点的确定性拓扑 A* 路线；`plan_distance()` 生成允许重复合法拓扑的距离覆盖路线；`plan_distance_compatible()` 按调用者给定顺序选择首个满足车道走廊和速度窗口的起点。`mission_placement()` 将任务绝对 `route_s` 减去重规划累计 offset，已经错过或超出当前活动路线的事件不会重新触发。

### 场景兼容与进度参数

| 合同 / 参数 | 默认 | 约束与消费点 |
|---|---:|---|
| `LaneCorridorRequirement.relation` | 无 | 仅 LEFT/RIGHT，可兼容去掉 `_ADJACENT` 后缀 |
| `start_s_m/end_s_m` | mapping 缺失时 0 | 必须有限、非负且 `end>=start`，不能越过路线总长 |
| `junction_free` | `False` | 严格 bool；为 True 时源/邻道均不能进入 junction |
| `SpeedWindowRequirement.max_lateral_accel_mps2` | `2.0` | m/s²；结合曲率计算窗口可支持速度 |
| `SpeedWindowRequirement.lookahead_m` | `45.0` | m；每个 s 位置向前检查的曲率范围 |
| `RouteProgressTracker.forward_window_m` | 动态 `max(20, speed*delta*8)` | 依赖上一进度的路线投影窗 |
| `DistanceCoverageTracker.minimum_jump_gate_m` | `2.0` | 实际门限为 `max(2, speed*delta*3+1)`；超限位移按 teleport 忽略 |

路线投影进度和实际累计里程承担不同合同。前者用于终点路线、事件和全局状态；后者用于长期距离覆盖，允许合法换道后继续累计，但过滤恢复 teleport。不得用其中一个数值替换另一个而不修改验收合同。

### 生产横向有效配置

`config/strategy_config.yaml` 的当前值为：轴距 2.8m，基础/最小/最大前视 2.5/2.5/8.0m，速度增益 0.45s，最大转向角尺度 0.60rad，归一化 steer 上限 0.60、下限 0.35，基础/最小/最大每步变化率 0.038/0.025/0.038，`steer_sign=1.0`。runner 另外固定 `nearest_search_window=2`、`route_reacquire_search_window=50`；这两个值尚未进入统一策略配置。

`max_steer_delta_per_step` 是每次 `step()` 的变化量，不随 dt 自动归一化。改变控制频率会改变实际每秒转向变化能力。Pure Pursuit 按实际点容器对象保存各路线最近索引，临时路线恢复时可找回原进度；`reset(preserve_steer=True)` 会清路线进度但保留上一 steer，使下一条路线仍经过变化率限制。

## 模块接口与参数核对（2026-09-20）

B接收VehiclePose和RouteReference，返回LateralOutput。输入位置m、yaw_rad弧度、速度m/s；输出steer归一化，cross_track_error_m和heading_error_rad供诊断。nearest_index/target_index指向当前路线，换路线不能沿用旧索引。

### 参数语义与生效边界

RouteReference默认target_speed_mps=5、curvature_per_m=0，metadata默认新字典。PurePursuit/Stanley的阈值多数取DEFAULT_STRATEGY.lateral，nearest_search_window=None应按实现处理而非擅自解释为固定窗口。max_steer_delta_per_step按步限制，改变dt需核对动态效果。

### 上下游与修改影响

CARLA右向坐标与canonical左向坐标边界需明确。修改路线/steer要联动route manager、C曲率限速、D偏离保护和证据；路线投影progress与实际里程不是同一验收量。

### [car_control_B/schemas.py](../../../car_control_B/schemas.py) 的入口与声明

```python
VehiclePose.to_dict(self) -> Dict[str, Any]
RouteReference.to_dict(self) -> Dict[str, Any]
LateralOutput.to_dict(self) -> Dict[str, Any]
```

类级字段（含配置、输入输出和内部状态；仅声明默认，不是当前run生效配置）：

| 字段 | 类型 | 默认值/来源 |
|---|---|---|
| `VehiclePose.x_m` | `float` | `无声明默认（构造/赋值方提供）` |
| `VehiclePose.y_m` | `float` | `无声明默认（构造/赋值方提供）` |
| `VehiclePose.yaw_rad` | `float` | `无声明默认（构造/赋值方提供）` |
| `VehiclePose.speed_mps` | `float` | `无声明默认（构造/赋值方提供）` |
| `VehiclePose.frame` | `Optional[int]` | `None` |
| `VehiclePose.sim_time_s` | `Optional[float]` | `None` |
| `RouteReference.points_xy_m` | `List[Point2D]` | `无声明默认（构造/赋值方提供）` |
| `RouteReference.curvature_per_m` | `float` | `0.0` |
| `RouteReference.target_speed_mps` | `float` | `5.0` |
| `RouteReference.route_id` | `Optional[str]` | `None` |
| `RouteReference.metadata` | `Dict[str, Any]` | `field(default_factory=dict)` |
| `LateralOutput.steer` | `float` | `无声明默认（构造/赋值方提供）` |
| `LateralOutput.cross_track_error_m` | `float` | `无声明默认（构造/赋值方提供）` |
| `LateralOutput.heading_error_rad` | `float` | `无声明默认（构造/赋值方提供）` |
| `LateralOutput.target_point_xy_m` | `Point2D` | `无声明默认（构造/赋值方提供）` |
| `LateralOutput.lookahead_distance_m` | `float` | `无声明默认（构造/赋值方提供）` |
| `LateralOutput.nearest_index` | `int` | `无声明默认（构造/赋值方提供）` |
| `LateralOutput.target_index` | `int` | `无声明默认（构造/赋值方提供）` |
| `LateralOutput.status` | `str` | `'OK'` |
| `LateralOutput.reason` | `str` | `'NONE'` |

### [car_control_B/pure_pursuit.py](../../../car_control_B/pure_pursuit.py) 的入口与声明

```python
PurePursuitController.__init__(self, params: PurePursuitParams | None=None)
PurePursuitController.reset(self, *, preserve_steer: bool=False) -> None
PurePursuitController.synchronize_route_progress(self, reference: Any, progress_m: float) -> int
PurePursuitController.step(self, vehicle: VehiclePose, reference: RouteReference) -> LateralOutput
```

类级字段（含配置、输入输出和内部状态；仅声明默认，不是当前run生效配置）：

| 字段 | 类型 | 默认值/来源 |
|---|---|---|
| `PurePursuitParams.wheel_base_m` | `float` | `DEFAULT_STRATEGY.lateral.wheel_base_m` |
| `PurePursuitParams.base_lookahead_m` | `float` | `DEFAULT_STRATEGY.lateral.base_lookahead_m` |
| `PurePursuitParams.speed_gain_s` | `float` | `DEFAULT_STRATEGY.lateral.speed_gain_s` |
| `PurePursuitParams.min_lookahead_m` | `float` | `DEFAULT_STRATEGY.lateral.min_lookahead_m` |
| `PurePursuitParams.max_lookahead_m` | `float` | `DEFAULT_STRATEGY.lateral.max_lookahead_m` |
| `PurePursuitParams.curvature_lookahead_gain` | `float` | `DEFAULT_STRATEGY.lateral.curvature_lookahead_gain` |
| `PurePursuitParams.error_lookahead_gain` | `float` | `DEFAULT_STRATEGY.lateral.error_lookahead_gain` |
| `PurePursuitParams.max_steer_angle_rad` | `float` | `DEFAULT_STRATEGY.lateral.max_steer_angle_rad` |
| `PurePursuitParams.steer_gain` | `float` | `DEFAULT_STRATEGY.lateral.steer_gain` |
| `PurePursuitParams.max_steer` | `float` | `DEFAULT_STRATEGY.lateral.max_steer` |
| `PurePursuitParams.min_steer_limit` | `float` | `DEFAULT_STRATEGY.lateral.min_steer_limit` |
| `PurePursuitParams.high_speed_steer_reduction_per_mps` | `float` | `DEFAULT_STRATEGY.lateral.high_speed_steer_reduction_per_mps` |
| `PurePursuitParams.curvature_steer_gain` | `float` | `DEFAULT_STRATEGY.lateral.curvature_steer_gain` |
| `PurePursuitParams.max_steer_delta_per_step` | `float` | `DEFAULT_STRATEGY.lateral.base_steer_delta_per_step` |
| `PurePursuitParams.min_steer_delta_per_step` | `float` | `DEFAULT_STRATEGY.lateral.min_steer_delta_per_step` |
| `PurePursuitParams.adaptive_max_steer_delta_per_step` | `float` | `DEFAULT_STRATEGY.lateral.max_steer_delta_per_step` |
| `PurePursuitParams.low_speed_steer_gain` | `float` | `DEFAULT_STRATEGY.lateral.low_speed_steer_gain` |
| `PurePursuitParams.curvature_rate_gain` | `float` | `DEFAULT_STRATEGY.lateral.curvature_rate_gain` |
| `PurePursuitParams.error_rate_gain` | `float` | `DEFAULT_STRATEGY.lateral.error_rate_gain` |
| `PurePursuitParams.cross_track_gain` | `float` | `0.8` |
| `PurePursuitParams.cross_track_softening_speed_mps` | `float` | `1.0` |
| `PurePursuitParams.steer_sign` | `float` | `DEFAULT_STRATEGY.lateral.steer_sign` |
| `PurePursuitParams.nearest_search_window` | `int &#124; None` | `None` |
| `PurePursuitParams.route_reacquire_search_window` | `int &#124; None` | `None` |

### [car_control_B/stanley.py](../../../car_control_B/stanley.py) 的入口与声明

```python
StanleyController.__init__(self, params: StanleyParams | None=None)
StanleyController.reset(self, *, preserve_steer: bool=False) -> None
StanleyController.step(self, vehicle: VehiclePose, reference: RouteReference) -> LateralOutput
```

类级字段（含配置、输入输出和内部状态；仅声明默认，不是当前run生效配置）：

| 字段 | 类型 | 默认值/来源 |
|---|---|---|
| `StanleyParams.gain` | `float` | `DEFAULT_STRATEGY.lateral.stanley_gain` |
| `StanleyParams.softening_speed_mps` | `float` | `DEFAULT_STRATEGY.lateral.stanley_softening_speed_mps` |
| `StanleyParams.curvature_gain` | `float` | `DEFAULT_STRATEGY.lateral.stanley_curvature_gain` |
| `StanleyParams.max_steer_angle_rad` | `float` | `DEFAULT_STRATEGY.lateral.max_steer_angle_rad` |
| `StanleyParams.max_steer` | `float` | `DEFAULT_STRATEGY.lateral.max_steer` |
| `StanleyParams.min_steer_limit` | `float` | `DEFAULT_STRATEGY.lateral.min_steer_limit` |
| `StanleyParams.high_speed_steer_reduction_per_mps` | `float` | `DEFAULT_STRATEGY.lateral.high_speed_steer_reduction_per_mps` |
| `StanleyParams.curvature_steer_gain` | `float` | `DEFAULT_STRATEGY.lateral.curvature_steer_gain` |
| `StanleyParams.max_steer_delta_per_step` | `float` | `DEFAULT_STRATEGY.lateral.base_steer_delta_per_step` |
| `StanleyParams.min_steer_delta_per_step` | `float` | `DEFAULT_STRATEGY.lateral.min_steer_delta_per_step` |
| `StanleyParams.adaptive_max_steer_delta_per_step` | `float` | `DEFAULT_STRATEGY.lateral.max_steer_delta_per_step` |
| `StanleyParams.low_speed_steer_gain` | `float` | `DEFAULT_STRATEGY.lateral.low_speed_steer_gain` |
| `StanleyParams.curvature_rate_gain` | `float` | `DEFAULT_STRATEGY.lateral.curvature_rate_gain` |
| `StanleyParams.error_rate_gain` | `float` | `DEFAULT_STRATEGY.lateral.error_rate_gain` |
| `StanleyParams.steer_sign` | `float` | `DEFAULT_STRATEGY.lateral.steer_sign` |
| `StanleyParams.nearest_search_window` | `int &#124; None` | `None` |

以上为核心交接入口；模块内其余实现、CLI和资源的完整字段/拒绝条件见本页功能小文档索引。类型未声明的返回值不凭名称推断。当前代码基线fe1ba839，静态复核不证明实际CARLA/GPU/板端运行成功。

## Complete implementation inventory

- [car_control_B/__init__.py](../../../car_control_B/__init__.py) - module/resource/documentation
- [car_control_B/adapters.py](../../../car_control_B/adapters.py) - `_get`, `adapt_vehicle_pose`, `adapt_route_reference`
- [car_control_B/demo_fake_lateral.py](../../../car_control_B/demo_fake_lateral.py) - `straight_path`, `curved_path`, `run_case`, `main`
- [car_control_B/lane_change.py](../../../car_control_B/lane_change.py) - `smoothstep5`, `offset_path`, `generate_lane_change_path`
- [car_control_B/lateral_controller_base.py](../../../car_control_B/lateral_controller_base.py) - `LateralController`, `LateralController.reset`, `LateralController.step`, `LateralController.step_any`, `LateralController.steer`
- [car_control_B/path_utils.py](../../../car_control_B/path_utils.py) - `clamp`, `wrap_angle_rad`, `distance`, `cumulative_lengths`, `resample_path`, `find_nearest_index`, `find_lookahead_index`, `compute_path_heading`, `signed_cross_track_error`, `estimate_curvature`, `max_abs_curvature_ahead`
- [car_control_B/pure_pursuit.py](../../../car_control_B/pure_pursuit.py) - `PurePursuitParams`, `PurePursuitController`, `PurePursuitController.reset`, `PurePursuitController.synchronize_route_progress`, `PurePursuitController.step`
- [car_control_B/README.md](../../../car_control_B/README.md) - module/resource/documentation
- [car_control_B/schemas.py](../../../car_control_B/schemas.py) - `SchemaError`, `_finite`, `_point_list`, `VehiclePose`, `VehiclePose.to_dict`, `RouteReference`, `RouteReference.to_dict`, `LateralOutput`, `LateralOutput.to_dict`
- [car_control_B/stanley.py](../../../car_control_B/stanley.py) - `StanleyParams`, `StanleyController`, `StanleyController.reset`, `StanleyController.step`
- [car_control_B/validation/README.md](../../../car_control_B/validation/README.md) - module/resource/documentation
- [integration/execution_stage.py](../../../integration/execution_stage.py) - `RouteProgressTracker`, `RouteProgressTracker.update`, `DistanceCoverageTracker`, `DistanceCoverageTracker.update`
- [integration/planning_stage.py](../../../integration/planning_stage.py) - `PreparedScenarioRoute`, `prepare_scenario_route`
- [integration/route_geometry.py](../../../integration/route_geometry.py) - `_finite`, `polyline_length_m`, `cumulative_distances_m`, `RoutePose`, `RouteQuality`, `RouteQuality.to_dict`, `route_pose_at_s`, `offset_route_pose`, `actor_route_coordinates`, `project_route_progress_m`, `evaluate_route_quality`
- [integration/route_manager.py](../../../integration/route_manager.py) - `RoutePlanningError`, `RouteSample`, `RouteSample.point_xy_m`, `RouteValidation`, `RouteValidation.to_dict`, `GlobalRoute`, `GlobalRoute.total_length_m`, `RouteState`, `RouteState.to_dict`, `RoutePlacement`, `LaneCorridorRequirement`, `LaneCorridorRequirement.from_mapping`, `SpeedWindowRequirement`, `SpeedWindowRequirement.from_mapping`, `RouteRecoveryPolicy`, `RouteRecoveryPolicy.from_mapping`, `RouteRecoveryDecision`, `RouteRecoveryTracker`, `RouteRecoveryTracker.attempts`, `RouteRecoveryTracker.observe`, `RouteRecoveryTracker.note_replan_succeeded`, `RouteRecoveryTracker.reset_mission`, `_TopologyEdge`, `_LaneChangeTransition`, `_BlendedWaypoint`, `_BlendedWaypoint.get_left_lane`, `_BlendedWaypoint.get_right_lane`, `_location`, `_transform`, `_xy`, `_distance`, `_wrap_degrees`, `_yaw`, `_is_driving_lane`, `_lane_identity`, `_visit_key`, `_same_direction`, `_lane_change_allowed`, `_curvature`, `RouteManager`, `RouteManager.plan`, `RouteManager.plan_distance`, `RouteManager.plan_distance_compatible`, `RouteManager.validate_compatibility`, `RouteManager.state`, `RouteManager.placement`, `RouteManager.local_reference`, `RouteManager.mission_placement`, `RouteManager.replan`
- [integration/route_planner.py](../../../integration/route_planner.py) - `_WaypointSpatialIndex`, `_wrap_degrees`, `_yaw`, `_branch_delta`, `_choose_branch`, `_waypoint_visit_key`, `_future_route_capacity`, `_choose_coverage_branch`, `_route_curvature`, `_route_length`, `_heading`, `_route_yaw_change`, `_is_driving_lane`, `_same_direction`, `_ego_yaw_deg`, `_waypoint_distance_m`, `warm_heading_waypoint_cache`, `_nearby_indexed_waypoints`, `select_heading_compatible_waypoint`, `_next_straight`, `_advance_waypoint`, `_adjacent_driving_lane`, `_hermite_lane_change`, `build_lane_change_route_reference`, `build_scenario_route_reference`, `build_destination_route_reference`, `select_topology_route_anchor`, `build_route_reference`, `command_turn_direction`

## Dependencies and coordinated changes

- 改 `RouteReference`、坐标符号或 `steer` 范围：联动 `car_control_A.routing`、B schemas/adapters、`runtime_loop`、D 安全仲裁、接口 Schema 和 runner 日志。
- 改全局路线采样或 topology 搜索：联动 actor 路线放置、事件 `route_s`、局部参考窗、曲率限速、路线质量与场景 acceptance。
- 改 progress/replan：联动任务累计 offset、临时机动恢复、actor tracker、距离覆盖完成条件和 `route_replanned` 证据。
- 改 Pure Pursuit 参数：先确认配置 schema 与 runner 的 2/50 搜索窗覆盖关系，再覆盖直道、弯道、路口、重叠路线、临时路线返回和变化率测试。
- `lane_change.py` 只做折线几何偏移；CARLA 生产变道必须继续检查拓扑、同向 Driving lane、车道线权限和 junction，不可把纯几何路径当合法性证据。
- 历史 CARLA 报告只能证明其记录的提交/地图/配置。当前静态精读与离线测试不能替代真实闭环重跑。

## Validation entry points

`python -m pytest car_control_B/tests integration/tests/test_route_geometry.py integration/tests/test_route_manager.py integration/tests/test_route_planner.py integration/tests/test_runtime_stages.py`

Run from the worktree root. Listed commands are relevant checks, not claims that tests were executed. CARLA, remote-model and hardware acceptance require their actual environments and run manifests.

## 功能小文档完整索引

以下功能页分别记录实现入口、输入输出声明、内部调用、异常、配置和静态上下游；测试文件保留在源码索引中。

- [car_control_B/__init__.py](../functions/car_control_B--__init__--py.md)
- [car_control_B/adapters.py](../functions/car_control_B--adapters--py.md)
- [car_control_B/demo_fake_lateral.py](../functions/car_control_B--demo_fake_lateral--py.md)
- [car_control_B/lane_change.py](../functions/car_control_B--lane_change--py.md)
- [car_control_B/lateral_controller_base.py](../functions/car_control_B--lateral_controller_base--py.md)
- [car_control_B/path_utils.py](../functions/car_control_B--path_utils--py.md)
- [car_control_B/pure_pursuit.py](../functions/car_control_B--pure_pursuit--py.md)
- [car_control_B/schemas.py](../functions/car_control_B--schemas--py.md)
- [car_control_B/stanley.py](../functions/car_control_B--stanley--py.md)
- [integration/execution_stage.py](../functions/integration--execution_stage--py.md)
- [integration/planning_stage.py](../functions/integration--planning_stage--py.md)
- [integration/route_geometry.py](../functions/integration--route_geometry--py.md)
- [integration/route_manager.py](../functions/integration--route_manager--py.md)
- [integration/route_planner.py](../functions/integration--route_planner--py.md)

## 诊断与维护交接

本模块证据：路线身份、progress/remaining、CTE、steer；区分累计里程。功能实现与上下游见本页原索引；跨模块回查[追踪矩阵](../TRACEABILITY.md)与[诊断入口](../DIAGNOSIS.md)。实际run必须核对版本，未执行的检查不视为已通过。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `car_control_B/tests/__init__.py`

来源 SHA256：`bc05baf9f14df9dfb1093844ecac009f60ef62c12d1110e3cd3c65c4c7b2f0f9`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `car_control_B/tests/test_path_utils.py`

来源 SHA256：`dcda562d8314c8d2380a795e0dcff1999c2f56b0c5e1abb1e26e7d066cddbf24`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `test_local_curvature_rejects_invalid_contract_values` / 68 | `本地无直接if；检查上下文` | `raise AssertionError('zero curvature horizon must be rejected')` |
### `car_control_B/tests/test_pure_pursuit.py`

来源 SHA256：`df6d6e258680abb575980d5081efeb2ade57509c5a1764fb628c2b26b3bcabb2`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `car_control_B/tests/test_stanley.py`

来源 SHA256：`e344a08eaf7fa6541e9271076623739eeeb1f4654d2606e5b4949692b593ed64`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
