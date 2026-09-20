# Model planning and async contracts

## 开发维护先读：实际语义

以下功能页说明实现理由、分支、接口含义、改动联动与验证。先读这些内容，再按逐文件索引定位方法；不要用函数名推断业务语义。

- [异步等待、旧结果拒绝与多层命令ID](../functions/async-plan-dispatch.md)
- [计划可行性校验与内部步骤展开](../functions/plan-validation-compilation.md)

[Vehicle module](../modules/vehicle.md)

## Responsibility, contracts and failure behavior

PipelineOrchestrator validates DrivingCommand/PerceptionState, dispatches bounded worker requests and rejects expired/superseded results. atomic_v1 produces DecisionPlan; planner_v2 produces ManeuverPlan validated and compiled by PlanValidator/PlanCompiler. CanonicalRuntimeBridge installs STOP while waiting and maps validated output to vehicle envelopes. command_id, deadline_ns, confidence, target IDs and model timing connect the stages. Remote clients, image staging, profiles and fault injection must preserve the same authority boundary.


## 第2模块逐入口精读：链路、参数索引与限制

本轮以工作树源码 `fe1ba839` 为基线，覆盖本页列出的 **21 个实现文件**，替换19份逐文件页的189处占位，另外2份无占位页补充实际转换/导出边界。下方链接直达方法说明，参数类型和完整签名仍保留在逐文件页；此处区分默认值、消费方和运行约束，不能用文档默认替代 run manifest。

### 先选对请求协议

| 链路 | 请求→响应 | 时限与实际接线 |
|---|---|---|
| canonical，runner `--qwen-service-url` | DrivingCommand+PerceptionState→ModelRequest→atomic_v1 DecisionPlan / planner_v2 ManeuverPlan→ControlCommand→车辆envelope | runner导入 **qwen_service.client.QwenServiceClient**；Orchestrator负责300ms默认模型预算，HTTP实际超时由runner设为max(0.1,模型预算秒数+0.05) |
| 旧版remote/本地VL | QwenInputContext→严格高层action→HighLevelCommandAdapter→车辆envelope | AsyncQwenDecisionBridge；推理wall超时、仿真时间TTL和车辆命令TTL三者独立 |
| integration HTTP封装 | QwenInputContext→`{status: READY, request_id, decision}`→高层action | **integration.qwen_service_client.QwenServiceClient**，默认5s；不能代替上行canonical客户端，即使类名和`/infer`路径相同 |

canonical客户端的细节见[服务客户端逐文件页](../functions/qwen_service--client--py.md)（归模块17）；本轮只核对跨模块接线，不把模块17标为精读完成。canonical图片在worker经 request_transform 编码；同名 integration 客户端没有该参数。

### 配置参数索引：默认、单位、约束和消费位置

| 参数/数据 | 默认值或来源 | 实际作用与边界 | 精确入口 |
|---|---|---|---|
| config.qwen_queue_size / sensor_queue_size / log_queue_size | 1 / 4 / 1024；正整数 | 等待模型请求、感知、日志队列独立；满时最新项替换旧项，模型被挤出项有QUEUE_OVERFLOW反馈；已执行请求不取消 | [Config](../functions/runtime--orchestrator--py.md#fn-orchestratorconfig---post-init--)、[入队](../functions/runtime--orchestrator--py.md#fn-pipelineorchestrator--put-latest) |
| config.model_timeout_ms | 300.0 ms，有限正数 | 请求deadline上界和active超时预算；包含排队/预处理等待，不是HTTP的timeout_s | [请求构造](../functions/runtime--orchestrator--py.md#fn-pipelineorchestrator--model-request)、[poll](../functions/runtime--orchestrator--py.md#fn-pipelineorchestrator-poll-slow) |
| minimum_confidence | config/router/validator各默认0.8 | 存在三个可独立构造的来源；编排结果低于阈值或requires_confirmation拒绝，不应只调router | [配置](../functions/runtime--orchestrator--py.md#fn-orchestratorconfig)、[路由](../functions/runtime--complexity_router--py.md#fn-complexityrouter---init--)、[校验](../functions/runtime--plan_validator--py.md#fn-planvalidator---init--) |
| max_speed_mps / max_accel_mps2 / max_decel_mps2 | 13.8888888889 m/s / 2.5 m/s² / 5.0 m/s² | 有限正值，写入request.limits；速度结合场景限速；不是最终油门/制动值 | [limits](../functions/runtime--orchestrator--py.md#fn-pipelineorchestrator--limits) |
| stop_line_guard_m | 8.0 m，有限正数 | 停止线/信号安全判断阈值，与感知状态合用 | [停车判断](../functions/runtime--orchestrator--py.md#fn-pipelineorchestrator--perception-stop-reason) |
| top_k_targets | 8，正整数 | 请求目标按distance、负confidence、track_id排序截取；相对纵向速度由对象velocity_x取负 | [请求](../functions/runtime--orchestrator--py.md#fn-pipelineorchestrator--model-request) |
| qwen_mode / allowed_slow_behaviors | atomic_v1；11项支持行为元组见下方字段表 | mode只允许atomic_v1/planner_v2，行为集非空不重复且支持；具体请求还按命令/路由缩窄 | [行为权限](../functions/runtime--orchestrator--py.md#fn-pipelineorchestrator--allowed-model-behaviors) |
| infer / registry / router / validator / compiler | infer可None，其余可省略构造默认对象 | inferNone时无法产生模型计划；初始化启动单daemon worker；注入组件须保持Schema/阈值一致 | [构造](../functions/runtime--orchestrator--py.md#fn-pipelineorchestrator---init--) |
| clock_ns / now_ns / wait_timeout_ms | monotonic_ns / None / 0.0 ms | 支持调用方时间域；poll默认不阻塞，等待后处理结果；不能混用wall秒和仿真秒 | [poll](../functions/runtime--orchestrator--py.md#fn-pipelineorchestrator-poll-slow) |
| close.timeout_s | 1.0 s | 限时join线程，不中止已进入的HTTP/模型调用 | [close](../functions/runtime--orchestrator--py.md#fn-pipelineorchestrator-close) |
| command_id / request_id / plan_id / source_step_id | 调用方命令、编排请求、模型计划、编译源步骤 | 不能合并：用户任务、一次模型调用、计划与展开步骤各有身份 | [bridge poll](../functions/integration--second_group_runtime--py.md#fn-canonicalruntimebridge-poll)、[compiler](../functions/runtime--plan_compiler--py.md#fn-plancompiler-compile) |
| runtime_state / grounded_target_ids / rgb_ref | submit可选，grounding来自场景/调用方 | 缓存提交时scene与grounding；rgb_ref是模型可解析引用，不是图像字节或任意远端路径 | [submit](../functions/runtime--orchestrator--py.md#fn-pipelineorchestrator-submit-command) |
| canonical voice TTL / speed | 无效TTL回退3s；旧speed默认km/h | SI目标速度优先；旧单位换算、置信度夹取和FOLLOW保留见转换；转换不是原输入严格校验 | [voice转换](../functions/integration--canonical_bridge--py.md#fn-voice-envelope-to-driving-command) |
| canonical perception缺省 | distance=50m；部分速度缺失补0 | 包含bbox近似投影，不是完整测量融合；传入stale/sync标志不等于在转换层检查过传感器 | [perception转换](../functions/integration--canonical_bridge--py.md#fn-perception-frame-to-state) |
| 等待envelope TTL / V2执行TTL | 等待3s；V2至少各编译步timeout之和+1s | 等待独立UUID；执行首步用内部ID，由FSM保有用户命令生命周期 | [安全等待](../functions/integration--second_group_runtime--py.md#fn-canonicalruntimebridge--pending-safety-envelope)、[poll](../functions/integration--second_group_runtime--py.md#fn-canonicalruntimebridge-poll) |
| validator.maximum_speed_mps / minimum_confidence / allow_confirmation | 13.8888888889 / 0.8 / False | 速度/置信度约束；允许确认仅容许计划保留该标志，不代表车辆已确认 | [validate](../functions/runtime--plan_validator--py.md#fn-planvalidator-validate) |
| expected_request_id / expected_command_id / now_ns | None / None /时钟 | 指定身份则核对；now>=valid_until_ns过期；worker传提交时刻，完成时再由编排器检查 | [validate](../functions/runtime--plan_validator--py.md#fn-planvalidator-validate) |
| preconditions / completion / timeout_s / on_failure | 每个模型步骤必备，Schema与载荷定义 | 校验可观测性与字段约束；前置条件为False不必然拒绝，应由FSM等待。Compiler保留或按展开规则设置内部条件 | [前置校验](../functions/runtime--plan_validator--py.md#fn-planvalidator--validate-preconditions)、[完成校验](../functions/runtime--plan_validator--py.md#fn-planvalidator--validate-completion) |
| AVOID默认速度 / 内部等待 | 未指定3m/s；具体步timeout/hold由compiler派生 | 展开降速→等待间隙→变道→通过目标；模型1–4步不限制编译后总步数 | [avoid](../functions/runtime--plan_compiler--py.md#fn-plancompiler--compile-avoid)、[return](../functions/runtime--plan_compiler--py.md#fn-plancompiler--compile-return) |
| ComplexityRouter.qwen_score | 3，正整数 | 复杂度规则阈值；CONFIRM_SAFE也调用Qwen一次；安全等待建议与实际bridge STOP分开 | [decide](../functions/runtime--complexity_router--py.md#fn-complexityrouter-decide) |
| AsyncQwenDecisionBridge.ttl_s / max_inference_s / command_ttl_s | 3仿真秒 / 5墙钟秒 / 30秒 | READY以age>ttl过期；模型超时从submit计时；后二者有限正数，ttl检查未拒绝NaN/Infinity | [旧bridge](../functions/integration--qwen_async--py.md#fn-asyncqwendecisionbridge---init--)、[latest](../functions/integration--qwen_async--py.md#fn-asyncqwendecisionbridge-latest) |
| QwenInputContext | request_id/frame/sim_time_s/voice_command/rgb_ref/scene_state/perception/safety_state均由调用方给出 | 非负帧/有限非负秒；三映射检查JSON但只顶层只读，不是深快照 | [构造校验](../functions/integration--qwen_boundary--py.md#fn-qweninputcontext---post-init--) |
| build_high_level_command.valid_duration_s / command_id | 3s / None生成qwen_UUID8 | 仅5种高层action；可选track保留，速度仅SET_SPEED/SLOW_DOWN带出 | [命令转换](../functions/integration--qwen_command_adapter--py.md#fn-build-high-level-command) |
| image_root / ref_prefix / frame_id | root必填；artifacts/qwen_live；frame必填 | runner覆盖prefix为自己的CLI配置；measurement先缓存引用，worker消费；不在stage校验实际measurement.frame | [图像构造](../functions/integration--qwen_image_stager--py.md#fn-qwenimagestager---init--)、[消费](../functions/integration--qwen_image_stager--py.md#fn-qwenimagestager-prepare-request) |
| 图像编码常量 | 单图224×224；四图112×112各一块；JPEG75 | 四图键为rgb_front/rgb_left/rgb_right/rgb_rear，排布front/left、right/rear；消费先pop，写失败不会自动保留重试 | [stage_multiview](../functions/integration--qwen_image_stager--py.md#fn-qwenimagestager-stage-multiview) |
| QwenPlannerV2Adapter.generate / infer.routing / infer.scene | generate必填；routing/scene为infer必填关键字 | generate(prompt,rgb_ref)返回文本/bytes/映射；infer返回PlannerV2Result而非dict；摘要<=512字符 | [adapter](../functions/integration--qwen_plan_adapter--py.md#fn-qwenplannerv2adapter-infer) |
| profile / QWEN_PROFILE | 默认qwen3vl-2b-int4；可选qwen3vl-2b-fp8 | 两者image_max_side256、visual_tokens64、port8001、prompt compact-v2；完整model/revision在逐文件源码字段记录，不能替代Teacher身份 | [profile选择](../functions/integration--qwen_profiles--py.md#fn-resolve-qwen-profile) |
| remote base_url / api_key / timeout_s / max_tokens / jpeg_quality / client | URL必填 / local-offline / 30s / 1 / 75 / None | max_tokens必须1，JPEG1–95；model及image_max_side须匹配profile；默认OpenAI无重试；返回A–E动作码概率 | [remote](../functions/integration--qwen_remote_backend--py.md#fn-openaicompatibleqwenvlbackend---init--) |
| StrictQwenVLAdapter.backend / image_root | backend必填 / None | generate(prompt,image_path)或generate_action(prompt,image_path,context)；后者优先；配置根目录时路径须在根内且存在 | [strict infer](../functions/integration--qwen_vl_adapter--py.md#fn-strictqwenvladapter-infer)、[路径](../functions/integration--qwen_vl_adapter--py.md#fn-strictqwenvladapter--resolve-image) |
| assemble_action_choice.confidence_threshold / 显式速度grounding | 0.60 / grounding置信度至少0.90 | 先安全/置信度/视觉/目标门禁，再允许C纠正为SET_SPEED；与canonical0.8阈值分开 | [动作组装](../functions/integration--qwen_vl_adapter--py.md#fn-assemble-action-choice) |
| 显式目标匹配阈值 | 检测confidence<0.5过滤；约定距离±2m；最近候选±0.25m | 缺confidence不自动过滤；候选唯一才本地补正track，None表示规则不适用，空list表示目标未找到 | [候选](../functions/integration--qwen_vl_adapter--py.md#fn--explicit-target-candidates)、[grounding](../functions/integration--qwen_vl_adapter--py.md#fn--ground-explicit-target) |
| 本地VL max_new_tokens / device_map / torch_dtype / awq_backend | 48 / auto / auto / auto | AWQ枚举auto/torch_awq/gemm/gemm_triton；显式backend要求AWQ checkpoint；构造即本地加载 | [本地后端](../functions/integration--qwen_vl_adapter--py.md#fn-transformersqwen25vlbackend---init--) |
| 本地VL min_pixels / max_pixels / crop_top_ratio / crop_bottom_ratio | 50176 / 50176 / .04 / .08 | min>=784且max>=min；各crop[0,.5)且和<.5；速度单位与图像crop无关 | [本地后端](../functions/integration--qwen_vl_adapter--py.md#fn-transformersqwen25vlbackend---init--) |
| integration客户端 base_url / timeout_s | URL必填 / 5s | HTTP(S)绝对URL无query/fragment，timeout有限正数；响应必须READY且同request_id | [旧HTTP客户端](../functions/integration--qwen_service_client--py.md#fn-qwenserviceclient-infer) |
| fault.type / delay_ms / command_index / trigger.time_s / duration_s | type必填；延迟型需正delay_ms；index可选；start0、duration∞ | index优先于时间窗；缺命令时间按0；支持TIMEOUT、LOW_LEVEL_FIELD、QWEN_RESPONSE_DELAY、QWEN_COMMAND_DELAY、QWEN_INVALID_TOKEN、QWEN_SERVICE_DISCONNECT | [故障构造](../functions/integration--qwen_fault_injection--py.md#fn-scenarioqwenfaultinjector---init--)、[触发](../functions/integration--qwen_fault_injection--py.md#fn-scenarioqwenfaultinjector--active-for-call) |
| qwen_expected.route / min_calls / max_calls | 必填；route两枚举，0<=min<=max | expected_behaviors默认空集合；expected_terminal缺失则终态检查不通过；expected_terminal_reason_prefix默认空；allowed_replans默认0 | [场景监控](../functions/integration--qwen_scenario_monitor--py.md#fn-qwenscenariomonitor-finalize) |
| InterfaceRegistry.root / warm.names | 仓库interfaces / None预热全部7项 | 首次读Schema后缓存；validate返回严格JSON深复制；运行中改Schema不自动失效缓存 | [registry](../functions/runtime--interface_registry--py.md#fn-interfaceregistry-validate) |
| StageTrace.trace_id / path_type / clock_ns / timestamp_ns | ID/path必填，monotonic_ns，可注入stamp | 10阶段允许跳过但不允许倒序/重复；输出ms；统计count/mean/p95/p99/max包含失败样本，按path_type分组 | [mark](../functions/runtime--latency_trace--py.md#fn-stagetrace-mark)、[report](../functions/runtime--latency_trace--py.md#fn-latencycollector-report) |
| healthcheck七个CLI参数 | url8765、host127.0.0.1、port2000、timeout3s、require_qwen=False、require_carla=False、output=None | 两个require只改变门禁，不取消网络探测；仍需required依赖可导入 | [main](../functions/runtime--healthcheck--py.md#fn-main) |

### 状态与时钟：定位超时先判断发生在哪一层

| 事件 | 当前实现结果 | 必须保留的证据 |
|---|---|---|
| 合法submit | 记录SLOW_PENDING，车辆接收独立安全等待命令 | 用户command_id、request_id、等待ID、request.created_at_ns/deadline_ns |
| 等待队列满 | 淘汰最旧等待项并报告QUEUE_OVERFLOW；不取消在执行项 | 队列深度/overflow计数、被挤出请求身份 |
| active超时 | poll标记TIMED_OUT并撤销请求资格；worker仍可能被原调用占用 | submitted_wall_ns、预算、poll时刻；不能仅看active字段为空认定线程空闲 |
| worker返回晚于截止 | QWEN_STALE；已被poll撤销的迟到结果丢弃避免重复终态 | completed_wall_ns及时间域换算后的model_completed_ns |
| 及时结果迟迟未poll | 当前consume按**模型完成时间**检查deadline，不是poll当时的时间 | 不能据此宣称分发时重新校验了整个计划期限；实际调度延迟需另测 |
| 新用户命令替换 | bridge按latest_command_id拒绝旧命令的返回结果 | latest/returned command_id；编排器独立使用不等于已做这一层检查 |
| 目标可见性变化 | 编排器用提交快照校验V2各相关目标；bridge用最新帧再核对control首目标，并合并提交时grounded IDs | 提交帧、消费帧、步骤目标、actor↔track关联来源；不能声称每个后续步骤都用最新帧复核 |
| V2成功下发 | 将语义计划编译到FSM，首步内部ID不结算用户整条命令 | plan_id、source_step_id、内部step_id与用户整体终态 |

### 精读发现与修改联动

- **M02-01**：文本解析接受NaN而映射输入拒绝，独立解析器严格性不一致；后续InterfaceRegistry仍拒绝非严格JSON，不能推断已绕过完整Validator。
- **M02-02**：场景monitor的single_terminal仅遍历已有终态ID，不能证明每个路由命令都有终态；终态和原因前缀也分开匹配。报告passed不能替代完整命令生命周期核对。
- 两项纯函数复现及后续回归条件记录在[审计台账](../AUDIT.md)。不修改代码；本轮不证明CARLA、Qwen服务或GPU运行通过。
- 修改队列/timeout需覆盖等待挤出、active超时、迟到返回、新命令覆盖；修改图片路径需同时检查runner的ref_prefix、服务image_root及collector归档；修改grounding需查最新帧与提交快照两处，避免把允许的grounded ID当作实时观测。

## 模块接口与参数核对（2026-09-20）

PipelineOrchestrator连接DrivingCommand/PerceptionState与infer回调。atomic_v1输出DecisionPlan，planner_v2输出ManeuverPlan后再校验编译。OrchestrationResult同时包含disposition、reason_code、feedback及可能为空的request/plan/compiled_plan；不是每次提交都有已完成计划。

### 参数语义与生效边界

OrchestratorConfig是独立默认源：模型300ms、confidence0.8、top_k_targets8、Qwen队列1；不是Qwen HTTP客户端15s超时的同一参数。qwen_mode默认atomic_v1，不能把V2消费端直接接到V1输出。默认最大速度13.8888888889m/s参与请求limits与计划校验；实际还受场景速度限制，不能直接当作车辆当前目标速度。

### 上下游与修改影响

结果关联command_id和期限，需拒绝过期/被替换结果。修改动作需同时查Schema、Teacher构造、validator、compiler和FSM；compile后的内部步骤不一定等同于模型原步骤。

### [runtime/orchestrator.py](../../../runtime/orchestrator.py) 的入口与声明

```python
PipelineOrchestrator.__init__(self, infer: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None=None, *, config: OrchestratorConfig | None=None, registry: InterfaceRegistry | None=None, complexity_router: ComplexityRouter | None=None, plan_validator: PlanValidator | None=None, plan_compiler: PlanCompiler | None=None, clock_ns: Callable[[], int]=time.monotonic_ns) -> None
PipelineOrchestrator.submit_command(self, command: Mapping[str, Any], perception: Mapping[str, Any], *, now_ns: int | None=None, rgb_ref: str | None=None, runtime_state: Mapping[str, Any] | None=None) -> OrchestrationResult
PipelineOrchestrator.poll_slow(self, *, now_ns: int | None=None, wait_timeout_ms: float=0.0) -> tuple[OrchestrationResult, ...]
PipelineOrchestrator.publish_perception(self, payload: Mapping[str, Any]) -> bool
PipelineOrchestrator.latest_perception(self) -> dict[str, Any] | None
PipelineOrchestrator.publish_log(self, record: Mapping[str, Any]) -> bool
PipelineOrchestrator.drain_logs(self, *, maximum: int | None=None) -> tuple[dict[str, Any], ...]
PipelineOrchestrator.queue_snapshot(self) -> QueueSnapshot
PipelineOrchestrator.close(self, *, timeout_s: float=1.0) -> None
```

类级字段（含配置、输入输出和内部状态；仅声明默认，不是当前run生效配置）：

| 字段 | 类型 | 默认值/来源 |
|---|---|---|
| `OrchestratorConfig.qwen_queue_size` | `int` | `1` |
| `OrchestratorConfig.sensor_queue_size` | `int` | `4` |
| `OrchestratorConfig.log_queue_size` | `int` | `1024` |
| `OrchestratorConfig.model_timeout_ms` | `float` | `300.0` |
| `OrchestratorConfig.minimum_confidence` | `float` | `0.8` |
| `OrchestratorConfig.max_speed_mps` | `float` | `13.8888888889` |
| `OrchestratorConfig.max_accel_mps2` | `float` | `2.5` |
| `OrchestratorConfig.max_decel_mps2` | `float` | `5.0` |
| `OrchestratorConfig.stop_line_guard_m` | `float` | `8.0` |
| `OrchestratorConfig.top_k_targets` | `int` | `8` |
| `OrchestratorConfig.qwen_mode` | `str` | `'atomic_v1'` |
| `OrchestratorConfig.allowed_slow_behaviors` | `tuple[str, ...]` | `('KEEP_LANE', 'SET_SPEED', 'SLOW_DOWN', 'STOP', 'YIELD', 'FOLLOW', 'CHANGE_LANE', 'TURN', 'AVOID_OBSTACLE', 'RETURN_TO_LANE', 'PULL_OVER')` |
| `QueueSnapshot.qwen_depth` | `int` | `无声明默认（构造/赋值方提供）` |
| `QueueSnapshot.sensor_depth` | `int` | `无声明默认（构造/赋值方提供）` |
| `QueueSnapshot.log_depth` | `int` | `无声明默认（构造/赋值方提供）` |
| `QueueSnapshot.qwen_overflow` | `int` | `无声明默认（构造/赋值方提供）` |
| `QueueSnapshot.sensor_overflow` | `int` | `无声明默认（构造/赋值方提供）` |
| `QueueSnapshot.log_overflow` | `int` | `无声明默认（构造/赋值方提供）` |
| `OrchestrationResult.disposition` | `str` | `无声明默认（构造/赋值方提供）` |
| `OrchestrationResult.command_id` | `str` | `无声明默认（构造/赋值方提供）` |
| `OrchestrationResult.control_command` | `Mapping[str, Any] &#124; None` | `None` |
| `OrchestrationResult.model_request` | `Mapping[str, Any] &#124; None` | `None` |
| `OrchestrationResult.decision_plan` | `Mapping[str, Any] &#124; None` | `None` |
| `OrchestrationResult.feedback` | `Mapping[str, Any] &#124; None` | `None` |
| `OrchestrationResult.reason_code` | `str` | `'NONE'` |
| `OrchestrationResult.queues` | `QueueSnapshot &#124; None` | `None` |
| `OrchestrationResult.routing_score` | `int &#124; None` | `None` |
| `OrchestrationResult.routing_reasons` | `tuple[str, ...]` | `()` |
| `OrchestrationResult.routing_features` | `Mapping[str, Any] &#124; None` | `None` |
| `OrchestrationResult.qwen_mode` | `str` | `'atomic_v1'` |
| `OrchestrationResult.safe_wait_behavior` | `str` | `'STOP'` |
| `OrchestrationResult.compiled_plan` | `Mapping[str, Any] &#124; None` | `None` |
| `OrchestrationResult.model_completed_ns` | `int &#124; None` | `None` |
| `OrchestrationResult.model_timing` | `Mapping[str, float] &#124; None` | `None` |

### [runtime/plan_validator.py](../../../runtime/plan_validator.py) 的入口与声明

```python
PlanValidationError.__init__(self, reason_code: str, detail: str) -> None
PlanValidator.__init__(self, *, registry: InterfaceRegistry | None=None, maximum_speed_mps: float=13.8888888889, minimum_confidence: float=0.8, clock_ns: Any=time.monotonic_ns) -> None
PlanValidator.validate(self, payload: Mapping[str, Any], *, scene: Mapping[str, Any], expected_request_id: str | None=None, expected_command_id: str | None=None, now_ns: int | None=None, allow_confirmation: bool=False) -> dict[str, Any]
```

### [runtime/plan_compiler.py](../../../runtime/plan_compiler.py) 的入口与声明

```python
CompiledPlanStep.to_dict(self) -> dict[str, Any]
CompiledManeuverPlan.to_dict(self) -> dict[str, Any]
PlanCompiler.compile(self, plan: Mapping[str, Any], *, scene: Mapping[str, Any] | None=None) -> CompiledManeuverPlan
```

类级字段（含配置、输入输出和内部状态；仅声明默认，不是当前run生效配置）：

| 字段 | 类型 | 默认值/来源 |
|---|---|---|
| `CompiledPlanStep.step_id` | `str` | `无声明默认（构造/赋值方提供）` |
| `CompiledPlanStep.source_step_id` | `str` | `无声明默认（构造/赋值方提供）` |
| `CompiledPlanStep.behavior` | `str` | `无声明默认（构造/赋值方提供）` |
| `CompiledPlanStep.target` | `Mapping[str, Any]` | `无声明默认（构造/赋值方提供）` |
| `CompiledPlanStep.preconditions` | `tuple[str, ...]` | `无声明默认（构造/赋值方提供）` |
| `CompiledPlanStep.completion` | `Mapping[str, Any]` | `无声明默认（构造/赋值方提供）` |
| `CompiledPlanStep.timeout_s` | `float` | `无声明默认（构造/赋值方提供）` |
| `CompiledPlanStep.on_failure` | `str` | `无声明默认（构造/赋值方提供）` |
| `CompiledManeuverPlan.command_id` | `str` | `无声明默认（构造/赋值方提供）` |
| `CompiledManeuverPlan.plan_id` | `str` | `无声明默认（构造/赋值方提供）` |
| `CompiledManeuverPlan.steps` | `tuple[CompiledPlanStep, ...]` | `无声明默认（构造/赋值方提供）` |
| `CompiledManeuverPlan.replan_conditions` | `tuple[str, ...]` | `无声明默认（构造/赋值方提供）` |
| `CompiledManeuverPlan.valid_until_ns` | `int` | `无声明默认（构造/赋值方提供）` |

以上为核心交接入口；模块内其余实现、CLI和资源的完整字段/拒绝条件见本页功能小文档索引。类型未声明的返回值不凭名称推断。当前代码基线fe1ba839，静态复核不证明实际CARLA/GPU/板端运行成功。

## Complete implementation inventory

- [integration/canonical_bridge.py](../../../integration/canonical_bridge.py) - `voice_envelope_to_driving_command`, `perception_frame_to_state`, `control_command_to_voice_envelope`
- [integration/qwen_async.py](../../../integration/qwen_async.py) - `AsyncDecisionResult`, `AsyncDecisionResult.ready`, `AsyncDecisionResult.watchdog_alerts`, `_Request`, `AsyncQwenDecisionBridge`, `AsyncQwenDecisionBridge.submit`, `AsyncQwenDecisionBridge.latest`, `AsyncQwenDecisionBridge.close`, `_sim_time`
- [integration/qwen_boundary.py](../../../integration/qwen_boundary.py) - `QwenInputContext`, `QwenInputContext.to_payload`, `QwenBoundaryFailure`, `validate_qwen_response`, `_unwrap_single_json_fence`, `fail_closed`, `_json_mapping`, `_nonempty_text`, `_bounded_number`
- [integration/qwen_command_adapter.py](../../../integration/qwen_command_adapter.py) - `build_high_level_command`, `build_command`
- [integration/qwen_fault_injection.py](../../../integration/qwen_fault_injection.py) - `ScenarioQwenFaultInjector`
- [integration/qwen_image_stager.py](../../../integration/qwen_image_stager.py) - `QwenImageStager`, `QwenImageStager.stage`, `QwenImageStager.stage_multiview`, `QwenImageStager.discard`, `QwenImageStager.prepare_request`
- [integration/qwen_plan_adapter.py](../../../integration/qwen_plan_adapter.py) - `QwenPlanParseError`, `PlannerV2Result`, `build_planner_v2_prompt`, `parse_maneuver_plan`, `QwenPlannerV2Adapter`, `QwenPlannerV2Adapter.infer`, `_summary`
- [integration/qwen_profiles.py](../../../integration/qwen_profiles.py) - `QwenModelProfile`, `get_qwen_profile`, `get_qwen_profile_by_model`, `resolve_qwen_profile`
- [integration/qwen_remote_backend.py](../../../integration/qwen_remote_backend.py) - `OpenAICompatibleQwenVLBackend`, `OpenAICompatibleQwenVLBackend.generate_action`, `OpenAICompatibleQwenVLBackend.close`, `_first_token_confidence`, `_scene_focus_montage`, `_focus_regions`, `_valid_focus_count`, `_normalized_box`
- [integration/qwen_scenario_monitor.py](../../../integration/qwen_scenario_monitor.py) - `QwenScenarioReport`, `QwenScenarioReport.to_dict`, `QwenScenarioMonitor`, `QwenScenarioMonitor.record_routing`, `QwenScenarioMonitor.record_plan`, `QwenScenarioMonitor.record_behavior`, `QwenScenarioMonitor.record_replan`, `QwenScenarioMonitor.record_terminal`, `QwenScenarioMonitor.finalize`, `_forbidden_paths`
- [integration/qwen_service_client.py](../../../integration/qwen_service_client.py) - `QwenServiceClient`, `QwenServiceClient.infer`, `QwenServiceClient.health`, `QwenServiceClient.metrics`, `_response_json`
- [integration/qwen_vl_adapter.py](../../../integration/qwen_vl_adapter.py) - `QwenVLGenerationBackend`, `QwenVLGenerationBackend.generate`, `QwenVLActionChoice`, `QwenVLActionChoice.from_code`, `QwenVLInferenceTrace`, `QwenVLInferenceTrace.latency_ms`, `QwenVLInferenceTrace.to_dict`, `StrictQwenVLAdapter`, `StrictQwenVLAdapter.from_local_checkpoint`, `StrictQwenVLAdapter.last_trace`, `StrictQwenVLAdapter.infer`, `build_strict_qwen_prompt`, `_compact_choice_mapping`, `build_action_choice_prompt`, `assemble_action_choice`, `_base_choice_decision`, `_deterministic_safety_action`, `_voice_target_speed_mps`, `_explicit_voice_set_speed_mps`, `_chinese_number_below_100`, `_validate_target_reference`, `_explicit_target_candidates`, `_ground_explicit_target`, `TransformersQwen25VLBackend`, `TransformersQwen25VLBackend.generate`, `crop_road_roi`
- [integration/second_group_runtime.py](../../../integration/second_group_runtime.py) - `CanonicalSubmission`, `CanonicalResolution`, `_PendingSlow`, `CanonicalRuntimeBridge`, `CanonicalRuntimeBridge.has_pending`, `CanonicalRuntimeBridge.submit`, `CanonicalRuntimeBridge.poll`, `CanonicalRuntimeBridge.fail_all_pending`
- [runtime/__init__.py](../../../runtime/__init__.py) - module/resource/documentation
- [runtime/complexity_router.py](../../../runtime/complexity_router.py) - `ComplexityFeatures`, `ComplexityFeatures.to_dict`, `QwenRoutingDecision`, `ComplexityRouter`, `ComplexityRouter.decide`, `_normalized_text`, `_confidence`, `_nested`, `_actions`, `_parameters_complete`, `_target_candidates`, `_scene_conflict`, `_safe_wait_behavior`
- [runtime/healthcheck.py](../../../runtime/healthcheck.py) - `_http_json`, `_interfaces`, `_dependencies`, `_carla`, `run_healthcheck`, `main`
- [runtime/interface_registry.py](../../../runtime/interface_registry.py) - `InterfaceValidationError`, `InterfaceRegistry`, `InterfaceRegistry.validate`, `InterfaceRegistry.warm`
- [runtime/latency_trace.py](../../../runtime/latency_trace.py) - `_percentile`, `_statistics`, `StageTrace`, `StageTrace.mark`, `StageTrace.finish`, `StageTrace.durations_ms`, `StageTrace.to_dict`, `LatencyCollector`, `LatencyCollector.add`, `LatencyCollector.report`, `LatencyCollector.write`, `summarize_latency_records`
- [runtime/orchestrator.py](../../../runtime/orchestrator.py) - `OrchestratorConfig`, `QueueSnapshot`, `OrchestrationResult`, `_SlowJob`, `_SlowResult`, `PipelineOrchestrator`, `PipelineOrchestrator.submit_command`, `PipelineOrchestrator.poll_slow`, `PipelineOrchestrator.publish_perception`, `PipelineOrchestrator.latest_perception`, `PipelineOrchestrator.publish_log`, `PipelineOrchestrator.drain_logs`, `PipelineOrchestrator.queue_snapshot`, `PipelineOrchestrator.close`
- [runtime/plan_compiler.py](../../../runtime/plan_compiler.py) - `CompiledPlanStep`, `CompiledPlanStep.to_dict`, `CompiledManeuverPlan`, `CompiledManeuverPlan.to_dict`, `PlanCompiler`, `PlanCompiler.compile`, `_copy_step`
- [runtime/plan_validator.py](../../../runtime/plan_validator.py) - `PlanValidationError`, `PlanValidator`, `PlanValidator.validate`, `_find_forbidden_fields`, `_nested`, `_speed_limit`, `_must_stop`, `_available_lanes`

## Dependencies and coordinated changes

上游是[模块1运行入口](vehicle-entry.md)与[模块9接口](vehicle-interfaces.md)，下游是[模块3命令/FSM](vehicle-behavior.md)及[模块7安全层](vehicle-safety.md)；远端服务实现归[模块17](support-qwen.md)，实际采集/训练消费归[模块12](challenge-data.md)。修改行为枚举须贯通 Schema→模型提示/输出→Validator→Compiler→FSM；改 target 字段须贯通 perception.track_id→scene_capabilities.grounded_target_ids→plan.target→执行反馈/场景 oracle，不能只改字符串名字。


## Validation entry points

`python -m pytest integration/tests/test_role_a_orchestrator.py integration/tests/test_qwen_planner_orchestrator.py integration/tests/test_qwen_plan_boundary.py integration/tests/test_qwen_async.py integration/tests/test_qwen_async_timeout.py integration/tests/test_qwen_async_supersede.py integration/tests/test_second_group_runtime.py integration/tests/test_plan_compiler.py`

Run from the worktree root. Listed commands are relevant checks, not claims that tests were executed. CARLA, remote-model and hardware acceptance require their actual environments and run manifests.

## 功能小文档完整索引

以下功能页分别记录实现入口、输入输出声明、内部调用、异常、配置和静态上下游；测试文件保留在源码索引中。

- [integration/canonical_bridge.py](../functions/integration--canonical_bridge--py.md)
- [integration/qwen_async.py](../functions/integration--qwen_async--py.md)
- [integration/qwen_boundary.py](../functions/integration--qwen_boundary--py.md)
- [integration/qwen_command_adapter.py](../functions/integration--qwen_command_adapter--py.md)
- [integration/qwen_fault_injection.py](../functions/integration--qwen_fault_injection--py.md)
- [integration/qwen_image_stager.py](../functions/integration--qwen_image_stager--py.md)
- [integration/qwen_plan_adapter.py](../functions/integration--qwen_plan_adapter--py.md)
- [integration/qwen_profiles.py](../functions/integration--qwen_profiles--py.md)
- [integration/qwen_remote_backend.py](../functions/integration--qwen_remote_backend--py.md)
- [integration/qwen_scenario_monitor.py](../functions/integration--qwen_scenario_monitor--py.md)
- [integration/qwen_service_client.py](../functions/integration--qwen_service_client--py.md)
- [integration/qwen_vl_adapter.py](../functions/integration--qwen_vl_adapter--py.md)
- [integration/second_group_runtime.py](../functions/integration--second_group_runtime--py.md)
- [runtime/__init__.py](../functions/runtime--__init__--py.md)
- [runtime/complexity_router.py](../functions/runtime--complexity_router--py.md)
- [runtime/healthcheck.py](../functions/runtime--healthcheck--py.md)
- [runtime/interface_registry.py](../functions/runtime--interface_registry--py.md)
- [runtime/latency_trace.py](../functions/runtime--latency_trace--py.md)
- [runtime/orchestrator.py](../functions/runtime--orchestrator--py.md)
- [runtime/plan_compiler.py](../functions/runtime--plan_compiler--py.md)
- [runtime/plan_validator.py](../functions/runtime--plan_validator--py.md)

## 诊断与维护交接

本模块证据：command/request/plan身份、返回时间、拒绝原因；检查旧结果和超时。功能实现与上下游见本页原索引；跨模块回查[追踪矩阵](../TRACEABILITY.md)与[诊断入口](../DIAGNOSIS.md)。实际run必须核对版本，未执行的检查不视为已通过。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

### `runtime/tests/test_complexity_router.py`

来源 SHA256：`e35598bd340a94ea36e8b09966ae59a241613ebaa54bc306a19919679477fbee`。

此文件未发现类级注解字段、argparse声明或显式raise。接口签名见原入口章节；这不证明没有外部异常或副作用。
