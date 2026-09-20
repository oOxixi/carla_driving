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

Run from the worktree root. Listed commands are relevant checks, not claims that tests were executed. CARLA, remote-model and hardware acceptance require their actual environments and run manifests.

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
