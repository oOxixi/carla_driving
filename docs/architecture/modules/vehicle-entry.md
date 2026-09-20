# Runtime entry and lifecycle


## 第1模块精读状态与具体参数索引

2026-09-20：本模块按函数体逐项补正，11份实现页中的98处“源码未提供说明”已替换为实际行为。这个状态不表示其余19模块已完成同等级精读；上一轮全量静态复核是基线，不能替代此次工作。

### 从参数或问题进入实现

| 对象/参数 | 默认或输入约定 | 生效处、限制与具体文档 |
|---|---|---|
| `ControlRuntime.default_speed_mps` / `command_timeout_s` | 5m/s / 15s | [构造器](../functions/integration--runtime_loop--py.md#fn-controlruntime---init--)；前者>=0、后者>0，当前比较未单独拒绝NaN |
| `step.dt_s` / `speed_cap_mps` | dt必传秒；cap=None | [逐帧执行](../functions/integration--runtime_loop--py.md#fn-controlruntime-step)；额外上限与C/D同时生效 |
| `step.watchdog_alerts` / `raw_control_override` | 空tuple / None | [逐帧执行](../functions/integration--runtime_loop--py.md#fn-controlruntime-step)；覆盖输入仍经过安全仲裁 |
| SET_SPEED完成阈值 | 误差<=0.25m/s连续3帧 | [完成判定](../functions/integration--runtime_loop--py.md#fn-controlruntime--completion-feedback)，不是场景整体通过 |
| STOP完成阈值 | FuzzyCommandPolicy配置的standstill_speed_mps | [完成判定](../functions/integration--runtime_loop--py.md#fn-controlruntime--completion-feedback)，成功后保留停车保持 |
| `driving_policy`路径、visual/route/stop override | 默认config/driving_policy.json，override非None替代对应项 | [加载](../functions/integration--driving_policy--py.md#fn-load-driving-policy)、[感知参数](../functions/integration--driving_policy--py.md#fn-drivingpolicy-perception-parameters)、[D参数](../functions/integration--driving_policy--py.md#fn-drivingpolicy-safety-config) |
| `LiveVoiceConfig`全部10项 | 见下表 | [VAD配置](../functions/integration--live_voice--py.md#fn-livevoiceconfig)，capture与ASR异步，不能当主线程同步输入 |
| replay `frame/sim_time_s/vehicle` | 帧/时间严格递增，vehicle固定6键 | [载入](../functions/integration--offline_replay--py.md#fn-load-replay-manifest)、[vehicle](../functions/integration--offline_replay--py.md#fn--vehicle) |
| replay `dt_s/route_points` | 0.05s；缺路线时世界x+30m | [执行](../functions/integration--offline_replay--py.md#fn--run-frame)、[路线](../functions/integration--offline_replay--py.md#fn--route) |
| replay `rgb_path/lidar_path/lidar_points` | 可缺；LiDAR文件优先于内联点 | [RGB](../functions/integration--offline_replay--py.md#fn--load-rgb)、[LiDAR](../functions/integration--offline_replay--py.md#fn--load-lidar)、[路径约束](../functions/integration--offline_replay--py.md#fn--dataset-path) |
| replay `expected` | 默认{}，即不做业务断言 | [实际可检查字段](../functions/integration--offline_replay--py.md#fn--evaluate-expected)；空expected的passed不能证明功能正确 |
| `begin_run(output_root,metadata)` | 两者必传 | [清单创建](../functions/integration--run_manifest--py.md#fn-begin-run)，输出root/runs/run_id及3个子目录 |
| `finish_run(status,failure_reason)` | 调用方提供，不校验枚举 | [终结](../functions/integration--run_manifest--py.md#fn-finish-run)；不是带状态迁移保护的数据库事务 |
| 运行异常分类 | 按消息关键词首命中 | [分类规则](../functions/integration--runtime_diagnostics--py.md#fn-diagnose-runtime-failure)，不是堆栈根因分析 |

### runner完整CLI索引

以下为`main`声明的全部选项。默认表达式不等于实际值；下方“覆盖与组合条件”解释运行变化。所有行均进入[main参数校验](../functions/integration--carla_runner--py.md#fn-main)及[run生效路径](../functions/integration--carla_runner--py.md#fn-run)。未列数字上下界的项目，不推断实现一定会拒绝非法值。

| CLI参数 | 类型/动作 | 声明默认 | 选项范围 |
|---|---|---|---|
| `--host` | `str` | `'127.0.0.1'` | 由后续校验/消费者处理 |
| `--port` | `int` | `2000` | 由后续校验/消费者处理 |
| `--timeout-s` | `float` | `30.0` | 由后续校验/消费者处理 |
| `--fixed-delta-s` | `float` | `0.05` | 由后续校验/消费者处理 |
| `--frames` | `int` | `200` | 由后续校验/消费者处理 |
| `--max-frames` | `int` | `None` | 由后续校验/消费者处理 |
| `--realtime` | `'store_true'` | `False` | 由后续校验/消费者处理 |
| `--print-every` | `int` | `10` | 由后续校验/消费者处理 |
| `--log-dir` | `str` | `'artifacts/logs'` | 由后续校验/消费者处理 |
| `--no-log` | `'store_true'` | `False` | 由后续校验/消费者处理 |
| `--spawn-index` | `int` | `0` | 由后续校验/消费者处理 |
| `--seed` | `int` | `None` | 由后续校验/消费者处理 |
| `--warmup-frames` | `int` | `40` | 由后续校验/消费者处理 |
| `--map` | `str` | `None` | 由后续校验/消费者处理 |
| `--default-speed-mps` | `float` | `5.0` | 由后续校验/消费者处理 |
| `--driving-policy` | `str` | `None` | 由后续校验/消费者处理 |
| `--perception-mode` | `str` | `'sensors'` | ('sensors', 'world', 'virtual') |
| `--sensor-timeout-s` | `float` | `0.5` | 由后续校验/消费者处理 |
| `--sensor-warmup-frames` | `int` | `10` | 由后续校验/消费者处理 |
| `--sensor-startup-grace-frames` | `int` | `2` | 由后续校验/消费者处理 |
| `--sensor-profile` | `str` | `'default'` | ('default', 'low', 'competition_multiview') |
| `--rgb-detector-model` | `str` | `None` | 由后续校验/消费者处理 |
| `--rgb-detector-confidence` | `float` | `0.35` | 由后续校验/消费者处理 |
| `--rgb-detector-iou` | `float` | `0.45` | 由后续校验/消费者处理 |
| `--rgb-detector-input-size` | `int` | `640` | 由后续校验/消费者处理 |
| `--c-visual-confidence-threshold` | `float` | `DEFAULT_STRATEGY.perception_safety.visual_confidence_threshold` | 由后续校验/消费者处理 |
| `--qwen-remote` | `'store_true'` | `False` | 由后续校验/消费者处理 |
| `--qwen-voice-command` | `str` | `None` | 由后续校验/消费者处理 |
| `--qwen-base-url` | `str` | `os.environ.get('QWEN_BASE_URL', 'http://127.0.0.1:18000/v1')` | 由后续校验/消费者处理 |
| `--qwen-model` | `str` | `os.environ.get('QWEN_MODEL', DEFAULT_QWEN_MODEL)` | 由后续校验/消费者处理 |
| `--qwen-request-timeout-s` | `float` | `15.0` | 由后续校验/消费者处理 |
| `--qwen-max-inference-s` | `float` | `10.0` | 由后续校验/消费者处理 |
| `--qwen-decision-ttl-s` | `float` | `12.0` | 由后续校验/消费者处理 |
| `--qwen-command-ttl-s` | `float` | `30.0` | 由后续校验/消费者处理 |
| `--qwen-max-tokens` | `int` | `1` | 由后续校验/消费者处理 |
| `--qwen-image-max-side` | `int` | `256` | 由后续校验/消费者处理 |
| `--qwen-jpeg-quality` | `int` | `75` | 由后续校验/消费者处理 |
| `--qwen-image-dir` | `str` | `'artifacts/runtime/qwen_live'` | 由后续校验/消费者处理 |
| `--watchdog-timeout-s` | `float` | `1.0` | 由后续校验/消费者处理 |
| `--watchdog-startup-grace-s` | `float` | `0.5` | 由后续校验/消费者处理 |
| `--route-distance-m` | `float` | `500.0` | 由后续校验/消费者处理 |
| `--resume-route-progress-m` | `float` | `0.0` | 由后续校验/消费者处理 |
| `--resume-command-count` | `int` | `0` | 由后续校验/消费者处理 |
| `--resume-target-speed-kph` | `float` | `40.0` | 由后续校验/消费者处理 |
| `--route-refresh-frames` | `int` | `200` | 由后续校验/消费者处理 |
| `--scenario` | `str` | `'cruise'` | ('cruise', 'follow', 'red_stop', 'emergency') |
| `--lead-distance-m` | `float` | `18.0` | 由后续校验/消费者处理 |
| `--emergency-distance-m` | `float` | `6.0` | 由后续校验/消费者处理 |
| `--stop-line-m` | `float` | `20.0` | 由后续校验/消费者处理 |
| `--stop-line-guard-m` | `float` | `DEFAULT_STRATEGY.supervisor.stop_line_guard_m` | 由后续校验/消费者处理 |
| `--test-command-ttl-s` | `float` | `None` | 由后续校验/消费者处理 |
| `--command-json` | `str` | `None` | 由后续校验/消费者处理 |
| `--audio` | `str` | `None` | 由后续校验/消费者处理 |
| `--live-mic` | `'store_true'` | `False` | 由后续校验/消费者处理 |
| `--live-mic-source` | `str` | `'@DEFAULT_SOURCE@'` | 由后续校验/消费者处理 |
| `--qwen-service-url` | `str` | `None` | 由后续校验/消费者处理 |
| `--qwen-mode` | `str` | `'atomic_v1'` | ('atomic_v1', 'planner_v2') |
| `--qwen-timeout-ms` | `float` | `300.0` | 由后续校验/消费者处理 |
| `--qwen-queue-size` | `int` | `1` | 由后续校验/消费者处理 |
| `--qwen-image-root` | `Path` | `Path(__file__).resolve().parents[1]` | 由后续校验/消费者处理 |
| `--qwen-image-prefix` | `str` | `'artifacts/runtime/qwen_images'` | 由后续校验/消费者处理 |
| `--follow-spectator` | `'store_true'` | `False` | 由后续校验/消费者处理 |
| `--scenario-file` | `str` | `None` | 由后续校验/消费者处理 |
| `--spawn-all-scenario-actors` | `'store_true'` | `False` | 由后续校验/消费者处理 |
| `--validate-scenario-only` | `'store_true'` | `False` | 由后续校验/消费者处理 |
| `--use-current-map` | `'store_true'` | `False` | 由后续校验/消费者处理 |
| `--scenario-facts-mode` | `str` | `'fuse'` | ('perception', 'scenario', 'fuse') |

### CLI之后的覆盖与组合条件

- `scenario_file`覆盖map/fixed_delta_s/frames/scenario；`use_current_map`令实际map参数为None；`max_frames`在场景帧数之后取min。场景extensions.sensor_profile优先于CLI，并验证profile存在。
- `seed`未给时证据使用spec.seed；明确给出时同时改evidence_seed与spawn_index。只换seed不等于换Teacher版本。
- sensors模式下，若拥有真实场景actor或要求Qwen语义，`scenario_facts_mode`被强制为perception，不能用CLI默认fuse推断实际输入来源。
- `qwen_remote`是OpenAI-compatible旧边界，`qwen_service_url`是canonical异步入口；两条路径的图片参数不能混用。remote需sensors和realtime，禁止command-json/audio；服务路径的V2行为另受qwen_mode约束。
- `live_mic`不能与audio/command-json/scenario-file并用；command-json与audio同时存在时_load_command先取JSON，不能凭两个选项都出现推断两者都会执行。
- `validate_scenario_only`在连接CARLA之前返回，但已加载driving policy并解析scenario/extensions；它只证明这一层解析通过。
- 日志的`CARLA_DRIVING_CODE_VERSION`环境变量优先于git HEAD；git HEAD不包含未提交改动。证据配置只自动保存args的标量/None，Path类型需要其他来源补齐。

### 麦克风/VAD参数索引

| 参数 | 默认 | 单位和消费语义 |
|---|---|---|
| source | @DEFAULT_SOURCE@ | PulseAudio设备，交parec |
| sample_rate | 16000 | Hz；下游音频入口按16kHz，当前不自动重采样 |
| frame_ms | 20 | 毫秒，必须整除1000；默认320样本/640字节 |
| pre_roll_ms | 300 | 预滚，至少保留1帧，即使设置0也非零帧 |
| end_silence_ms | 700 | 激活后尾静音长度，换算帧数 |
| max_utterance_s | 7.0 | 整段上限含预滚/尾静音 |
| min_voice_ms | 160 | 最小有声帧阈值，不是片段总长度 |
| min_rms | 0.003 | s16le归一化振幅RMS下限 |
| noise_ratio | 3.0 | 3秒噪声历史中位数倍率，需>1 |
| trigger_frames | 3 | 连续高能帧数，需>=1 |

[具体校验与VAD状态](../functions/integration--live_voice--py.md#fn-livevoiceconfig---post-init--)；音频段队列固定4，放入最多等0.1s，满时丢段；结果队列无界。停止后应创建新LiveVoiceSource，当前没有重启复位接口。

### 传感器probe参数索引

此入口用当前地图，不调用load_world；默认与主runner不同，不能照抄runner参数名。

| 参数 | 默认 | 含义 |
|---|---|---|
| host / port | 127.0.0.1 / 2000 | CARLA连接 |
| timeout_s / sensor_timeout_s | 10 / 2 | 秒；RPC/精确帧等待 |
| fixed_delta_s | 0.05 | 仿真秒步长 |
| mode / profile | rgb / low | mode可rgb/lidar/radar/both/all；profile可default/low |
| frames / startup_frames | 100 / 10 | 测量目标/预热最大尝试次数；预热需min(2,startup_frames)连续对齐 |
| spawn_index | 0 | 从index取模位置起逐个尝试出生点 |
| expected_map | None | 指定时匹配当前地图末段，不换图 |
| minimum_wall_duration_s | 0 | 秒；达到帧目标后仍需满足测量墙钟窗口 |

[run_sensor_probe](../functions/integration--sensor_stability--py.md#fn-run-sensor-probe)存在启动失败误报success的问题，见同页记录与[AUDIT](../AUDIT.md)。检查aligned_frames/reason，不只看success。

## 开发维护先读：实际语义

以下功能页说明实现理由、分支、接口含义、改动联动与验证。先读这些内容，再按逐文件索引定位方法；不要用函数名推断业务语义。

- [一帧控制的实际顺序与执行值](../functions/control-frame.md)

[Vehicle module](../modules/vehicle.md)

## Responsibility, contracts and failure behavior

integration.carla_runner.run owns CARLA connection, synchronous tick, control application, logging and cleanup. ControlRuntime.step consumes vehicle state, route and PerceptionFrame; returns FrameResult. Simulation time uses seconds; canonical deadlines use monotonic nanoseconds. CLI defaults: sensors and atomic_v1. Config sources: config/strategy.py, strategy_config.yaml, CLI, driving_policy.json and separate OrchestratorConfig defaults. Watchdog faults latch braking until explicit reset. Startup grace overrides final_control after SafetySupervisor.


## 模块接口与参数核对（2026-09-20）

调用方为carla_runner；ControlRuntime.step接收RuntimeVehicleState、PerceptionFrame、RouteReference及dt_s，返回FrameResult。final_control才是运行结果，raw_control保留仲裁前值；feedback可能为空，longitudinal/lateral可能为None，消费者不能假设每帧都有两路结果。

### 参数语义与生效边界

ControlRuntime构造默认速度5m/s、命令超时15s；step的speed_cap_mps=None表示本次未额外传入上限，不是无限授权。raw_control_override改变控制输入路径，watchdog_alerts触发故障处理；启动宽限的最终覆盖在runner，不能仅看ControlRuntime。

### 上下游与修改影响

vehicle使用yaw_deg而B的VehiclePose使用yaw_rad；sim_time_s与canonical的monotonic ns分别处理。修改FrameResult需联动runner、证据记录及评分；修改时钟/超时需查编排与状态机。

### [integration/runtime_loop.py](../../../integration/runtime_loop.py) 的入口与声明

```python
ControlRuntime.__init__(self, lateral: LateralController, *, longitudinal: LongitudinalController | None=None, safety: SafetySupervisor | None=None, voice_adapter: VoiceCommandAdapter | None=None, default_speed_mps: float=5.0, command_timeout_s: float=15.0) -> None
ControlRuntime.yellow_clear_committed(self) -> bool
ControlRuntime.submit_voice(self, envelope: Mapping[str, object], *, now_s: float) -> AdaptedVoiceCommand
ControlRuntime.safety_latched(self) -> bool
ControlRuntime.active_command_id(self) -> str | None
ControlRuntime.confirm_voice(self, command_id: str, *, approved: bool, now_s: float) -> ExecutionFeedback | None
ControlRuntime.reset_safety_latch(self) -> None
ControlRuntime.clear_safety_alerts(self, alerts: tuple[str, ...]) -> None
ControlRuntime.clear_safety_alert_prefix(self, prefix: str) -> tuple[str, ...]
ControlRuntime.release_scenario_stop_hold(self, *, requested_speed_mps: float) -> bool
ControlRuntime.fail_active(self, *, now_s: float, detail: str, resume_speed_mps: float | None=None) -> ExecutionFeedback | None
ControlRuntime.complete_active(self, *, now_s: float, detail: str) -> ExecutionFeedback | None
ControlRuntime.step(self, vehicle: RuntimeVehicleState, scene: PerceptionFrame, route: RouteReference, *, dt_s: float, watchdog_alerts: tuple[str, ...]=(), raw_control_override: object | None=None, speed_cap_mps: float | None=None, safety_override_reason: str | None=None) -> FrameResult
```

### [integration/contracts.py](../../../integration/contracts.py) 的入口与声明


类级字段（含配置、输入输出和内部状态；仅声明默认，不是当前run生效配置）：

| 字段 | 类型 | 默认值/来源 |
|---|---|---|
| `DetectedObject.class_id` | `int` | `无声明默认（构造/赋值方提供）` |
| `DetectedObject.class_name` | `str` | `无声明默认（构造/赋值方提供）` |
| `DetectedObject.confidence` | `float` | `无声明默认（构造/赋值方提供）` |
| `DetectedObject.bbox_xyxy_norm` | `tuple[float, float, float, float]` | `无声明默认（构造/赋值方提供）` |
| `DetectedObject.distance_m` | `float &#124; None` | `None` |
| `DetectedObject.track_id` | `str &#124; None` | `None` |
| `PerceptionFrame.frame` | `int` | `无声明默认（构造/赋值方提供）` |
| `PerceptionFrame.sim_time_s` | `float` | `无声明默认（构造/赋值方提供）` |
| `PerceptionFrame.lead_distance_m` | `float &#124; None` | `None` |
| `PerceptionFrame.lead_speed_mps` | `float &#124; None` | `None` |
| `PerceptionFrame.traffic_light` | `str` | `'UNKNOWN'` |
| `PerceptionFrame.distance_to_stop_line_m` | `float &#124; None` | `None` |
| `PerceptionFrame.speed_limit_mps` | `float &#124; None` | `None` |
| `PerceptionFrame.lane_offset_m` | `float &#124; None` | `None` |
| `PerceptionFrame.route_deviation_m` | `float &#124; None` | `None` |
| `PerceptionFrame.collision` | `bool` | `False` |
| `PerceptionFrame.red_light_violation` | `bool` | `False` |
| `PerceptionFrame.lane_invasion` | `bool` | `False` |
| `PerceptionFrame.detected_objects` | `tuple[DetectedObject, ...]` | `()` |
| `FrameResult.vehicle` | `RuntimeVehicleState` | `无声明默认（构造/赋值方提供）` |
| `FrameResult.final_control` | `ControlOutput` | `无声明默认（构造/赋值方提供）` |
| `FrameResult.longitudinal` | `LongitudinalOutput &#124; None` | `无声明默认（构造/赋值方提供）` |
| `FrameResult.safety_reason` | `str` | `无声明默认（构造/赋值方提供）` |
| `FrameResult.safety_override` | `bool` | `无声明默认（构造/赋值方提供）` |
| `FrameResult.feedback` | `tuple[ExecutionFeedback, ...]` | `()` |
| `FrameResult.raw_control` | `Any &#124; None` | `None` |
| `FrameResult.lateral` | `LateralOutput &#124; None` | `None` |
| `FrameResult.safety_reason_category` | `str` | `'NONE'` |

以上为核心交接入口；模块内其余实现、CLI和资源的完整字段/拒绝条件见本页功能小文档索引。类型未声明的返回值不凭名称推断。当前代码基线fe1ba839，静态复核不证明实际CARLA/GPU/板端运行成功。

## Complete implementation inventory

- [integration/__init__.py](../../../integration/__init__.py) - package boundary and exports

- [integration/carla_runner.py](../../../integration/carla_runner.py) - `_DeferredCommand`, `_select_deferred_commands`, `_canonical_poll_wait_timeout_ms`, `_compiled_plan_from_payload`, `_maneuver_target_visible`, `_legacy_target_classes`, `_maneuver_target_gap_s`, `_maneuver_target_distance_m`, `_physical_actor_id_for_target`, `_maneuver_target_passed`, `_maneuver_step_reanchors_target`, `_record_maneuver_update`, `_note_extension_terminal`, `_note_safety_feedback`, `_qwen_resolution_reason`, `_speed_mps`, `_actor_bbox_clearance_m`, `_actor_horizontal_radius_m`, `_actor_signed_route_clearance_m`, `_actor_signed_longitudinal_clearance_m`, `_acceptance_lateral_controller`, `_follow_ego_spectator`, `_scenario_maneuver`, `_scenario_route_distance_m`, `_scenario_requires_adjacent_lane_anchor`, `_scenario_actor_lanes_fit_route`, `_scenario_requires_target_lane_occupancy`, `_actor_activation_due`, `_actor_deactivation_due`, `_release_scenario_actor_if_due`, `_scenario_uses_dynamic_out_and_back`, `_scenario_startup_maneuver`, `_scenario_lane_change_profile`, `_traffic_light_stop_points`, `_vehicle_state`, `_planner_runtime_state`, `_apply_compiled_plan_route`, `_route_starts_near_ego`, `_lane_change_route_parameters`, `_is_deferred_dynamic_lane_change`, `_dynamic_return_destination_xy`, `_maneuver_lane_label`, `_mission_speed_after_maneuver`, `_retain_route_for_maneuver`, `_scene_from_world`, `_world_vehicle_detections`, `_bind_scenario_actor_ids`, `_sensor_evidence_actor_ids`, `_sensor_evidence_target_aliases`, `_spawn_static_lead`, `_scenario_actor`, `_scenario_actors`, `_scenario_walkers`, `_scenario_static_props`, `_cleanup_stale_scenario_actors`, `_scenario_local_transform`, `_active_actor_route_context`, `_scenario_vehicle_speed_mps`, `_signed_forward_speed_mps`, `_occupied_actor_locations`, `_spawn_scenario_vehicle`, `_update_scenario_vehicle`, `_scenario_target_lane_occupied_count`, `_spawn_scenario_walker`, `_update_scenario_walker`, `_spawn_scenario_static_prop`, `_select_scenario_lead`, `_scenario_traffic_light_distance`, `_traffic_light_scenario_anchor`, `_scenario_traffic_light_observation`, `_scenario_traffic_light_distance_to_stop_line_m`, `_scenario_traffic_light_signed_clearance_m`, `_apply_virtual_scenario`, `_scenario_facts`, `_lead_vehicle_travel_m`, `_select_scene_facts`, `_apply_scenario_speed_limit`, `_load_command`, `_qwen_voice_command`, `_qwen_desired_speed_mps`, `_save_qwen_rgb_image`, `_build_qwen_context`, `_evidence_recorder`, `_git_code_version`, `_rejected_load_envelope`, `_warm_up_sensor_bridge`, `_scenario_completed`, `_runtime_health_completed`, `_declared_scenario_runtime_completed`, `_c_perception_safety_reason`, `_c_safety_speed_cap_mps`, `_single_sensor_fault_speed_cap_mps`, `_c_speed_cap_control_override`, `_expected_safety_completed`, `_scenario_raw_control_fault`, `_route_contract_completed`, `_route_finish_reached`, `_route_run_can_end_early`, `_remaining_route_distances`, `_distance_contract_remaining_m`, `_minimum_gap_contract_completed`, `_intentional_qwen_failure_completed`, `_route_stop_trigger_m`, `_topology_planning_distance_m`, `_route_recovery_hold_reference`, `_route_local_reference_needs_refresh`, `_map_short_name`, `_map_contract_name`, `_scenario_clean_world_on_start`, `_build_resume_segment_spec`, `_select_load_map`, `_warm_up_loaded_map`, `_import_carla_api`, `_maneuver_junction_exited`, `run`, `main`
- [integration/demo_offline.py](../../../integration/demo_offline.py) - `main`
- [integration/driving_policy.py](../../../integration/driving_policy.py) - `_number`, `DrivingPolicy`, `DrivingPolicy.perception_parameters`, `DrivingPolicy.safety_config`, `load_driving_policy`
- [integration/live_voice.py](../../../integration/live_voice.py) - `LiveVoiceConfig`, `LiveVoiceConfig.samples_per_frame`, `LiveVoiceConfig.bytes_per_frame`, `EnergyVadSegmenter`, `EnergyVadSegmenter.feed`, `EnergyVadSegmenter.flush`, `LiveVoiceResult`, `LiveVoiceSource`, `LiveVoiceSource.preload`, `LiveVoiceSource.start`, `LiveVoiceSource.poll`, `LiveVoiceSource.stop`
- [integration/offline_replay.py](../../../integration/offline_replay.py) - `ReplayFrameResult`, `ReplayReport`, `ReplayReport.to_payload`, `load_replay_manifest`, `run_replay_manifest`, `_run_frame`, `_evaluate_expected`, `_vehicle`, `_route`, `_detections`, `_load_rgb`, `_load_lidar`, `_dataset_path`, `_mapping`, `_integer`, `_number`, `write_replay_report`
- [integration/run_manifest.py](../../../integration/run_manifest.py) - `RunContext`, `_write_atomic`, `begin_run`, `finish_run`, `update_run_metadata`
- [integration/runtime_diagnostics.py](../../../integration/runtime_diagnostics.py) - `FailureStage`, `RuntimeFailureDiagnosis`, `RuntimeFailureDiagnosis.to_dict`, `diagnose_runtime_failure`
- [integration/runtime_loop.py](../../../integration/runtime_loop.py) - `ControlRuntime`, `ControlRuntime.yellow_clear_committed`, `ControlRuntime.submit_voice`, `ControlRuntime.safety_latched`, `ControlRuntime.active_command_id`, `ControlRuntime.confirm_voice`, `ControlRuntime.reset_safety_latch`, `ControlRuntime.clear_safety_alerts`, `ControlRuntime.clear_safety_alert_prefix`, `ControlRuntime.release_scenario_stop_hold`, `ControlRuntime.fail_active`, `ControlRuntime.complete_active`, `ControlRuntime.step`
- [integration/sensor_stability.py](../../../integration/sensor_stability.py) - `map_contract_name`, `selected_sensor_specs`, `SensorFrameCounter`, `SensorFrameCounter.callback`, `SensorFrameCounter.wait_for_frame`, `SensorFrameCounter.counts`, `SensorFrameCounter.frame_bounds`, `SensorFrameCounter.invalid_callbacks`, `SensorProbeResult`, `SensorProbeResult.to_json`, `_make_transform`, `_configure_blueprint`, `_spawn_ego`, `run_sensor_probe`, `build_argument_parser`, `main`

## Dependencies and coordinated changes


## Validation entry points

`python -m pytest integration/tests/test_carla_runner_defaults.py integration/tests/test_carla_runner_helpers.py integration/tests/test_runtime_loop.py integration/tests/test_runtime_diagnostics.py integration/tests/test_sensor_stability.py integration/tests/test_run_manifest.py integration/tests/test_driving_policy.py`

Run from the worktree root. Listed commands are relevant checks, not claims that tests were executed. CARLA, remote-model and hardware acceptance require their actual environments and run manifests.

## 功能小文档完整索引

以下功能页分别记录实现入口、输入输出声明、内部调用、异常、配置和静态上下游；测试文件保留在源码索引中。

- [compat.py](../functions/compat--py.md)
- [integration/__init__.py](../functions/integration--__init__--py.md)
- [integration/carla_runner.py](../functions/integration--carla_runner--py.md)
- [integration/demo_offline.py](../functions/integration--demo_offline--py.md)
- [integration/driving_policy.py](../functions/integration--driving_policy--py.md)
- [integration/live_voice.py](../functions/integration--live_voice--py.md)
- [integration/offline_replay.py](../functions/integration--offline_replay--py.md)
- [integration/run_manifest.py](../functions/integration--run_manifest--py.md)
- [integration/runtime_diagnostics.py](../functions/integration--runtime_diagnostics--py.md)
- [integration/runtime_loop.py](../functions/integration--runtime_loop--py.md)
- [integration/sensor_stability.py](../functions/integration--sensor_stability--py.md)

## 诊断与维护交接

本模块证据：模拟/墙钟、预算、最终control、异常；D后覆盖见AUDIT R05。功能实现与上下游见本页原索引；跨模块回查[追踪矩阵](../TRACEABILITY.md)与[诊断入口](../DIAGNOSIS.md)。实际run必须核对版本，未执行的检查不视为已通过。

专项记录：[WATCHDOG_ALERT与持续停车](../functions/watchdog-diagnosis.md)。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `integration/tests/test_acceptance_suite_a800_runner.py`

来源 SHA256：`00eaacf44c493876a95dd084120a2429cf7b262fb6af264f0438a8eee76dede8`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_acceptance_suite_contracts.py`

来源 SHA256：`1f025990dd39231219fdfde8da22a36b20e8f9531486d3d7854afec6f93bc605`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_basic_track_scorecard.py`

来源 SHA256：`f5624974b193bed25c2d8068dd00fc30ee0ba42d26c43e760d5e7a9e822455e8`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_canonical_bridge.py`

来源 SHA256：`3bf4d2d821a1d497789dade1185bdda35353e9b627bcc036647e88354efaa675`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_carla_perception.py`

来源 SHA256：`b9481fa29bf3cb096b7c82dc02687528c07a119b53b64d416cf47c2c3f7e2eca`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `Vec.x` | `float` | `0.0` |
| `Vec.y` | `float` | `0.0` |
| `Vec.z` | `float` | `0.0` |
| `RadarDetection.depth` | `float` | `无声明默认；构造/赋值方提供` |
| `RadarDetection.azimuth` | `float` | `0.0` |
| `RadarDetection.altitude` | `float` | `0.0` |
| `RadarDetection.velocity` | `float` | `0.0` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `test_rgb_detector_failure_is_fail_closed.Detector.detect_measurement` / 584 | `本地无直接if；检查上下文` | `raise RuntimeError('inference unavailable')` |
| `test_configured_visual_provider_failure_is_fail_closed.provider` / 600 | `本地无直接if；检查上下文` | `raise RuntimeError('provider unavailable')` |
### `integration/tests/test_carla_runner_defaults.py`

来源 SHA256：`44827532c0d225543672bee4cd29841570e8e6eb5cf586395b7aa2e251c9427f`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_carla_runner_helpers.py`

来源 SHA256：`ecb89f7c96f8d48cceaa86355563c4bd907a3815c93a937d1ead0e4dcf557bc6`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `test_actor_lane_route_validator_skips_heading_mismatch.heading_mismatch` / 149 | `本地无直接if；检查上下文` | `raise RuntimeError('no nearby driving waypoint agrees with ego heading')` |
| `test_active_prevalidated_route_is_not_rebuilt_after_ego_leaves_its_origin.unexpected_rebuild` / 906 | `本地无直接if；检查上下文` | `raise AssertionError('active out-and-back route must be retained')` |
| `test_sensor_warmup_retries_until_two_consecutive_aligned_frames_arrive.Bridge.acquire` / 2282 | `self.calls == 1` | `raise PerceptionTimeoutError('not ready')` |
| `test_sensor_warmup_resets_streak_after_pipeline_bubble.Bridge.acquire` / 2315 | `self.calls == 2` | `raise PerceptionTimeoutError('pipeline bubble')` |
### `integration/tests/test_driving_policy.py`

来源 SHA256：`835f0be32bf4f2e8086b813431ee9bb6b719d8a6e644c13b1956aa239e0f1a22`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_four_modal_full_chain_remote.py`

来源 SHA256：`b83de067f32db461a3f48cd324a0f7a6cdd8bf45e28991e2d825ae48bba5544c`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_four_modal_provided_transcript.py`

来源 SHA256：`49f2d1eb88990d3708812fbb77ebebfd362984802acc62f7f68501263209f3e8`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_generalization_gate.py`

来源 SHA256：`5d529334d6b6b797835bc243e211275273da4cf001c3a55b8383545922c4ddc3`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_interface_schemas.py`

来源 SHA256：`e01f63e3991437e20fc936f097d88984c4844a702a6df2182c050fccfa89757f`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_language_benchmark_release.py`

来源 SHA256：`ac73c0cf3e1439afecb20e87a413cb4b6030313d3b848b60c464c251d6457115`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_language_testset.py`

来源 SHA256：`179576858a3c589a0bee5fd4fb9d7f19c2a6333d8f1fc45df92befa09ad1b376`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_live_voice.py`

来源 SHA256：`f81ce58f5d34ebe90265a1688316accc0b4f9a9a936cba74cfeadd89ed6aacb7`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_maneuver_plan_schema.py`

来源 SHA256：`3e67aae7f5db5234a75e0df34c238b2c6ac31a93cd23a6f0ee33415d072ed121`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_model_manifest.py`

来源 SHA256：`dc47db93664d9b912929417da4a7244ebb5ab3f74a4b152126e65496f62d1e3e`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_multimodal_dataset_builder.py`

来源 SHA256：`a79b4fdbe6c6dea87b1d3c781aa311153f033111acde5b8c2dd15e6b79053e71`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_multimodal_dataset_validator.py`

来源 SHA256：`d88c7124a94f1a6b30d7c567ad0a9a9f4f15b393ef19fa9ee0c9f5c672bd49a4`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_object_tracker.py`

来源 SHA256：`8f3b8e52ecac8e809ef795de93fc0e0c4dfecf5164588a4723799932b83aaa62`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_official_scenario_runner.py`

来源 SHA256：`bb4042f5033e8f6405e19645f2ae43c668138501eaf5cd3924e4b2b7742104cc`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_offline_replay.py`

来源 SHA256：`103ff87f182d8e64ad4e6dd487350df56b4681179350c80e2dc4d00faae7b99f`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_perception_bridge.py`

来源 SHA256：`38252b7753c09938066b5784c8d3719e81955b717abb3cdcd8570d13aa746eb8`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_perception_stage.py`

来源 SHA256：`7dc27aac26f16b40e7059efd4e18150c592dac42e1289174bd3710da07586502`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_plan_compiler.py`

来源 SHA256：`303389a16d426b80e91f805791e1f9042a46fd32d03188f9e24090cacae92371`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_qwen_async.py`

来源 SHA256：`94342f9e831e1e0600f0bb8809c1774d39066b1608efb24b80d1e8712c8ed7da`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `Context.voice_command` | `str` | `无声明默认；构造/赋值方提供` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `_wait_until_ready` / 28 | `本地无直接if；检查上下文` | `raise AssertionError('async Qwen result did not finish')` |
| `test_inference_error_has_no_executable_command.fail` / 96 | `本地无直接if；检查上下文` | `raise RuntimeError('model unavailable')` |
### `integration/tests/test_qwen_async_supersede.py`

来源 SHA256：`d55c6d4c99f898d19ba448cba7b46fb4c8c57b6b53532928bafd58d2c0898394`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `Context.voice_command` | `str` | `无声明默认；构造/赋值方提供` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `test_superseded_slow_result_cannot_replace_newer_request` / 47 | `本地无直接if；检查上下文` | `raise AssertionError('newest async decision did not finish')` |
### `integration/tests/test_qwen_async_timeout.py`

来源 SHA256：`49963510a8a7ca419243c476785a1bb901d8f0e4d783f748fb6875dec5b92925`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_qwen_batch_benchmark.py`

来源 SHA256：`5e8abce83aa53294f8ee3bcc01f536520261c386b87313846423adcbf18dd3d5`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_qwen_boundary.py`

来源 SHA256：`fbfa4b3629b4a0107150aa7c183a0957f35831eca42ab257d95962231fd6b89d`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_qwen_expanded_instruction_benchmark.py`

来源 SHA256：`0a07397ddc9394dfecf1f5d47fee8a3f9e8756b813a38b07c661b2e4bb27e6b5`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_qwen_fault_injection.py`

来源 SHA256：`dbbbf8a93c9e1654bd62973533eb4f59df37c4557871f805ba80f54c9fafabfb`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_qwen_four_modal_stress_set.py`

来源 SHA256：`076b7c722fa60ad9fdb671eb9af4792c03fcfd586fe38cf55301ed5cd8206079`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_qwen_image_stager.py`

来源 SHA256：`4439957afc01f48d72a634ece07d232a52456a281478f98c31a8f4841f745f62`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_qwen_latency_gate.py`

来源 SHA256：`51958c27ee93cb81d103db0ffbe81888b0ec3e001a03a409450804b231a8099a`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_qwen_plan_boundary.py`

来源 SHA256：`ae65a1afa1c542b3e1465980a8ebf9a795b7c788d49ae8d499696659f7d099ee`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_qwen_planner_orchestrator.py`

来源 SHA256：`abce24ad73419a62711f4169da3fb03e44c73928836a0fccf3e96661bdca2d8b`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_qwen_profiles.py`

来源 SHA256：`dc76c4352acf3cf887488531b2dfc0b704692dbf5d4939885e1b48fb9ba6f4ed`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_qwen_remote_backend.py`

来源 SHA256：`74e44238287496c955f1836a938930e0be0fb6c045216cf0c536f1c5a9b2dcc7`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_qwen_scenario_contracts.py`

来源 SHA256：`6bb220436e722e94171204915b38b696a8c1c03d881889d6dd8ff8e2fbcf906d`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_qwen_scenario_monitor.py`

来源 SHA256：`772e8f6efb695885b35d55d2295d8dc5460cf3addd7a62caef3bca7007ef4a4e`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_qwen_service.py`

来源 SHA256：`225bb2fde95de4341848efc7e0f43315605e28a8b373bd193f29d028a195f561`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `test_planner_v2_service_classifies_malformed_generation_as_bad_gateway.MalformedPlanner.infer` / 180 | `本地无直接if；检查上下文` | `raise QwenPlanParseError('MODEL_OUTPUT_MUST_BE_BARE_JSON_OBJECT')` |
### `integration/tests/test_qwen_vl_adapter.py`

来源 SHA256：`9eafbb56eebbf7fc8e8f62c6c73ea64883ff8ad085b91d9864d4f887a086e29c`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `test_local_checkpoint_defaults_to_64_visual_tokens.CapturingBackend.generate` / 645 | `本地无直接if；检查上下文` | `raise AssertionError('generation is not part of this test')` |
### `integration/tests/test_qwen_vl_cli.py`

来源 SHA256：`9d203f7b27341761b010e65d806d9f9d6caf90bbdf96558b8a53f591046cbf72`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_repro_compose.py`

来源 SHA256：`03c225c18176a6d4167a09e8fec5a7bfc215371fc9d518c267a5564ff48284bd`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_repro_delivery.py`

来源 SHA256：`0e5073b205e5c432e48169732a5d8b19a86dcaa0d94c2d781d873255e0afabc4`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_rgb_detector.py`

来源 SHA256：`55fdc2a9f5ddac49915c663e573cd359bef5c556fb0bee259cddf6e4be0c6cb2`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
|---|---|---|
| `Input.name` | `str` | `'images'` |
| `Input.shape` | `tuple[int, int, int, int]` | `(1, 3, 640, 640)` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `Session.run` / 35 | `self.fail` | `raise RuntimeError('backend failed')` |
### `integration/tests/test_role_a_orchestrator.py`

来源 SHA256：`83d4997ce54e1b8f8a2a34966deba660625ede8d486c4af36c3acc09260e5e58`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `test_qwen_timeout_does_not_block_caller.infer` / 181 | `本地无直接if；检查上下文` | `raise RuntimeError('offline')` |
| `test_evicted_qwen_request_gets_explicit_queue_overflow_terminal.infer` / 260 | `本地无直接if；检查上下文` | `raise RuntimeError('released')` |
### `integration/tests/test_role_c_perception.py`

来源 SHA256：`0bb78c4dab410c902f0ebe518dce27a65d4b0d7bcc44ca76131c86c1c4709b30`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_role_d_control_runtime.py`

来源 SHA256：`2f468540d3b37258a9d645c33959e64767a05f9a6b6a8b92674b565b9f96f7a2`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_route_generalization_tool.py`

来源 SHA256：`19dd7828fdc2e621b6292296677b7106da68a75f0b16e0bf176e9c13bf8c3982`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_route_geometry.py`

来源 SHA256：`ee13776ac51e02fcb8308545642632b4af742ecc98a882ec7a1553b5b215ebd1`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_route_manager.py`

来源 SHA256：`2cc141cd4bf6aee65529facb487e61322c9ef96d0ec7f0884fcc55deed890f18`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_route_planner.py`

来源 SHA256：`9562d6e7882ab438048eb133ff5154511fa988e8b43388cbe25dbe2f843a0001`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_run_manifest.py`

来源 SHA256：`d2248b2276440a9d439795caa7936075f41fcb94b5aa42f534449bd72de89a09`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_runtime_diagnostics.py`

来源 SHA256：`d04ab0f00965376625ca377e05eda2e097fbe841a17e51d7e2f1fa79fbf44e30`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_runtime_loop.py`

来源 SHA256：`e697fbfaf7d417e67f5cf257cd5d11df04d243a82d679aab23f821fb568d841c`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_runtime_stages.py`

来源 SHA256：`a72dc77e193e69b8d07a5cdce030d2c2b3e17485a1bf531e2621673e06414e6f`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_scenario_acceptance.py`

来源 SHA256：`d5d3aac3c15537a721d6a3e18a13d84a09e0ae21ed0324b87e94afbdef50baf5`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_scenario_builder.py`

来源 SHA256：`36c5af4aa44bdc96e045d7b5138f5e982fd5b24f90df45278ecf20585b041c70`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_scenario_evidence.py`

来源 SHA256：`65e576b89b50e73b9fa458e742b82b58c67d87768cb12ae0c978193a4c7f36ec`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_scenario_execution.py`

来源 SHA256：`e85eb849f620fa768b8c52396a06eeccd5449cc4a2c97f62a0aa9b9220e0b007`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_scenario_extensions.py`

来源 SHA256：`d0f1b9c077da240ea8ca787bb5552318d15909dde826f67e88d5c1dec3285c49`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_scenario_matrix_tool.py`

来源 SHA256：`057abcbaad5cd09d01aa49aa6ada78182eb4e26f393fd4968a5f5b3544d4bd4b`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_second_group_runtime.py`

来源 SHA256：`060f4313892a32a6ec45f259eaa19e939a402de676545c017bc159762541a155`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `test_runtime_end_gives_pending_qwen_command_a_terminal.infer` / 352 | `本地无直接if；检查上下文` | `raise RuntimeError('released')` |
### `integration/tests/test_sensor_profiles.py`

来源 SHA256：`4c94fd9d60dc83a818e59fef1a04ba9fda2580886907834d129fcfb78ff677a8`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_sensor_stability.py`

来源 SHA256：`83ac11ec47565793a18753dbb81137fc66ef6e313eddef0b75d46b89fc5ed608`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_unseen_scenario_generalization.py`

来源 SHA256：`1406e5e37e950db2542d6802dfcf6c756c53ab1c122b1442d52d7ed34d6b1ed5`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_validate_s2_member3_evidence.py`

来源 SHA256：`a2fa8b1fcce9a1a3da857ad2b90510ed08b2fe3275567c20bf73e1918b23ef2f`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_validate_s3_member4_evidence.py`

来源 SHA256：`94fa1bba67384c57c4b0fbe10fa00b6e4abcc81c6acb962cfc3049b1daa4edbe`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_validate_scenarios.py`

来源 SHA256：`8d318a5df0a1e45d56c0eabe76dbcb5460f52e9221b908e0c637a1ca6aea411e`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_vllm_cu132_build.py`

来源 SHA256：`e0791c36a1245df164d1205420a0fe0fed3401ad141d3a7cd8d50b4087f7638e`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_voice_adapter.py`

来源 SHA256：`e0ac36249ab5b7bbd9c230e1ed3062af521259b9b02da1e942aed4fe033a9a85`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_voice_compound_routing.py`

来源 SHA256：`6a180dd9c54be7ea51ccf45b0d21c7caad0e3ef8f657f3b3e9f1cfcebcc55336`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `integration/tests/test_voice_qwen_semantic_coverage.py`

来源 SHA256：`48d821a47264cb8291b6e75735f91cc9cc6fe760dafa566ecd58238a570827bb`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
