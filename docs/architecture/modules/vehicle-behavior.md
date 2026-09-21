# Command adaptation and behavior state machines

## 开发维护先读：实际语义

以下功能页说明实现理由、分支、接口含义、改动联动与验证。先读这些内容，再按逐文件索引定位方法；不要用函数名推断业务语义。

- [授权、确认、过期与停车保持](../functions/command-lifecycle.md)
- [前置条件锁存、步骤完成与重规划](../functions/maneuver-progress.md)

[Vehicle module](../modules/vehicle.md)

## Responsibility, contracts and failure behavior

VoiceCommandAdapter consumes schema_version, command_id, intent, parameters, confidence, status, errors, confirm_required and valid_duration_s. It converts speed to m/s; invalid input becomes unauthorized NO_OP. BehaviorFSM owns confirmation, timeout and terminal feedback. ManeuverFSM owns compiled steps, preconditions, completion, failure and replan. A dataclasses are process-local and require adapters to frozen JSON contracts. Simulator, examples, routing, watchdog and telemetry support offline execution and diagnostics.


## 第3模块逐项精读：接线与参数索引

基线提交`36baa428`（业务源码与此前`fe1ba839`一致）。本轮覆盖本页10份实现记录、4份命令示例及A目录README/RUN的适用范围，改写9份逐文件页的137处占位说明，并补充原来仅有简短docstring的关键入口。这里记录当前实现与缺口，不把“有方法/字段”当作运行闭环已完成。

### 三种命令及两种FSM不能混用

| 边界 | 输入→输出 | 身份/时间/授权 |
|---|---|---|
| HighLevelCommandAdapter | Qwen风格action JSON→voice风格intent envelope | TTL默认3s；timestamp_ns仅作为元数据；复杂action通常valid但强制确认，FOLLOW不在此动作集合 |
| VoiceCommandAdapter | voice envelope→AdaptedVoiceCommand(A DrivingCommand+metadata) | 接收帧now_s为仿真秒，expires=now+TTL；坏输入为未授权NO_OP；control_authorized=True仍可能要求确认 |
| BehaviorFSM | A DrivingCommand→BehaviorResult/ExecutionFeedback | 一份全局行为状态、一个正常活动owner；绝对到期>=，相对timeout>；终态缓存按command_id幂等 |
| ManeuverFSM | CompiledManeuverPlan+snapshot→ManeuverUpdate | 用户command_id、plan_id、step_id分开；步骤连续完成、入口条件锁存；safe_behavior/重规划事件只是输出，需消费者实际执行 |

A内部DrivingCommand不是`interfaces/driving_command.schema.json`的canonical载荷：前者action/仿真秒，后者intent/纳秒与参数结构。跨边界走[模块2桥接](vehicle-planner.md)；不能直接from_dict互换。BehaviorFSM.CONFIRMING为活动等待状态，而ManeuverFSM.CONFIRMING是终态且没有confirm方法，需要外层重新决策。

### 具体参数与字段消费索引

| 参数/字段 | 默认、单位或合法集合 | 实际消费/失败边界 | 入口 |
|---|---|---|---|
| 两个Adapter.default_ttl_s / default_slow_speed_mps | 3秒 / 2m/s | 有限正TTL、有限非负速度；两实例各自默认，非共享运行配置 | [high-level](../functions/car_control_A--high_level_command--py.md#fn-highlevelcommandadapter---init--) / [voice](../functions/integration--voice_adapter--py.md#fn-voicecommandadapter---init--) |
| high-level.schema_version/command_id/action | 1.0、非空ID、已支持动作 | 非Mapping/必填坏类型可抛异常；禁止低层字段/错版本返回invalid envelope，不能声称全部错误统一返回 | [adapt](../functions/car_control_A--high_level_command--py.md#fn-highlevelcommandadapter-adapt) |
| action动作集合 | SET_SPEED/SLOW_DOWN/STOP/EMERGENCY_STOP/EMERGENCY_BRAKE/KEEP_LANE/START可映射 | START→KEEP_LANE；复杂TURN*/CHANGE_LANE*/AVOID*/PULL_OVER/FOLLOW_ROUTE/SPEED_UP要求确认；FOLLOW/YIELD在此不支持 | [动作转换](../functions/car_control_A--high_level_command--py.md#fn-highlevelcommandadapter--runtime-fields) |
| confidence / intent_confidence | high-level都缺默认0；voice都缺拒绝 | confidence键优先，显式None不回退；有限[0,1]。DrivingCommand低置信阈值来自DEFAULT_STRATEGY，当前0.80 | [高层confidence](../functions/car_control_A--high_level_command--py.md#fn--confidence) / [voice confidence](../functions/integration--voice_adapter--py.md#fn--confidence) / [确认](../functions/car_control_A--contracts--py.md#fn-drivingcommand-requires-confirmation) |
| requires_confirmation / confirm_required | 高层两个键任一True即确认；voice读confirm_required | 必须bool；is_ambiguous也会要求确认；低置信不会因control_authorized=True消失 | [合并确认](../functions/car_control_A--high_level_command--py.md#fn--confirmation-requested) |
| target_speed_mps / parameters.speed/unit | 高层m/s；voice缺unit默认km/h | km/h除3.6，支持kph/kmh及中文斜杠单位；速度有限>=0，无本层最大车速夹取。SLOW_DOWN在A内部变SET_SPEED | [高层速度](../functions/car_control_A--high_level_command--py.md#fn--speed-parameters) / [voice速度](../functions/integration--voice_adapter--py.md#fn--speed-command-fields) |
| SLOW_DOWN相对参数 | mode=RELATIVE、action=DECELERATE且无speed | 使用voice默认2m/s，非“当前速度减固定增量” | [运行字段](../functions/integration--voice_adapter--py.md#fn-voicecommandadapter--runtime-fields) |
| status / errors / warnings / ambiguity_type | status必须valid、errors为空才能接纳；warnings不直接拒绝 | diagnostics为list，元素为文本或{code,message}；非NONE ambiguity标待确认 | [voice校验](../functions/integration--voice_adapter--py.md#fn-voicecommandadapter--adapt-validated) |
| compiled_maneuver | False，exact bool | True允许复杂intent转KEEP_LANE，PULL_OVER转STOP；本层不验证上游是否真正经过PlanValidator，依赖可信外层输入 | [运行字段](../functions/integration--voice_adapter--py.md#fn-voicecommandadapter--runtime-fields) |
| visual_valid / target_track_id | 高层False只加warning；target不透传 | 本层不是视觉安全/grounding最终门禁，target只存在上游决策时可能在转换中丢失（M03-03） | [高层adapt](../functions/car_control_A--high_level_command--py.md#fn-highlevelcommandadapter-adapt) |
| t_audio_start_ns/t_asr_end_ns/t_intent_end_ns | None或非负exact int | 仅延迟元数据；高层timestamp_ns映t_intent_end_ns；不影响仿真expires，不检查三个stamp顺序 | [voice时间](../functions/integration--voice_adapter--py.md#fn--optional-timestamp) |
| BehaviorFSM.command_timeout_s | 15秒，当前仅>0比较 | 从submit接受时刻计，confirm不重置；未独立拒绝NaN/Infinity。到期检查优先于timeout及普通完成/失败 | [构造](../functions/car_control_A--behavior_fsm--py.md#fn-behaviorfsm---init--) / [时限](../functions/car_control_A--behavior_fsm--py.md#fn-behaviorfsm--due-feedback) |
| DrivingCommand.received_at_s/expires_at_s | 必填有限非负秒，expires>=received | expires相等可构造，但到该时刻即过期；action仅非空文本，不限定枚举 | [命令契约](../functions/car_control_A--contracts--py.md#fn-drivingcommand---post-init--) |
| BehaviorFSM.confirm.approved | 调用方提供 | FSM按truthy判断；ControlRuntime.confirm_voice强制bool，审批复杂MULTIMODAL_DECISION仍失败，不能凭确认生成路线 | [confirm](../functions/car_control_A--behavior_fsm--py.md#fn-behaviorfsm-confirm) |
| command_id重复/替换 | 无TTL缓存淘汰 | 活动重复不更新payload/计时，终态重复返原反馈；新ID替换旧ID的反馈需外层收集 | [submit](../functions/car_control_A--behavior_fsm--py.md#fn-behaviorfsm-submit) |
| ManeuverFSM.replan_cooldown_s / max_replans_per_command | 2秒有限非负 / 2非负exact int | cooldown内抑制，不计数；额度满失败停车；每次start重置，非跨新计划累计预算 | [重规划](../functions/car_control_A--maneuver_fsm--py.md#fn-maneuverfsm-request-replan) |
| plan.valid_until_ns / replan_conditions | 编译计划带入 | FSM不直接读valid_until_ns；仅根据声明的PLAN_EXPIRING及snapshot.plan_expiring触发，不能混用纳秒与now_s | [原因](../functions/car_control_A--maneuver_fsm--py.md#fn-maneuverfsm--replan-reason) |
| step.timeout_s / on_failure | 编译器给出；超时严格> | REPLAN→事件；CONFIRM→终态CONFIRMING/STOP；SAFE_STOP→FAILED/STOP；其余→FAILED/KEEP_LANE | [失败策略](../functions/car_control_A--maneuver_fsm--py.md#fn-maneuverfsm--step-failure) |
| preconditions / snapshot | 10种固定前置映射，详见下层表 | 首次满足后锁存；PASS_TARGET可用target_seen；unknown条件KeyError，未做snapshot Schema校验 | [判定](../functions/car_control_A--maneuver_fsm--py.md#fn--precondition-satisfied) |
| completion.type/value/lane/hold_frames | SPEED_BELOW/REACHED、LANE_CENTERED、JUNCTION_EXITED、TARGET_GAP_REACHED、TARGET_PASSED、STOPPED、HOLD_FRAMES | 连续update次数而非frame去重；hold_condition缺省True；SLOW_DOWN+TARGET_PASSED额外速度与观察时间门禁 | [完成判定](../functions/car_control_A--maneuver_fsm--py.md#fn--completion-satisfied) / [update](../functions/car_control_A--maneuver_fsm--py.md#fn-maneuverfsm-update) |
| snapshot速度/车道容差 | speed_below .05m/s、speed_reached .6m/s、lane_center .3m、stopped .1m/s | 由snapshot可覆盖，FSM不独立校验范围；和ControlRuntime完成阈值不是同一配置 | [完整snapshot字段表](../functions/car_control_A--maneuver_fsm--py.md) |
| A契约schema_version / from_dict | 1.0；plain dict、键集完全相等 | 不可省略带构造默认的字段；拒绝未知键/非有限数/bool冒充数字；与canonical Schema独立 | [字典边界](../functions/car_control_A--contracts--py.md#fn--payload) |
| RuntimeVehicleState | frame>=0、sim_time>=0、speed>=0；位置m/yaw度有限 | 不转换坐标系；lane_id非空且保留空白；详见下方完整字段表 | [车况](../functions/car_control_A--contracts--py.md#fn-runtimevehiclestate---post-init--) |
| TrafficConstraint | SignalState实例RED/YELLOW/GREEN/UNKNOWN；距离/限速可None | None非0；from_dict枚举字符串转实例；距离与速度非负有限 | [交通](../functions/car_control_A--contracts--py.md#fn-trafficconstraint---post-init--) |
| LongitudinalRequest | requested_speed>=0、曲率可正负、traffic可None | lead_distance与closing_speed成对提供；closing=ego-lead可负，正值表示追近 | [纵向请求](../functions/car_control_A--contracts--py.md#fn-longitudinalrequest---post-init--) |
| ControlOutput / RiskMetrics / LongitudinalOutput | throttle/brake[0,1]且互斥，steer[-1,1]默认0；ttc可None | target_accel可正负，target_speed>=0；C输出不代表D最终仲裁结果 | [控制](../functions/car_control_A--contracts--py.md#fn-controloutput---post-init--) / [风险](../functions/car_control_A--contracts--py.md#fn-riskmetrics---post-init--) / [输出](../functions/car_control_A--contracts--py.md#fn-longitudinaloutput---post-init--) |
| ExecutionFeedback | 六种终态，completed_at_s非负秒，detail非空 | is_terminal恒True；无CONFIRMING/SUPERSEDED枚举；不是canonical执行中反馈 | [反馈](../functions/car_control_A--contracts--py.md#fn-executionfeedback---post-init--) |
| RouteReference | >=2点；speed>=0；route_id=None、metadata独立空dict | 只做两项浅检查，未验证点shape/有限数/曲率；metadata可变；B负责steer实现 | [route](../functions/car_control_A--routing--py.md#fn-routereference---post-init--) |
| SensorFrameBuffer.max_frames | 32个frame桶，正exact int | 同frame/sensor覆盖，超容量删最旧数值帧；消费水位前迟到回调丢弃 | [buffer](../functions/car_control_A--simulator--py.md#fn-sensorframebuffer-push) |
| pop_aligned_optional.timeout_s / optional_grace_s | timeout必填非负秒 / .01秒 | required齐后有限等待optional，总deadline封顶；成功清该帧及更旧，超时不推进水位 | [对齐](../functions/car_control_A--simulator--py.md#fn-sensorframebuffer-pop-aligned-optional) |
| SynchronousWorld.fixed_delta_seconds / TM旧状态 | .05秒；有TM时旧状态必须显式bool | enter修改world/TM，exit恢复；失败清理不应遮蔽主体异常；world首apply失败回滚范围有限 | [同步进入](../functions/car_control_A--simulator--py.md#fn-synchronousworld---enter--) / [退出](../functions/car_control_A--simulator--py.md#fn-synchronousworld---exit--) |
| CarlaSession.world / **options / tick.timeout_s | world必填；options转交同步world；timeout=None | 生命周期有外部副作用，active才允许spawn/tick；退出逆序尽力清actor再还原设置 | [session](../functions/car_control_A--simulator--py.md#fn-carlasession---init--) |
| RuntimeWatchdog.timeout_s / required_modules / startup_grace_s / started_at_s | 1秒 / () / 0 / 0 | 启动deadline=start+grace+timeout；缺required检查>=，已有所有模块心跳超时>；不是D最终安全层 | [watchdog](../functions/car_control_A--watchdog--py.md#fn-runtimewatchdog-check) |
| watchdog.pause/resume.now_s | 调用方统一秒时钟 | 暂停禁止heartbeat/check；恢复平移所有心跳和启动截止；只排除系统冻结的外部等待 | [暂停](../functions/car_control_A--watchdog--py.md#fn-runtimewatchdog-pause) / [恢复](../functions/car_control_A--watchdog--py.md#fn-runtimewatchdog-resume) |
| LatencyTrace.command_id / stage / timestamp_ns / extra | ID必填、stage任意非空、stamp默认monotonic_ns、extra=None | 禁重复stage/时间倒退；JSONL追加，extra禁覆盖核心键；不是模块2固定阶段LatencyCollector，无聚合分位数 | [trace](../functions/car_control_A--telemetry--py.md#fn-latencytrace-mark) / [写入](../functions/car_control_A--telemetry--py.md#fn-latencytrace-append-jsonl) |

### 状态迁移及实际执行分工

| 触发 | BehaviorFSM / ManeuverFSM 当前处理 | 外层需要承担 |
|---|---|---|
| 新合法命令 | BehaviorFSM终结旧活动owner，保存新owner；按确认/动作映状态 | ControlRuntime先收集旧终态、更新requested_speed和stop_hold |
| 确认 | BehaviorFSM只改状态不改原command确认字段；超时/过期优先 | ControlRuntime确认具体可执行动作后更新授权副本；复杂动作无计划仍失败 |
| 完成 | BehaviorFSM全SUCCEEDED统一STOPPED；ManeuverFSM连续计数后推进步或整计划成功 | 单步车辆完成不能提前终结原用户多步计划；物理停车看车速与stop_hold |
| 红灯等待 | ManeuverFSM重置计时、清完成计数、保持计划，safe_behavior=STOP | 真实停车由运行/交通/D链处理，建议字段不自动产生控制 |
| 等间隙→同源变道 | 继承入口前置锁存 | runner路线生成与D动态安全不能因此省略 |
| REPLAN_PENDING | 触发事件/计数，无模型调用；触发条件消失可恢复原步骤 | 当前runner只记录replan事件，未见据该事件发起新请求的消费者（M03-02） |
| on_failure建议STOP等 | safe_behavior仅当次返回，终态重复update通常不重发 | 当前runner未读取ManeuverUpdate.safe_behavior；不能据FSM单测宣称车已按建议执行 |
| watchdog返回全刹 | Watchdog自身不锁存，补心跳可恢复 | ControlRuntime另有故障锁存/复位；排查长路线停住必须同时看两层 |

ControlRuntime自身SET_SPEED完成阈值为误差<=0.25m/s连续3帧，KEEP_LANE为3个完成检查帧，停车阈值来自fuzzy_policy.config.standstill_speed_mps；这些不等于ManeuverFSM默认0.6/0.1。来源见[模块1 runtime记录](../functions/integration--runtime_loop--py.md)，本模块仅核对接线，不重复修改模块1实现。

### 示例与历史说明的适用范围

| 资源 | 当前内容/实际结果 |
|---|---|
| [qwen_set_speed_20.json](../../../car_control_A/examples/qwen_set_speed_20.json) | action SET_SPEED，5.5555555556m/s，confidence .95、TTL30s，经两个Adapter转A SET_SPEED |
| [qwen_slow_down.json](../../../car_control_A/examples/qwen_slow_down.json) | SLOW_DOWN，2m/s、.94、TTL3s；最终A action为SET_SPEED |
| [qwen_keep_lane.json](../../../car_control_A/examples/qwen_keep_lane.json) | KEEP_LANE，.9、TTL3s；没有目标速度，不等于自动设置巡航速度 |
| [qwen_change_lane_rejected.json](../../../car_control_A/examples/qwen_change_lane_rejected.json) | CHANGE_LANE_LEFT，.82、TTL3s；高层adapt实际status=valid且要求确认，voice转MULTIMODAL_DECISION；文件名rejected不等于adapter立即REJECTED |
| [A README](../../../car_control_A/README.md) | 7月演示基线，列出的5种终态漏当前SAFETY_OVERRIDE；“未来决策模块”不涵盖当前canonical planner_v2；提到的command_adapter.py当前已不存在，不应按它寻找入口 |
| [A RUN](../../../car_control_A/RUN.md) | 保留历史环境命令，CARLA_SMOKE=1一行是POSIX shell语法，不能直接当PowerShell赋值；烟测需真实服务，历史147 passed等不是本轮结果 |

完整参数类型/默认声明仍见本页下方及逐文件页。新发现M03-01–M03-03和验证证据见[审计台账](../AUDIT.md)，业务未修复。此模块文档精读完成不等于重规划、目标传播等链路没有缺口。

## 模块接口与参数核对（2026-09-20）

VoiceCommandAdapter负责外部envelope到A内部命令；BehaviorFSM处理授权、确认、超时与终态，ManeuverFSM处理步骤前置条件、完成/失败和重规划。A DrivingCommand的received_at_s/expires_at_s是内部秒时钟，不直接等同于JSON纳秒deadline。

### 参数语义与生效边界

LongitudinalRequest.requested_speed_mps为请求速度；traffic、lead_distance_m、closing_speed_mps均可缺失。DrivingCommand.target_speed_mps=None不是0速；confirmation_requested与is_ambiguous必须保留，不能丢掉后执行。

### 上下游与修改影响

ExecutionFeedback.completed_at_s/ExecutionStatus需经adapter映射到跨进程协议。新增意图要查语音、canonical、模型、编译器、状态机和验收；新增内部步骤需保留source_step身份。

### [car_control_A/contracts.py](../../../car_control_A/contracts.py) 的入口与声明

```python
RuntimeVehicleState.to_dict(self) -> dict[str, object]
RuntimeVehicleState.from_dict(cls, payload: object) -> RuntimeVehicleState
DrivingCommand.is_expired_at(self, sim_time_s: float) -> bool
DrivingCommand.requires_confirmation(self) -> bool
DrivingCommand.to_dict(self) -> dict[str, object]
DrivingCommand.from_dict(cls, payload: object) -> DrivingCommand
TrafficConstraint.to_dict(self) -> dict[str, object]
TrafficConstraint.from_dict(cls, payload: object) -> TrafficConstraint
LongitudinalRequest.to_dict(self) -> dict[str, object]
LongitudinalRequest.from_dict(cls, payload: object) -> LongitudinalRequest
ControlOutput.to_dict(self) -> dict[str, object]
ControlOutput.from_dict(cls, payload: object) -> ControlOutput
RiskMetrics.to_dict(self) -> dict[str, object]
RiskMetrics.from_dict(cls, payload: object) -> RiskMetrics
LongitudinalOutput.to_dict(self) -> dict[str, object]
LongitudinalOutput.from_dict(cls, payload: object) -> LongitudinalOutput
ExecutionFeedback.is_terminal(self) -> bool
ExecutionFeedback.to_dict(self) -> dict[str, object]
ExecutionFeedback.from_dict(cls, payload: object) -> ExecutionFeedback
```

类级字段（含配置、输入输出和内部状态；仅声明默认，不是当前run生效配置）：

| 字段 | 类型 | 默认值/来源 |
|---|---|---|
| `RuntimeVehicleState.frame` | `int` | `无声明默认（构造/赋值方提供）` |
| `RuntimeVehicleState.sim_time_s` | `float` | `无声明默认（构造/赋值方提供）` |
| `RuntimeVehicleState.speed_mps` | `float` | `无声明默认（构造/赋值方提供）` |
| `RuntimeVehicleState.x_m` | `float` | `无声明默认（构造/赋值方提供）` |
| `RuntimeVehicleState.y_m` | `float` | `无声明默认（构造/赋值方提供）` |
| `RuntimeVehicleState.z_m` | `float` | `无声明默认（构造/赋值方提供）` |
| `RuntimeVehicleState.yaw_deg` | `float` | `无声明默认（构造/赋值方提供）` |
| `RuntimeVehicleState.lane_id` | `str` | `无声明默认（构造/赋值方提供）` |
| `DrivingCommand.command_id` | `str` | `无声明默认（构造/赋值方提供）` |
| `DrivingCommand.received_at_s` | `float` | `无声明默认（构造/赋值方提供）` |
| `DrivingCommand.expires_at_s` | `float` | `无声明默认（构造/赋值方提供）` |
| `DrivingCommand.confidence` | `float` | `无声明默认（构造/赋值方提供）` |
| `DrivingCommand.action` | `str` | `无声明默认（构造/赋值方提供）` |
| `DrivingCommand.target_speed_mps` | `float &#124; None` | `None` |
| `DrivingCommand.is_ambiguous` | `bool` | `False` |
| `DrivingCommand.confirmation_requested` | `bool` | `False` |
| `TrafficConstraint.signal_state` | `SignalState` | `无声明默认（构造/赋值方提供）` |
| `TrafficConstraint.distance_to_stop_line_m` | `float &#124; None` | `无声明默认（构造/赋值方提供）` |
| `TrafficConstraint.speed_limit_mps` | `float &#124; None` | `None` |
| `LongitudinalRequest.vehicle` | `RuntimeVehicleState` | `无声明默认（构造/赋值方提供）` |
| `LongitudinalRequest.requested_speed_mps` | `float` | `无声明默认（构造/赋值方提供）` |
| `LongitudinalRequest.path_curvature_per_m` | `float` | `无声明默认（构造/赋值方提供）` |
| `LongitudinalRequest.traffic` | `TrafficConstraint &#124; None` | `None` |
| `LongitudinalRequest.lead_distance_m` | `float &#124; None` | `None` |
| `LongitudinalRequest.closing_speed_mps` | `float &#124; None` | `None` |
| `ControlOutput.throttle` | `float` | `无声明默认（构造/赋值方提供）` |
| `ControlOutput.brake` | `float` | `无声明默认（构造/赋值方提供）` |
| `ControlOutput.steer` | `float` | `0.0` |
| `RiskMetrics.ttc_s` | `float &#124; None` | `无声明默认（构造/赋值方提供）` |
| `RiskMetrics.desired_gap_m` | `float` | `无声明默认（构造/赋值方提供）` |
| `RiskMetrics.emergency_brake_requested` | `bool` | `无声明默认（构造/赋值方提供）` |
| `LongitudinalOutput.control` | `ControlOutput` | `无声明默认（构造/赋值方提供）` |
| `LongitudinalOutput.target_accel_mps2` | `float` | `无声明默认（构造/赋值方提供）` |
| `LongitudinalOutput.target_speed_mps` | `float` | `无声明默认（构造/赋值方提供）` |
| `LongitudinalOutput.state` | `str` | `无声明默认（构造/赋值方提供）` |
| `LongitudinalOutput.reason` | `str` | `无声明默认（构造/赋值方提供）` |
| `LongitudinalOutput.risk` | `RiskMetrics` | `无声明默认（构造/赋值方提供）` |
| `ExecutionFeedback.command_id` | `str` | `无声明默认（构造/赋值方提供）` |
| `ExecutionFeedback.status` | `ExecutionStatus` | `无声明默认（构造/赋值方提供）` |
| `ExecutionFeedback.completed_at_s` | `float` | `无声明默认（构造/赋值方提供）` |
| `ExecutionFeedback.detail` | `str` | `无声明默认（构造/赋值方提供）` |

### [car_control_A/behavior_fsm.py](../../../car_control_A/behavior_fsm.py) 的入口与声明

```python
BehaviorFSM.__init__(self, *, command_timeout_s: float=15.0) -> None
BehaviorFSM.state(self) -> BehaviorState
BehaviorFSM.submit(self, command: DrivingCommand, *, now_s: float) -> BehaviorResult
BehaviorFSM.confirm(self, command_id: str, *, approved: bool, now_s: float) -> BehaviorResult
BehaviorFSM.complete(self, command_id: str, *, now_s: float, detail: str) -> ExecutionFeedback | None
BehaviorFSM.fail(self, command_id: str, *, now_s: float, detail: str) -> ExecutionFeedback | None
BehaviorFSM.safety_override(self, command_id: str, *, now_s: float, detail: str) -> ExecutionFeedback | None
BehaviorFSM.tick(self, *, now_s: float) -> tuple[ExecutionFeedback, ...]
```

类级字段（含配置、输入输出和内部状态；仅声明默认，不是当前run生效配置）：

| 字段 | 类型 | 默认值/来源 |
|---|---|---|
| `BehaviorResult.state` | `BehaviorState` | `无声明默认（构造/赋值方提供）` |
| `BehaviorResult.feedback` | `ExecutionFeedback &#124; None` | `None` |

### [car_control_A/maneuver_fsm.py](../../../car_control_A/maneuver_fsm.py) 的入口与声明

```python
ManeuverFSM.__init__(self, *, replan_cooldown_s: float=2.0, max_replans_per_command: int=2) -> None
ManeuverFSM.current_step(self) -> CompiledPlanStep | None
ManeuverFSM.replan_count(self) -> int
ManeuverFSM.start(self, plan: CompiledManeuverPlan, *, now_s: float) -> ManeuverUpdate
ManeuverFSM.update(self, snapshot: Mapping[str, Any], *, now_s: float) -> ManeuverUpdate
ManeuverFSM.request_replan(self, reason_code: str, *, now_s: float) -> ManeuverUpdate
ManeuverFSM.fail(self, reason_code: str, *, now_s: float) -> ManeuverUpdate
```

类级字段（含配置、输入输出和内部状态；仅声明默认，不是当前run生效配置）：

| 字段 | 类型 | 默认值/来源 |
|---|---|---|
| `ManeuverEvent.event_type` | `str` | `无声明默认（构造/赋值方提供）` |
| `ManeuverEvent.command_id` | `str` | `无声明默认（构造/赋值方提供）` |
| `ManeuverEvent.plan_id` | `str` | `无声明默认（构造/赋值方提供）` |
| `ManeuverEvent.step_id` | `str &#124; None` | `无声明默认（构造/赋值方提供）` |
| `ManeuverEvent.state` | `str` | `无声明默认（构造/赋值方提供）` |
| `ManeuverEvent.reason_code` | `str` | `无声明默认（构造/赋值方提供）` |
| `ManeuverEvent.now_s` | `float` | `无声明默认（构造/赋值方提供）` |
| `ManeuverUpdate.state` | `str` | `无声明默认（构造/赋值方提供）` |
| `ManeuverUpdate.current_step` | `CompiledPlanStep &#124; None` | `无声明默认（构造/赋值方提供）` |
| `ManeuverUpdate.events` | `tuple[ManeuverEvent, ...]` | `无声明默认（构造/赋值方提供）` |
| `ManeuverUpdate.safe_behavior` | `str &#124; None` | `无声明默认（构造/赋值方提供）` |
| `ManeuverUpdate.terminal` | `bool` | `无声明默认（构造/赋值方提供）` |

以上为核心交接入口；模块内其余实现、CLI和资源的完整字段/拒绝条件见本页功能小文档索引。类型未声明的返回值不凭名称推断。当前代码基线fe1ba839，静态复核不证明实际CARLA/GPU/板端运行成功。

## Complete implementation inventory

- [car_control_A/__init__.py](../../../car_control_A/__init__.py) - module/resource/documentation
- [car_control_A/ARCHITECTURE.md](../../../car_control_A/ARCHITECTURE.md) - module/resource/documentation
- [car_control_A/behavior_fsm.py](../../../car_control_A/behavior_fsm.py) - `BehaviorState`, `BehaviorResult`, `_ActiveCommand`, `BehaviorFSM`, `BehaviorFSM.state`, `BehaviorFSM.submit`, `BehaviorFSM.confirm`, `BehaviorFSM.complete`, `BehaviorFSM.fail`, `BehaviorFSM.safety_override`, `BehaviorFSM.tick`
- [car_control_A/contracts.py](../../../car_control_A/contracts.py) - `_number`, `_integer`, `_text`, `_boolean`, `_payload`, `SignalState`, `RuntimeVehicleState`, `RuntimeVehicleState.to_dict`, `RuntimeVehicleState.from_dict`, `DrivingCommand`, `DrivingCommand.is_expired_at`, `DrivingCommand.requires_confirmation`, `DrivingCommand.to_dict`, `DrivingCommand.from_dict`, `TrafficConstraint`, `TrafficConstraint.to_dict`, `TrafficConstraint.from_dict`, `LongitudinalRequest`, `LongitudinalRequest.to_dict`, `LongitudinalRequest.from_dict`, `ControlOutput`, `ControlOutput.to_dict`, `ControlOutput.from_dict`, `RiskMetrics`, `RiskMetrics.to_dict`, `RiskMetrics.from_dict`, `LongitudinalOutput`, `LongitudinalOutput.to_dict`, `LongitudinalOutput.from_dict`, `ExecutionStatus`, `ExecutionFeedback`, `ExecutionFeedback.is_terminal`, `ExecutionFeedback.to_dict`, `ExecutionFeedback.from_dict`
- [car_control_A/examples/qwen_change_lane_rejected.json](../../../car_control_A/examples/qwen_change_lane_rejected.json) - module/resource/documentation
- [car_control_A/examples/qwen_keep_lane.json](../../../car_control_A/examples/qwen_keep_lane.json) - module/resource/documentation
- [car_control_A/examples/qwen_set_speed_20.json](../../../car_control_A/examples/qwen_set_speed_20.json) - module/resource/documentation
- [car_control_A/examples/qwen_slow_down.json](../../../car_control_A/examples/qwen_slow_down.json) - module/resource/documentation
- [car_control_A/high_level_command.py](../../../car_control_A/high_level_command.py) - `is_high_level_command`, `HighLevelCommandAdapter`, `HighLevelCommandAdapter.adapt`, `_speed_parameters`, `_direction_parameters`, `_source_text`, `_required_text`, `_optional_text`, `_safe_text`, `_confidence`, `_bounded_confidence`, `_nonnegative_number`, `_positive_number`, `_optional_timestamp`, `_optional_timestamp_lenient`, `_confirmation_requested`
- [car_control_A/maneuver_fsm.py](../../../car_control_A/maneuver_fsm.py) - `ManeuverEvent`, `ManeuverUpdate`, `ManeuverFSM`, `ManeuverFSM.current_step`, `ManeuverFSM.replan_count`, `ManeuverFSM.start`, `ManeuverFSM.update`, `ManeuverFSM.request_replan`, `ManeuverFSM.fail`, `_time`, `_precondition_satisfied`, `_completion_satisfied`
- [car_control_A/README.md](../../../car_control_A/README.md) - module/resource/documentation
- [car_control_A/routing.py](../../../car_control_A/routing.py) - `RouteReference`, `LateralController`, `LateralController.steer`
- [car_control_A/RUN.md](../../../car_control_A/RUN.md) - module/resource/documentation
- [car_control_A/simulator.py](../../../car_control_A/simulator.py) - `_clone_world_settings`, `SensorFrameBuffer`, `SensorFrameBuffer.pending_frames`, `SensorFrameBuffer.push`, `SensorFrameBuffer.callback`, `SensorFrameBuffer.pop_aligned`, `SensorFrameBuffer.pop_aligned_optional`, `ActorRegistry`, `ActorRegistry.track`, `ActorRegistry.release`, `ActorRegistry.cleanup`, `ActorRegistry.dispose`, `SynchronousWorld`, `SynchronousWorld.tick`, `CarlaSession`, `CarlaSession.track_actor`, `CarlaSession.tick`, `CarlaSession.spawn_ego`, `CarlaSession.attach_sensor`
- [car_control_A/telemetry.py](../../../car_control_A/telemetry.py) - `LatencyTrace`, `LatencyTrace.mark`, `LatencyTrace.segment_ms`, `LatencyTrace.end_to_end_ms`, `LatencyTrace.to_dict`, `LatencyTrace.append_jsonl`
- [car_control_A/watchdog.py](../../../car_control_A/watchdog.py) - `RuntimeWatchdog`, `RuntimeWatchdog.heartbeat`, `RuntimeWatchdog.pause`, `RuntimeWatchdog.resume`, `RuntimeWatchdog.check`, `RuntimeWatchdog.module_failed`
- [integration/voice_adapter.py](../../../integration/voice_adapter.py) - `VoiceDiagnostic`, `VoiceCommandMetadata`, `AdaptedVoiceCommand`, `VoiceCommandAdapter`, `VoiceCommandAdapter.adapt`, `_speed_command_fields`, `_required_text`, `_nonnegative_number`, `_positive_number`, `_confidence`, `_optional_bool`, `_diagnostic_tuple`, `_diagnostic_tuple_lenient`, `_safe_text`, `_optional_timestamp`, `_optional_timestamp_lenient`

## Dependencies and coordinated changes

上游[模块2异步规划](vehicle-planner.md)交付已验证/编译计划及内部步骤envelope，[模块16语音](support-voice.md)交付voice协议；运行驱动由[模块1](vehicle-entry.md)负责。RouteReference接[模块4横向](vehicle-lateral.md)，LongitudinalRequest/Output接[模块5纵向](vehicle-longitudinal.md)，实际控制交[模块7安全](vehicle-safety.md)。修改动作/确认字段需检查两个Adapter、BehaviorFSM、ControlRuntime和D；修改步骤条件需检查Schema→Validator→Compiler→ManeuverFSM→runner snapshot→验收，不能仅新增枚举。


## Validation entry points

`python -m pytest car_control_A/tests integration/tests/test_voice_adapter.py integration/tests/test_voice_compound_routing.py integration/tests/test_voice_qwen_semantic_coverage.py`

Run from the worktree root. Listed commands are relevant checks, not claims that tests were executed. CARLA, remote-model and hardware acceptance require their actual environments and run manifests.

## 功能小文档完整索引

以下功能页分别记录实现入口、输入输出声明、内部调用、异常、配置和静态上下游；测试文件保留在源码索引中。

- [car_control_A/__init__.py](../functions/car_control_A--__init__--py.md)
- [car_control_A/behavior_fsm.py](../functions/car_control_A--behavior_fsm--py.md)
- [car_control_A/contracts.py](../functions/car_control_A--contracts--py.md)
- [car_control_A/high_level_command.py](../functions/car_control_A--high_level_command--py.md)
- [car_control_A/maneuver_fsm.py](../functions/car_control_A--maneuver_fsm--py.md)
- [car_control_A/routing.py](../functions/car_control_A--routing--py.md)
- [car_control_A/simulator.py](../functions/car_control_A--simulator--py.md)
- [car_control_A/telemetry.py](../functions/car_control_A--telemetry--py.md)
- [car_control_A/watchdog.py](../functions/car_control_A--watchdog--py.md)
- [integration/voice_adapter.py](../functions/integration--voice_adapter--py.md)

## 诊断与维护交接

本模块证据：授权、step、feedback、terminal原因；单步成功不等于任务完成。功能实现与上下游见本页原索引；跨模块回查[追踪矩阵](../TRACEABILITY.md)与[诊断入口](../DIAGNOSIS.md)。实际run必须核对版本，未执行的检查不视为已通过。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `car_control_A/tests/test_ac_integration.py`

来源 SHA256：`1151052543e8735a3af5ed653f56e206f63a9ccc5095344bbb1756602a212796`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `car_control_A/tests/test_behavior_fsm.py`

来源 SHA256：`fc85a3fc22b65a40e479ae54ea2763195f41d2cb2cf716d61652183416355230`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `car_control_A/tests/test_contracts.py`

来源 SHA256：`2e545d58d2c7de079f5df165255bd1b1714d91f3ca402c7bfc48d21514bf66c2`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `car_control_A/tests/test_high_level_command.py`

来源 SHA256：`be9afb03bfdd979db698bf66eb92174990e81070fbeb79dd86afe7038a9a1c89`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `car_control_A/tests/test_maneuver_fsm.py`

来源 SHA256：`a6c27950fa22c1891f0fd9032cf4a5b0b532053d2bf27723204e2914b3d9bb26`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `car_control_A/tests/test_routing.py`

来源 SHA256：`f6c7557a6f03fa53210de0554740f1868cdd13247c4173d292226ee39a1afe3c`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `car_control_A/tests/test_simulator.py`

来源 SHA256：`a9ee20724d0ee7c6361817727c90197c34b75d06dd0bfbd5592b689d60fe9b39`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `test_world_settings_restore_even_if_traffic_manager_restore_fails.FailingRestoreTrafficManager.set_synchronous_mode` / 88 | `enabled is False` | `raise RuntimeError('TM unavailable')` |
| `test_world_and_tm_restore_when_tm_enable_changes_state_then_raises.FailingEnableTrafficManager.set_synchronous_mode` / 104 | `enabled is True` | `raise RuntimeError('TM enabled then failed')` |
| `test_exit_clears_sync_state_when_world_restore_raises_and_preserves_business_error` / 143 | `本地无直接if；检查上下文` | `raise ValueError('business failure')` |
| `test_exit_clears_sync_state_when_world_restore_raises_and_preserves_business_error.FailingRestoreWorld.apply_settings` / 124 | `self.fail_restore` | `raise RuntimeError('restore failed')` |
| `test_attach_sensor_validates_before_spawn_and_immediately_releases_listen_failure.FailingSensor.listen` / 203 | `本地无直接if；检查上下文` | `raise RuntimeError('listen failed')` |
| `test_actor_registry_cleans_every_actor_when_one_destroy_fails.BrokenActor.destroy` / 231 | `本地无直接if；检查上下文` | `raise RuntimeError('network lost')` |
### `car_control_A/tests/test_simulator_smoke.py`

来源 SHA256：`54219e701114d4817cf90fceaad22fa2fde63bc8e486e1861517539c8c8e38cb`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
### `car_control_A/tests/test_telemetry.py`

来源 SHA256：`183be80c6f2f9996d113ab72da98f63c8dcf18bc5e04d1e55a33e73ad41b1ac2`。


显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `test_trace_rejects_non_monotonic_and_duplicate_stage` / 27 | `本地无直接if；检查上下文` | `raise AssertionError('expected duplicate stage rejection')` |
| `test_trace_rejects_non_monotonic_and_duplicate_stage` / 33 | `本地无直接if；检查上下文` | `raise AssertionError('expected non-monotonic rejection')` |
### `car_control_A/tests/test_watchdog.py`

来源 SHA256：`aef4d6383111acfe32ae67dd35b3b465b4767f6bf18f795bfce7e6356effcef2`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。

### 环境参数读取位置

这里只记录源码表达式，不读取当前进程环境；缓存与覆盖关系需查调用时机。

| 来源/行 | 环境变量表达式 | 源码fallback |
|---|---|---|
| `car_control_A/tests/test_simulator_smoke.py:10` | `'CARLA_SMOKE'` | `None（未传默认）` |
