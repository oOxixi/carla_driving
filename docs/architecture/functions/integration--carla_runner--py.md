# carla_runner：功能记录

上级模块：[模块说明](../modules/vehicle-entry.md) · 实现：[integration/carla_runner.py](../../../integration/carla_runner.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [一帧控制的实际顺序与执行值](control-frame.md)

## 功能职责与范围

CARLA 0.9.16 acceptance runner with one synchronous tick/control apply.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `_DeferredCommand.envelope: dict[str, object]`；默认：`未在声明处设置`。
- `_DeferredCommand.received_ns: int`；默认：`未在声明处设置`。
- `_DeferredCommand.origin: str`；默认：`未在声明处设置`。
- `_DeferredCommand.audio_duration_s: float | None`；默认：`None`。

## 功能入口：输入、输出与实现说明

<a id="fn--deferredcommand"></a>

### `_DeferredCommand`

源码位置：[integration/carla_runner.py 第 110 行](../../../integration/carla_runner.py#L110)。类型：`ClassDef`。

保留尚未提交的命令envelope、received_ns（纳秒）、origin和可选audio_duration_s（秒）。后续runner排队/时延证据依赖原始接收时刻，不能把出队时间替换成接收时间。

<a id="fn--select-deferred-commands"></a>

### `_select_deferred_commands`

源码位置：[integration/carla_runner.py 第 117 行](../../../integration/carla_runner.py#L117)。类型：`FunctionDef`。

```python
_select_deferred_commands(commands: Sequence[_DeferredCommand], *, scenario_plan_active: bool, perception_target_available: bool=True) -> tuple[tuple[_DeferredCommand, ...], list[_DeferredCommand]]
```

Submit at most one grounded scenario command without dropping triggers.

<a id="fn--canonical-poll-wait-timeout-ms"></a>

### `_canonical_poll_wait_timeout_ms`

源码位置：[integration/carla_runner.py 第 143 行](../../../integration/carla_runner.py#L143)。类型：`FunctionDef`。

```python
_canonical_poll_wait_timeout_ms(*, slow_submitted_now: bool, emergency_submitted_now: bool, configured_timeout_ms: float) -> float
```

Never synchronously wait through an emergency command's brake frame.

<a id="fn--compiled-plan-from-payload"></a>

### `_compiled_plan_from_payload`

源码位置：[integration/carla_runner.py 第 155 行](../../../integration/carla_runner.py#L155)。类型：`FunctionDef`。

```python
_compiled_plan_from_payload(payload: Mapping[str, Any]) -> CompiledManeuverPlan
```

Rebuild the typed A/FSM contract from an orchestrator audit payload.

<a id="fn--maneuver-target-visible"></a>

### `_maneuver_target_visible`

源码位置：[integration/carla_runner.py 第 187 行](../../../integration/carla_runner.py#L187)。类型：`FunctionDef`。

```python
_maneuver_target_visible(step: CompiledPlanStep | None, scene: PerceptionFrame) -> bool
```

Match a legacy planner target by semantic class, not any detection.

<a id="fn--legacy-target-classes"></a>

### `_legacy_target_classes`

源码位置：[integration/carla_runner.py 第 201 行](../../../integration/carla_runner.py#L201)。类型：`FunctionDef`。

```python
_legacy_target_classes(target_id: str) -> set[str]
```

移除legacy-前缀及最后一个-后缀编号，归一化vehicle→car/truck/bus/vehicle、pedestrian→person/pedestrian、cyclist→bicycle/motorcycle/cyclist；未知类别返回自身单元素set。只用于类别兼容，不证明某个actor身份匹配。

<a id="fn--maneuver-target-gap-s"></a>

### `_maneuver_target_gap_s`

源码位置：[integration/carla_runner.py 第 212 行](../../../integration/carla_runner.py#L212)。类型：`FunctionDef`。

```python
_maneuver_target_gap_s(step: CompiledPlanStep | None, scene: PerceptionFrame, ego_speed_mps: float, actor_distances_m: Mapping[str, float] | None=None) -> float | None
```

Return time gap to the exact actor bound into the current plan.

<a id="fn--maneuver-target-distance-m"></a>

### `_maneuver_target_distance_m`

源码位置：[integration/carla_runner.py 第 225 行](../../../integration/carla_runner.py#L225)。类型：`FunctionDef`。

```python
_maneuver_target_distance_m(step: CompiledPlanStep | None, scene: PerceptionFrame, actor_distances_m: Mapping[str, float] | None=None) -> float | None
```

Return only the range of the actor explicitly bound to this step.

<a id="fn--physical-actor-id-for-target"></a>

### `_physical_actor_id_for_target`

源码位置：[integration/carla_runner.py 第 260 行](../../../integration/carla_runner.py#L260)。类型：`FunctionDef`。

```python
_physical_actor_id_for_target(target_id: str, target_aliases: Mapping[str, str] | None) -> str
```

Resolve a sensor track to its audited physical actor for progress only.

Qwen must continue to receive and bind sensor track IDs.  Once its plan is
accepted, the already-audited association lets the executor evaluate
whether that exact actor has passed behind ego; scenario actor IDs are not
injected into model perception or planning input.

<a id="fn--maneuver-target-passed"></a>

### `_maneuver_target_passed`

源码位置：[integration/carla_runner.py 第 277 行](../../../integration/carla_runner.py#L277)。类型：`FunctionDef`。

```python
_maneuver_target_passed(*, target_seen: bool, target_visible: bool, distance_from_plan_start_m: float, pass_after_m: float | None) -> bool
```

Require the measured pass distance when the target range is known.

<a id="fn--maneuver-step-reanchors-target"></a>

### `_maneuver_step_reanchors_target`

源码位置：[integration/carla_runner.py 第 292 行](../../../integration/carla_runner.py#L292)。类型：`FunctionDef`。

```python
_maneuver_step_reanchors_target(step: CompiledPlanStep, current_target_id: str) -> bool
```

Re-anchor PASS_TARGET distance even when adjacent steps share a target.

<a id="fn--record-maneuver-update"></a>

### `_record_maneuver_update`

源码位置：[integration/carla_runner.py 第 304 行](../../../integration/carla_runner.py#L304)。类型：`FunctionDef`。

```python
_record_maneuver_update(update: ManeuverUpdate, *, monitor: QwenScenarioMonitor | None, recorder: ScenarioEvidenceRecorder | None, extension_runtime: ScenarioExtensionRuntime | None=None) -> None
```

Persist step/terminal events and feed only plan-owned terminals to acceptance.

<a id="fn--note-extension-terminal"></a>

### `_note_extension_terminal`

源码位置：[integration/carla_runner.py 第 344 行](../../../integration/carla_runner.py#L344)。类型：`FunctionDef`。

```python
_note_extension_terminal(runtime: ScenarioExtensionRuntime | None, feedback: Mapping[str, object] | object) -> None
```

runtime=None不处理；从mapping或对象读status，支持枚举.value并大写。只转发SUCCEEDED/FAILED/REJECTED/EXPIRED/TIMED_OUT/SAFETY_OVERRIDE到note_terminal，取command_id并转str；其他状态忽略，不在本函数去重。

<a id="fn--note-safety-feedback"></a>

### `_note_safety_feedback`

源码位置：[integration/carla_runner.py 第 367 行](../../../integration/carla_runner.py#L367)。类型：`FunctionDef`。

```python
_note_safety_feedback(safety_reasons: set[str], feedback: Mapping[str, object] | object) -> None
```

Promote canonical safety events into scenario completion evidence.

<a id="fn--qwen-resolution-reason"></a>

### `_qwen_resolution_reason`

源码位置：[integration/carla_runner.py 第 382 行](../../../integration/carla_runner.py#L382)。类型：`FunctionDef`。

```python
_qwen_resolution_reason(orchestration: object | None) -> str | None
```

orchestration=None返回None；取reason_code，优先feedback.detail，否则action_summary（兼容mapping/对象）。有效非空字符串与reason拼接并strip，否则返回reason字符串或None，用于诊断而非重新判定状态。

<a id="fn--speed-mps"></a>

### `_speed_mps`

源码位置：[integration/carla_runner.py 第 399 行](../../../integration/carla_runner.py#L399)。类型：`FunctionDef`。

```python
_speed_mps(vector: Any) -> float
```

返回hypot(vector.x,vector.y)，单位m/s；刻意忽略垂直z速度，避免车辆落地/重力被当成纵向运动。

<a id="fn--actor-bbox-clearance-m"></a>

### `_actor_bbox_clearance_m`

源码位置：[integration/carla_runner.py 第 405 行](../../../integration/carla_runner.py#L405)。类型：`FunctionDef`。

```python
_actor_bbox_clearance_m(ego: Any, actor: Any) -> float
```

Return conservative horizontal body-to-body clearance for two actors.

<a id="fn--actor-horizontal-radius-m"></a>

### `_actor_horizontal_radius_m`

源码位置：[integration/carla_runner.py 第 414 行](../../../integration/carla_runner.py#L414)。类型：`FunctionDef`。

```python
_actor_horizontal_radius_m(actor: Any) -> float
```

从bounding_box.extent的x/y半尺寸计算hypot，作为水平包围圆半径；缺extent或负/非有限尺寸返回0，不能当真实障碍物尺寸已测得。

<a id="fn--actor-signed-route-clearance-m"></a>

### `_actor_signed_route_clearance_m`

源码位置：[integration/carla_runner.py 第 424 行](../../../integration/carla_runner.py#L424)。类型：`FunctionDef`。

```python
_actor_signed_route_clearance_m(ego_progress_m: float, actor_progress_m: float, ego: Any, actor: Any) -> float
```

Return signed body clearance along the monotonic mission route.

<a id="fn--actor-signed-longitudinal-clearance-m"></a>

### `_actor_signed_longitudinal_clearance_m`

源码位置：[integration/carla_runner.py 第 440 行](../../../integration/carla_runner.py#L440)。类型：`FunctionDef`。

```python
_actor_signed_longitudinal_clearance_m(ego: Any, actor: Any) -> float
```

Return signed body clearance along ego's forward axis.

Positive values mean the other actor is ahead; negative values mean it is
fully behind.  This is used only to verify completion of a named scenario
interaction, not to synthesize perception detections or steering control.

<a id="fn--acceptance-lateral-controller"></a>

### `_acceptance_lateral_controller`

源码位置：[integration/carla_runner.py 第 464 行](../../../integration/carla_runner.py#L464)。类型：`FunctionDef`。

```python
_acceptance_lateral_controller() -> PurePursuitController
```

Build the shared speed/curvature/error-adaptive lateral controller.

<a id="fn--follow-ego-spectator"></a>

### `_follow_ego_spectator`

源码位置：[integration/carla_runner.py 第 484 行](../../../integration/carla_runner.py#L484)。类型：`FunctionDef`。

```python
_follow_ego_spectator(world: Any, ego: Any, carla: Any) -> None
```

Keep the graphical spectator behind the ego during live demonstrations.

<a id="fn--scenario-maneuver"></a>

### `_scenario_maneuver`

源码位置：[integration/carla_runner.py 第 499 行](../../../integration/carla_runner.py#L499)。类型：`FunctionDef`。

```python
_scenario_maneuver(spec: ScenarioSpec) -> str
```

按命令顺序找转向/变道及方向；AVOID_OBSTACLE选择多车道拓扑，无方向时用CHANGE_LANE_LEFT作锚点需求，不是授权车辆立即左变道。无此类命令时根据local_route首尾横向/纵向比例（>=0.12且前向>1m）判FOLLOW_LEFT/RIGHT，否则FOLLOW。

<a id="fn--scenario-route-distance-m"></a>

### `_scenario_route_distance_m`

源码位置：[integration/carla_runner.py 第 534 行](../../../integration/carla_runner.py#L534)。类型：`FunctionDef`。

```python
_scenario_route_distance_m(spec: ScenarioSpec) -> float
```

直接返回ScenarioSpec.route_distance_contract_m，不自行累加几何或读取实际行驶里程；距离契约的计算由ScenarioSpec负责。

<a id="fn--scenario-requires-adjacent-lane-anchor"></a>

### `_scenario_requires_adjacent_lane_anchor`

源码位置：[integration/carla_runner.py 第 538 行](../../../integration/carla_runner.py#L538)。类型：`FunctionDef`。

```python
_scenario_requires_adjacent_lane_anchor(spec: ScenarioSpec) -> bool
```

runtime_support.declared_requirements含adjacent_lane_occupancy_acceptance时True；否则检查vehicle actor的LEFT/RIGHT_ADJACENT route_position，或未用route_position且旧spawn.y绝对值>=2m。用于选拓扑，避免旧邻道场景落到单车道路段。

<a id="fn--scenario-actor-lanes-fit-route"></a>

### `_scenario_actor_lanes_fit_route`

源码位置：[integration/carla_runner.py 第 574 行](../../../integration/carla_runner.py#L574)。类型：`FunctionDef`。

```python
_scenario_actor_lanes_fit_route(carla_api: Any, world_map: Any, route: RouteReference, spec: ScenarioSpec) -> bool
```

Check declared vehicle lane relations without mutating CARLA state.

<a id="fn--scenario-requires-target-lane-occupancy"></a>

### `_scenario_requires_target_lane_occupancy`

源码位置：[integration/carla_runner.py 第 595 行](../../../integration/carla_runner.py#L595)。类型：`FunctionDef`。

```python
_scenario_requires_target_lane_occupancy(spec: ScenarioSpec) -> bool
```

Return whether startup must produce adjacent-lane occupancy evidence.

<a id="fn--actor-activation-due"></a>

### `_actor_activation_due`

源码位置：[integration/carla_runner.py 第 610 行](../../../integration/carla_runner.py#L610)。类型：`FunctionDef`。

```python
_actor_activation_due(actor_spec: Mapping[str, object], *, elapsed_s: float, route_progress_m: float) -> bool
```

Return whether a deferred scenario actor may be created this frame.

Long Town routes revisit the same physical roads.  Spawning every actor at
episode start lets a kilometre-7 actor obstruct an earlier lap and makes
Euclidean proximity triggers fire out of order.  ``activation_trigger`` is
therefore evaluated against monotonic route progress before the actor is
introduced into the CARLA world.

<a id="fn--actor-deactivation-due"></a>

### `_actor_deactivation_due`

源码位置：[integration/carla_runner.py 第 636 行](../../../integration/carla_runner.py#L636)。类型：`FunctionDef`。

```python
_actor_deactivation_due(actor_spec: Mapping[str, object], *, elapsed_s: float, route_progress_m: float) -> bool
```

Return whether a temporary scenario actor has completed its lifetime.

<a id="fn--release-scenario-actor-if-due"></a>

### `_release_scenario_actor_if_due`

源码位置：[integration/carla_runner.py 第 655 行](../../../integration/carla_runner.py#L655)。类型：`FunctionDef`。

```python
_release_scenario_actor_if_due(session: CarlaSession, actor: Any, actor_spec: Mapping[str, object], *, elapsed_s: float, route_progress_m: float) -> bool
```

Release an event-scoped actor once its declarative lifetime ends.

<a id="fn--scenario-uses-dynamic-out-and-back"></a>

### `_scenario_uses_dynamic_out_and_back`

源码位置：[integration/carla_runner.py 第 682 行](../../../integration/carla_runner.py#L682)。类型：`FunctionDef`。

```python
_scenario_uses_dynamic_out_and_back(spec: ScenarioSpec | None) -> bool
```

无spec为False；extensions.maneuver_route_mode去空白转小写后等于dynamic_out_and_back为True，不构建路线。

<a id="fn--scenario-startup-maneuver"></a>

### `_scenario_startup_maneuver`

源码位置：[integration/carla_runner.py 第 690 行](../../../integration/carla_runner.py#L690)。类型：`FunctionDef`。

```python
_scenario_startup_maneuver(spec: ScenarioSpec) -> str
```

Keep the mission lane until a dynamic manoeuvre is actually commanded.

<a id="fn--scenario-lane-change-profile"></a>

### `_scenario_lane_change_profile`

源码位置：[integration/carla_runner.py 第 720 行](../../../integration/carla_runner.py#L720)。类型：`FunctionDef`。

```python
_scenario_lane_change_profile(spec: ScenarioSpec | None) -> Mapping[str, object] | None
```

无spec/无lane_change_profile返回None；存在必须Mapping否则TypeError。原样返回映射，字段/数值有效性由下游使用处负责。

<a id="fn--traffic-light-stop-points"></a>

### `_traffic_light_stop_points`

源码位置：[integration/carla_runner.py 第 733 行](../../../integration/carla_runner.py#L733)。类型：`FunctionDef`。

```python
_traffic_light_stop_points(world: Any) -> tuple[tuple[float, float], ...]
```

Collect signal stop locations so deterministic routes can avoid them.

<a id="fn--vehicle-state"></a>

### `_vehicle_state`

源码位置：[integration/carla_runner.py 第 748 行](../../../integration/carla_runner.py#L748)。类型：`FunctionDef`。

```python
_vehicle_state(ego: Any, frame: int, sim_time_s: float, world_map: Any) -> RuntimeVehicleState
```

读取ego transform/velocity、以project_to_road=True查waypoint，构造带frame/sim_time_s的RuntimeVehicleState；地速用_speed_mps、yaw保留度、lane_id转字符串，无waypoint用"0"。会调用CARLA对象但不tick。

<a id="fn--planner-runtime-state"></a>

### `_planner_runtime_state`

源码位置：[integration/carla_runner.py 第 756 行](../../../integration/carla_runner.py#L756)。类型：`FunctionDef`。

```python
_planner_runtime_state(world_map: Any, ego: Any, scene: PerceptionFrame, route: RouteReference) -> dict[str, object]
```

Expose only deterministic lane/route facts needed by Planner V2.

<a id="fn--planner-runtime-state-driving"></a>

### `_planner_runtime_state.driving`

源码位置：[integration/carla_runner.py 第 767 行](../../../integration/carla_runner.py#L767)。类型：`FunctionDef`。

```python
_planner_runtime_state.driving(candidate: Any | None) -> bool
```

局部车道判断：candidate=None为False；lane_type转字符串取最后一个点分段并大写是否DRIVING，缺lane_type默认Driving。它不是完整邻道合法性检查。

<a id="fn--apply-compiled-plan-route"></a>

### `_apply_compiled_plan_route`

源码位置：[integration/carla_runner.py 第 820 行](../../../integration/carla_runner.py#L820)。类型：`FunctionDef`。

```python
_apply_compiled_plan_route(compiled_plan: Mapping[str, Any], *, world_map: Any, ego: Any, current_route: RouteReference, requested_speed_mps: float, distance_m: float, prevalidated_maneuver_route: RouteReference | None=None, lane_change_profile: Mapping[str, object] | None=None) -> tuple[RouteReference, float, str | None]
```

Apply validated route semantics; B still generates the actual reference.

<a id="fn--route-starts-near-ego"></a>

### `_route_starts_near_ego`

源码位置：[integration/carla_runner.py 第 897 行](../../../integration/carla_runner.py#L897)。类型：`FunctionDef`。

```python
_route_starts_near_ego(route: RouteReference, ego: Any, *, maximum_distance_m: float=15.0) -> bool
```

Reject a scenario route whose origin is stale for a live manoeuvre.

<a id="fn--lane-change-route-parameters"></a>

### `_lane_change_route_parameters`

源码位置：[integration/carla_runner.py 第 914 行](../../../integration/carla_runner.py#L914)。类型：`FunctionDef`。

```python
_lane_change_route_parameters(profile: Mapping[str, object] | None, *, mission_distance_m: float) -> dict[str, float]
```

Validate the S2 comfort profile before it reaches CARLA topology code.

<a id="fn--is-deferred-dynamic-lane-change"></a>

### `_is_deferred_dynamic_lane_change`

源码位置：[integration/carla_runner.py 第 961 行](../../../integration/carla_runner.py#L961)。类型：`FunctionDef`。

```python
_is_deferred_dynamic_lane_change(step: CompiledPlanStep, *, dynamic_out_and_back: bool, mission_route: RouteReference | None) -> bool
```

Allow either leg of a dynamic detour to wait for a legal corridor.

<a id="fn--dynamic-return-destination-xy"></a>

### `_dynamic_return_destination_xy`

源码位置：[integration/carla_runner.py 第 975 行](../../../integration/carla_runner.py#L975)。类型：`FunctionDef`。

```python
_dynamic_return_destination_xy(mission_route: RouteReference, x_m: float, y_m: float, *, previous_progress_m: float | None=None, lookahead_m: float=25.0) -> tuple[float, float]
```

Choose an ahead point on the retained route for a topology-safe merge.

A temporary lane-change route has its own arc-length origin.  Its progress
must not be used to index the retained mission route, otherwise a return
near a bend can select a point behind ego and make the vehicle turn around.
Project the live pose onto the retained route instead.

<a id="fn--maneuver-lane-label"></a>

### `_maneuver_lane_label`

源码位置：[integration/carla_runner.py 第 1003 行](../../../integration/carla_runner.py#L1003)。类型：`FunctionDef`。

```python
_maneuver_lane_label(lane_id: str, lane_ids: Mapping[str, str], step: CompiledPlanStep | None, mission_route: RouteReference | None, *, x_m: float, y_m: float, return_destination_xy: tuple[float, float] | None=None, return_tolerance_m: float=0.5) -> str
```

Resolve semantic lanes across junctions where CARLA renumbers lane IDs.

<a id="fn--mission-speed-after-maneuver"></a>

### `_mission_speed_after_maneuver`

源码位置：[integration/carla_runner.py 第 1035 行](../../../integration/carla_runner.py#L1035)。类型：`FunctionDef`。

```python
_mission_speed_after_maneuver(original_mission_speed_mps: float, persistent_speed_mps: float | None) -> float
```

Restore route geometry without discarding an explicit SET_SPEED.

<a id="fn--retain-route-for-maneuver"></a>

### `_retain_route_for_maneuver`

源码位置：[integration/carla_runner.py 第 1045 行](../../../integration/carla_runner.py#L1045)。类型：`FunctionDef`。

```python
_retain_route_for_maneuver(*, topology_coverage_planning: bool, dynamic_out_and_back: bool, must_finish_route: bool=False, lane_change_step_count: int, route_behavior: str | None) -> bool
```

Return whether a finite manoeuvre needs a mission-route continuation.

Topology-coverage missions measure distance independently from their current
local reference. A turn or lane change can replace that reference with a
finite manoeuvre route, so retain a marker that causes a fresh continuation
to be planned from the vehicle's terminal pose. Dynamic out-and-back plans
retain their original route until their explicit return leg completes.

<a id="fn--scene-from-world"></a>

### `_scene_from_world`

源码位置：[integration/carla_runner.py 第 1072 行](../../../integration/carla_runner.py#L1072)。类型：`FunctionDef`。

```python
_scene_from_world(world_map: Any, ego: Any, frame: int, sim_time_s: float, *, route: RouteReference | None=None, scenario_lead: Any | None=None, scenario_vehicles: Sequence[Any]=(), events: EventLedger | None=None) -> tuple[PerceptionFrame, dict[str, str]]
```

Build scene truth; synthetic scenarios may nominate their only lead actor.

Acceptance scenarios must not accidentally follow an unrelated vehicle
left by another CARLA client, so they never select the globally nearest
actor when a scenario-owned lead is supplied (or explicitly absent).

<a id="fn--world-vehicle-detections"></a>

### `_world_vehicle_detections`

源码位置：[integration/carla_runner.py 第 1153 行](../../../integration/carla_runner.py#L1153)。类型：`FunctionDef`。

```python
_world_vehicle_detections(ego: Any, vehicles: Sequence[Any]) -> tuple[DetectedObject, ...]
```

Expose scenario-owned actors only in the explicit world debug mode.

<a id="fn--bind-scenario-actor-ids"></a>

### `_bind_scenario_actor_ids`

源码位置：[integration/carla_runner.py 第 1192 行](../../../integration/carla_runner.py#L1192)。类型：`FunctionDef`。

```python
_bind_scenario_actor_ids(scene: PerceptionFrame, ego: Any, actors: Sequence[tuple[Any, Mapping[str, object]]]) -> PerceptionFrame
```

Attach stable scenario IDs to sensor detections by nearest range.

CARLA RGB/LiDAR fusion currently has no persistent tracker.  The
acceptance actors do have stable IDs, so a deterministic nearest-range
association supplies the provenance needed to audit target binding while
leaving unmatched road users on legacy tracker IDs.

<a id="fn--sensor-evidence-actor-ids"></a>

### `_sensor_evidence_actor_ids`

源码位置：[integration/carla_runner.py 第 1288 行](../../../integration/carla_runner.py#L1288)。类型：`FunctionDef`。

```python
_sensor_evidence_actor_ids(scene: PerceptionFrame, ego: Any, actors: Sequence[tuple[Any, Mapping[str, object]]]) -> tuple[str, ...]
```

Associate sensor detections for audit without changing control input.

The returned labels are used only by the evidence recorder.  The original
sensor-derived ``scene`` remains untouched and is still the sole input to
C, D, and Qwen in strict perception mode.

<a id="fn--sensor-evidence-target-aliases"></a>

### `_sensor_evidence_target_aliases`

源码位置：[integration/carla_runner.py 第 1304 行](../../../integration/carla_runner.py#L1304)。类型：`FunctionDef`。

```python
_sensor_evidence_target_aliases(scene: PerceptionFrame, ego: Any, actors: Sequence[tuple[Any, Mapping[str, object]]]) -> dict[str, str]
```

Map sensor tracker IDs to scenario IDs for evidence only.

The map is captured with the exact perception frame submitted to Qwen.
Neither the perception state nor the model request is rewritten, so the
model still has to choose the correct sensor-grounded target itself.

<a id="fn--spawn-static-lead"></a>

### `_spawn_static_lead`

源码位置：[integration/carla_runner.py 第 1336 行](../../../integration/carla_runner.py#L1336)。类型：`FunctionDef`。

```python
_spawn_static_lead(session: CarlaSession, world: Any, world_map: Any, ego: Any, blueprint: Any, distance_m: float) -> Any
```

Spawn a deterministic stationary lead vehicle in ego's current lane.

<a id="fn--scenario-actor"></a>

### `_scenario_actor`

源码位置：[integration/carla_runner.py 第 1364 行](../../../integration/carla_runner.py#L1364)。类型：`FunctionDef`。

```python
_scenario_actor(spec: ScenarioSpec | None, actor_type: str) -> dict[str, object] | None
```

Return the unique configured actor of ``actor_type``.

Submission scenarios deliberately support one owned lead vehicle and one
owned traffic light.  Failing on duplicates is safer than silently binding
perception evidence to an arbitrary actor.

<a id="fn--scenario-actors"></a>

### `_scenario_actors`

源码位置：[integration/carla_runner.py 第 1379 行](../../../integration/carla_runner.py#L1379)。类型：`FunctionDef`。

```python
_scenario_actors(spec: ScenarioSpec | None, actor_type: str) -> tuple[dict[str, object], ...]
```

Return all declared actors of one exact type.

``_scenario_actor`` remains deliberately strict for singleton resources
such as the traffic light selected for a stop-line contract.  Dynamic
traffic, however, is naturally plural; callers that own it must use this
collection rather than silently binding to an arbitrary vehicle.

<a id="fn--scenario-walkers"></a>

### `_scenario_walkers`

源码位置：[integration/carla_runner.py 第 1399 行](../../../integration/carla_runner.py#L1399)。类型：`FunctionDef`。

```python
_scenario_walkers(spec: ScenarioSpec | None) -> tuple[dict[str, object], ...]
```

Return all walker/pedestrian declarations, preserving scenario order.

<a id="fn--scenario-static-props"></a>

### `_scenario_static_props`

源码位置：[integration/carla_runner.py 第 1409 行](../../../integration/carla_runner.py#L1409)。类型：`FunctionDef`。

```python
_scenario_static_props(spec: ScenarioSpec | None) -> tuple[dict[str, object], ...]
```

Return declarative static obstacles used for construction/occlusion tests.

<a id="fn--cleanup-stale-scenario-actors"></a>

### `_cleanup_stale_scenario_actors`

源码位置：[integration/carla_runner.py 第 1421 行](../../../integration/carla_runner.py#L1421)。类型：`FunctionDef`。

```python
_cleanup_stale_scenario_actors(world: Any, spec: ScenarioSpec | None) -> int
```

Remove only acceptance-runner actors left by an interrupted prior run.

<a id="fn--scenario-local-transform"></a>

### `_scenario_local_transform`

源码位置：[integration/carla_runner.py 第 1444 行](../../../integration/carla_runner.py#L1444)。类型：`FunctionDef`。

```python
_scenario_local_transform(carla_api: Any, anchor_transform: Any, spawn: Mapping[str, object], *, forward_offset_m: float=0.0) -> Any
```

Convert a scenario-local actor pose to a CARLA world transform.

<a id="fn--active-actor-route-context"></a>

### `_active_actor_route_context`

源码位置：[integration/carla_runner.py 第 1473 行](../../../integration/carla_runner.py#L1473)。类型：`FunctionDef`。

```python
_active_actor_route_context(actor_spec: Mapping[str, object], scenario_route: RouteReference | None, global_route: GlobalRoute | None, mission_progress_offset_m: float) -> tuple[RouteReference | None, Mapping[str, object]]
```

Bind a mission-absolute actor position to the current active route.

<a id="fn--scenario-vehicle-speed-mps"></a>

### `_scenario_vehicle_speed_mps`

源码位置：[integration/carla_runner.py 第 1488 行](../../../integration/carla_runner.py#L1488)。类型：`FunctionDef`。

```python
_scenario_vehicle_speed_mps(actor_spec: Mapping[str, object], elapsed_s: float) -> float
```

behavior须Mapping；initial_speed默认0且截到非负，brake_at_s默认inf，target_speed默认initial且截非负。elapsed_s<brake_at取initial，到达边界取target；无加速度插值，亦未显式检查所有数值有限。

<a id="fn--signed-forward-speed-mps"></a>

### `_signed_forward_speed_mps`

源码位置：[integration/carla_runner.py 第 1501 行](../../../integration/carla_runner.py#L1501)。类型：`FunctionDef`。

```python
_signed_forward_speed_mps(actor: Any) -> float
```

Return actor velocity projected onto its current forward direction.

<a id="fn--occupied-actor-locations"></a>

### `_occupied_actor_locations`

源码位置：[integration/carla_runner.py 第 1512 行](../../../integration/carla_runner.py#L1512)。类型：`FunctionDef`。

```python
_occupied_actor_locations(world: Any) -> tuple[Any, ...]
```

Snapshot physical actor locations for deterministic spawn preflight.

<a id="fn--spawn-scenario-vehicle"></a>

### `_spawn_scenario_vehicle`

源码位置：[integration/carla_runner.py 第 1533 行](../../../integration/carla_runner.py#L1533)。类型：`FunctionDef`。

```python
_spawn_scenario_vehicle(session: CarlaSession, world: Any, carla_api: Any, ego: Any, fallback_blueprint: Any, actor_spec: Mapping[str, object], *, route: RouteReference | None=None, seed: int=0) -> Any
```

Spawn a real CARLA lead vehicle from a scenario actor declaration.

<a id="fn--update-scenario-vehicle"></a>

### `_update_scenario_vehicle`

源码位置：[integration/carla_runner.py 第 1651 行](../../../integration/carla_runner.py#L1651)。类型：`FunctionDef`。

```python
_update_scenario_vehicle(lead: Any, actor_spec: Mapping[str, object], elapsed_s: float, carla_api: Any, *, desired_speed_mps: float | None=None, behavior_elapsed_s: float | None=None, world_map: Any | None=None, route_points_xy_m: Sequence[tuple[float, float]] | None=None) -> None
```

Apply deterministic speed and lane-following control to a scenario vehicle.

<a id="fn--scenario-target-lane-occupied-count"></a>

### `_scenario_target_lane_occupied_count`

源码位置：[integration/carla_runner.py 第 1820 行](../../../integration/carla_runner.py#L1820)。类型：`FunctionDef`。

```python
_scenario_target_lane_occupied_count(world_map: Any, ego: Any, scenario_vehicles: Sequence[tuple[Any, Mapping[str, object]]], maneuver: str) -> int
```

Count owned scenario vehicles in the commanded adjacent lane.

<a id="fn--spawn-scenario-walker"></a>

### `_spawn_scenario_walker`

源码位置：[integration/carla_runner.py 第 1875 行](../../../integration/carla_runner.py#L1875)。类型：`FunctionDef`。

```python
_spawn_scenario_walker(session: CarlaSession, world: Any, carla_api: Any, ego: Any, actor_spec: Mapping[str, object], *, route: RouteReference | None=None, seed: int=0) -> tuple[Any, Any]
```

Spawn a real pedestrian and return it with its world-space target.

The target is anchored to the ego's actual map pose, just as vehicles are.
This avoids a Town-specific world coordinate and makes crossing scenarios
portable across the maps used by the evaluation harness.

<a id="fn--update-scenario-walker"></a>

### `_update_scenario_walker`

源码位置：[integration/carla_runner.py 第 2000 行](../../../integration/carla_runner.py#L2000)。类型：`FunctionDef`。

```python
_update_scenario_walker(walker: Any, actor_spec: Mapping[str, object], elapsed_s: float, target_location: Any, carla_api: Any, *, trigger_ready: bool=True) -> None
```

Move a scenario pedestrian with CARLA's public WalkerControl API.

<a id="fn--spawn-scenario-static-prop"></a>

### `_spawn_scenario_static_prop`

源码位置：[integration/carla_runner.py 第 2048 行](../../../integration/carla_runner.py#L2048)。类型：`FunctionDef`。

```python
_spawn_scenario_static_prop(session: CarlaSession, world: Any, carla_api: Any, ego: Any, actor_spec: Mapping[str, object], *, route: RouteReference | None=None, seed: int=0) -> Any
```

Spawn a declared static obstacle for construction/occlusion coverage.

<a id="fn--select-scenario-lead"></a>

### `_select_scenario_lead`

源码位置：[integration/carla_runner.py 第 2125 行](../../../integration/carla_runner.py#L2125)。类型：`FunctionDef`。

```python
_select_scenario_lead(ego: Any, vehicles: Sequence[Any]) -> Any | None
```

Choose the closest owned vehicle ahead of ego, never map background traffic.

<a id="fn--scenario-traffic-light-distance"></a>

### `_scenario_traffic_light_distance`

源码位置：[integration/carla_runner.py 第 2143 行](../../../integration/carla_runner.py#L2143)。类型：`FunctionDef`。

```python
_scenario_traffic_light_distance(spec: ScenarioSpec | None) -> float | None
```

取首个traffic_light actor，无则None；distance_to_stop_line_m默认0，必须有限且>0，否则ValueError。配置距离不是传感器观测。

<a id="fn--traffic-light-scenario-anchor"></a>

### `_traffic_light_scenario_anchor`

源码位置：[integration/carla_runner.py 第 2153 行](../../../integration/carla_runner.py#L2153)。类型：`FunctionDef`。

```python
_traffic_light_scenario_anchor(world: Any, world_map: Any, carla_api: Any, distance_to_stop_line_m: float, *, candidate_index: int=0) -> tuple[Any, Any]
```

Return a real signal and a driving-lane transform behind its stop line.

<a id="fn--scenario-traffic-light-observation"></a>

### `_scenario_traffic_light_observation`

源码位置：[integration/carla_runner.py 第 2207 行](../../../integration/carla_runner.py#L2207)。类型：`FunctionDef`。

```python
_scenario_traffic_light_observation(scene: PerceptionFrame, ego: Any, light: Any) -> tuple[PerceptionFrame, dict[str, str]]
```

Bind D08 to the selected real CARLA signal and map stop waypoint.

<a id="fn--scenario-traffic-light-distance-to-stop-line-m"></a>

### `_scenario_traffic_light_distance_to_stop_line_m`

源码位置：[integration/carla_runner.py 第 2234 行](../../../integration/carla_runner.py#L2234)。类型：`FunctionDef`。

```python
_scenario_traffic_light_distance_to_stop_line_m(ego: Any, light: Any) -> float
```

Measure non-negative front-bumper distance for perception/control.

<a id="fn--scenario-traffic-light-signed-clearance-m"></a>

### `_scenario_traffic_light_signed_clearance_m`

源码位置：[integration/carla_runner.py 第 2239 行](../../../integration/carla_runner.py#L2239)。类型：`FunctionDef`。

```python
_scenario_traffic_light_signed_clearance_m(ego: Any, light: Any) -> float
```

Measure signed front-bumper clearance to the selected CARLA stop line.

Positive is before the line and negative is crossed.  The perception
contract remains non-negative, while this signed value is retained for
acceptance evidence so crossing then stopping cannot look successful.

<a id="fn--apply-virtual-scenario"></a>

### `_apply_virtual_scenario`

源码位置：[integration/carla_runner.py 第 2272 行](../../../integration/carla_runner.py#L2272)。类型：`FunctionDef`。

```python
_apply_virtual_scenario(scene: PerceptionFrame, ego: Any, origin: tuple[float, float, float], args: argparse.Namespace) -> PerceptionFrame
```

以当前ego到origin的3D直线距离（非路线累计距离）更新虚拟事实。red_stop写RED和max(0,stop_line-travelled)；follow/emergency写固定静止前车，gap下限0.1m。其余保持scene；这是测试真值注入，不能归为实测感知。

<a id="fn--scenario-facts"></a>

### `_scenario_facts`

源码位置：[integration/carla_runner.py 第 2286 行](../../../integration/carla_runner.py#L2286)。类型：`FunctionDef`。

```python
_scenario_facts(ego: Any, origin: tuple[float, float, float], spec: ScenarioSpec, *, frame: int, sim_time_s: float, elapsed_s: float) -> PerceptionFrame
```

Build deterministic configured actors without mutating perception.

<a id="fn--lead-vehicle-travel-m"></a>

### `_lead_vehicle_travel_m`

源码位置：[integration/carla_runner.py 第 2350 行](../../../integration/carla_runner.py#L2350)。类型：`FunctionDef`。

```python
_lead_vehicle_travel_m(elapsed_s: float, initial_speed_mps: float, brake_at_s: float, target_speed_mps: float) -> float
```

Integrate the scenario lead's piecewise speed without a position jump at braking.

<a id="fn--select-scene-facts"></a>

### `_select_scene_facts`

源码位置：[integration/carla_runner.py 第 2362 行](../../../integration/carla_runner.py#L2362)。类型：`FunctionDef`。

```python
_select_scene_facts(perception: PerceptionFrame, scenario: PerceptionFrame | None, mode: str) -> tuple[PerceptionFrame, dict[str, str]]
```

Select perception, scenario truth, or perception-first fallback.

<a id="fn--apply-scenario-speed-limit"></a>

### `_apply_scenario_speed_limit`

源码位置：[integration/carla_runner.py 第 2397 行](../../../integration/carla_runner.py#L2397)。类型：`FunctionDef`。

```python
_apply_scenario_speed_limit(scene: PerceptionFrame, scenario_limit_mps: float | None, sources: dict[str, str], *, override_map_limit: bool=False) -> PerceptionFrame
```

Expose the scenario speed contract to both Qwen and local control.

The default remains fail-safe and only tightens CARLA's map limit.  A
scenario may explicitly replace it when the simulator-map sign metadata is
not the competition road contract; this is opt-in and never affects other
scenes.

<a id="fn--load-command"></a>

### `_load_command`

源码位置：[integration/carla_runner.py 第 2427 行](../../../integration/carla_runner.py#L2427)。类型：`FunctionDef`。

```python
_load_command(args: argparse.Namespace) -> dict[str, object] | None
```

command_json优先于audio；JSON根必须Mapping，高层命令经HighLevelCommandAdapter转换。音频须存在，先预热voice模型再audio_to_command且结果须Mapping。test_command_ttl_s非None覆盖valid_duration_s；均未指定返回None，未在此授予控制权限。

<a id="fn--qwen-voice-command"></a>

### `_qwen_voice_command`

源码位置：[integration/carla_runner.py 第 2458 行](../../../integration/carla_runner.py#L2458)。类型：`FunctionDef`。

```python
_qwen_voice_command(args: argparse.Namespace, spec: ScenarioSpec | None) -> str
```

显式非空qwen_voice_command优先；否则需spec且恰好一条time_s<=1e-9的命令，source_text非空，否则ValueError。这是qwen_remote路径限制，不代表canonical多命令路径也只有一条。

<a id="fn--qwen-desired-speed-mps"></a>

### `_qwen_desired_speed_mps`

源码位置：[integration/carla_runner.py 第 2474 行](../../../integration/carla_runner.py#L2474)。类型：`FunctionDef`。

```python
_qwen_desired_speed_mps(args: argparse.Namespace, spec: ScenarioSpec | None) -> float
```

无spec/非单命令/无数值speed时回退default_speed_mps；先resolve_scenario_command，再读parameters。接受m/s/mps/米每秒，km/h等除3.6；未知单位ValueError，bool不当数值。

<a id="fn--save-qwen-rgb-image"></a>

### `_save_qwen_rgb_image`

源码位置：[integration/carla_runner.py 第 2497 行](../../../integration/carla_runner.py#L2497)。类型：`FunctionDef`。

```python
_save_qwen_rgb_image(measurement: Any, image_root: str | Path, *, request_id: str) -> str
```

Persist one aligned CARLA RGB frame and return an image-root-relative ref.

<a id="fn--build-qwen-context"></a>

### `_build_qwen_context`

源码位置：[integration/carla_runner.py 第 2523 行](../../../integration/carla_runner.py#L2523)。类型：`FunctionDef`。

```python
_build_qwen_context(*, request_id: str, voice_command: str, rgb_ref: str, state: RuntimeVehicleState, scene: PerceptionFrame, behavior_state: str, desired_speed_mps: float, route_end_distance_m: float | None, c_safety_state: Mapping[str, object] | None) -> QwenInputContext
```

组装remote路径QwenInputContext：车辆速度/行为/目标速度/路线末端距离、感知距离/灯态/检测、C安全摘要。检测项仅带class_name/confidence/distance/bbox，不包含track_id；此helper将visual_valid固定True，不能据此推断测量真实有效。

<a id="fn--evidence-recorder"></a>

### `_evidence_recorder`

源码位置：[integration/carla_runner.py 第 2580 行](../../../integration/carla_runner.py#L2580)。类型：`FunctionDef`。

```python
_evidence_recorder(args: argparse.Namespace, spec: ScenarioSpec | None=None) -> ScenarioEvidenceRecorder | None
```

no_log返回None；否则创建log_dir，在<scenario>_<本地时间含微秒>.jsonl开启ScenarioEvidenceRecorder。config仅收args中的str/int/float/bool/None，Path等对象不会自动收入；补seed/config_path/code_version，后者优先CARLA_DRIVING_CODE_VERSION再git HEAD。start_run后打印路径。

<a id="fn--git-code-version"></a>

### `_git_code_version`

源码位置：[integration/carla_runner.py 第 2602 行](../../../integration/carla_runner.py#L2602)。类型：`FunctionDef`。

```python
_git_code_version() -> str
```

在仓库根执行git rev-parse HEAD，最多等2s；OSError/子进程失败/空stdout返回UNKNOWN，不记录dirty diff。因此HEAD相同仍不能证明运行工作区内容完全相同。

<a id="fn--rejected-load-envelope"></a>

### `_rejected_load_envelope`

源码位置：[integration/carla_runner.py 第 2617 行](../../../integration/carla_runner.py#L2617)。类型：`FunctionDef`。

```python
_rejected_load_envelope(error: BaseException) -> dict[str, object]
```

Represent voice loading failures as a vehicle-side auditable NO_OP.

<a id="fn--warm-up-sensor-bridge"></a>

### `_warm_up_sensor_bridge`

源码位置：[integration/carla_runner.py 第 2636 行](../../../integration/carla_runner.py#L2636)。类型：`FunctionDef`。

```python
_warm_up_sensor_bridge(session: Any, world: Any, bridge: CarlaPerceptionBridge, *, attempts: int, tick_timeout_s: float, sensor_timeout_s: float) -> None
```

Wait for a stable aligned RGB/LiDAR stream before command execution.

<a id="fn--scenario-completed"></a>

### `_scenario_completed`

源码位置：[integration/carla_runner.py 第 2661 行](../../../integration/carla_runner.py#L2661)。类型：`FunctionDef`。

```python
_scenario_completed(args: argparse.Namespace, *, frames: int, final_speed_mps: float | None, final_scene: PerceptionFrame | None, min_gap_m: float | None, collision_seen: bool, max_speed_mps: float=0.0) -> bool
```

基础内置场景判断：帧数必须恰等args.frames、末速度非None且无碰撞；red_stop需<=0.15m/s且停止线距离<=1m；follow需最小gap>=3m且曾达0.2m/s；emergency需<=0.15m/s；其他需曾达0.2m/s。该helper不替代scenario文件的基础/Qwen/extension验收。

<a id="fn--runtime-health-completed"></a>

### `_runtime_health_completed`

源码位置：[integration/carla_runner.py 第 2676 行](../../../integration/carla_runner.py#L2676)。类型：`FunctionDef`。

```python
_runtime_health_completed(safety_reasons: set[str]) -> bool
```

Reject ordinary scenario success after a runtime/integration fail-safe.

Intentional D interventions are evaluated separately by
``_expected_safety_completed``.  The basic runner must not report success
merely because a watchdog-latched vehicle stayed still and avoided impact.

<a id="fn--declared-scenario-runtime-completed"></a>

### `_declared_scenario_runtime_completed`

源码位置：[integration/carla_runner.py 第 2700 行](../../../integration/carla_runner.py#L2700)。类型：`FunctionDef`。

```python
_declared_scenario_runtime_completed(spec: ScenarioSpec, *, frames: int, final_speed_mps: float | None, collision_seen: bool, command_finished: bool, safety_reasons: set[str], route_run_ended_early: bool=False) -> bool
```

Check runtime health only; declared contracts own task semantics.

A valid STOP/HOLD task may begin and end at rest.  Requiring arbitrary
motion here makes such scenarios fail despite satisfying every explicit
base, extension, and oracle contract.

<a id="fn--c-perception-safety-reason"></a>

### `_c_perception_safety_reason`

源码位置：[integration/carla_runner.py 第 2725 行](../../../integration/carla_runner.py#L2725)。类型：`FunctionDef`。

```python
_c_perception_safety_reason(c_safety_state: Mapping[str, object] | None) -> str | None
```

Convert C fail-closed perception summaries into acceptance evidence.

<a id="fn--c-safety-speed-cap-mps"></a>

### `_c_safety_speed_cap_mps`

源码位置：[integration/carla_runner.py 第 2740 行](../../../integration/carla_runner.py#L2740)。类型：`FunctionDef`。

```python
_c_safety_speed_cap_mps(c_safety_state: Mapping[str, object] | None) -> float | None
```

Accept only an explicit finite C-side temporary speed cap.

A cap is intentionally transient: it is applied to the current control
step's route reference and never overwrites the driver's requested speed
or command FSM state.  D still arbitrates the resulting control.

<a id="fn--single-sensor-fault-speed-cap-mps"></a>

### `_single_sensor_fault_speed_cap_mps`

源码位置：[integration/carla_runner.py 第 2758 行](../../../integration/carla_runner.py#L2758)。类型：`FunctionDef`。

```python
_single_sensor_fault_speed_cap_mps(active_sensor_faults: set[str], nominal_speed_mps: float) -> float | None
```

Cap speed while exactly one primary perception sensor remains unavailable.

<a id="fn--c-speed-cap-control-override"></a>

### `_c_speed_cap_control_override`

源码位置：[integration/carla_runner.py 第 2770 行](../../../integration/carla_runner.py#L2770)。类型：`FunctionDef`。

```python
_c_speed_cap_control_override(current_speed_mps: float, speed_cap_mps: float | None) -> dict[str, float] | None
```

Return a D-arbitrated braking request when a temporary C cap is exceeded.

<a id="fn--expected-safety-completed"></a>

### `_expected_safety_completed`

源码位置：[integration/carla_runner.py 第 2788 行](../../../integration/carla_runner.py#L2788)。类型：`FunctionDef`。

```python
_expected_safety_completed(spec: ScenarioSpec, *, frames: int, final_speed_mps: float | None, collision_seen: bool, safety_reasons: set[str], route_run_ended_early: bool=False) -> bool | None
```

Evaluate scenario contracts whose success is an intentional D intervention.

<a id="fn--scenario-raw-control-fault"></a>

### `_scenario_raw_control_fault`

源码位置：[integration/carla_runner.py 第 2831 行](../../../integration/carla_runner.py#L2831)。类型：`FunctionDef`。

```python
_scenario_raw_control_fault(spec: ScenarioSpec | None, elapsed_s: float) -> dict[str, object] | None
```

Build the one-shot pre-D fault required by D05/D06 contracts.

<a id="fn--route-contract-completed"></a>

### `_route_contract_completed`

源码位置：[integration/carla_runner.py 第 2853 行](../../../integration/carla_runner.py#L2853)。类型：`FunctionDef`。

```python
_route_contract_completed(spec: ScenarioSpec | None, distance_to_route_end_m: float | None, route_remaining_m: float | None=None) -> bool | None
```

Evaluate explicit route-finish contracts instead of treating frame exhaustion as success.

<a id="fn--route-finish-reached"></a>

### `_route_finish_reached`

源码位置：[integration/carla_runner.py 第 2868 行](../../../integration/carla_runner.py#L2868)。类型：`FunctionDef`。

```python
_route_finish_reached(*, route_remaining_m: float | None, distance_to_route_end_m: float | None, finish_radius_m: float) -> bool
```

Accept the continuous endpoint without trusting a coarse waypoint alone.

Route progress remains the primary guard so that a looping route cannot finish
merely because it passes close to its endpoint early. Near the final few
samples, however, physical endpoint distance is more precise than the
nearest-waypoint remainder.

<a id="fn--route-run-can-end-early"></a>

### `_route_run_can_end_early`

源码位置：[integration/carla_runner.py 第 2891 行](../../../integration/carla_runner.py#L2891)。类型：`FunctionDef`。

```python
_route_run_can_end_early(spec: ScenarioSpec | None, *, elapsed_s: float, speed_mps: float, route_remaining_m: float | None, distance_to_route_end_m: float | None, timeline_completed: bool, command_finished: bool, canonical_pending: bool, deferred_command_count: int, maneuver_active: bool, qwen_contract_completed: bool, extension_contract_completed: bool, collision_seen: bool, safety_reasons: set[str]) -> bool
```

End a bounded route run once its real completion contracts are terminal.

``duration_s`` remains a fail-safe upper bound. Long routes may finish
earlier, but only after their declared minimum evidence duration and every
command/Qwen/extension lifecycle has completed.

<a id="fn--remaining-route-distances"></a>

### `_remaining_route_distances`

源码位置：[integration/carla_runner.py 第 2937 行](../../../integration/carla_runner.py#L2937)。类型：`FunctionDef`。

```python
_remaining_route_distances(points: Sequence[tuple[float, float]]) -> tuple[float, ...]
```

Return distance-to-go at each route point, including repeated coordinates.

<a id="fn--distance-contract-remaining-m"></a>

### `_distance_contract_remaining_m`

源码位置：[integration/carla_runner.py 第 2951 行](../../../integration/carla_runner.py#L2951)。类型：`FunctionDef`。

```python
_distance_contract_remaining_m(total_distance_m: float, route_progress_m: float) -> float
```

Return distance-to-go from independent mission progress.

A voice manoeuvre may temporarily replace the controller's local route.
Distance-coverage completion must not freeze on the last nearest index of
the replaced route.

<a id="fn--minimum-gap-contract-completed"></a>

### `_minimum_gap_contract_completed`

源码位置：[integration/carla_runner.py 第 2970 行](../../../integration/carla_runner.py#L2970)。类型：`FunctionDef`。

```python
_minimum_gap_contract_completed(spec: ScenarioSpec | None, min_gap_m: float | None) -> bool | None
```

Evaluate a declared front-gap floor as a hard scenario contract.

<a id="fn--intentional-qwen-failure-completed"></a>

### `_intentional_qwen_failure_completed`

源码位置：[integration/carla_runner.py 第 2978 行](../../../integration/carla_runner.py#L2978)。类型：`FunctionDef`。

```python
_intentional_qwen_failure_completed(spec: ScenarioSpec | None, *, frames: int, final_speed_mps: float | None, collision_seen: bool) -> bool | None
```

Accept fail-closed system probes without requiring a valid Qwen plan.

<a id="fn--route-stop-trigger-m"></a>

### `_route_stop_trigger_m`

源码位置：[integration/carla_runner.py 第 3006 行](../../../integration/carla_runner.py#L3006)。类型：`FunctionDef`。

```python
_route_stop_trigger_m(speed_mps: float, finish_radius_m: float, decel_mps2: float=2.5) -> float
```

Choose an endpoint braking trigger that stops inside the finish radius.

Aim for the middle of the permitted standstill envelope rather than its
outer edge.  The margin absorbs controller and route-projection error while
a realistic closed-loop service deceleration still avoids stopping a long
route before its physical distance contract is satisfied.

<a id="fn--topology-planning-distance-m"></a>

### `_topology_planning_distance_m`

源码位置：[integration/carla_runner.py 第 3020 行](../../../integration/carla_runner.py#L3020)。类型：`FunctionDef`。

```python
_topology_planning_distance_m(remaining_contract_m: float, finish_radius_m: float) -> float
```

Keep a topology reference available until physical coverage is complete.

Ego motion can be slightly shorter than the sampled centreline because the
controller rounds corners.  Planning exactly the remaining distance can
therefore exhaust the reference before the distance tracker reaches its
contract.  A small proportional reserve prevents terminal speed tapering;
physical coverage remains the only completion metric.

<a id="fn--route-recovery-hold-reference"></a>

### `_route_recovery_hold_reference`

源码位置：[integration/carla_runner.py 第 3038 行](../../../integration/carla_runner.py#L3038)。类型：`FunctionDef`。

```python
_route_recovery_hold_reference(vehicle: RuntimeVehicleState) -> RouteReference
```

Build a valid ego-aligned zero-speed reference while replanning is pending.

<a id="fn--route-local-reference-needs-refresh"></a>

### `_route_local_reference_needs_refresh`

源码位置：[integration/carla_runner.py 第 3058 行](../../../integration/carla_runner.py#L3058)。类型：`FunctionDef`。

```python
_route_local_reference_needs_refresh(reference: RouteReference | None, global_route: GlobalRoute, route_s: float, refresh_margin_m: float) -> bool
```

Refresh a local window only when its usable forward horizon is exhausted.

<a id="fn--map-short-name"></a>

### `_map_short_name`

源码位置：[integration/carla_runner.py 第 3080 行](../../../integration/carla_runner.py#L3080)。类型：`FunctionDef`。

```python
_map_short_name(map_name: str) -> str
```

仅按正斜杠取地图路径末段；不处理反斜杠规范化，不等同于sensor_stability.map_contract_name。

<a id="fn--map-contract-name"></a>

### `_map_contract_name`

源码位置：[integration/carla_runner.py 第 3084 行](../../../integration/carla_runner.py#L3084)。类型：`FunctionDef`。

```python
_map_contract_name(map_name: str) -> str
```

先取末段，再大小写不敏感去掉末尾_Opt，用于普通/优化地图契约比较；不证明两张地图资产内容相同。

<a id="fn--scenario-clean-world-on-start"></a>

### `_scenario_clean_world_on_start`

源码位置：[integration/carla_runner.py 第 3089 行](../../../integration/carla_runner.py#L3089)。类型：`FunctionDef`。

```python
_scenario_clean_world_on_start(spec: ScenarioSpec | None) -> bool
```

Return an explicit isolated-run reset policy without affecting other scenes.

<a id="fn--build-resume-segment-spec"></a>

### `_build_resume_segment_spec`

源码位置：[integration/carla_runner.py 第 3099 行](../../../integration/carla_runner.py#L3099)。类型：`FunctionDef`。

```python
_build_resume_segment_spec(spec: ScenarioSpec, *, route_progress_m: float, completed_command_count: int, target_speed_kph: float) -> tuple[ScenarioSpec, tuple[str, ...]]
```

Derive a clearly labelled continuation contract from verified progress.

<a id="fn--select-load-map"></a>

### `_select_load_map`

源码位置：[integration/carla_runner.py 第 3255 行](../../../integration/carla_runner.py#L3255)。类型：`FunctionDef`。

```python
_select_load_map(requested_map: str, available_maps: tuple[str, ...]) -> str
```

请求已带_Opt时原样返回；否则若available_maps含同名_Opt（末段大小写不敏感），返回优化短名，未找到回原请求。选择字符串，不执行load_world。

<a id="fn--warm-up-loaded-map"></a>

### `_warm_up_loaded_map`

源码位置：[integration/carla_runner.py 第 3266 行](../../../integration/carla_runner.py#L3266)。类型：`FunctionDef`。

```python
_warm_up_loaded_map(world: Any, timeout_s: float) -> None
```

Ensure a prior interrupted synchronous run cannot stall map warm-up.

<a id="fn--import-carla-api"></a>

### `_import_carla_api`

源码位置：[integration/carla_runner.py 第 3279 行](../../../integration/carla_runner.py#L3279)。类型：`FunctionDef`。

```python
_import_carla_api() -> Any
```

先常规import carla；仅确实缺carla包时fallback，其他缺依赖直接重抛。按当前Python cp标签在仓库及父目录simulator/carla0916/PythonAPI/carla/dist找首个匹配wheel，解压到/tmp/carla_python_api并前插sys.path再导入。会写临时文件、修改导入路径；找不到抛ModuleNotFoundError，不下载wheel。

<a id="fn--maneuver-junction-exited"></a>

### `_maneuver_junction_exited`

源码位置：[integration/carla_runner.py 第 3312 行](../../../integration/carla_runner.py#L3312)。类型：`FunctionDef`。

```python
_maneuver_junction_exited(*, junction_seen: bool, current_is_junction: bool, heading_change_deg: float, distance_from_start_m: float, behavior: str | None) -> bool
```

Return whether an explicit turn maneuver has completed the junction.

Prefer CARLA's waypoint junction transition when it is available.  Some
valid turns do not expose a reliable ``is_junction`` transition, so an
explicit TURN_LEFT/TURN_RIGHT step may use a conservative geometric
fallback after a substantial heading change and forward displacement.

<a id="fn-run"></a>

### `run`

源码位置：[integration/carla_runner.py 第 3342 行](../../../integration/carla_runner.py#L3342)。类型：`FunctionDef`。

```python
run(args: argparse.Namespace) -> None
```

加载DrivingPolicy/ScenarioSpec，处理resume和扩展合同；validate_scenario_only输出合同摘要后返回（不连CARLA，但仍读取policy并解析扩展）。正常路径解析参数覆盖、连接CARLA、生成参与者/路线/传感器，循环tick→感知→命令/异步规划→A/B/C/D→apply_control→证据。末尾合并Qwen/extension/base验收。外层BaseException打印分类、尽力全刹/终结活动命令/记录失败后重抛，finally关闭桥/后端/麦克风等；资源还由CarlaSession管理。会修改args的有效配置，不应复用原args断言CLI值未变。

<a id="fn-main"></a>

### `main`

源码位置：[integration/carla_runner.py 第 6785 行](../../../integration/carla_runner.py#L6785)。类型：`FunctionDef`。

```python
main() -> None
```

创建并解析runner CLI，先做数值范围和组合约束再run(args)。remote路径需sensors+realtime，不能并用command-json/audio；live-mic与输入文件冲突在run判定。parser.error退出，不统一包装成run证据；只有代码实际检查的约束才能称已拒绝，不能把所有float默认都当有isfinite校验。

## 内部调用与异常路径

- `_select_deferred_commands` 调用：`command.envelope.get`, `retained.append`, `selected.append`, `str`, `str(command.envelope.get('intent', '')).strip`, `str(command.envelope.get('intent', '')).strip().upper`, `tuple`.
- `_canonical_poll_wait_timeout_ms` 调用：`float`.
- `_compiled_plan_from_payload` 调用：`CompiledManeuverPlan`, `CompiledPlanStep`, `TypeError`, `ValueError`, `dict`, `float`, `int`, `isinstance`, `len`, `payload.get`, `str`, `tuple`.
- `_maneuver_target_visible` 调用：`_legacy_target_classes`, `any`, `item.class_name.lower`, `step.target.get`, `str`, `target_id.startswith`.
- `_legacy_target_classes` 调用：`aliases.get`, `target_id.removeprefix`, `target_id.removeprefix('legacy-').rsplit`.
- `_maneuver_target_gap_s` 调用：`_maneuver_target_distance_m`, `float`, `max`.
- `_maneuver_target_distance_m` 调用：`_legacy_target_classes`, `float`, `item.class_name.lower`, `next`, `step.target.get`, `str`, `target_id.startswith`.
- `_physical_actor_id_for_target` 调用：`str`, `target_aliases.get`.
- `_maneuver_step_reanchors_target` 调用：`step.target.get`, `str`.
- `_record_maneuver_update` 调用：`asdict`, `extension_runtime.note_maneuver_terminal_reason`, `extension_runtime.note_terminal`, `json.dumps`, `monitor.record_replan`, `monitor.record_terminal`, `print`, `recorder.record_canonical_routing`, `recorder.record_feedback`.
- `_note_extension_terminal` 调用：`feedback.get`, `getattr`, `isinstance`, `runtime.note_terminal`, `str`, `str(getattr(status, 'value', status)).upper`.
- `_note_safety_feedback` 调用：`feedback.get`, `getattr`, `isinstance`, `safety_event.get`, `safety_reasons.add`.
- `_qwen_resolution_reason` 调用：`f"{reason or ''} {detail}".strip`, `feedback.get`, `getattr`, `isinstance`, `str`.
- `_speed_mps` 调用：`math.hypot`.
- `_actor_bbox_clearance_m` 调用：`_actor_horizontal_radius_m`, `actor.get_location`, `ego.get_location`, `ego.get_location().distance`, `float`, `max`.
- `_actor_horizontal_radius_m` 调用：`float`, `getattr`, `math.hypot`, `math.isfinite`.
- `_actor_signed_route_clearance_m` 调用：`_actor_horizontal_radius_m`, `float`.
- `_actor_signed_longitudinal_clearance_m` 调用：`_actor_horizontal_radius_m`, `actor.get_location`, `ego.get_transform`, `ego_transform.get_forward_vector`, `float`.
- `_acceptance_lateral_controller` 调用：`PurePursuitController`, `PurePursuitParams`.
- `_follow_ego_spectator` 调用：`carla.Location`, `carla.Rotation`, `carla.Transform`, `ego.get_transform`, `transform.get_forward_vector`, `world.get_spectator`, `world.get_spectator().set_transform`.
- `_scenario_maneuver` 调用：`abs`, `isinstance`, `item.envelope.get`, `parameters.get`, `str`, `str(item.envelope.get('intent', '')).upper`, `str(parameters.get('direction', '')).upper`.
- `_scenario_requires_adjacent_lane_anchor` 调用：`abs`, `actor.get`, `float`, `isinstance`, `position.get`, `runtime_support.get`, `spawn.get`, `spec.extensions.get`, `str`, `str(actor.get('type', '')).strip`, `str(actor.get('type', '')).strip().lower`, `str(position.get('lane_relation', 'CURRENT')).strip`, `str(position.get('lane_relation', 'CURRENT')).strip().upper`.
- `_scenario_actor_lanes_fit_route` 调用：`_scenario_actors`, `route_relative_carla_transform`.
- `_scenario_requires_target_lane_occupancy` 调用：`any`, `bool`, `isinstance`, `spec.extensions.get`.
- `_actor_activation_due` 调用：`TypeError`, `actor_spec.get`, `isinstance`, `scenario_trigger_satisfied`.
- `_actor_deactivation_due` 调用：`TypeError`, `actor_spec.get`, `isinstance`, `scenario_trigger_satisfied`.
- `_release_scenario_actor_if_due` 调用：`RuntimeError`, `_actor_deactivation_due`, `actor_spec.get`, `json.dumps`, `print`, `session.actors.release`, `str`.
- `_scenario_uses_dynamic_out_and_back` 调用：`spec.extensions.get`, `str`, `str(spec.extensions.get('maneuver_route_mode', '')).strip`, `str(spec.extensions.get('maneuver_route_mode', '')).strip().lower`.
- `_scenario_startup_maneuver` 调用：`_scenario_maneuver`, `_scenario_uses_dynamic_out_and_back`, `first.get`, `isinstance`, `len`, `parameters.get`, `str`, `str(first.get('intent', '')).strip`, `str(first.get('intent', '')).strip().upper`, `str(parameters.get('direction', '')).strip`, `str(parameters.get('direction', '')).strip().upper`.
- `_scenario_lane_change_profile` 调用：`TypeError`, `isinstance`, `spec.extensions.get`.
- `_traffic_light_stop_points` 调用：`actors.filter`, `callable`, `float`, `getattr`, `getter`, `points.append`, `tuple`, `world.get_actors`.
- `_vehicle_state` 调用：`RuntimeVehicleState`, `_speed_mps`, `ego.get_transform`, `ego.get_velocity`, `str`, `world_map.get_waypoint`.
- `_planner_runtime_state` 调用：`any`, `available.append`, `bool`, `current.next`, `driving`, `ego.get_location`, `getattr`, `len`, `range`, `str`, `str(getattr(candidate, 'lane_type', 'Driving')).split`, `str(getattr(candidate, 'lane_type', 'Driving')).split('.')[-1].upper`, `tuple`, `waypoint.get_left_lane`, `waypoint.get_right_lane`, `world_map.get_waypoint`.
- `_apply_compiled_plan_route` 调用：`ValueError`, `_lane_change_route_parameters`, `_route_starts_near_ego`, `build_lane_change_route_reference`, `build_route_reference`, `compiled_plan.get`, `float`, `isinstance`, `replace`, `route_behavior.rsplit`, `route_behavior.startswith`, `step.get`, `str`, `str(step.get('behavior', '')).upper`, `target.get`.
- `_route_starts_near_ego` 调用：`ego.get_location`, `float`, `math.hypot`.
- `_lane_change_route_parameters` 调用：`ValueError`, `any`, `defaults.items`, `dict`, `float`, `math.isfinite`, `min`, `positive_values.values`, `raw.get`, `set`, `sorted`, `values.items`.
- `_is_deferred_dynamic_lane_change` 调用：`bool`, `step.behavior.startswith`.
- `_dynamic_return_destination_xy` 调用：`float`, `max`, `project_route_progress_m`, `route_pose_at_s`.
- `_maneuver_lane_label` 调用：`bool`, `lane_ids.items`, `math.dist`, `next`, `route_deviation_m`, `step.target.get`, `str`, `str(step.target.get('target_lane') or '').strip`, `str(step.target.get('target_lane') or '').strip().upper`.
- `_mission_speed_after_maneuver` 调用：`float`.
- `_retain_route_for_maneuver` 调用：`bool`.
- `_scene_from_world` 调用：`PerceptionFrame`, `_speed_mps`, `_world_vehicle_detections`, `actor_speed_limit_mps`, `ego.get_location`, `ego.get_velocity`, `events.flags_for_frame`, `getattr`, `lane_metrics`, `scenario_lead.get_location`, `scenario_lead.get_location().distance`, `scenario_lead.get_velocity`, `traffic_light_and_stop_distance`.
- `_world_vehicle_detections` 调用：`DetectedObject`, `TypeError`, `actor.get_location`, `detections.append`, `detections.sort`, `ego.get_transform`, `float`, `getattr`, `isinstance`, `math.hypot`, `max`, `min`, `transform.get_forward_vector`, `transform.get_right_vector`, `tuple`.
- `_bind_scenario_actor_ids` 调用：`abs`, `actor.get_location`, `actor_spec.get`, `bound.append`, `candidates.append`, `ego.get_transform`, `ego_transform.get_forward_vector`, `float`, `getattr`, `math.atan2`, `math.radians`, `max`, `min`, `origin.distance`, `replace`, `semantic_updates.update`, `set`, `str`, `str(actor_spec.get('type', '')).lower`, `str(detection.class_name).lower`, `tuple`, `used.add`.
- `_sensor_evidence_actor_ids` 调用：`_sensor_evidence_target_aliases`, `_sensor_evidence_target_aliases(scene, ego, actors).values`, `dict.fromkeys`, `tuple`.
- `_sensor_evidence_target_aliases` 调用：`_bind_scenario_actor_ids`, `actor_spec.get`, `str`, `zip`.
- `_spawn_static_lead` 调用：`RuntimeError`, `ego.get_location`, `ego.get_transform`, `ego_transform.get_forward_vector`, `lead.get_location`, `lead.get_location().distance`, `lead.set_simulate_physics`, `print`, `range`, `session.track_actor`, `type`, `type(origin)`, `world.try_spawn_actor`.
- `_scenario_actor` 调用：`ValueError`, `_scenario_actors`, `len`.
- `_scenario_actors` 调用：`actor.get`, `actor_type.strip`, `actor_type.strip().lower`, `str`, `str(actor.get('type', '')).strip`, `str(actor.get('type', '')).strip().lower`, `tuple`.
- `_scenario_walkers` 调用：`actor.get`, `str`, `str(actor.get('type', '')).strip`, `str(actor.get('type', '')).strip().lower`, `str(actor.get('type', '')).strip().lower().startswith`, `tuple`.
- `_scenario_static_props` 调用：`actor.get`, `str`, `str(actor.get('type', '')).strip`, `str(actor.get('type', '')).strip().lower`, `tuple`.
- `_cleanup_stale_scenario_actors` 调用：`actor.get`, `attributes.get`, `callable`, `destroy`, `getattr`, `isinstance`, `role_name.startswith`, `str`, `str(actor.get('actor_id', '')).strip`, `tuple`, `world.get_actors`.
- `_scenario_local_transform` 调用：`carla_api.Location`, `carla_api.Rotation`, `carla_api.Transform`, `float`, `getattr`, `math.cos`, `math.radians`, `math.sin`, `max`, `spawn.get`.
- `_active_actor_route_context` 调用：`rebase_actor_route_position`.
- `_scenario_vehicle_speed_mps` 调用：`TypeError`, `actor_spec.get`, `behavior.get`, `float`, `isinstance`, `max`.
- `_signed_forward_speed_mps` 调用：`actor.get_transform`, `actor.get_transform().get_forward_vector`, `actor.get_velocity`, `float`.
- `_occupied_actor_locations` 调用：`callable`, `get_actors`, `get_location`, `getattr`, `locations.append`, `str`, `str(getattr(actor, 'type_id', '')).startswith`, `tuple`.
- `_spawn_scenario_vehicle` 调用：`LookupError`, `RuntimeError`, `TypeError`, `_occupied_actor_locations`, `_scenario_local_transform`, `_scenario_vehicle_speed_mps`, `actor_resample_offsets`, `actor_spec.get`, `blueprint.has_attribute`, `blueprint.set_attribute`, `callable`, `candidate_spec.get`, `carla_api.Vector3D`, `ego.get_location`, `ego.get_transform`, `float`, `getattr`, `isinstance`, `library.find`, `max`, `offset_actor_route_position`, `placement_failures.append`, `print`, `route_relative_carla_transform`, `session.track_actor`, `set_physics`, `set_velocity`, `str`, `transform.get_forward_vector`, `transform.location.distance`, `validate_actor_transform`, `world.get_blueprint_library`, `world.get_map`, `world.try_spawn_actor`, `world_map.get_waypoint`.
- `_update_scenario_vehicle` 调用：`RuntimeError`, `_scenario_vehicle_speed_mps`, `_signed_forward_speed_mps`, `abs`, `actor_spec.get`, `behavior.get`, `bool`, `callable`, `carla_api.Vector3D`, `carla_api.VehicleControl`, `float`, `getattr`, `int`, `isinstance`, `lead.apply_control`, `lead.get_location`, `lead.get_transform`, `lead.get_transform().get_forward_vector`, `len`, `math.atan2`, `math.cos`, `math.degrees`, `math.hypot`, `math.radians`, `math.sin`, `max`, `min`, `range`, `round`, `set_velocity`, `str`, `str(behavior.get('direction', 'RIGHT')).strip`, `str(behavior.get('direction', 'RIGHT')).strip().upper`, `str(behavior.get('mode', '')).strip`, `str(behavior.get('mode', '')).strip().lower`, `type`, `waypoint.next`, `world_map.get_waypoint`.
- `_scenario_target_lane_occupied_count` 调用：`RuntimeError`, `callable`, `ego.get_location`, `ego_waypoint.get_left_lane`, `ego_waypoint.get_right_lane`, `getattr`, `next_frontier.extend`, `next_waypoints`, `normalized.endswith`, `range`, `set`, `str`, `str(maneuver).upper`, `target_segments.add`, `tuple`, `vehicle.get_location`, `world_map.get_waypoint`.
- `_spawn_scenario_walker` 调用：`LookupError`, `RuntimeError`, `TypeError`, `_occupied_actor_locations`, `_scenario_local_transform`, `actor_resample_offsets`, `actor_spec.get`, `blueprint.set_attribute`, `callable`, `candidate_behavior.get`, `candidate_spec.get`, `ego.get_transform`, `float`, `getattr`, `has_attribute`, `isinstance`, `len`, `library.filter`, `library.find`, `list`, `max`, `offset_actor_route_position`, `placement_failures.append`, `print`, `route_relative_carla_transform`, `route_relative_target_location`, `session.track_actor`, `set_physics`, `spawn.get`, `str`, `tuple`, `validate_actor_transform`, `world.get_blueprint_library`, `world.get_map`, `world.try_spawn_actor`, `world_map.get_waypoint`.
- `_update_scenario_walker` 调用：`RuntimeError`, `TypeError`, `actor_spec.get`, `behavior.get`, `carla_api.Vector3D`, `carla_api.WalkerControl`, `float`, `getattr`, `isinstance`, `len`, `math.hypot`, `max`, `spawn.get`, `walker.apply_control`, `walker.get_location`.
- `_spawn_scenario_static_prop` 调用：`LookupError`, `RuntimeError`, `TypeError`, `ValueError`, `_occupied_actor_locations`, `_scenario_local_transform`, `actor_resample_offsets`, `actor_spec.get`, `callable`, `candidate_spec.get`, `ego.get_transform`, `getattr`, `isinstance`, `offset_actor_route_position`, `placement_failures.append`, `print`, `route_relative_carla_transform`, `session.track_actor`, `set_physics`, `str`, `validate_actor_transform`, `world.get_blueprint_library`, `world.get_blueprint_library().find`, `world.get_map`, `world.try_spawn_actor`.
- `_select_scenario_lead` 调用：`abs`, `candidates.append`, `ego.get_location`, `ego.get_transform`, `ego.get_transform().get_forward_vector`, `float`, `getattr`, `math.hypot`, `min`, `vehicle.get_location`.
- `_scenario_traffic_light_distance` 调用：`ValueError`, `_scenario_actor`, `actor.get`, `float`, `math.isfinite`.
- `_traffic_light_scenario_anchor` 调用：`RuntimeError`, `actors.filter`, `callable`, `candidates.append`, `candidates.sort`, `carla_api.Location`, `carla_api.Rotation`, `carla_api.Transform`, `float`, `getattr`, `getter`, `int`, `len`, `lights.sort`, `list`, `transform.get_forward_vector`, `world.get_actors`, `world_map.get_waypoint`.
- `_scenario_traffic_light_observation` 调用：`RuntimeError`, `_scenario_traffic_light_signed_clearance_m`, `light.get_state`, `max`, `replace`, `str`, `str(light.get_state()).split`, `str(light.get_state()).split('.')[-1].upper`.
- `_scenario_traffic_light_distance_to_stop_line_m` 调用：`_scenario_traffic_light_signed_clearance_m`, `max`.
- `_scenario_traffic_light_signed_clearance_m` 调用：`RuntimeError`, `abs`, `callable`, `candidates.append`, `ego.get_location`, `ego.get_transform`, `ego.get_transform().get_forward_vector`, `float`, `getattr`, `getter`, `max`, `min`.
- `_apply_virtual_scenario` 调用：`ego.get_location`, `math.sqrt`, `max`, `replace`.
- `_scenario_facts` 调用：`PerceptionFrame`, `_lead_vehicle_travel_m`, `abs`, `actor.get`, `actor_type.startswith`, `behavior.get`, `ego.get_location`, `float`, `isinstance`, `len`, `math.sqrt`, `max`, `min`, `spawn.get`, `str`, `str(actor.get('state', 'UNKNOWN')).upper`, `str(actor.get('type', '')).lower`, `updates.get`.
- `_lead_vehicle_travel_m` 调用：`max`, `min`.
- `_select_scene_facts` 调用：`ValueError`, `getattr`, `replace`.
- `_apply_scenario_speed_limit` 调用：`float`, `max`, `min`, `replace`.
- `_load_command` 调用：`FileNotFoundError`, `HighLevelCommandAdapter`, `HighLevelCommandAdapter().adapt`, `Path`, `Path(args.command_json).read_text`, `TypeError`, `audio_path.is_file`, `audio_to_command`, `dict`, `is_high_level_command`, `isinstance`, `json.loads`, `preload_voice_models`, `print`, `str`.
- `_qwen_voice_command` 调用：`ValueError`, `getattr`, `len`, `spec.commands[0].envelope.get`, `str`, `str(getattr(args, 'qwen_voice_command', '') or '').strip`, `str(spec.commands[0].envelope.get('source_text', '')).strip`.
- `_qwen_desired_speed_mps` 调用：`ValueError`, `float`, `isinstance`, `len`, `parameters.get`, `resolve_scenario_command`, `resolved.get`, `str`, `str(parameters.get('unit', 'm/s')).strip`, `str(parameters.get('unit', 'm/s')).strip().lower`, `str(parameters.get('unit', 'm/s')).strip().lower().replace`, `type`.
- `_save_qwen_rgb_image` 调用：`''.join`, `Image.fromarray`, `Image.fromarray(carla_rgb_array(measurement), mode='RGB').save`, `Path`, `Path(image_root).expanduser`, `Path(image_root).expanduser().resolve`, `RuntimeError`, `ValueError`, `carla_rgb_array`, `character.isalnum`, `path.relative_to`, `path.relative_to(root).as_posix`, `root.mkdir`.
- `_build_qwen_context` 调用：`QwenInputContext`, `dict`, `list`, `safety.get`.
- `_evidence_recorder` 调用：`Path`, `ScenarioEvidenceRecorder`, `_git_code_version`, `datetime.now`, `datetime.now().strftime`, `directory.mkdir`, `getattr`, `os.environ.get`, `print`, `recorder.start_run`, `spec.expected.get`, `type`, `vars`, `vars(args).items`.
- `_git_code_version` 调用：`Path`, `Path(__file__).resolve`, `completed.stdout.strip`, `subprocess.run`.
- `_rejected_load_envelope` 调用：`time.monotonic_ns`, `type`.
- `_warm_up_sensor_bridge` 调用：`RuntimeError`, `bridge.acquire`, `min`, `range`, `session.tick`, `world.get_snapshot`.
- `_runtime_health_completed` 调用：`any`, `reason.startswith`.
- `_declared_scenario_runtime_completed` 调用：`_runtime_health_completed`.
- `_c_perception_safety_reason` 调用：`''.join`, `''.join((char if char.isalnum() else '_' for char in reason)).strip`, `c_safety_state.get`, `char.isalnum`, `str`, `str(c_safety_state.get('object_class') or 'HAZARD').strip`, `str(c_safety_state.get('object_class') or 'HAZARD').strip().upper`, `str(c_safety_state.get('reason') or 'FAIL_CLOSED').strip`, `str(c_safety_state.get('reason') or 'FAIL_CLOSED').strip().upper`, `str(c_safety_state.get('recommended_action', '')).strip`, `str(c_safety_state.get('recommended_action', '')).strip().upper`.
- `_c_safety_speed_cap_mps` 调用：`c_safety_state.get`, `float`, `isinstance`, `math.isfinite`, `str`, `str(c_safety_state.get('recommended_action', '')).upper`, `type`.
- `_single_sensor_fault_speed_cap_mps` 调用：`float`, `len`, `max`, `min`, `str`, `{str(item) for item in active_sensor_faults}.intersection`.
- `_c_speed_cap_control_override` 调用：`float`, `math.isfinite`, `min`.
- `_expected_safety_completed` 调用：`' '.join`, `' '.join(meaningful).lower`, `_runtime_health_completed`, `any`, `expected.get`, `float`, `isinstance`, `str`, `str(token).lower`.
- `_scenario_raw_control_fault` 调用：`expected.get`, `reason_tokens.intersection`, `str`, `str(token).strip`, `str(token).strip().lower`.
- `_route_contract_completed` 调用：`_route_finish_reached`, `spec.expected.get`.
- `_route_finish_reached` 调用：`max`.
- `_route_run_can_end_early` 调用：`_route_finish_reached`, `_runtime_health_completed`, `float`, `spec.expected.get`.
- `_remaining_route_distances` 调用：`len`, `math.dist`, `range`, `tuple`.
- `_distance_contract_remaining_m` 调用：`ValueError`, `float`, `math.isfinite`, `max`.
- `_minimum_gap_contract_completed` 调用：`float`.
- `_intentional_qwen_failure_completed` 调用：`any`, `float`, `int`, `isinstance`, `proposed.get`, `spec.expected.get`, `spec.extensions.get`.
- `_route_stop_trigger_m` 调用：`ValueError`.
- `_topology_planning_distance_m` 调用：`ValueError`, `max`.
- `_route_recovery_hold_reference` 调用：`RouteReference`, `math.cos`, `math.radians`, `math.sin`, `tuple`.
- `_route_local_reference_needs_refresh` 调用：`float`, `metadata.get`.
- `_map_short_name` 调用：`map_name.rsplit`.
- `_map_contract_name` 调用：`_map_short_name`, `short_name.lower`, `short_name.lower().endswith`.
- `_scenario_clean_world_on_start` 调用：`TypeError`, `spec.extensions.get`, `type`.
- `_build_resume_segment_spec` 调用：`ValueError`, `_actor_activation_due`, `_actor_deactivation_due`, `activation_windows.items`, `actor.get`, `any`, `command.envelope.get`, `dict`, `expected_behaviors.add`, `extensions.get`, `extensions.pop`, `int`, `isinstance`, `len`, `minimum_distances.items`, `next`, `proposed.get`, `proposed.pop`, `qwen_expected.pop`, `replace`, `round`, `set`, `sorted`, `str`, `str(command.envelope.get('intent', '')).upper`, `tuple`, `values.items`.
- `_select_load_map` 调用：`_map_short_name`, `_map_short_name(available).lower`, `optimized_short.lower`, `requested_short.lower`, `requested_short.lower().endswith`.
- `_warm_up_loaded_map` 调用：`bool`, `getattr`, `print`, `world.apply_settings`, `world.get_settings`, `world.wait_for_tick`.
- `_import_carla_api` 调用：`', '.join`, `ModuleNotFoundError`, `Path`, `Path(__file__).resolve`, `archive.extractall`, `extract_root.exists`, `extract_root.mkdir`, `importlib.import_module`, `root.glob`, `sorted`, `str`, `sys.path.insert`, `zipfile.ZipFile`.
- `run` 调用：`','.join`, `(submission.orchestration.model_request or {}).get`, `AsyncQwenDecisionBridge`, `CanonicalRuntimeBridge`, `CarlaPerceptionBridge`, `CarlaSession`, `CommandTimeline`, `ConservativeSensorFusion`, `ControlOutput`, `ControlRuntime`, `DistanceCoverageTracker`, `FrameTiming`, `InterfaceRegistry`, `LiveVoiceConfig`, `LiveVoiceSource`, `ManeuverFSM`, `OnnxYoloDetector`, `OpenAICompatibleQwenVLBackend`, `OrchestratorConfig`, `Path`, `Path(getattr(args, 'qwen_image_dir', 'artifacts/runtime/qwen_live')).expanduser`, `Path(getattr(args, 'qwen_image_dir', 'artifacts/runtime/qwen_live')).expanduser().resolve`, `PerceptionFrame`, `PipelineOrchestrator`, `QwenImageStager`, `QwenScenarioMonitor`, `QwenServiceClient`, `RouteManager`, `RouteProgressTracker`, `RouteRecoveryPolicy.from_mapping`, `RouteRecoveryTracker`, `RouteReference`, `RuntimeError`, `RuntimeWatchdog`, `SafetySupervisor`, `ScenarioExtensionRuntime`, `ScenarioQwenFaultInjector`, `ScenarioSpec.load`, `StrictQwenVLAdapter`, `TypeError`, `ValueError`, `_DeferredCommand`, `_acceptance_lateral_controller`, `_active_actor_route_context`, `_actor_activation_due`, `_actor_bbox_clearance_m`, `_actor_signed_longitudinal_clearance_m`, `_actor_signed_route_clearance_m`, `_apply_compiled_plan_route`, `_apply_scenario_speed_limit`, `_apply_virtual_scenario`, `_bind_scenario_actor_ids`, `_build_qwen_context`, `_build_resume_segment_spec`, `_c_perception_safety_reason`, `_c_safety_speed_cap_mps`, `_c_speed_cap_control_override`, `_canonical_poll_wait_timeout_ms`, `_cleanup_stale_scenario_actors`, `_compiled_plan_from_payload`, `_declared_scenario_runtime_completed`, `_distance_contract_remaining_m`, `_dynamic_return_destination_xy`, `_evidence_recorder`, `_expected_safety_completed`, `_follow_ego_spectator`, `_import_carla_api`, `_intentional_qwen_failure_completed`, `_is_deferred_dynamic_lane_change`, `_lane_change_route_parameters`, `_load_command`, `_maneuver_junction_exited`, `_maneuver_lane_label`, `_maneuver_step_reanchors_target`, `_maneuver_target_distance_m`, `_maneuver_target_gap_s`, `_maneuver_target_passed`, `_maneuver_target_visible`, `_map_contract_name`, `_map_contract_name(current_map).lower`, `_map_contract_name(requested_map).lower`, `_minimum_gap_contract_completed`, `_mission_speed_after_maneuver`, `_note_extension_terminal`, `_note_safety_feedback`, `_physical_actor_id_for_target`, `_planner_runtime_state`, `_qwen_desired_speed_mps`, `_qwen_resolution_reason`, `_qwen_voice_command`, `_record_maneuver_update`, `_rejected_load_envelope`, `_release_scenario_actor_if_due`, `_remaining_route_distances`, `_retain_route_for_maneuver`, `_route_contract_completed`, `_route_finish_reached`, `_route_local_reference_needs_refresh`, `_route_recovery_hold_reference`, `_route_run_can_end_early`, `_route_starts_near_ego`, `_route_stop_trigger_m`, `_runtime_health_completed`, `_save_qwen_rgb_image`, `_scenario_actor`, `_scenario_actor_lanes_fit_route`, `_scenario_actors`, `_scenario_clean_world_on_start`, `_scenario_completed`, `_scenario_facts`, `_scenario_lane_change_profile`, `_scenario_maneuver`, `_scenario_raw_control_fault`, `_scenario_requires_adjacent_lane_anchor`, `_scenario_requires_target_lane_occupancy`, `_scenario_route_distance_m`, `_scenario_startup_maneuver`, `_scenario_static_props`, `_scenario_target_lane_occupied_count`, `_scenario_traffic_light_distance`, `_scenario_traffic_light_observation`, `_scenario_traffic_light_signed_clearance_m`, `_scenario_uses_dynamic_out_and_back`, `_scenario_walkers`, `_scene_from_world`, `_select_deferred_commands`, `_select_load_map`, `_select_scenario_lead`, `_select_scene_facts`, `_sensor_evidence_target_aliases`, `_single_sensor_fault_speed_cap_mps`, `_spawn_scenario_static_prop`, `_spawn_scenario_vehicle`, `_spawn_scenario_walker`, `_spawn_static_lead`, `_speed_mps`, `_topology_planning_distance_m`, `_traffic_light_scenario_anchor`, `_traffic_light_stop_points`, `_update_scenario_vehicle`, `_update_scenario_walker`, `_vehicle_state`, `_warm_up_loaded_map`, `_warm_up_sensor_bridge`, `abs`, `actor.get_location`, `actor.get_velocity`, `actor_longitudinal_clearances_m.get`, `actor_route_position.get`, `actor_spec.get`, `actor_state.get`, `anchor_waypoint.next`, `any`, `asdict`, `attach_default_sensors`, `attach_event_sensors`, `audit_control_sources`, `bool`, `bp.has_attribute`, `bp.set_attribute`, `build_acceptance_context`, `build_destination_route_reference`, `build_lane_change_route_reference`, `build_route_reference`, `build_scenario_route_reference`, `callable`, `canonical_bridge.fail_all_pending`, `canonical_bridge.poll`, `canonical_bridge.submit`, `canonical_mode.upper`, `canonical_orchestrator.close`, `canonical_registry.warm`, `carla.Client`, `carla.Location`, `carla.Rotation`, `carla.Transform`, `carla.Vector3D`, `carla.VehicleControl`, `client.get_available_maps`, `client.get_world`, `client.load_world`, `client.set_timeout`, `command_turn_direction`, `compiled_step.get`, `configured_light.get`, `configured_state.upper`, `deferred.envelope.get`, `deferred.envelope.get('parameters', {}).get`, `deferred_commands.append`, `diagnose_runtime_failure`, `diagnose_runtime_failure(error).to_dict`, `dict`, `dict.fromkeys`, `distance_coverage_tracker.update`, `driving_policy.perception_parameters`, `driving_policy.safety_config`, `ego.apply_control`, `ego.get_location`, `ego.get_transform`, `ego.set_simulate_physics`, `ego.set_target_angular_velocity`, `ego.set_target_velocity`, `ego.set_transform`, `evidence_target_aliases.values`, `expected_contract.setdefault`, `extension_runtime.actor_state`, `extension_runtime.evaluate`, `extension_runtime.evidence`, `extension_runtime.note_actor_activated`, `extension_runtime.note_actor_trigger`, `extension_runtime.note_command_submitted`, `extension_runtime.note_control_observation`, `extension_runtime.note_emergency_recovered`, `extension_runtime.note_front_path_observation`, `extension_runtime.note_mission_route_restored`, `extension_runtime.note_perception_observation`, `extension_runtime.note_phase_completed`, `extension_runtime.note_qwen_plan`, `extension_runtime.note_qwen_resolution`, `extension_runtime.note_target_lane_occupancy`, `extension_runtime.ready_emergency_recovery`, `extension_runtime.restore_terminal_phase`, `extension_runtime.update_frame`, `extension_runtime.weather_parameters.items`, `float`, `frozen_getter`, `getattr`, `global_route.validation.to_dict`, `global_route_manager.local_reference`, `global_route_manager.plan`, `global_route_manager.plan_distance`, `global_route_manager.replan`, `global_route_manager.state`, `global_route_recovery.note_replan_succeeded`, `global_route_recovery.observe`, `global_route_state.to_dict`, `hasattr`, `high_level.get`, `int`, `isinstance`, `item.envelope.get`, `item.get`, `json.dumps`, `len`, `list`, `live_command.get`, `live_voice.poll`, `live_voice.preload`, `live_voice.start`, `live_voice.stop`, `load_driving_policy`, `maneuver_fsm.current_step.target.get`, `maneuver_fsm.fail`, `maneuver_fsm.start`, `maneuver_fsm.update`, `maneuver_route_steps_applied.add`, `maneuver_route_steps_applied.clear`, `math.cos`, `math.dist`, `math.hypot`, `math.radians`, `math.sin`, `max`, `min`, `next`, `orchestration.compiled_plan.get`, `os.environ.get`, `pending_prop_specs.append`, `pending_prop_specs.remove`, `pending_vehicle_specs.append`, `pending_vehicle_specs.remove`, `pending_walker_specs.append`, `pending_walker_specs.remove`, `perception_bridge.acquire`, `perception_sources.get`, `perception_sources.update`, `plan_waypoint.get_left_lane`, `plan_waypoint.get_right_lane`, `prepare_scenario_route`, `prepared_route.quality.to_dict`, `print`, `progress_tracker.update`, `project_route_progress_m`, `prop_spec.get`, `qwen_backend.close`, `qwen_bridge.close`, `qwen_bridge.latest`, `qwen_bridge.submit`, `qwen_client.pop_timing`, `qwen_context.to_payload`, `qwen_contract_report.to_dict`, `qwen_faults.append`, `qwen_faults.extend`, `qwen_image_stager.discard`, `qwen_image_stager.stage`, `qwen_image_stager.stage_multiview`, `qwen_pre_submit_timing.pop`, `qwen_scenario_monitor.finalize`, `qwen_scenario_monitor.record_behavior`, `qwen_scenario_monitor.record_plan`, `qwen_scenario_monitor.record_routing`, `qwen_scenario_monitor.record_terminal`, `qwen_target_aliases_by_command.pop`, `range`, `recorder.close`, `recorder.complete`, `recorder.fail`, `recorder.record_canonical_routing`, `recorder.record_command`, `recorder.record_feedback`, `recorder.record_qwen_event`, `recorder.record_qwen_trajectory`, `recorder.record_route_recovery_event`, `recorder.record_runtime_frame`, `replace`, `request_routing.get`, `resolution.runtime_envelope.get`, `resolve_scenario_command`, `result.final_control.to_dict`, `result.safety_reason.startswith`, `round`, `route_pose_at_s`, `route_refresh_alerts.append`, `runtime.clear_safety_alert_prefix`, `runtime.clear_safety_alerts`, `runtime.complete_active`, `runtime.fail_active`, `runtime.lateral.reset`, `runtime.release_scenario_stop_hold`, `runtime.step`, `runtime.submit_voice`, `safety_reasons.add`, `safety_reasons.discard`, `sample.safety_summary.reason.upper`, `sample.safety_summary.to_dict`, `scenario_actor_progress_trackers.clear`, `scenario_actor_progress_trackers.get`, `scenario_props.append`, `scenario_props.remove`, `scenario_traffic_light.freeze`, `scenario_traffic_light.get_state`, `scenario_traffic_light.set_state`, `scenario_trigger_satisfied`, `scenario_vehicles.append`, `scenario_vehicles.remove`, `scenario_walkers.append`, `scenario_walkers.remove`, `select_topology_route_anchor`, `sensor_specs_for_profile`, `session.spawn_ego`, `session.tick`, `set`, `setattr`, `sorted`, `source_audit.to_dict`, `spawned_scenario_actor_types.append`, `spec.expected.get`, `spec.extensions.get`, `spec.extensions['qwen_policy'].get`, `spec.route_contract.get`, `spec.world_destination`, `spec.world_route`, `started_route_step.behavior.rsplit`, `started_route_step.behavior.startswith`, `started_route_step.target.get`, `steer_fault.get`, `str`, `str(configured_light.get('state', 'RED')).strip`, `str(configured_light.get('state', 'RED')).strip().title`, `str(deferred.envelope.get('intent', '')).upper`, `str(getattr(feedback.status, 'value', feedback.status)).upper`, `str(high_level.get('action', '')).strip`, `str(high_level.get('action', '')).strip().upper`, `str(high_level.get('action', '')).upper`, `str(high_level.get('decision_source', '')).strip`, `str(high_level.get('decision_source', '')).strip().upper`, `str(item.envelope.get('intent', '')).upper`, `str(item.get('type', '')).lower`, `str(light_state).title`, `str(prop_spec.get('type', 'static.prop')).lower`, `str(scenario_traffic_light.get_state()).rsplit`, `str(scenario_traffic_light.get_state()).rsplit('.', 1)[-1].upper`, `str(started_route_step.target.get('target_lane') or '').strip`, `str(started_route_step.target.get('target_lane') or '').strip().upper`, `str(walker_spec.get('type', 'walker.pedestrian')).lower`, `summary.get`, `synchronize_route_progress`, `time.monotonic`, `time.monotonic_ns`, `time.sleep`, `timeline.due`, `topology_route.metadata.get`, `tracker.update`, `tuple`, `type`, `type(error).__name__.upper`, `vehicle_spec.get`, `walker_behavior.get`, `walker_spec.get`, `walker_trigger.get`, `warm_heading_waypoint_cache`, `watchdog.check`, `watchdog.heartbeat`, `watchdog.pause`, `watchdog.resume`, `watchdog_alerts.append`, `watchdog_alerts.extend`, `world.get_blueprint_library`, `world.get_blueprint_library().filter`, `world.get_map`, `world.get_snapshot`, `world.get_spectator`, `world.get_spectator().set_transform`, `world.set_weather`, `world_map.get_spawn_points`, `world_map.get_waypoint`, `{'front_rgb', 'lidar'}.issubset`.
- `main` 调用：`Path`, `Path(__file__).resolve`, `argparse.ArgumentParser`, `getattr`, `name.replace`, `os.environ.get`, `parser.add_argument`, `parser.error`, `parser.parse_args`, `run`, `str`, `str(args.qwen_base_url).strip`, `str(args.qwen_image_dir).strip`, `str(args.qwen_model).strip`.
- `driving` 调用：`getattr`, `str`, `str(getattr(candidate, 'lane_type', 'Driving')).split`, `str(getattr(candidate, 'lane_type', 'Driving')).split('.')[-1].upper`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `_actor_activation_due`，第 628 行：`TypeError('scenario actor activation_trigger must be an object')`。
- `_actor_deactivation_due`，第 647 行：`TypeError('scenario actor deactivation_trigger must be an object')`。
- `_apply_compiled_plan_route`，第 834 行：`ValueError('compiled plan steps must be a non-empty list')`。
- `_apply_compiled_plan_route`，第 839 行：`ValueError('compiled plan step must be an object')`。
- `_build_resume_segment_spec`，第 3110 行：`ValueError('resume command count exceeds the scenario command count')`。
- `_compiled_plan_from_payload`，第 158 行：`TypeError('compiled plan payload must be a mapping')`。
- `_compiled_plan_from_payload`，第 161 行：`ValueError('compiled plan payload must contain steps')`。
- `_compiled_plan_from_payload`，第 177 行：`TypeError('every compiled plan step must be a mapping')`。
- `_distance_contract_remaining_m`，第 2964 行：`ValueError('total_distance_m must be finite and non-negative')`。
- `_distance_contract_remaining_m`，第 2966 行：`ValueError('route_progress_m must be finite and non-negative')`。
- `_import_carla_api`，第 3305 行：`ModuleNotFoundError(f'No CARLA Python API for {py_tag}; searched {searched}. Use Python 3.10/3.11/3.12 with the bundled CARLA 0.9.16 wheel.')`。
- `_lane_change_route_parameters`，第 927 行：`ValueError(f'unsupported lane-change profile fields: {sorted(unknown)}')`。
- `_lane_change_route_parameters`，第 944 行：`ValueError('lane-change profile values must be finite and positive')`。
- `_lane_change_route_parameters`，第 949 行：`ValueError('lane-change target-lane offset must be between 0.0 and 0.30 m')`。
- `_lane_change_route_parameters`，第 951 行：`ValueError('lane-change route must retain a post-transition stabilization segment')`。
- `_load_command`，第 2431 行：`TypeError('voice command JSON root must be an object')`。
- `_load_command`，第 2441 行：`FileNotFoundError(f'audio file not found: {audio_path}. Pass an existing 16 kHz mono WAV path via --audio.')`。
- `_load_command`，第 2450 行：`TypeError('voice pipeline result must be an object')`。
- `_qwen_desired_speed_mps`，第 2494 行：`ValueError(f'unsupported Qwen desired-speed unit: {unit!r}')`。
- `_qwen_voice_command`，第 2463 行：`ValueError('--qwen-remote requires --qwen-voice-command or a scenario file')`。
- `_qwen_voice_command`，第 2465 行：`ValueError('remote Qwen scenario mode currently requires exactly one command at time_s=0')`。
- `_qwen_voice_command`，第 2470 行：`ValueError('scenario command must provide source_text for remote Qwen')`。
- `_release_scenario_actor_if_due`，第 672 行：`RuntimeError(f'scenario actor {actor_id!r} is not owned by this session')`。
- `_route_stop_trigger_m`，第 3015 行：`ValueError('speed/finish radius must be non-negative and deceleration positive')`。
- `_save_qwen_rgb_image`，第 2507 行：`RuntimeError('remote Qwen live mode requires Pillow')`。
- `_save_qwen_rgb_image`，第 2512 行：`ValueError('request_id has no filesystem-safe characters')`。
- `_scenario_actor`，第 1373 行：`ValueError(f'scenario {spec.scenario_id!r} declares multiple {actor_type!r} actors')`。
- `_scenario_clean_world_on_start`，第 3095 行：`TypeError('extensions.clean_world_on_start must be bool')`。
- `_scenario_lane_change_profile`，第 729 行：`TypeError('extensions.lane_change_profile must be an object')`。
- `_scenario_target_lane_occupied_count`，第 1829 行：`RuntimeError('cannot measure target-lane occupancy without ego waypoint')`。
- `_scenario_target_lane_occupied_count`，第 1840 行：`RuntimeError('scenario target lane is unavailable for occupancy acceptance')`。
- `_scenario_traffic_light_distance`，第 2149 行：`ValueError('scenario traffic-light distance_to_stop_line_m must be positive')`。
- `_scenario_traffic_light_observation`，第 2215 行：`RuntimeError(f'selected CARLA traffic light has unsupported state {state!r}')`。
- `_scenario_traffic_light_signed_clearance_m`，第 2264 行：`RuntimeError('selected CARLA traffic light has no stop waypoint')`。
- `_scenario_vehicle_speed_mps`，第 1494 行：`TypeError('scenario vehicle behavior must be an object')`。
- `_select_scene_facts`，第 2369 行：`ValueError(f'unsupported scenario facts mode: {mode!r}')`。
- `_spawn_scenario_static_prop`，第 2061 行：`TypeError('scenario static prop spawn must be an object')`。
- `_spawn_scenario_static_prop`，第 2064 行：`ValueError('scenario static prop requires blueprint_id')`。
- `_spawn_scenario_static_prop`，第 2068 行：`LookupError(f'scenario static prop blueprint not found: {blueprint_id!r}')`。
- `_spawn_scenario_static_prop`，第 2070 行：`LookupError(f'scenario static prop blueprint not found: {blueprint_id!r}')`。
- `_spawn_scenario_static_prop`，第 2109 行：`RuntimeError(f'cannot spawn configured scenario static prop after deterministic resampling: {detail}')`。
- `_spawn_scenario_vehicle`，第 1547 行：`TypeError('scenario vehicle spawn must be an object')`。
- `_spawn_scenario_vehicle`，第 1556 行：`LookupError(f'scenario vehicle blueprint not found: {blueprint_id!r}')`。
- `_spawn_scenario_vehicle`，第 1615 行：`RuntimeError(f'cannot spawn configured scenario lead vehicle after deterministic resampling: {detail}')`。
- `_spawn_scenario_walker`，第 1894 行：`TypeError('scenario walker requires spawn and behavior objects')`。
- `_spawn_scenario_walker`，第 1903 行：`LookupError(f'scenario walker blueprint not found: {blueprint_id!r}')`。
- `_spawn_scenario_walker`，第 1967 行：`RuntimeError(f"cannot spawn configured scenario walker {actor_spec.get('actor_id', 'walker')!r} after deterministic resampling: {detail}")`。
- `_spawn_scenario_walker`，第 1985 行：`TypeError('scenario walker target_xy_m must be [x, y]')`。
- `_spawn_static_lead`，第 1361 行：`RuntimeError('cannot place lead vehicle: all forward candidate positions are occupied')`。
- `_topology_planning_distance_m`，第 3033 行：`ValueError('remaining contract and finish radius must be non-negative')`。
- `_traffic_light_scenario_anchor`，第 2201 行：`RuntimeError('current map has no usable traffic-light stop waypoint')`。
- `_update_scenario_vehicle`，第 1664 行：`RuntimeError('configured scenario lead vehicle is not alive')`。
- `_update_scenario_walker`，第 2012 行：`TypeError('scenario walker behavior must be an object')`。
- `_update_scenario_walker`，第 2030 行：`RuntimeError('configured scenario walker is not alive')`。
- `_warm_up_sensor_bridge`，第 2655 行：`last_error`。
- `_warm_up_sensor_bridge`，第 2656 行：`RuntimeError(f'sensor warm-up did not produce {required_streak} consecutive aligned frames')`。
- `_world_vehicle_detections`，第 1159 行：`TypeError('vehicles must be an actor sequence')`。
- `run`，第 3352 行：`ValueError('--resume-route-progress-m requires --scenario-file')`。
- `run`，第 3374 行：`ValueError('--validate-scenario-only requires --scenario-file')`。
- `run`，第 3396 行：`ValueError('acceptance-suite v2 requires --qwen-service-url so every voice event is audited by Qwen')`。
- `run`，第 3409 行：`ValueError('--live-mic cannot be combined with --audio, --command-json, or --scenario-file')`。
- `run`，第 3417 行：`ValueError('--rgb-detector-model requires --perception-mode sensors')`。
- `run`，第 3564 行：`ValueError(f'CARLA has no WeatherParameters preset named {spec.weather!r}')`。
- `run`，第 3568 行：`ValueError(f'CARLA weather has no parameter {name!r}')`。
- `run`，第 3580 行：`RuntimeError('no Tesla Model 3 vehicle blueprint is available')`。
- `run`，第 3590 行：`RuntimeError('map has no vehicle spawn points')`。
- `run`，第 3710 行：`TypeError('extensions.route_anchor_spawn_index must be an integer')`。
- `run`，第 3714 行：`ValueError('extensions.route_anchor_spawn_index is outside the map spawn list')`。
- `run`，第 3906 行：`ValueError(f'CARLA has no TrafficLightState {configured_state!r}')`。
- `run`，第 5184 行：`RuntimeError('ready Qwen result has no runtime command')`。
- `run`，第 5312 行：`RuntimeError('sensor-bound scenario commands require canonical routing')`。
- `run`，第 5327 行：`RuntimeError('sensor-ready timestamp was not captured')`。
- `run`，第 6518 行：`TypeError('extensions.proposed_acceptance must be an object')`。
- `run`，第 6676 行：`TypeError('extensions.proposed_acceptance must be an object')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。

## 命令行参数

- 第 6787 行：`parser.add_argument('--host', default='127.0.0.1')`。
- 第 6788 行：`parser.add_argument('--port', type=int, default=2000)`。
- 第 6789 行：`parser.add_argument('--timeout-s', type=float, default=30.0)`。
- 第 6790 行：`parser.add_argument('--fixed-delta-s', type=float, default=0.05)`。
- 第 6791 行：`parser.add_argument('--frames', type=int, default=200)`。
- 第 6792 行：`parser.add_argument('--max-frames', type=int, help='debug cap applied after a scenario file computes its normal frame count')`。
- 第 6794 行：`parser.add_argument('--realtime', action='store_true', help='pace control frames in wall-clock time for visual observation')`。
- 第 6796 行：`parser.add_argument('--print-every', type=int, default=10, help='emit one telemetry line every N control frames')`。
- 第 6798 行：`parser.add_argument('--log-dir', default='artifacts/logs', help='directory for automatic per-run JSONL evidence logs')`。
- 第 6800 行：`parser.add_argument('--no-log', action='store_true', help='disable automatic JSONL evidence logging')`。
- 第 6801 行：`parser.add_argument('--spawn-index', type=int, default=0)`。
- 第 6802 行：`parser.add_argument('--seed', type=int, help='evidence seed override; selects deterministic spawn/signal candidates')`。
- 第 6807 行：`parser.add_argument('--warmup-frames', type=int, default=40, help='synchronous ticks used to stream a tiled map before spawning ego')`。
- 第 6809 行：`parser.add_argument('--map', help='optional CARLA map name, e.g. Town05; omit to use current world')`。
- 第 6810 行：`parser.add_argument('--default-speed-mps', type=float, default=5.0)`。
- 第 6811 行：`parser.add_argument('--driving-policy', help='validated JSON policy shared by C perception and D safety; defaults to config/driving_policy.json')`。
- 第 6815 行：`parser.add_argument('--perception-mode', choices=('sensors', 'world', 'virtual'), default='sensors', help='sensors uses required RGB/LiDAR plus optional aligned Radar; world is a debug truth bridge; virtual is deterministic test-only input')`。
- 第 6817 行：`parser.add_argument('--sensor-timeout-s', type=float, default=0.5, help='wall-clock wait for one aligned RGB/LiDAR frame')`。
- 第 6819 行：`parser.add_argument('--sensor-warmup-frames', type=int, default=10, help='maximum ticks used to obtain the first aligned RGB/LiDAR frame')`。
- 第 6821 行：`parser.add_argument('--sensor-startup-grace-frames', type=int, default=2, help='initial perception misses that brake without permanently latching watchdog')`。
- 第 6823 行：`parser.add_argument('--sensor-profile', choices=('default', 'low', 'competition_multiview'), default='default', help='default uses full validation density; low reduces RGB/LiDAR/Radar load for unstable Windows/UE4 hosts')`。
- 第 6826 行：`parser.add_argument('--rgb-detector-model', help='optional Ultralytics-style ONNX model for RGB vehicle/person detection')`。
- 第 6828 行：`parser.add_argument('--rgb-detector-confidence', type=float, default=0.35, help='minimum RGB detector confidence')`。
- 第 6830 行：`parser.add_argument('--rgb-detector-iou', type=float, default=0.45, help='class-aware NMS IoU threshold')`。
- 第 6832 行：`parser.add_argument('--rgb-detector-input-size', type=int, default=640, help='fallback square input size for dynamic ONNX models')`。
- 第 6834 行：`parser.add_argument('--c-visual-confidence-threshold', type=float, default=DEFAULT_STRATEGY.perception_safety.visual_confidence_threshold, help='C-side minimum visual confidence accepted by safety fusion')`。
- 第 6837 行：`parser.add_argument('--qwen-remote', action='store_true', help='use the OpenAI-compatible remote Qwen 2B high-level planner')`。
- 第 6839 行：`parser.add_argument('--qwen-voice-command', help='Chinese command sent to Qwen; a one-command scenario can supply source_text')`。
- 第 6841 行：`parser.add_argument('--qwen-base-url', default=os.environ.get('QWEN_BASE_URL', 'http://127.0.0.1:18000/v1'), help='OpenAI-compatible /v1 endpoint; QWEN_API_KEY is read only from the environment')`。
- 第 6844 行：`parser.add_argument('--qwen-model', default=os.environ.get('QWEN_MODEL', DEFAULT_QWEN_MODEL), help='exact remote Qwen 2B model id')`。
- 第 6849 行：`parser.add_argument('--qwen-request-timeout-s', type=float, default=15.0, help='OpenAI client wall-clock timeout')`。
- 第 6851 行：`parser.add_argument('--qwen-max-inference-s', type=float, default=10.0, help='fail-closed wall-clock deadline enforced by the async bridge')`。
- 第 6853 行：`parser.add_argument('--qwen-decision-ttl-s', type=float, default=12.0, help='maximum simulation-time age of a usable Qwen result')`。
- 第 6855 行：`parser.add_argument('--qwen-command-ttl-s', type=float, default=30.0, help='maximum simulation-time duration for the accepted runtime command')`。
- 第 6857 行：`parser.add_argument('--qwen-max-tokens', type=int, default=1, help='fixed one-token budget for the A-E decision choice')`。
- 第 6859 行：`parser.add_argument('--qwen-image-max-side', type=int, default=256, help='square montage side sent to the remote Qwen model')`。
- 第 6861 行：`parser.add_argument('--qwen-jpeg-quality', type=int, default=75)`。
- 第 6862 行：`parser.add_argument('--qwen-image-dir', default='artifacts/runtime/qwen_live', help='local replay images; this directory is gitignored')`。
- 第 6864 行：`parser.add_argument('--watchdog-timeout-s', type=float, default=1.0)`。
- 第 6865 行：`parser.add_argument('--watchdog-startup-grace-s', type=float, default=0.5)`。
- 第 6866 行：`parser.add_argument('--route-distance-m', type=float, default=500.0)`。
- 第 6867 行：`parser.add_argument('--resume-route-progress-m', type=float, default=0.0, help='reconstruct a scenario segment at this deterministic route arc length')`。
- 第 6871 行：`parser.add_argument('--resume-command-count', type=int, default=0, help='verified leading scenario commands omitted from a reconstructed segment')`。
- 第 6875 行：`parser.add_argument('--resume-target-speed-kph', type=float, default=40.0, help='desired cruise speed restored for a reconstructed segment')`。
- 第 6879 行：`parser.add_argument('--route-refresh-frames', type=int, default=200)`。
- 第 6880 行：`parser.add_argument('--scenario', choices=('cruise', 'follow', 'red_stop', 'emergency'), default='cruise', help='basic CARLA acceptance scenario; all use the same A/B/C/D control loop')`。
- 第 6882 行：`parser.add_argument('--lead-distance-m', type=float, default=18.0, help='initial stationary lead distance for --scenario follow')`。
- 第 6884 行：`parser.add_argument('--emergency-distance-m', type=float, default=6.0, help='initial stationary lead distance for --scenario emergency')`。
- 第 6886 行：`parser.add_argument('--stop-line-m', type=float, default=20.0, help='virtual red stop-line distance for --scenario red_stop')`。
- 第 6888 行：`parser.add_argument('--stop-line-guard-m', type=float, default=DEFAULT_STRATEGY.supervisor.stop_line_guard_m, help='D safety fallback distance used by the acceptance runner; C plans the approach before it')`。
- 第 6891 行：`parser.add_argument('--test-command-ttl-s', type=float, help='explicit test-only command TTL override; keeps long acceptance runs from expiring early')`。
- 第 6893 行：`parser.add_argument('--command-json')`。
- 第 6894 行：`parser.add_argument('--audio')`。
- 第 6895 行：`parser.add_argument('--live-mic', action='store_true', help='continuously segment and recognize PulseAudio microphone commands')`。
- 第 6897 行：`parser.add_argument('--live-mic-source', default='@DEFAULT_SOURCE@', help='PulseAudio source name used by --live-mic')`。
- 第 6899 行：`parser.add_argument('--qwen-service-url', help='enable canonical async routing and use this Qwen service URL')`。
- 第 6901 行：`parser.add_argument('--qwen-mode', choices=('atomic_v1', 'planner_v2'), default='atomic_v1', help='atomic_v1 keeps the five-action baseline; planner_v2 expects ManeuverPlan V2')`。
- 第 6905 行：`parser.add_argument('--qwen-timeout-ms', type=float, default=300.0, help='wall-clock deadline for one complex Qwen request')`。
- 第 6907 行：`parser.add_argument('--qwen-queue-size', type=int, default=1, help='bounded pending Qwen request queue; newest request wins')`。
- 第 6909 行：`parser.add_argument('--qwen-image-root', type=Path, default=Path(__file__).resolve().parents[1], help='shared filesystem root configured on the Qwen service')`。
- 第 6914 行：`parser.add_argument('--qwen-image-prefix', default='artifacts/runtime/qwen_images', help='safe relative subdirectory for asynchronously staged RGB frames')`。
- 第 6918 行：`parser.add_argument('--follow-spectator', action='store_true', help='move the graphical spectator camera behind the ego each frame')`。
- 第 6920 行：`parser.add_argument('--scenario-file', help='run a scenarios/*.json contract; overrides map, fixed delta, frames and scenario id')`。
- 第 6922 行：`parser.add_argument('--spawn-all-scenario-actors', action='store_true', help='placement-only debug: ignore activation triggers and validate all actors at startup')`。
- 第 6927 行：`parser.add_argument('--validate-scenario-only', action='store_true', help='load and validate --scenario-file without connecting to CARLA')`。
- 第 6929 行：`parser.add_argument('--use-current-map', action='store_true', help='debug only: run a scenario contract on the current CARLA map without load_world')`。
- 第 6931 行：`parser.add_argument('--scenario-facts-mode', choices=('perception', 'scenario', 'fuse'), default='fuse', help='perception: measured facts only; scenario: configured actors override; fuse: perception first, configured actors fill missing fields')`。

## 上下游与关联验证

静态导入的项目内实现：

- [car_control_A/__init__.py](../../../car_control_A/__init__.py)
- [car_control_A/high_level_command.py](../../../car_control_A/high_level_command.py)
- [car_control_A/maneuver_fsm.py](../../../car_control_A/maneuver_fsm.py)
- [car_control_A/routing.py](../../../car_control_A/routing.py)
- [car_control_A/watchdog.py](../../../car_control_A/watchdog.py)
- [car_control_B/pure_pursuit.py](../../../car_control_B/pure_pursuit.py)
- [car_control_C/__init__.py](../../../car_control_C/__init__.py)
- [car_control_D/__init__.py](../../../car_control_D/__init__.py)
- [config/strategy.py](../../../config/strategy.py)
- [integration/carla_perception.py](../../../integration/carla_perception.py)
- [integration/contracts.py](../../../integration/contracts.py)
- [integration/driving_policy.py](../../../integration/driving_policy.py)
- [integration/execution_stage.py](../../../integration/execution_stage.py)
- [integration/live_voice.py](../../../integration/live_voice.py)
- [integration/perception_stage.py](../../../integration/perception_stage.py)
- [integration/planning_stage.py](../../../integration/planning_stage.py)
- [integration/qwen_async.py](../../../integration/qwen_async.py)
- [integration/qwen_boundary.py](../../../integration/qwen_boundary.py)
- [integration/qwen_fault_injection.py](../../../integration/qwen_fault_injection.py)
- [integration/qwen_image_stager.py](../../../integration/qwen_image_stager.py)
- [integration/qwen_remote_backend.py](../../../integration/qwen_remote_backend.py)
- [integration/qwen_scenario_monitor.py](../../../integration/qwen_scenario_monitor.py)
- [integration/qwen_vl_adapter.py](../../../integration/qwen_vl_adapter.py)
- [integration/rgb_detector.py](../../../integration/rgb_detector.py)
- [integration/route_geometry.py](../../../integration/route_geometry.py)
- [integration/route_manager.py](../../../integration/route_manager.py)
- [integration/route_planner.py](../../../integration/route_planner.py)
- [integration/runtime_diagnostics.py](../../../integration/runtime_diagnostics.py)
- [integration/runtime_loop.py](../../../integration/runtime_loop.py)
- [integration/scenario_builder.py](../../../integration/scenario_builder.py)
- [integration/scenario_evidence.py](../../../integration/scenario_evidence.py)
- [integration/scenario_execution.py](../../../integration/scenario_execution.py)
- [integration/scenario_extensions.py](../../../integration/scenario_extensions.py)
- [integration/scoring_stage.py](../../../integration/scoring_stage.py)
- [integration/second_group_runtime.py](../../../integration/second_group_runtime.py)
- [qwen_service/client.py](../../../qwen_service/client.py)
- [runtime/__init__.py](../../../runtime/__init__.py)
- [runtime/interface_registry.py](../../../runtime/interface_registry.py)
- [voice_group/pipeline.py](../../../voice_group/pipeline.py)

静态 import 消费者（含测试）：

- [integration/tests/test_carla_runner_defaults.py](../../../integration/tests/test_carla_runner_defaults.py)
- [integration/tests/test_carla_runner_helpers.py](../../../integration/tests/test_carla_runner_helpers.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-entry.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

<a id="fn-integration-carla-runner-py"></a>

### `integration/carla_runner.py`

来源 SHA256：`6d91a753ba9b0938fb6e243406a26a00bdd5f6cb70063dc28e6d90e44afc72c4`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `_DeferredCommand.envelope` | `dict[str, object]` | `无声明默认；构造/赋值方提供` |
| `_DeferredCommand.received_ns` | `int` | `无声明默认；构造/赋值方提供` |
| `_DeferredCommand.origin` | `str` | `无声明默认；构造/赋值方提供` |
| `_DeferredCommand.audio_duration_s` | `float &#124; None` | `None` |

CLI 参数声明：未写 default 时遵循 argparse/action 语义；choices/required/action 与 default 一起读取。字符串帮助不是额外约束。

| 源码行 | 参数 | 类型、默认、选项及帮助 |
|---|---|---|
| 6787 | `'--host'` | `default='127.0.0.1'` |
| 6788 | `'--port'` | `type=int; default=2000` |
| 6789 | `'--timeout-s'` | `type=float; default=30.0` |
| 6790 | `'--fixed-delta-s'` | `type=float; default=0.05` |
| 6791 | `'--frames'` | `type=int; default=200` |
| 6792 | `'--max-frames'` | `type=int; help='debug cap applied after a scenario file computes its normal frame count'` |
| 6794 | `'--realtime'` | `action='store_true'; help='pace control frames in wall-clock time for visual observation'` |
| 6796 | `'--print-every'` | `type=int; default=10; help='emit one telemetry line every N control frames'` |
| 6798 | `'--log-dir'` | `default='artifacts/logs'; help='directory for automatic per-run JSONL evidence logs'` |
| 6800 | `'--no-log'` | `action='store_true'; help='disable automatic JSONL evidence logging'` |
| 6801 | `'--spawn-index'` | `type=int; default=0` |
| 6802 | `'--seed'` | `type=int; help='evidence seed override; selects deterministic spawn/signal candidates'` |
| 6807 | `'--warmup-frames'` | `type=int; default=40; help='synchronous ticks used to stream a tiled map before spawning ego'` |
| 6809 | `'--map'` | `help='optional CARLA map name, e.g. Town05; omit to use current world'` |
| 6810 | `'--default-speed-mps'` | `type=float; default=5.0` |
| 6811 | `'--driving-policy'` | `help='validated JSON policy shared by C perception and D safety; defaults to config/driving_policy.json'` |
| 6815 | `'--perception-mode'` | `choices=('sensors', 'world', 'virtual'); default='sensors'; help='sensors uses required RGB/LiDAR plus optional aligned Radar; world is a debug truth bridge; virtual is deterministic test-only input'` |
| 6817 | `'--sensor-timeout-s'` | `type=float; default=0.5; help='wall-clock wait for one aligned RGB/LiDAR frame'` |
| 6819 | `'--sensor-warmup-frames'` | `type=int; default=10; help='maximum ticks used to obtain the first aligned RGB/LiDAR frame'` |
| 6821 | `'--sensor-startup-grace-frames'` | `type=int; default=2; help='initial perception misses that brake without permanently latching watchdog'` |
| 6823 | `'--sensor-profile'` | `choices=('default', 'low', 'competition_multiview'); default='default'; help='default uses full validation density; low reduces RGB/LiDAR/Radar load for unstable Windows/UE4 hosts'` |
| 6826 | `'--rgb-detector-model'` | `help='optional Ultralytics-style ONNX model for RGB vehicle/person detection'` |
| 6828 | `'--rgb-detector-confidence'` | `type=float; default=0.35; help='minimum RGB detector confidence'` |
| 6830 | `'--rgb-detector-iou'` | `type=float; default=0.45; help='class-aware NMS IoU threshold'` |
| 6832 | `'--rgb-detector-input-size'` | `type=int; default=640; help='fallback square input size for dynamic ONNX models'` |
| 6834 | `'--c-visual-confidence-threshold'` | `type=float; default=DEFAULT_STRATEGY.perception_safety.visual_confidence_threshold; help='C-side minimum visual confidence accepted by safety fusion'` |
| 6837 | `'--qwen-remote'` | `action='store_true'; help='use the OpenAI-compatible remote Qwen 2B high-level planner'` |
| 6839 | `'--qwen-voice-command'` | `help='Chinese command sent to Qwen; a one-command scenario can supply source_text'` |
| 6841 | `'--qwen-base-url'` | `default=os.environ.get('QWEN_BASE_URL', 'http://127.0.0.1:18000/v1'); help='OpenAI-compatible /v1 endpoint; QWEN_API_KEY is read only from the environment'` |
| 6844 | `'--qwen-model'` | `default=os.environ.get('QWEN_MODEL', DEFAULT_QWEN_MODEL); help='exact remote Qwen 2B model id'` |
| 6849 | `'--qwen-request-timeout-s'` | `type=float; default=15.0; help='OpenAI client wall-clock timeout'` |
| 6851 | `'--qwen-max-inference-s'` | `type=float; default=10.0; help='fail-closed wall-clock deadline enforced by the async bridge'` |
| 6853 | `'--qwen-decision-ttl-s'` | `type=float; default=12.0; help='maximum simulation-time age of a usable Qwen result'` |
| 6855 | `'--qwen-command-ttl-s'` | `type=float; default=30.0; help='maximum simulation-time duration for the accepted runtime command'` |
| 6857 | `'--qwen-max-tokens'` | `type=int; default=1; help='fixed one-token budget for the A-E decision choice'` |
| 6859 | `'--qwen-image-max-side'` | `type=int; default=256; help='square montage side sent to the remote Qwen model'` |
| 6861 | `'--qwen-jpeg-quality'` | `type=int; default=75` |
| 6862 | `'--qwen-image-dir'` | `default='artifacts/runtime/qwen_live'; help='local replay images; this directory is gitignored'` |
| 6864 | `'--watchdog-timeout-s'` | `type=float; default=1.0` |
| 6865 | `'--watchdog-startup-grace-s'` | `type=float; default=0.5` |
| 6866 | `'--route-distance-m'` | `type=float; default=500.0` |
| 6867 | `'--resume-route-progress-m'` | `type=float; default=0.0; help='reconstruct a scenario segment at this deterministic route arc length'` |
| 6871 | `'--resume-command-count'` | `type=int; default=0; help='verified leading scenario commands omitted from a reconstructed segment'` |
| 6875 | `'--resume-target-speed-kph'` | `type=float; default=40.0; help='desired cruise speed restored for a reconstructed segment'` |
| 6879 | `'--route-refresh-frames'` | `type=int; default=200` |
| 6880 | `'--scenario'` | `choices=('cruise', 'follow', 'red_stop', 'emergency'); default='cruise'; help='basic CARLA acceptance scenario; all use the same A/B/C/D control loop'` |
| 6882 | `'--lead-distance-m'` | `type=float; default=18.0; help='initial stationary lead distance for --scenario follow'` |
| 6884 | `'--emergency-distance-m'` | `type=float; default=6.0; help='initial stationary lead distance for --scenario emergency'` |
| 6886 | `'--stop-line-m'` | `type=float; default=20.0; help='virtual red stop-line distance for --scenario red_stop'` |
| 6888 | `'--stop-line-guard-m'` | `type=float; default=DEFAULT_STRATEGY.supervisor.stop_line_guard_m; help='D safety fallback distance used by the acceptance runner; C plans the approach before it'` |
| 6891 | `'--test-command-ttl-s'` | `type=float; help='explicit test-only command TTL override; keeps long acceptance runs from expiring early'` |
| 6893 | `'--command-json'` | `` |
| 6894 | `'--audio'` | `` |
| 6895 | `'--live-mic'` | `action='store_true'; help='continuously segment and recognize PulseAudio microphone commands'` |
| 6897 | `'--live-mic-source'` | `default='@DEFAULT_SOURCE@'; help='PulseAudio source name used by --live-mic'` |
| 6899 | `'--qwen-service-url'` | `help='enable canonical async routing and use this Qwen service URL'` |
| 6901 | `'--qwen-mode'` | `choices=('atomic_v1', 'planner_v2'); default='atomic_v1'; help='atomic_v1 keeps the five-action baseline; planner_v2 expects ManeuverPlan V2'` |
| 6905 | `'--qwen-timeout-ms'` | `type=float; default=300.0; help='wall-clock deadline for one complex Qwen request'` |
| 6907 | `'--qwen-queue-size'` | `type=int; default=1; help='bounded pending Qwen request queue; newest request wins'` |
| 6909 | `'--qwen-image-root'` | `type=Path; default=Path(__file__).resolve().parents[1]; help='shared filesystem root configured on the Qwen service'` |
| 6914 | `'--qwen-image-prefix'` | `default='artifacts/runtime/qwen_images'; help='safe relative subdirectory for asynchronously staged RGB frames'` |
| 6918 | `'--follow-spectator'` | `action='store_true'; help='move the graphical spectator camera behind the ego each frame'` |
| 6920 | `'--scenario-file'` | `help='run a scenarios/*.json contract; overrides map, fixed delta, frames and scenario id'` |
| 6922 | `'--spawn-all-scenario-actors'` | `action='store_true'; help='placement-only debug: ignore activation triggers and validate all actors at startup'` |
| 6927 | `'--validate-scenario-only'` | `action='store_true'; help='load and validate --scenario-file without connecting to CARLA'` |
| 6929 | `'--use-current-map'` | `action='store_true'; help='debug only: run a scenario contract on the current CARLA map without load_world'` |
| 6931 | `'--scenario-facts-mode'` | `choices=('perception', 'scenario', 'fuse'); default='fuse'; help='perception: measured facts only; scenario: configured actors override; fuse: perception first, configured actors fill missing fields'` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `_compiled_plan_from_payload` / 158 | `not isinstance(payload, Mapping)` | `raise TypeError('compiled plan payload must be a mapping')` |
| `_compiled_plan_from_payload` / 161 | `not isinstance(raw_steps, list) or not raw_steps` | `raise ValueError('compiled plan payload must contain steps')` |
| `_compiled_plan_from_payload` / 177 | `len(steps) != len(raw_steps)` | `raise TypeError('every compiled plan step must be a mapping')` |
| `_actor_activation_due` / 628 | `not isinstance(trigger, Mapping)` | `raise TypeError('scenario actor activation_trigger must be an object')` |
| `_actor_deactivation_due` / 647 | `not isinstance(trigger, Mapping)` | `raise TypeError('scenario actor deactivation_trigger must be an object')` |
| `_release_scenario_actor_if_due` / 672 | `not session.actors.release(actor)` | `raise RuntimeError(f'scenario actor {actor_id!r} is not owned by this session')` |
| `_scenario_lane_change_profile` / 729 | `not isinstance(profile, Mapping)` | `raise TypeError('extensions.lane_change_profile must be an object')` |
| `_apply_compiled_plan_route` / 834 | `not isinstance(steps, list) or not steps` | `raise ValueError('compiled plan steps must be a non-empty list')` |
| `_apply_compiled_plan_route` / 839 | `not isinstance(step, Mapping)` | `raise ValueError('compiled plan step must be an object')` |
| `_lane_change_route_parameters` / 927 | `unknown` | `raise ValueError(f'unsupported lane-change profile fields: {sorted(unknown)}')` |
| `_lane_change_route_parameters` / 944 | `any((not math.isfinite(value) or value <= 0.0 for value in positive_values.values()))` | `raise ValueError('lane-change profile values must be finite and positive')` |
| `_lane_change_route_parameters` / 949 | `not math.isfinite(values['target_lane_offset_m']) or not 0.0 <= values['target_lane_offset_m'] <= 0.3` | `raise ValueError('lane-change target-lane offset must be between 0.0 and 0.30 m')` |
| `_lane_change_route_parameters` / 951 | `values['transition_start_m'] + values['transition_length_m'] >= values['route_distance_m']` | `raise ValueError('lane-change route must retain a post-transition stabilization segment')` |
| `_world_vehicle_detections` / 1159 | `isinstance(vehicles, (str, bytes))` | `raise TypeError('vehicles must be an actor sequence')` |
| `_spawn_static_lead` / 1361 | `本地无直接if；检查上下文` | `raise RuntimeError('cannot place lead vehicle: all forward candidate positions are occupied')` |
| `_scenario_actor` / 1373 | `len(matches) > 1` | `raise ValueError(f'scenario {spec.scenario_id!r} declares multiple {actor_type!r} actors')` |
| `_scenario_vehicle_speed_mps` / 1494 | `not isinstance(behavior, Mapping)` | `raise TypeError('scenario vehicle behavior must be an object')` |
| `_spawn_scenario_vehicle` / 1547 | `not isinstance(spawn, Mapping)` | `raise TypeError('scenario vehicle spawn must be an object')` |
| `_spawn_scenario_vehicle` / 1556 | `blueprint is None` | `raise LookupError(f'scenario vehicle blueprint not found: {blueprint_id!r}')` |
| `_spawn_scenario_vehicle` / 1615 | `lead is None` | `raise RuntimeError(f'cannot spawn configured scenario lead vehicle after deterministic resampling: {detail}')` |
| `_update_scenario_vehicle` / 1664 | `lead is None or not getattr(lead, 'is_alive', True)` | `raise RuntimeError('configured scenario lead vehicle is not alive')` |
| `_scenario_target_lane_occupied_count` / 1829 | `ego_waypoint is None` | `raise RuntimeError('cannot measure target-lane occupancy without ego waypoint')` |
| `_scenario_target_lane_occupied_count` / 1840 | `target is None AND normalized.endswith('LEFT') or normalized.endswith('RIGHT')` | `raise RuntimeError('scenario target lane is unavailable for occupancy acceptance')` |
| `_spawn_scenario_walker` / 1894 | `not isinstance(spawn, Mapping) or not isinstance(behavior, Mapping)` | `raise TypeError('scenario walker requires spawn and behavior objects')` |
| `_spawn_scenario_walker` / 1903 | `blueprint is None` | `raise LookupError(f'scenario walker blueprint not found: {blueprint_id!r}')` |
| `_spawn_scenario_walker` / 1967 | `walker is None` | `raise RuntimeError(f"cannot spawn configured scenario walker {actor_spec.get('actor_id', 'walker')!r} after deterministic resampling: {detail}")` |
| `_spawn_scenario_walker` / 1985 | `NOT (route is not None) AND not isinstance(target_xy, (list, tuple)) or len(target_xy) != 2` | `raise TypeError('scenario walker target_xy_m must be [x, y]')` |
| `_update_scenario_walker` / 2012 | `not isinstance(behavior, Mapping)` | `raise TypeError('scenario walker behavior must be an object')` |
| `_update_scenario_walker` / 2030 | `walker is None or not getattr(walker, 'is_alive', True)` | `raise RuntimeError('configured scenario walker is not alive')` |
| `_spawn_scenario_static_prop` / 2061 | `not isinstance(spawn, Mapping)` | `raise TypeError('scenario static prop spawn must be an object')` |
| `_spawn_scenario_static_prop` / 2064 | `not isinstance(blueprint_id, str) or not blueprint_id` | `raise ValueError('scenario static prop requires blueprint_id')` |
| `_spawn_scenario_static_prop` / 2068 | `except (IndexError, KeyError)` | `raise LookupError(f'scenario static prop blueprint not found: {blueprint_id!r}') from error` |
| `_spawn_scenario_static_prop` / 2070 | `blueprint is None` | `raise LookupError(f'scenario static prop blueprint not found: {blueprint_id!r}')` |
| `_spawn_scenario_static_prop` / 2109 | `prop is None` | `raise RuntimeError(f'cannot spawn configured scenario static prop after deterministic resampling: {detail}')` |
| `_scenario_traffic_light_distance` / 2149 | `not math.isfinite(distance) or distance <= 0.0` | `raise ValueError('scenario traffic-light distance_to_stop_line_m must be positive')` |
| `_traffic_light_scenario_anchor` / 2201 | `not candidates` | `raise RuntimeError('current map has no usable traffic-light stop waypoint')` |
| `_scenario_traffic_light_observation` / 2215 | `state not in {'RED', 'YELLOW', 'GREEN'}` | `raise RuntimeError(f'selected CARLA traffic light has unsupported state {state!r}')` |
| `_scenario_traffic_light_signed_clearance_m` / 2264 | `not candidates` | `raise RuntimeError('selected CARLA traffic light has no stop waypoint')` |
| `_select_scene_facts` / 2369 | `mode not in {'perception', 'scenario', 'fuse'}` | `raise ValueError(f'unsupported scenario facts mode: {mode!r}')` |
| `_load_command` / 2431 | `args.command_json AND not isinstance(command, Mapping)` | `raise TypeError('voice command JSON root must be an object')` |
| `_load_command` / 2441 | `args.audio AND not audio_path.is_file()` | `raise FileNotFoundError(f'audio file not found: {audio_path}. Pass an existing 16 kHz mono WAV path via --audio.')` |
| `_load_command` / 2450 | `args.audio AND not isinstance(command, Mapping)` | `raise TypeError('voice pipeline result must be an object')` |
| `_qwen_voice_command` / 2463 | `spec is None` | `raise ValueError('--qwen-remote requires --qwen-voice-command or a scenario file')` |
| `_qwen_voice_command` / 2465 | `len(spec.commands) != 1 or spec.commands[0].time_s > 1e-09` | `raise ValueError('remote Qwen scenario mode currently requires exactly one command at time_s=0')` |
| `_qwen_voice_command` / 2470 | `not source_text` | `raise ValueError('scenario command must provide source_text for remote Qwen')` |
| `_qwen_desired_speed_mps` / 2494 | `本地无直接if；检查上下文` | `raise ValueError(f'unsupported Qwen desired-speed unit: {unit!r}')` |
| `_save_qwen_rgb_image` / 2507 | `except ImportError` | `raise RuntimeError('remote Qwen live mode requires Pillow') from error` |
| `_save_qwen_rgb_image` / 2512 | `not safe_id` | `raise ValueError('request_id has no filesystem-safe characters')` |
| `_warm_up_sensor_bridge` / 2655 | `last_error is not None` | `raise last_error` |
| `_warm_up_sensor_bridge` / 2656 | `本地无直接if；检查上下文` | `raise RuntimeError(f'sensor warm-up did not produce {required_streak} consecutive aligned frames')` |
| `_distance_contract_remaining_m` / 2964 | `not math.isfinite(total) or total < 0.0` | `raise ValueError('total_distance_m must be finite and non-negative')` |
| `_distance_contract_remaining_m` / 2966 | `not math.isfinite(progress) or progress < 0.0` | `raise ValueError('route_progress_m must be finite and non-negative')` |
| `_route_stop_trigger_m` / 3015 | `speed_mps < 0.0 or finish_radius_m < 0.0 or decel_mps2 <= 0.0` | `raise ValueError('speed/finish radius must be non-negative and deceleration positive')` |
| `_topology_planning_distance_m` / 3033 | `remaining_contract_m < 0.0 or finish_radius_m < 0.0` | `raise ValueError('remaining contract and finish radius must be non-negative')` |
| `_scenario_clean_world_on_start` / 3095 | `type(value) is not bool` | `raise TypeError('extensions.clean_world_on_start must be bool')` |
| `_build_resume_segment_spec` / 3110 | `not 0 <= completed_command_count <= len(spec.commands)` | `raise ValueError('resume command count exceeds the scenario command count')` |
| `_import_carla_api` / 3284 | `except ModuleNotFoundError AND error.name != 'carla'` | `raise` |
| `_import_carla_api` / 3305 | `本地无直接if；检查上下文` | `raise ModuleNotFoundError(f'No CARLA Python API for {py_tag}; searched {searched}. Use Python 3.10/3.11/3.12 with the bundled CARLA 0.9.16 wheel.')` |
| `run` / 3352 | `resume_progress_m > 0.0 AND spec is None` | `raise ValueError('--resume-route-progress-m requires --scenario-file')` |
| `run` / 3374 | `args.validate_scenario_only AND spec is None` | `raise ValueError('--validate-scenario-only requires --scenario-file')` |
| `run` / 3396 | `extension_runtime is not None and isinstance(spec.extensions.get('qwen_policy'), Mapping) and (spec.extensions['qwen_policy'].get('required_for_every_voice_event') is True) and (not args.qwen_service_url)` | `raise ValueError('acceptance-suite v2 requires --qwen-service-url so every voice event is audited by Qwen')` |
| `run` / 3409 | `args.live_mic and (args.audio or args.command_json or args.scenario_file)` | `raise ValueError('--live-mic cannot be combined with --audio, --command-json, or --scenario-file')` |
| `run` / 3417 | `detector_model AND args.perception_mode != 'sensors'` | `raise ValueError('--rgb-detector-model requires --perception-mode sensors')` |
| `run` / 3564 | `spec is not None AND weather is None` | `raise ValueError(f'CARLA has no WeatherParameters preset named {spec.weather!r}')` |
| `run` / 3568 | `spec is not None AND extension_runtime is not None AND not hasattr(weather, name)` | `raise ValueError(f'CARLA weather has no parameter {name!r}')` |
| `run` / 3580 | `not blueprints` | `raise RuntimeError('no Tesla Model 3 vehicle blueprint is available')` |
| `run` / 3590 | `not spawn_points` | `raise RuntimeError('map has no vehicle spawn points')` |
| `run` / 3710 | `configured_anchor_index is not None AND isinstance(configured_anchor_index, bool) or not isinstance(configured_anchor_index, int)` | `raise TypeError('extensions.route_anchor_spawn_index must be an integer')` |
| `run` / 3714 | `configured_anchor_index is not None AND not 0 <= configured_anchor_index < len(spawn_points)` | `raise ValueError('extensions.route_anchor_spawn_index is outside the map spawn list')` |
| `run` / 3836 | `destination_planning AND except RoutePlanningError` | `raise` |
| `run` / 3871 | `NOT (destination_planning) AND topology_coverage_planning AND except RoutePlanningError` | `raise` |
| `run` / 3906 | `traffic_light_distance is not None AND desired_state is None` | `raise ValueError(f'CARLA has no TrafficLightState {configured_state!r}')` |
| `run` / 5184 | `qwen_bridge is not None AND qwen_result is not None AND qwen_result.ready and (not qwen_terminal_recorded) AND qwen_result.runtime_command is None` | `raise RuntimeError('ready Qwen result has no runtime command')` |
| `run` / 5312 | `timeline is not None and extension_frame is not None and (evidence_actor_ids is not None) AND canonical_bridge is None` | `raise RuntimeError('sensor-bound scenario commands require canonical routing')` |
| `run` / 5327 | `sensor_ready_ns is None` | `raise RuntimeError('sensor-ready timestamp was not captured')` |
| `run` / 6347 | `maneuver_fsm.plan is not None and maneuver_fsm.state not in TERMINAL_STATES AND started_route_step is not None AND NOT (started_route_step.behavior.startswith('CHANGE_LANE_') and prevalidated_avoid_route is not None and (not dynamic_out_and_back) and (route.points_xy_m == prevalidated_avoid_route.points_xy_m or _route_starts_near_ego(prevalidated_avoid_route, ego))) AND NOT (started_route_step.behavior.startswith('TURN_')) AND started_route_step.behavior.startswith('CHANGE_LANE_') AND except ValueError AND not (return_to_retained_route and maneuver_mission_route is not None and ('no safe post-junction lane-change corridor' in str(error)))` | `raise` |
| `run` / 6518 | `early_route_candidate and extension_runtime is not None and (spec is not None) AND not isinstance(proposed, Mapping)` | `raise TypeError('extensions.proposed_acceptance must be an object')` |
| `run` / 6676 | `extension_runtime is not None AND not isinstance(proposed, Mapping)` | `raise TypeError('extensions.proposed_acceptance must be an object')` |
| `run` / 6758 | `except BaseException` | `raise` |

### 环境参数读取位置

这里只记录源码表达式，不读取当前进程环境；缓存与覆盖关系需查调用时机。

| 来源/行 | 环境变量表达式 | 源码fallback |
|---|---|---|
| `integration/carla_runner.py:2594` | `'CARLA_DRIVING_CODE_VERSION'` | `None（未传默认）` |
| `integration/carla_runner.py:6842` | `'QWEN_BASE_URL'` | `'http://127.0.0.1:18000/v1'` |
| `integration/carla_runner.py:6845` | `'QWEN_MODEL'` | `DEFAULT_QWEN_MODEL` |
| `integration/carla_runner.py:3522` | `'QWEN_API_KEY'` | `凭据参数，不抄录值` |
