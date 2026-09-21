# Scenario construction, acceptance and evidence

## 开发维护先读：实际语义

以下功能页说明实现理由、分支、接口含义、改动联动与验证。先读这些内容，再按逐文件索引定位方法；不要用函数名推断业务语义。

- [场景触发、车辆行为与验收分离](../functions/scenario-evidence-contract.md)

[Vehicle module](../modules/vehicle.md)

## Responsibility, contracts and failure behavior

scenario_builder creates participants; scenario_execution/extensions manage events; scenario_acceptance evaluates expected conditions; ScenarioEvidenceRecorder writes JSONL and summary; scoring_stage assembles rule scores. official_scenario_runner verifies the pinned external checkout and owns the simulation clock during its run. Do not run another synchronous tick owner concurrently. scenario_runner_agent bridges execution. generalization_gate separates generalization evidence; scenario facts can trigger events and scoring but must not silently become sensor control input.


## 模块接口与参数核对（2026-09-20）

scenario_builder构建世界，execution/extensions处理事件，evidence采集事实，acceptance计算要求是否满足。expected与oracle是验收输入，不能反向充当传感器测量。official runner执行时拥有仿真时钟，其他入口不能同时tick。

### 参数语义与生效边界

PerturbationCase列出生成所需全部参数，无声明默认项需要调用方提供。fixed_delta_s是仿真秒步长；actor_speed_scale和actor_count_scale是比例而非m/s/个数。brake_time_offset_s与pedestrian_start_offset_s是相对时间偏移。

### 上下游与修改影响

基础验收输出checks/failed_keys；Qwen、extension与completion还会影响最终结果。修改expected必须查actual生产者，修改base要追全体GEN/selection，修改终态需查collector资格。

## 第8模块逐入口精读结论（2026-09-21）

### 四层职责不能混用

1. `ScenarioSpec/scenario_builder/generalization_gate` 只负责加载合同、将局部路线变到世界坐标、合法放置 actor 和生成确定性扰动；它们不控制 CARLA，也不证明 actor 已成功生成。
2. 仓库主运行链由 `carla_runner` 拥有 world tick、actor 生命周期和控制；`ScenarioExtensionRuntime` 只保存扩展触发/故障/phase/Qwen/安全响应状态，必须由 runner 每帧喂真实观测。
3. `ScenarioEvidenceRecorder → evaluate_expected/build_acceptance_context` 把已完成运行事实写成 JSONL/summary 并判合同；expected/oracle/context 都是评价输入，禁止反向成为传感或控制真值。
4. `official_scenario_runner` 只是固定外部 checkout `94ff3b8...` 的子进程边界；`ScenarioRunnerAgent` 是其独立、简化 agent，不等于主 runner，也不使用仓库场景 ID 来调参。

### 场景身份、调度与泛化

`ScenarioSpec.load` 要求 schema 1.0、basic/advanced/challenge、整数 seed、正仿真步长/时长、至少两个 local XY 点，并把命令按 time 排序。命令 ID 在排序前按 JSON 原 index 生成，所以场景文件仍应保持时间顺序；`CommandTimeline` 遇到首个未满足 trigger 会阻塞后续命令，以保证 phase 顺序而不是越过前置事件。

泛化矩阵不是所有维度的笛卡尔积。`GeneralizationMatrix.cases` 用固定互质步长做 bounded Latin-cycle，生成 `samples_per_scenario` 个可复现 case。扰动会改地图、天气、seed、fixed delta、actor位置/速度/时间/数量和有限传感参数，但保持 commands/oracles 语义；被 commands/expected/qwen_expected/extensions 的 actor_id 引用的车辆不会因密度缩放删除。派生 JSON 可加载只是第一道门禁，仍需真实地图 actor spawn、路线与传感测试。

### actor 与事件坐标

actor spawn 优先使用任务路线弧长和 CARLA lane topology；相邻车道必须存在、为 DRIVING 且同向。旧 `spawn.y≈车道宽` 会转换成真实左右车道并只保留剩余横向偏移。重规划时只把 actor/target 的任务绝对 s 映射到局部 route s，激活/停用 trigger 继续使用任务绝对里程。候选还检查有限值、车道中心误差、航向、道路高度和与已占用位置的最小间距；这些检查仍不能替代 `world.try_spawn_actor` 的最终结果。

`ScenarioExtensionRuntime` 是单场景有状态对象：每帧更新 actor最小距离、故障窗口、车道/速度/灯态/路线和 RSS，actor event 每次最多推进一项。紧急响应证据区分 danger、perception、decision、safety override、control effect 和 recovery；缺任一阶段保留 None，P95 仅基于完整 perception→control 样本。Qwen plan 的行为/目标提取是宽松递归证据，不等同 schema 验证。

### 验收、终态和评分证据等级

`evaluate_expected` 对未知 expected key 失败关闭；数值缺测/非有限也失败。`ScenarioEvidenceRecorder.complete` 没有 expected 时，有命令场景的默认 completion 是“任一最新终态为 SUCCEEDED”，不是“所有命令成功”；正式多命令场景必须同时提供 expected/extension/Qwen 合同。基础 metrics 中 context 在最后覆盖同名聚合值，因此 context 必须来自只读、可追溯的 scoring stage。

JSONL 以 exclusive create 防止覆盖旧 run，每条 flush；summary 则覆盖写且不是原子文件，也没有自行签发运行 manifest/hash。仓库 `OfficialScorer` 仍是内部基线规则，不能因被 evidence 调用就称为赛事官方评分。

### 外部 ScenarioRunner agent 的当前能力边界 M08-01（已复现、未修复）

`ScenarioRunnerAgent.sensors` 声明 front RGB、LiDAR、GNSS，但 `OfficialSensorFrame` 只保存 GNSS/LiDAR，`_qwen_high_level_command` 固定 `rgb_ref=None`、`visual_valid=False`、`detected_objects=[]`。在线模式还在每个 `run_step` 同步调用一次 Qwen，没有事件触发、异步复用或命令生命周期缓存。使用两帧含 RGB 的合法 mock sensor 输入，实际得到 Qwen calls=2、两个 rgb_ref 均 None、visual_valid 均 false。该结论只针对外部 ScenarioRunner adapter；仓库主 `carla_runner` 的 RGB/LiDAR/Radar 与事件式 Qwen 链是另一实现，不能扩大为全项目没有多模态输入。

在将该 agent 用作比赛外部/隐藏场景入口前，需要明确目标：若要求全链，应把 RGB asset/检测与同步来源送入 ModelRequest，改为事件触发异步请求并记录 request→plan→apply→terminal；若只作为未知路线安全 baseline，应在交付说明中明确它是 LiDAR+GNSS 控制和 Qwen 文本/结构 smoke，不能冒充完整 VLA。

### 修改联动清单

改场景 key 必须同步 `ScenarioSpec`、extension requirement、runner producer、evidence metric 和 acceptance；改 actor坐标需回归重规划 rebasing、任务绝对 trigger、泛化 offset 和真实 spawn；改 Qwen/phase 计数需同步 terminal/plan/resolution 三类事件；改评分 context 必须防止 oracle 泄漏并保存来源；改外部 agent 需同时验证 pinned ScenarioRunner loader、sensor contract、服务 profile 和 fail-closed 控制。

### [integration/scenario_evidence.py](../../../integration/scenario_evidence.py) 的入口与声明

```python
FrameTiming.to_dict(self) -> dict[str, float | int | None]
ScenarioEvidenceRecorder.__init__(self, path: str | Path, *, scorer: OfficialScorer | None=None, clock_ns: Any=time.monotonic_ns) -> None
ScenarioEvidenceRecorder.run_id(self) -> str | None
ScenarioEvidenceRecorder.start_run(self, *, scenario_id: str, difficulty: str='basic', config: Mapping[str, object] | None=None, expected_route_deviation: bool=False, run_id: str | None=None) -> str
ScenarioEvidenceRecorder.record_command(self, command: Mapping[str, object], *, disposition: str, adapted_command: object | None=None, received_ns: int | None=None, submitted_sim_time_s: float | None=None) -> None
ScenarioEvidenceRecorder.record_qwen_event(self, *, request_id: str, status: str, context: Mapping[str, object] | None=None, high_level_command: Mapping[str, object] | None=None, runtime_command: Mapping[str, object] | None=None, trace: object | None=None, error: str | None=None) -> None
ScenarioEvidenceRecorder.record_qwen_trajectory(self, *, command_id: str, request_id: str, sensor_ready_ns: int, model_completed_ns: int, trajectory_ready_ns: int, breakdown: Mapping[str, float] | None=None) -> None
ScenarioEvidenceRecorder.record_frame(self, *, vehicle: object, scene: object, raw_control: object, final_control: object, safety_reason: str, safety_override: bool, timing: FrameTiming, safety_reason_category: str='NONE', command_id: str | None=None, fsm_state: str | None=None, longitudinal: object | None=None, lateral: object | None=None, perception_sources: Mapping[str, str] | None=None, c_safety_state: object | None=None, lane_marking_crossing_expected: bool=False) -> None
ScenarioEvidenceRecorder.record_runtime_frame(self, result: object, scene: object, *, raw_control: object, timing: FrameTiming, command_id: str | None=None, fsm_state: str | None=None, perception_sources: Mapping[str, str] | None=None, c_safety_state: object | None=None, lane_marking_crossing_expected: bool=False) -> None
ScenarioEvidenceRecorder.record_feedback(self, feedback: object) -> None
ScenarioEvidenceRecorder.record_canonical_routing(self, *, phase: str, command_id: str, payload: object) -> None
ScenarioEvidenceRecorder.record_route_recovery_event(self, *, event_type: str, payload: Mapping[str, object]) -> None
ScenarioEvidenceRecorder.complete(self, *, completion: bool | None=None, detail: str='', expected: Mapping[str, object] | None=None, acceptance_context: Mapping[str, object] | None=None) -> dict[str, Any]
ScenarioEvidenceRecorder.fail(self, error: BaseException | str, *, detail: str='') -> dict[str, Any]
ScenarioEvidenceRecorder.close(self) -> None
```

类级字段（含配置、输入输出和内部状态；仅声明默认，不是当前run生效配置）：

| 字段 | 类型 | 默认值/来源 |
|---|---|---|
| `FrameTiming.decision_start_ns` | `int` | `无声明默认（构造/赋值方提供）` |
| `FrameTiming.decision_end_ns` | `int` | `无声明默认（构造/赋值方提供）` |
| `FrameTiming.control_applied_ns` | `int` | `无声明默认（构造/赋值方提供）` |
| `FrameTiming.sensor_ready_ns` | `int &#124; None` | `None` |
| `FrameTiming.simulator_tick_start_ns` | `int &#124; None` | `None` |
| `FrameTiming.simulator_tick_end_ns` | `int &#124; None` | `None` |
| `FrameTiming.perception_start_ns` | `int &#124; None` | `None` |

### [integration/generalization_gate.py](../../../integration/generalization_gate.py) 的入口与声明

```python
GeneralizationMatrix.cases(self, scenario_id: str) -> Iterator[PerturbationCase]
load_generalization_matrix(path: str | Path | None=None) -> GeneralizationMatrix
perturb_scenario(raw_scenario: Mapping[str, Any], case: PerturbationCase) -> dict[str, Any]
```

类级字段（含配置、输入输出和内部状态；仅声明默认，不是当前run生效配置）：

| 字段 | 类型 | 默认值/来源 |
|---|---|---|
| `PerturbationCase.case_id` | `str` | `无声明默认（构造/赋值方提供）` |
| `PerturbationCase.map_name` | `str` | `无声明默认（构造/赋值方提供）` |
| `PerturbationCase.weather` | `str` | `无声明默认（构造/赋值方提供）` |
| `PerturbationCase.seed` | `int` | `无声明默认（构造/赋值方提供）` |
| `PerturbationCase.fixed_delta_s` | `float` | `无声明默认（构造/赋值方提供）` |
| `PerturbationCase.actor_longitudinal_offset_m` | `float` | `无声明默认（构造/赋值方提供）` |
| `PerturbationCase.actor_lateral_offset_m` | `float` | `无声明默认（构造/赋值方提供）` |
| `PerturbationCase.actor_speed_scale` | `float` | `无声明默认（构造/赋值方提供）` |
| `PerturbationCase.brake_time_offset_s` | `float` | `无声明默认（构造/赋值方提供）` |
| `PerturbationCase.pedestrian_start_offset_s` | `float` | `无声明默认（构造/赋值方提供）` |
| `PerturbationCase.actor_count_scale` | `float` | `无声明默认（构造/赋值方提供）` |
| `PerturbationCase.target_lane_relation` | `str` | `无声明默认（构造/赋值方提供）` |
| `PerturbationCase.sensor_condition` | `str` | `无声明默认（构造/赋值方提供）` |
| `GeneralizationMatrix.source_path` | `Path` | `无声明默认（构造/赋值方提供）` |
| `GeneralizationMatrix.maps` | `tuple[str, ...]` | `无声明默认（构造/赋值方提供）` |
| `GeneralizationMatrix.weather_profiles` | `tuple[str, ...]` | `无声明默认（构造/赋值方提供）` |
| `GeneralizationMatrix.seeds` | `tuple[int, ...]` | `无声明默认（构造/赋值方提供）` |
| `GeneralizationMatrix.fixed_delta_seconds` | `tuple[float, ...]` | `无声明默认（构造/赋值方提供）` |
| `GeneralizationMatrix.actor_longitudinal_offsets_m` | `tuple[float, ...]` | `无声明默认（构造/赋值方提供）` |
| `GeneralizationMatrix.actor_lateral_offsets_m` | `tuple[float, ...]` | `无声明默认（构造/赋值方提供）` |
| `GeneralizationMatrix.actor_speed_scales` | `tuple[float, ...]` | `无声明默认（构造/赋值方提供）` |
| `GeneralizationMatrix.brake_time_offsets_s` | `tuple[float, ...]` | `无声明默认（构造/赋值方提供）` |
| `GeneralizationMatrix.pedestrian_start_offsets_s` | `tuple[float, ...]` | `无声明默认（构造/赋值方提供）` |
| `GeneralizationMatrix.actor_count_scales` | `tuple[float, ...]` | `无声明默认（构造/赋值方提供）` |
| `GeneralizationMatrix.target_lane_relations` | `tuple[str, ...]` | `无声明默认（构造/赋值方提供）` |
| `GeneralizationMatrix.sensor_conditions` | `tuple[str, ...]` | `无声明默认（构造/赋值方提供）` |
| `GeneralizationMatrix.samples_per_scenario` | `int` | `无声明默认（构造/赋值方提供）` |
| `GeneralizationMatrix.holdout_scenarios` | `tuple[str, ...]` | `无声明默认（构造/赋值方提供）` |

### [integration/scenario_acceptance.py](../../../integration/scenario_acceptance.py) 的入口与声明

```python
evaluate_expected(expected: Mapping[str, object], metrics: Mapping[str, object]) -> dict[str, Any]
```

以上为核心交接入口；模块内其余实现、CLI和资源的完整字段/拒绝条件见本页功能小文档索引。类型未声明的返回值不凭名称推断。当前代码基线fe1ba839，静态复核不证明实际CARLA/GPU/板端运行成功。

## Complete implementation inventory

- [integration/generalization_gate.py](../../../integration/generalization_gate.py) - `_sequence`, `PerturbationCase`, `GeneralizationMatrix`, `GeneralizationMatrix.cases`, `load_generalization_matrix`, `_referenced_actor_ids`, `_scale_auxiliary_vehicles`, `_apply_sensor_condition`, `perturb_scenario`
- [integration/official_scenario_runner.py](../../../integration/official_scenario_runner.py) - `ScenarioRunnerInvocation`, `verify_checkout`, `build_command`, `run`
- [integration/scenario_acceptance.py](../../../integration/scenario_acceptance.py) - `_number`, `evaluate_expected`
- [integration/scenario_builder.py](../../../integration/scenario_builder.py) - `ActorPlacementError`, `_wrap_degrees`, `_is_vehicle`, `_lane_width_m`, `_same_direction`, `_lane_relation`, `_target_lane_waypoint`, `_legacy_vehicle_lane`, `route_relative_carla_transform`, `offset_actor_route_position`, `rebase_actor_route_position`, `actor_resample_offsets`, `validate_actor_transform`, `route_relative_target_location`, `validate_actor_route_coverage`
- [integration/scenario_evidence.py](../../../integration/scenario_evidence.py) - `FrameTiming`, `FrameTiming.to_dict`, `_jsonable`, `_field`, `ScenarioEvidenceRecorder`, `ScenarioEvidenceRecorder.run_id`, `ScenarioEvidenceRecorder.start_run`, `ScenarioEvidenceRecorder.record_command`, `ScenarioEvidenceRecorder.record_qwen_event`, `ScenarioEvidenceRecorder.record_qwen_trajectory`, `ScenarioEvidenceRecorder.record_frame`, `ScenarioEvidenceRecorder.record_runtime_frame`, `ScenarioEvidenceRecorder.record_feedback`, `ScenarioEvidenceRecorder.record_canonical_routing`, `ScenarioEvidenceRecorder.record_route_recovery_event`, `ScenarioEvidenceRecorder.complete`, `ScenarioEvidenceRecorder.fail`, `ScenarioEvidenceRecorder.close`
- [integration/scenario_execution.py](../../../integration/scenario_execution.py) - `_finite_number`, `_nonempty_text`, `ScheduledCommand`, `ScenarioSpec`, `ScenarioSpec.load`, `ScenarioSpec.frame_count`, `ScenarioSpec.route_distance_contract_m`, `ScenarioSpec.route_planning_mode`, `ScenarioSpec.control_policy`, `ScenarioSpec.world_destination`, `ScenarioSpec.requires_qwen_semantics`, `ScenarioSpec.world_route`, `_resample_polyline`, `CommandTimeline`, `CommandTimeline.completed`, `CommandTimeline.due`, `scenario_trigger_satisfied`, `select_best_route_anchor`, `resolve_scenario_command`, `_parse_command`
- [integration/scenario_extensions.py](../../../integration/scenario_extensions.py) - `missing_runtime_requirements`, `ExtensionFrameState`, `ScenarioExtensionRuntime`, `ScenarioExtensionRuntime.qwen_faults`, `ScenarioExtensionRuntime.weather_parameters`, `ScenarioExtensionRuntime.route_loop`, `ScenarioExtensionRuntime.note_command_submitted`, `ScenarioExtensionRuntime.note_terminal`, `ScenarioExtensionRuntime.note_qwen_plan`, `ScenarioExtensionRuntime.note_qwen_resolution`, `ScenarioExtensionRuntime.note_maneuver_terminal_reason`, `ScenarioExtensionRuntime.note_phase_completed`, `ScenarioExtensionRuntime.restore_terminal_phase`, `ScenarioExtensionRuntime.note_actor_trigger`, `ScenarioExtensionRuntime.note_perception_observation`, `ScenarioExtensionRuntime.note_front_path_observation`, `ScenarioExtensionRuntime.ready_emergency_recovery`, `ScenarioExtensionRuntime.note_emergency_recovered`, `ScenarioExtensionRuntime.note_actor_activated`, `ScenarioExtensionRuntime.note_target_lane_occupancy`, `ScenarioExtensionRuntime.note_mission_route_restored`, `ScenarioExtensionRuntime.update_frame`, `ScenarioExtensionRuntime.note_control_observation`, `ScenarioExtensionRuntime.actor_state`, `ScenarioExtensionRuntime.evidence`, `ScenarioExtensionRuntime.evaluate`
- [integration/scenario_runner_agent.py](../../../integration/scenario_runner_agent.py) - `get_entry_point`, `OfficialAgentConfig`, `OfficialAgentConfig.load`, `OfficialSensorFrame`, `OfficialAgentCore`, `OfficialAgentCore.step`, `ScenarioRunnerAgent`, `ScenarioRunnerAgent.setup`, `ScenarioRunnerAgent.sensors`, `ScenarioRunnerAgent.run_step`, `_front_lidar_distance`, `_route_steer`, `_route_bearing`, `_gps_offset_m`, `_finite`
- [integration/scoring_stage.py](../../../integration/scoring_stage.py) - `build_acceptance_context`

## Dependencies and coordinated changes


## Validation entry points

`python -m pytest integration/tests/test_scenario_acceptance.py integration/tests/test_scenario_builder.py integration/tests/test_scenario_evidence.py integration/tests/test_scenario_execution.py integration/tests/test_scenario_extensions.py integration/tests/test_official_scenario_runner.py integration/tests/test_generalization_gate.py integration/tests/test_unseen_scenario_generalization.py`

2026-09-21 在工作树根目录执行上述入口：**134 passed in 2.59s**。结果覆盖场景加载/调度、actor几何、evidence/acceptance、扩展、固定外部进程命令、泛化与 unseen agent 纯 Python 边界；不包含真实 CARLA actor spawn、外部 ScenarioRunner checkout 运行、在线 Qwen、多模态质量或官方评分一致性。

## 功能小文档完整索引

以下功能页分别记录实现入口、输入输出声明、内部调用、异常、配置和静态上下游；测试文件保留在源码索引中。

- [integration/generalization_gate.py](../functions/integration--generalization_gate--py.md)
- [integration/official_scenario_runner.py](../functions/integration--official_scenario_runner--py.md)
- [integration/scenario_acceptance.py](../functions/integration--scenario_acceptance--py.md)
- [integration/scenario_builder.py](../functions/integration--scenario_builder--py.md)
- [integration/scenario_evidence.py](../functions/integration--scenario_evidence--py.md)
- [integration/scenario_execution.py](../functions/integration--scenario_execution--py.md)
- [integration/scenario_extensions.py](../functions/integration--scenario_extensions--py.md)
- [integration/scenario_runner_agent.py](../functions/integration--scenario_runner_agent--py.md)
- [integration/scoring_stage.py](../functions/integration--scoring_stage--py.md)

## 诊断与维护交接

本模块证据：scenario哈希、failed_keys、actual/required；A03实际证据缺失。功能实现与上下游见本页原索引；跨模块回查[追踪矩阵](../TRACEABILITY.md)与[诊断入口](../DIAGNOSIS.md)。实际run必须核对版本，未执行的检查不视为已通过。

专项记录：[场景来源与泛化漂移](../functions/scenario-lineage.md)、[验收合成与failed keys定位](../functions/acceptance-diagnosis.md)、[B1 D3 Wave2核查记录](../functions/wave2-audit.md)。
