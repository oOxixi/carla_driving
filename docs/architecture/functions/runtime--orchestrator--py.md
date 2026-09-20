# orchestrator：功能记录

上级模块：[模块说明](../modules/vehicle-planner.md) · 实现：[runtime/orchestrator.py](../../../runtime/orchestrator.py)

## 业务语义与维护关联

本页为逐文件实现记录。与该实现相关的运行语义、边界和修改判断见：

- [异步等待、旧结果拒绝与多层命令ID](async-plan-dispatch.md)
- [计划可行性校验与内部步骤展开](plan-validation-compilation.md)

## 功能职责与范围

A-owned Qwen planner boundary with strict deadlines and bounded queues.

此页记录当前实现，不提出重构或改变行为。功能边界按实现文件组织；文件中的独立函数、方法在下面分别登记。内部局部函数不等于对外接口。

## 数据结构与配置字段

- `OrchestratorConfig.qwen_queue_size: int`；默认：`1`。
- `OrchestratorConfig.sensor_queue_size: int`；默认：`4`。
- `OrchestratorConfig.log_queue_size: int`；默认：`1024`。
- `OrchestratorConfig.model_timeout_ms: float`；默认：`300.0`。
- `OrchestratorConfig.minimum_confidence: float`；默认：`0.8`。
- `OrchestratorConfig.max_speed_mps: float`；默认：`13.8888888889`。
- `OrchestratorConfig.max_accel_mps2: float`；默认：`2.5`。
- `OrchestratorConfig.max_decel_mps2: float`；默认：`5.0`。
- `OrchestratorConfig.stop_line_guard_m: float`；默认：`8.0`。
- `OrchestratorConfig.top_k_targets: int`；默认：`8`。
- `OrchestratorConfig.qwen_mode: str`；默认：`'atomic_v1'`。
- `OrchestratorConfig.allowed_slow_behaviors: tuple[str, ...]`；默认：`('KEEP_LANE', 'SET_SPEED', 'SLOW_DOWN', 'STOP', 'YIELD', 'FOLLOW', 'CHANGE_LANE', 'TURN', 'AVOID_OBSTACLE', 'RETURN_TO_LANE', 'PULL_OVER')`。
- `QueueSnapshot.qwen_depth: int`；默认：`未在声明处设置`。
- `QueueSnapshot.sensor_depth: int`；默认：`未在声明处设置`。
- `QueueSnapshot.log_depth: int`；默认：`未在声明处设置`。
- `QueueSnapshot.qwen_overflow: int`；默认：`未在声明处设置`。
- `QueueSnapshot.sensor_overflow: int`；默认：`未在声明处设置`。
- `QueueSnapshot.log_overflow: int`；默认：`未在声明处设置`。
- `OrchestrationResult.disposition: str`；默认：`未在声明处设置`。
- `OrchestrationResult.command_id: str`；默认：`未在声明处设置`。
- `OrchestrationResult.control_command: Mapping[str, Any] | None`；默认：`None`。
- `OrchestrationResult.model_request: Mapping[str, Any] | None`；默认：`None`。
- `OrchestrationResult.decision_plan: Mapping[str, Any] | None`；默认：`None`。
- `OrchestrationResult.feedback: Mapping[str, Any] | None`；默认：`None`。
- `OrchestrationResult.reason_code: str`；默认：`'NONE'`。
- `OrchestrationResult.queues: QueueSnapshot | None`；默认：`None`。
- `OrchestrationResult.routing_score: int | None`；默认：`None`。
- `OrchestrationResult.routing_reasons: tuple[str, ...]`；默认：`()`。
- `OrchestrationResult.routing_features: Mapping[str, Any] | None`；默认：`None`。
- `OrchestrationResult.qwen_mode: str`；默认：`'atomic_v1'`。
- `OrchestrationResult.safe_wait_behavior: str`；默认：`'STOP'`。
- `OrchestrationResult.compiled_plan: Mapping[str, Any] | None`；默认：`None`。
- `OrchestrationResult.model_completed_ns: int | None`；默认：`None`。
- `OrchestrationResult.model_timing: Mapping[str, float] | None`；默认：`None`。
- `_SlowJob.request: dict[str, Any]`；默认：`未在声明处设置`。
- `_SlowJob.perception: dict[str, Any]`；默认：`未在声明处设置`。
- `_SlowJob.submitted_wall_ns: int`；默认：`未在声明处设置`。
- `_SlowJob.routing: QwenRoutingDecision`；默认：`未在声明处设置`。
- `_SlowJob.runtime_state: dict[str, Any]`；默认：`未在声明处设置`。
- `_SlowResult.job: _SlowJob`；默认：`未在声明处设置`。
- `_SlowResult.status: str`；默认：`未在声明处设置`。
- `_SlowResult.completed_wall_ns: int`；默认：`未在声明处设置`。
- `_SlowResult.plan: dict[str, Any] | None`；默认：`None`。
- `_SlowResult.compiled: CompiledManeuverPlan | None`；默认：`None`。
- `_SlowResult.error: str | None`；默认：`None`。
- `_SlowResult.worker_started_wall_ns: int | None`；默认：`None`。
- `_SlowResult.inference_completed_wall_ns: int | None`；默认：`None`。

## 功能入口：输入、输出与实现说明

<a id="fn-orchestratorconfig"></a>

### `OrchestratorConfig`

源码位置：[runtime/orchestrator.py 第 31 行](../../../runtime/orchestrator.py#L31)。类型：`ClassDef`。

canonical异步编排配置；队列容量、请求预算ms、车辆限速m/s及模式是独立参数。不是HTTP客户端配置，也不会自动读取DrivingPolicy。

<a id="fn-orchestratorconfig---post-init--"></a>

### `OrchestratorConfig.__post_init__`

源码位置：[runtime/orchestrator.py 第 48 行](../../../runtime/orchestrator.py#L48)。类型：`FunctionDef`。

```python
OrchestratorConfig.__post_init__(self) -> None
```

队列和top_k必须精确正int；超时/速度/加减速度/停车线距离须有限正数且非bool；confidence在[0,1]；mode仅atomic_v1/planner_v2；allowed_slow_behaviors须非空tuple、去重且全部在支持集合内。

<a id="fn-queuesnapshot"></a>

### `QueueSnapshot`

源码位置：[runtime/orchestrator.py 第 78 行](../../../runtime/orchestrator.py#L78)。类型：`ClassDef`。

保存3个等待队列深度和各自溢出累计，不含正在执行worker数量；qsize为采样时刻，不能作为事务一致快照。

<a id="fn-orchestrationresult"></a>

### `OrchestrationResult`

源码位置：[runtime/orchestrator.py 第 88 行](../../../runtime/orchestrator.py#L88)。类型：`ClassDef`。

返回disposition和command_id，request/plan/control/feedback/compiled_plan均可空；model_completed_ns为映射后时钟，model_timing拆分排队、回调、校验。REJECTED disposition可能承载FAILED/EXPIRED/TIMED_OUT反馈，必须同时看status/reason。

<a id="fn--slowjob"></a>

### `_SlowJob`

源码位置：[runtime/orchestrator.py 第 108 行](../../../runtime/orchestrator.py#L108)。类型：`ClassDef`。

保存请求、提交时感知、runtime_state浅拷贝、路由结果及submitted_wall_ns；后续目标验证主要用此提交快照，并非自动改为最新感知。

<a id="fn--slowresult"></a>

### `_SlowResult`

源码位置：[runtime/orchestrator.py 第 117 行](../../../runtime/orchestrator.py#L117)。类型：`ClassDef`。

worker结果携带READY/REJECTED/ERROR/OVERFLOW及可空plan/compiled/error和三个时点。模型回调结束与校验编译结束分开计时。

<a id="fn-pipelineorchestrator"></a>

### `PipelineOrchestrator`

源码位置：[runtime/orchestrator.py 第 128 行](../../../runtime/orchestrator.py#L128)。类型：`ClassDef`。

Route every valid command through Qwen on a private worker.

``infer`` is deliberately a callback boundary. It may be an HTTP Qwen
client or a contract-test adapter, but it executes only on the private
worker. A missing callback rejects every valid voice command fail-closed.
``poll_slow`` is non-blocking by default; an explicit bounded wait is used
only on a newly submitted acceptance command to measure the same-frame
sensor-to-trajectory boundary.

<a id="fn-pipelineorchestrator---init--"></a>

### `PipelineOrchestrator.__init__`

源码位置：[runtime/orchestrator.py 第 139 行](../../../runtime/orchestrator.py#L139)。类型：`FunctionDef`。

```python
PipelineOrchestrator.__init__(self, infer: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None=None, *, config: OrchestratorConfig | None=None, registry: InterfaceRegistry | None=None, complexity_router: ComplexityRouter | None=None, plan_validator: PlanValidator | None=None, plan_compiler: PlanCompiler | None=None, clock_ns: Callable[[], int]=time.monotonic_ns) -> None
```

缺组件时构造registry/router/validator/compiler；建立qwen容量N、result容量2N+2、sensor/log有界队列，立即启动单个daemon worker。infer=None仍构造线程，但提交有效指令会拒绝QWEN_UNAVAILABLE。

<a id="fn-pipelineorchestrator-submit-command"></a>

### `PipelineOrchestrator.submit_command`

源码位置：[runtime/orchestrator.py 第 180 行](../../../runtime/orchestrator.py#L180)。类型：`FunctionDef`。

```python
PipelineOrchestrator.submit_command(self, command: Mapping[str, Any], perception: Mapping[str, Any], *, now_ns: int | None=None, rgb_ref: str | None=None, runtime_state: Mapping[str, Any] | None=None) -> OrchestrationResult
```

先验证canonical命令/感知及deadline，再计算路由和约束并生成request。所有合法命令包括STOP都提交Qwen；没有本地快执行路径。队列满淘汰等待请求并为其生成OVERFLOW结果；返回SLOW_PENDING/RECEIVED，不授予推进权限。关闭后入队抛RuntimeError。

<a id="fn-pipelineorchestrator-poll-slow"></a>

### `PipelineOrchestrator.poll_slow`

源码位置：[runtime/orchestrator.py 第 250 行](../../../runtime/orchestrator.py#L250)。类型：`FunctionDef`。

```python
PipelineOrchestrator.poll_slow(self, *, now_ns: int | None=None, wait_timeout_ms: float=0.0) -> tuple[OrchestrationResult, ...]
```

wait_timeout_ms默认0非阻塞，显式正值最多阻塞等待一个结果；参数须有限非负。用提交墙钟到当前的时间检查active超预算（严格>），撤销ID并输出一次TIMED_OUT；随后取尽结果，晚到撤销结果静默退休。超时不取消infer调用，也不能立即释放被阻塞的单worker。

<a id="fn-pipelineorchestrator-publish-perception"></a>

### `PipelineOrchestrator.publish_perception`

源码位置：[runtime/orchestrator.py 第 300 行](../../../runtime/orchestrator.py#L300)。类型：`FunctionDef`。

```python
PipelineOrchestrator.publish_perception(self, payload: Mapping[str, Any]) -> bool
```

经perception_state Schema验证后放有界sensor队列；满则丢最旧，返回False表示发生淘汰而非新值未入队。

<a id="fn-pipelineorchestrator-latest-perception"></a>

### `PipelineOrchestrator.latest_perception`

源码位置：[runtime/orchestrator.py 第 304 行](../../../runtime/orchestrator.py#L304)。类型：`FunctionDef`。

```python
PipelineOrchestrator.latest_perception(self) -> dict[str, Any] | None
```

非阻塞取尽sensor队列，只返回最后一条；队列原为空返回None，调用具有消费副作用。

<a id="fn-pipelineorchestrator-publish-log"></a>

### `PipelineOrchestrator.publish_log`

源码位置：[runtime/orchestrator.py 第 312 行](../../../runtime/orchestrator.py#L312)。类型：`FunctionDef`。

```python
PipelineOrchestrator.publish_log(self, record: Mapping[str, Any]) -> bool
```

JSON往返拷贝且allow_nan=False，非JSON记录转ValueError；写有界log队列，满则淘汰旧记录，不落盘。

<a id="fn-pipelineorchestrator-drain-logs"></a>

### `PipelineOrchestrator.drain_logs`

源码位置：[runtime/orchestrator.py 第 319 行](../../../runtime/orchestrator.py#L319)。类型：`FunctionDef`。

```python
PipelineOrchestrator.drain_logs(self, *, maximum: int | None=None) -> tuple[dict[str, Any], ...]
```

maximum=None取尽，否则需精确正int；FIFO非阻塞最多取maximum条并返回tuple，读取会清除对应队列项。

<a id="fn-pipelineorchestrator-queue-snapshot"></a>

### `PipelineOrchestrator.queue_snapshot`

源码位置：[runtime/orchestrator.py 第 330 行](../../../runtime/orchestrator.py#L330)。类型：`FunctionDef`。

```python
PipelineOrchestrator.queue_snapshot(self) -> QueueSnapshot
```

锁内复制溢出计数，分别读取三个qsize；深度不包括active任务，也不保证多队列原子快照。

<a id="fn-pipelineorchestrator-close"></a>

### `PipelineOrchestrator.close`

源码位置：[runtime/orchestrator.py 第 338 行](../../../runtime/orchestrator.py#L338)。类型：`FunctionDef`。

```python
PipelineOrchestrator.close(self, *, timeout_s: float=1.0) -> None
```

锁内标closed，重复调用直接返回；将None哨兵放入等待队列（必要时淘汰），join默认最多1s。不能强制终止正在infer的回调，关闭期间未完成命令需由外层结算。

<a id="fn-pipelineorchestrator---enter--"></a>

### `PipelineOrchestrator.__enter__`

源码位置：[runtime/orchestrator.py 第 346 行](../../../runtime/orchestrator.py#L346)。类型：`FunctionDef`。

```python
PipelineOrchestrator.__enter__(self) -> 'PipelineOrchestrator'
```

返回已构造并启动worker的self，不再次启动线程。

<a id="fn-pipelineorchestrator---exit--"></a>

### `PipelineOrchestrator.__exit__`

源码位置：[runtime/orchestrator.py 第 349 行](../../../runtime/orchestrator.py#L349)。类型：`FunctionDef`。

```python
PipelineOrchestrator.__exit__(self, *_: object) -> None
```

调用close；无True返回，不吞掉with内部异常。

<a id="fn-pipelineorchestrator--run-slow-worker"></a>

### `PipelineOrchestrator._run_slow_worker`

源码位置：[runtime/orchestrator.py 第 352 行](../../../runtime/orchestrator.py#L352)。类型：`FunctionDef`。

```python
PipelineOrchestrator._run_slow_worker(self) -> None
```

单线程依次取job，记录active并调用infer。V2按提交时scene+runtime_state+请求must_stop验证，now取request.created_at_ns后编译；V1校验decision_plan。校验错为REJECTED，其余Exception为ERROR；关闭后丢结果，否则入result队列。返回时有效期由consume再检查。

<a id="fn-pipelineorchestrator--consume-slow-result"></a>

### `PipelineOrchestrator._consume_slow_result`

源码位置：[runtime/orchestrator.py 第 421 行](../../../runtime/orchestrator.py#L421)。类型：`FunctionDef`。

```python
PipelineOrchestrator._consume_slow_result(self, result: _SlowResult) -> OrchestrationResult | None
```

先将worker耗时映射到请求时钟（提交与created差<=60s视为同epoch），移除撤销结果避免双终态。检查状态、完成时deadline/valid_until、ID、confidence/confirmation、提交快照目标与新鲜度，再生成control。V2检查全部非停车步骤目标，但随后bridge仅再核对首次control目标；不是全计划最新帧复验。

<a id="fn-pipelineorchestrator--model-timing"></a>

### `PipelineOrchestrator._model_timing`

源码位置：[runtime/orchestrator.py 第 565 行](../../../runtime/orchestrator.py#L565)。类型：`FunctionDef`。

```python
PipelineOrchestrator._model_timing(result: _SlowResult, created_ns: int, decision_ns: int) -> dict[str, float]
```

Split the slow path while avoiding comparisons across clock epochs.

以wall时点差得到queue_wait_ms、infer_callback_ms、validate_compile_ms，负差夹0；sensor_to_model_ms用映射后的decision_ns-created_ns。只有submitted与created相差<=60秒才输出sensor_to_submit_ms，避免混合epoch。回调耗时可能包含图像编码和HTTP，不是纯GPU推理。

<a id="fn-pipelineorchestrator--plan-control"></a>

### `PipelineOrchestrator._plan_control`

源码位置：[runtime/orchestrator.py 第 590 行](../../../runtime/orchestrator.py#L590)。类型：`FunctionDef`。

```python
PipelineOrchestrator._plan_control(self, plan: Mapping[str, Any], request: Mapping[str, Any], scene: Mapping[str, Any], now: int) -> dict[str, Any]
```

V1行为须在allowed内（允许方向后缀归一化），must_stop只允许STOP/HOLD。目标速度取计划与场景上限的min；生成SLOW control_command、deadline取请求/计划较早者并Schema校验，不生成油门刹车。

<a id="fn-pipelineorchestrator--compiled-plan-control"></a>

### `PipelineOrchestrator._compiled_plan_control`

源码位置：[runtime/orchestrator.py 第 625 行](../../../runtime/orchestrator.py#L625)。类型：`FunctionDef`。

```python
PipelineOrchestrator._compiled_plan_control(self, plan: Mapping[str, Any], compiled: CompiledManeuverPlan, request: Mapping[str, Any], scene: Mapping[str, Any], now: int) -> dict[str, Any]
```

从compiled首步组装control，WAIT_SAFE_GAP/PASS_TARGET映为HOLD；HOLD/STOP免allowed集合检查，其余须允许。速度受场景限速，reason附step_id。整个compiled_plan另随结果交FSM，首步control不是完整计划。

<a id="fn-pipelineorchestrator--model-request"></a>

### `PipelineOrchestrator._model_request`

源码位置：[runtime/orchestrator.py 第 663 行](../../../runtime/orchestrator.py#L663)。类型：`FunctionDef`。

```python
PipelineOrchestrator._model_request(self, command: Mapping[str, Any], scene: Mapping[str, Any], now: int, *, rgb_ref: str | None, runtime_state: Mapping[str, Any] | None=None, routing: QwenRoutingDecision | None=None) -> dict[str, Any]
```

按distance升序、confidence降序、track_id排序后截top_k；relative_speed取负velocity_x，生成新UUID request。deadline=min(command截止,now+预算)。STOP/遮挡/无安全邻道等收紧行为，交通灯停车理由不直接置must_stop；红灯确保STOP合法。确认请求仅允许STOP；V2复制列举的scene_capabilities，最后验证Schema。

<a id="fn-pipelineorchestrator--persistent-post-maneuver-speed-requested"></a>

### `PipelineOrchestrator._persistent_post_maneuver_speed_requested`

源码位置：[runtime/orchestrator.py 第 784 行](../../../runtime/orchestrator.py#L784)。类型：`FunctionDef`。

```python
PipelineOrchestrator._persistent_post_maneuver_speed_requested(command: Mapping[str, Any]) -> bool
```

Return whether a maneuver explicitly requests a persistent speed.

parameters须包含有限非负target_speed_mps且intent为TURN/CHANGE_LANE，再按中英文“转弯/变道后保持”等明确措辞判断；单有数值不自动认定完成maneuver后持续保持速度。

<a id="fn-pipelineorchestrator--allowed-model-behaviors"></a>

### `PipelineOrchestrator._allowed_model_behaviors`

源码位置：[runtime/orchestrator.py 第 841 行](../../../runtime/orchestrator.py#L841)。类型：`FunctionDef`。

```python
PipelineOrchestrator._allowed_model_behaviors(self, command: Mapping[str, Any], routing: QwenRoutingDecision | None, *, must_stop: bool) -> list[str]
```

must_stop只留STOP；否则按路由特征与intent收窄配置集合，空交集回STOP。FOLLOW允许FOLLOW/STOP，避障保留减速/绕障/变道/返回；明确行人/礼让可加YIELD，变道后明确保持速度可加SET_SPEED。不存在固定所有场景同一动作集。

<a id="fn-pipelineorchestrator--limits"></a>

### `PipelineOrchestrator._limits`

源码位置：[runtime/orchestrator.py 第 925 行](../../../runtime/orchestrator.py#L925)。类型：`FunctionDef`。

```python
PipelineOrchestrator._limits(self, scene: Mapping[str, Any]) -> dict[str, float]
```

返回场景限速与配置max_accel/max_decel三项，不计算油门/刹车比例。

<a id="fn-pipelineorchestrator--scene-speed-limit"></a>

### `PipelineOrchestrator._scene_speed_limit`

源码位置：[runtime/orchestrator.py 第 932 行](../../../runtime/orchestrator.py#L932)。类型：`FunctionDef`。

```python
PipelineOrchestrator._scene_speed_limit(self, scene: Mapping[str, Any]) -> float
```

scene.speed_limit_mps=None用配置最大速度，否则取两者min；依赖前面的Schema保证输入，不自行完整数值校验。

<a id="fn-pipelineorchestrator--perception-stop-reason"></a>

### `PipelineOrchestrator._perception_stop_reason`

源码位置：[runtime/orchestrator.py 第 936 行](../../../runtime/orchestrator.py#L936)。类型：`FunctionDef`。

```python
PipelineOrchestrator._perception_stop_reason(self, scene: Mapping[str, Any]) -> str | None
```

顺序检查stale/不同步、vehicle_state无效、EMERGENCY风险、近静止前物、近红黄灯。前物条件x>=0、横向绝对值<=1.5m、距离<=12.5m、confidence>=0.5、abs(vx)<=0.3；灯距离<=stop_line_guard_m。返回首个reason或None。

<a id="fn-pipelineorchestrator--command-stop-reason"></a>

### `PipelineOrchestrator._command_stop_reason`

源码位置：[runtime/orchestrator.py 第 979 行](../../../runtime/orchestrator.py#L979)。类型：`FunctionDef`。

```python
PipelineOrchestrator._command_stop_reason(command: Mapping[str, Any]) -> str | None
```

intent EMERGENCY_STOP/STOP对应明确理由；否则文本包含遮挡区域/盲区及英文关键词时COMMAND_OCCLUSION_STOP。只做字符串规则，不推断任意语言含义。

<a id="fn-pipelineorchestrator--blocked-maneuver-stop-reason"></a>

### `PipelineOrchestrator._blocked_maneuver_stop_reason`

源码位置：[runtime/orchestrator.py 第 996 行](../../../runtime/orchestrator.py#L996)。类型：`FunctionDef`。

```python
PipelineOrchestrator._blocked_maneuver_stop_reason(command: Mapping[str, Any], scene: Mapping[str, Any], runtime_state: Mapping[str, Any] | None) -> str | None
```

文本含绕避/变道且有车道能力时检查前方30m、横向1.8m内confidence>=0.5对象。显式AVOID/CHANGE_LANE若所需邻道存在，即使暂时gap不安全也不立即否定任务，留FSM等待；无可安全邻道才返回NO_SAFE_ADJACENT_LANE。

<a id="fn-pipelineorchestrator--target-relation"></a>

### `PipelineOrchestrator._target_relation`

源码位置：[runtime/orchestrator.py 第 1068 行](../../../runtime/orchestrator.py#L1068)。类型：`FunctionDef`。

```python
PipelineOrchestrator._target_relation(item: Mapping[str, Any]) -> str
```

position_m解包x/y/z；x>=0为ahead否则behind；y>1.5为left、y<-1.5为right，否则center，输出组合字符串。采用canonical左正坐标。

<a id="fn-pipelineorchestrator--feedback-result"></a>

### `PipelineOrchestrator._feedback_result`

源码位置：[runtime/orchestrator.py 第 1074 行](../../../runtime/orchestrator.py#L1074)。类型：`FunctionDef`。

```python
PipelineOrchestrator._feedback_result(self, command_id: str, now: int, status: str, reason: str, detail: str, *, model_request: Mapping[str, Any] | None=None, disposition: str='REJECTED', routing: QwenRoutingDecision | None=None, model_completed_ns: int | None=None, model_timing: Mapping[str, float] | None=None) -> OrchestrationResult
```

统一装配无control的OrchestrationResult，disposition默认REJECTED但feedback.status按入参；可带request、routing和计时，调用queue_snapshot。

<a id="fn-pipelineorchestrator--rejected"></a>

### `PipelineOrchestrator._rejected`

源码位置：[runtime/orchestrator.py 第 1097 行](../../../runtime/orchestrator.py#L1097)。类型：`FunctionDef`。

```python
PipelineOrchestrator._rejected(self, command_id: str, now: int, reason: str, detail: str) -> OrchestrationResult
```

将status固定REJECTED委托_feedback_result，保留reason/detail。

<a id="fn-pipelineorchestrator--routing-fields"></a>

### `PipelineOrchestrator._routing_fields`

源码位置：[runtime/orchestrator.py 第 1100 行](../../../runtime/orchestrator.py#L1100)。类型：`FunctionDef`。

```python
PipelineOrchestrator._routing_fields(self, routing: QwenRoutingDecision) -> dict[str, Any]
```

把路由score/reasons/features、安全等待建议及当前qwen_mode组成结果字段；不执行safe_wait动作。

<a id="fn-pipelineorchestrator--publish-routing-event"></a>

### `PipelineOrchestrator._publish_routing_event`

源码位置：[runtime/orchestrator.py 第 1109 行](../../../runtime/orchestrator.py#L1109)。类型：`FunctionDef`。

```python
PipelineOrchestrator._publish_routing_event(self, command_id: str, scene: Mapping[str, Any], routing: QwenRoutingDecision) -> None
```

向log队列写qwen_routing_event，含command/frame/sim_time、score、reason、mode、features，qwen_call_index初始0；不是持久化保证。

<a id="fn-pipelineorchestrator--feedback"></a>

### `PipelineOrchestrator._feedback`

源码位置：[runtime/orchestrator.py 第 1130 行](../../../runtime/orchestrator.py#L1130)。类型：`FunctionDef`。

```python
PipelineOrchestrator._feedback(self, command_id: str, now: int, status: str, detail: str, reason: str | None, *, safety_event_reason: str | None=None) -> dict[str, Any]
```

构造并Schema验证execution_feedback；只有终态填terminal_reason。safety_event_reason存在时写全刹占位raw/final control作为该反馈证据，不等于已实际apply_control。

<a id="fn-pipelineorchestrator--plan-safety-event-reason"></a>

### `PipelineOrchestrator._plan_safety_event_reason`

源码位置：[runtime/orchestrator.py 第 1161 行](../../../runtime/orchestrator.py#L1161)。类型：`FunctionDef`。

```python
PipelineOrchestrator._plan_safety_event_reason(plan: Mapping[str, Any], scene: Mapping[str, Any], request: Mapping[str, Any] | None=None) -> str | None
```

Expose a Qwen traffic-rule stop as canonical safety evidence.

取V2首步或V1行为；红灯且首动作STOP返回QWEN_TRAFFIC_LIGHT_STOP，其次请求routing含ILLEGAL_REQUEST且STOP返回QWEN_ILLEGAL_REQUEST_STOP，否则None。只产生反馈原因，不实际施加刹车。

<a id="fn-pipelineorchestrator--active-snapshot"></a>

### `PipelineOrchestrator._active_snapshot`

源码位置：[runtime/orchestrator.py 第 1193 行](../../../runtime/orchestrator.py#L1193)。类型：`FunctionDef`。

```python
PipelineOrchestrator._active_snapshot(self) -> _SlowJob | None
```

锁内取当前job对象引用，不拷贝job内部字典。

<a id="fn-pipelineorchestrator--enqueue-slow-job"></a>

### `PipelineOrchestrator._enqueue_slow_job`

源码位置：[runtime/orchestrator.py 第 1197 行](../../../runtime/orchestrator.py#L1197)。类型：`FunctionDef`。

```python
PipelineOrchestrator._enqueue_slow_job(self, job: _SlowJob) -> _SlowJob | None
```

Enqueue newest work and return any explicitly evicted request.

非阻塞放最新请求；满则取出旧等待项并累计qwen overflow，返回被淘汰job供调用者生成终态。遇关闭哨兵要放回并拒绝提交；已执行job不在此队列中，不被取消。

<a id="fn-pipelineorchestrator--now"></a>

### `PipelineOrchestrator._now`

源码位置：[runtime/orchestrator.py 第 1221 行](../../../runtime/orchestrator.py#L1221)。类型：`FunctionDef`。

```python
PipelineOrchestrator._now(self, value: int | None) -> int
```

None用注入clock_ns，否则使用传值；要求精确非负int，bool拒绝。单位为纳秒但不校验不同来源时钟是否同epoch。

<a id="fn-pipelineorchestrator--put-latest"></a>

### `PipelineOrchestrator._put_latest`

源码位置：[runtime/orchestrator.py 第 1227 行](../../../runtime/orchestrator.py#L1227)。类型：`FunctionDef`。

```python
PipelineOrchestrator._put_latest(self, queue: Queue[Any], value: Any, queue_name: str, *, count_overflow: bool=True) -> bool
```

非阻塞放入，满则先取掉一项再放新值，按开关累计overflow；返回是否未淘汰。closed时除None哨兵外拒绝，不能把False解读为新记录未保存。

## 内部调用与异常路径

- `__post_init__` 调用：`ValueError`, `any`, `float`, `getattr`, `isinstance`, `len`, `math.isfinite`, `set`, `type`.
- `__init__` 调用：`ComplexityRouter`, `InterfaceRegistry`, `Lock`, `OrchestratorConfig`, `PlanCompiler`, `PlanValidator`, `Queue`, `Thread`, `self._worker.start`, `set`.
- `submit_command` 调用：`OrchestrationResult`, `_SlowJob`, `_SlowResult`, `command.get`, `dict`, `isinstance`, `self._blocked_maneuver_stop_reason`, `self._clock_ns`, `self._command_stop_reason`, `self._enqueue_slow_job`, `self._feedback`, `self._feedback_result`, `self._model_request`, `self._now`, `self._perception_stop_reason`, `self._publish_routing_event`, `self._put_latest`, `self._rejected`, `self._routing_fields`, `self.complexity_router.decide`, `self.queue_snapshot`, `self.registry.validate`, `str`.
- `poll_slow` 调用：`ValueError`, `completed_results.append`, `float`, `isinstance`, `math.isfinite`, `results.append`, `self._active_snapshot`, `self._clock_ns`, `self._consume_slow_result`, `self._feedback_result`, `self._now`, `self._result_queue.get`, `self._result_queue.get_nowait`, `self._revoked_request_ids.add`, `tuple`, `type`.
- `publish_perception` 调用：`self._put_latest`, `self.registry.validate`.
- `latest_perception` 调用：`self._sensor_queue.get_nowait`.
- `publish_log` 调用：`ValueError`, `dict`, `json.dumps`, `json.loads`, `self._put_latest`.
- `drain_logs` 调用：`ValueError`, `len`, `records.append`, `self._log_queue.get_nowait`, `tuple`, `type`.
- `queue_snapshot` 调用：`QueueSnapshot`, `dict`, `self._log_queue.qsize`, `self._qwen_queue.qsize`, `self._sensor_queue.qsize`.
- `close` 调用：`float`, `max`, `self._put_latest`, `self._worker.join`.
- `__exit__` 调用：`self.close`.
- `_run_slow_worker` 调用：`_SlowResult`, `self._clock_ns`, `self._infer`, `self._put_latest`, `self._qwen_queue.get`, `self.plan_compiler.compile`, `self.plan_validator.validate`, `self.registry.validate`, `type`.
- `_consume_slow_result` 调用：`OrchestrationResult`, `ValueError`, `abs`, `available.update`, `capabilities.get`, `float`, `int`, `isinstance`, `iter`, `max`, `next`, `plan.get`, `request.get`, `result.compiled.to_dict`, `self._compiled_plan_control`, `self._feedback`, `self._feedback_result`, `self._model_timing`, `self._plan_control`, `self._plan_safety_event_reason`, `self._revoked_request_ids.remove`, `self._routing_fields`, `self.queue_snapshot`, `set`, `step.get`, `step['target'].get`, `str`, `str(plan.get('behavior', '')).upper`, `str(step.get('behavior', '')).upper`.
- `_model_timing` 调用：`abs`, `max`.
- `_plan_control` 调用：`ValueError`, `behavior.removesuffix`, `behavior.removesuffix('_LEFT').removesuffix`, `float`, `min`, `plan.get`, `plan['parameters'].get`, `self._limits`, `self._scene_speed_limit`, `self.registry.validate`, `set`, `str`.
- `_compiled_plan_control` 调用：`ValueError`, `behavior.removesuffix`, `behavior.removesuffix('_LEFT').removesuffix`, `float`, `min`, `self._limits`, `self._scene_speed_limit`, `self.registry.validate`, `set`, `step.target.get`.
- `_model_request` 调用：`ValueError`, `command.get`, `command['parameters'].get`, `float`, `int`, `list`, `min`, `runtime_state.get`, `scene.get`, `self._allowed_model_behaviors`, `self._blocked_maneuver_stop_reason`, `self._command_stop_reason`, `self._perception_stop_reason`, `self._scene_speed_limit`, `self._target_relation`, `self.registry.validate`, `sorted`, `str`, `str(scene.get('traffic_light', '')).upper`, `uuid4`.
- `_persistent_post_maneuver_speed_requested` 调用：`any`, `command.get`, `float`, `isinstance`, `math.isfinite`, `parameters.get`, `str`, `str(command.get('intent', '')).upper`, `str(command.get('source_text', '')).casefold`, `type`.
- `_allowed_model_behaviors` 调用：`any`, `command.get`, `list`, `non_maneuver_by_intent.get`, `permitted.add`, `self._persistent_post_maneuver_speed_requested`, `set`, `str`, `str(command.get('intent', '')).upper`, `str(command.get('source_text', '')).upper`.
- `_limits` 调用：`self._scene_speed_limit`.
- `_scene_speed_limit` 调用：`float`, `min`, `scene.get`.
- `_perception_stop_reason` 调用：`abs`, `float`, `isinstance`, `item.get`, `len`, `scene.get`, `type`.
- `_command_stop_reason` 调用：`any`, `command.get`, `str`, `str(command.get('intent', '')).upper`, `str(command.get('source_text', '')).upper`.
- `_blocked_maneuver_stop_reason` 调用：`abs`, `any`, `bool`, `capability_keys.intersection`, `command.get`, `dict`, `float`, `isinstance`, `item.get`, `len`, `parameters.get`, `scene.get`, `set`, `state.get`, `str`, `str(command.get('intent', '')).upper`, `str(command.get('source_text', '')).upper`, `str(parameters.get('direction', '')).upper`, `type`.
- `_target_relation` 调用：`float`.
- `_feedback_result` 调用：`OrchestrationResult`, `self._feedback`, `self._routing_fields`, `self.queue_snapshot`.
- `_rejected` 调用：`self._feedback_result`.
- `_routing_fields` 调用：`routing.features.to_dict`.
- `_publish_routing_event` 调用：`list`, `routing.features.to_dict`, `self.publish_log`.
- `_feedback` 调用：`dict`, `self.registry.validate`.
- `_plan_safety_event_reason` 调用：`isinstance`, `plan.get`, `request.get`, `routing.get`, `scene.get`, `step.get`, `str`, `str(item).upper`, `str(plan.get('behavior', '')).upper`, `str(scene.get('traffic_light', '')).upper`, `str(step.get('behavior', '')).upper`.
- `_enqueue_slow_job` 调用：`RuntimeError`, `self._qwen_queue.get_nowait`, `self._qwen_queue.put_nowait`.
- `_now` 调用：`ValueError`, `self._clock_ns`, `type`.
- `_put_latest` 调用：`RuntimeError`, `queue.get_nowait`, `queue.put_nowait`.

显式异常（仅 raise，未穷举依赖可能抛出的异常）：

- `__post_init__`，第 52 行：`ValueError(f'{name} must be a positive integer')`。
- `__post_init__`，第 59 行：`ValueError(f'{name} must be finite and positive')`。
- `__post_init__`，第 61 行：`ValueError('minimum_confidence must be in [0, 1]')`。
- `__post_init__`，第 63 行：`ValueError("qwen_mode must be 'atomic_v1' or 'planner_v2'")`。
- `__post_init__`，第 74 行：`ValueError('allowed_slow_behaviors must be a unique supported tuple')`。
- `_compiled_plan_control`，第 640 行：`ValueError(f'compiled behavior {behavior} violates allowed_behaviors')`。
- `_consume_slow_result`，第 532 行：`ValueError('planner_v2 result is missing compiled steps')`。
- `_enqueue_slow_job`，第 1201 行：`RuntimeError('orchestrator is closed')`。
- `_enqueue_slow_job`，第 1215 行：`RuntimeError('orchestrator is closed')`。
- `_model_request`，第 742 行：`ValueError('Qwen model requests require routing metadata')`。
- `_now`，第 1224 行：`ValueError('now_ns must be a non-negative integer')`。
- `_plan_control`，第 601 行：`ValueError(f'behavior {behavior} violates allowed_behaviors')`。
- `_plan_control`，第 603 行：`ValueError('must_stop constraint forbids propulsion plan')`。
- `_put_latest`，第 1237 行：`RuntimeError('orchestrator is closed')`。
- `drain_logs`，第 321 行：`ValueError('maximum must be a positive integer or None')`。
- `poll_slow`，第 262 行：`ValueError('wait_timeout_ms must be finite and non-negative')`。
- `publish_log`，第 316 行：`ValueError(f'log record must be strict JSON: {error}')`。

调用清单是静态语法记录，不保证每条分支都会执行；回调、反射和跨进程调用需结合模块说明。


## 上下游与关联验证

静态导入的项目内实现：

- [runtime/complexity_router.py](../../../runtime/complexity_router.py)
- [runtime/interface_registry.py](../../../runtime/interface_registry.py)
- [runtime/plan_compiler.py](../../../runtime/plan_compiler.py)
- [runtime/plan_validator.py](../../../runtime/plan_validator.py)

静态 import 消费者（含测试）：

- [integration/second_group_runtime.py](../../../integration/second_group_runtime.py)
- [runtime/__init__.py](../../../runtime/__init__.py)

## 后续修改需要一起阅读

- [上级模块](../modules/vehicle-planner.md)：业务语义、单位、默认值、边界和验证入口。
- [跨模块接口记录](../INTERFACES.md)：生产者、消费者与契约权威来源。
- [已知现状记录](../AUDIT.md)：问题与风险不等于本轮已修复。
- [源码索引](../SOURCE_INDEX.md)：全量文件归属；本页只说明当前功能实现。

## 2026-09-20 源码契约复核

基线 `fe1ba839`。以下从当前源码声明提取；用于补充原有语义说明。默认表达式不等于运行生效值，分支记录不覆盖被调用函数的全部异常。

<a id="fn-runtime-orchestrator-py"></a>

### `runtime/orchestrator.py`

来源 SHA256：`014ea7ca4b7201945d4f48b0ca6631e6da090d37af33e213036606dac57ef7db`。


字段类型与声明默认（完整类级注解字段；含内部状态，不全部是可配置项）：

| 字段 | 类型 | 默认来源 |
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
| `QueueSnapshot.qwen_depth` | `int` | `无声明默认；构造/赋值方提供` |
| `QueueSnapshot.sensor_depth` | `int` | `无声明默认；构造/赋值方提供` |
| `QueueSnapshot.log_depth` | `int` | `无声明默认；构造/赋值方提供` |
| `QueueSnapshot.qwen_overflow` | `int` | `无声明默认；构造/赋值方提供` |
| `QueueSnapshot.sensor_overflow` | `int` | `无声明默认；构造/赋值方提供` |
| `QueueSnapshot.log_overflow` | `int` | `无声明默认；构造/赋值方提供` |
| `OrchestrationResult.disposition` | `str` | `无声明默认；构造/赋值方提供` |
| `OrchestrationResult.command_id` | `str` | `无声明默认；构造/赋值方提供` |
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
| `_SlowJob.request` | `dict[str, Any]` | `无声明默认；构造/赋值方提供` |
| `_SlowJob.perception` | `dict[str, Any]` | `无声明默认；构造/赋值方提供` |
| `_SlowJob.submitted_wall_ns` | `int` | `无声明默认；构造/赋值方提供` |
| `_SlowJob.routing` | `QwenRoutingDecision` | `无声明默认；构造/赋值方提供` |
| `_SlowJob.runtime_state` | `dict[str, Any]` | `无声明默认；构造/赋值方提供` |
| `_SlowResult.job` | `_SlowJob` | `无声明默认；构造/赋值方提供` |
| `_SlowResult.status` | `str` | `无声明默认；构造/赋值方提供` |
| `_SlowResult.completed_wall_ns` | `int` | `无声明默认；构造/赋值方提供` |
| `_SlowResult.plan` | `dict[str, Any] &#124; None` | `None` |
| `_SlowResult.compiled` | `CompiledManeuverPlan &#124; None` | `None` |
| `_SlowResult.error` | `str &#124; None` | `None` |
| `_SlowResult.worker_started_wall_ns` | `int &#124; None` | `None` |
| `_SlowResult.inference_completed_wall_ns` | `int &#124; None` | `None` |

显式拒绝条件：下列仅保留局部 if/except 条件，不推断循环次数、跨函数状态或此前 return；必须结合入口调用链解释。

| 入口 / 行 | 局部条件 | 抛出 |
|---|---|---|
| `OrchestratorConfig.__post_init__` / 52 | `type(value) is not int or value < 1` | `raise ValueError(f'{name} must be a positive integer')` |
| `OrchestratorConfig.__post_init__` / 59 | `type(value) not in (int, float) or isinstance(value, bool) or (not math.isfinite(float(value))) or (value <= 0)` | `raise ValueError(f'{name} must be finite and positive')` |
| `OrchestratorConfig.__post_init__` / 61 | `not 0.0 <= self.minimum_confidence <= 1.0` | `raise ValueError('minimum_confidence must be in [0, 1]')` |
| `OrchestratorConfig.__post_init__` / 63 | `self.qwen_mode not in {'atomic_v1', 'planner_v2'}` | `raise ValueError("qwen_mode must be 'atomic_v1' or 'planner_v2'")` |
| `OrchestratorConfig.__post_init__` / 74 | `type(self.allowed_slow_behaviors) is not tuple or not self.allowed_slow_behaviors or len(set(self.allowed_slow_behaviors)) != len(self.allowed_slow_behaviors) or any((item not in allowed_values for item in self.allowed_slow_behaviors))` | `raise ValueError('allowed_slow_behaviors must be a unique supported tuple')` |
| `PipelineOrchestrator.poll_slow` / 262 | `type(wait_timeout_ms) not in (int, float) or isinstance(wait_timeout_ms, bool) or (not math.isfinite(float(wait_timeout_ms))) or (wait_timeout_ms < 0)` | `raise ValueError('wait_timeout_ms must be finite and non-negative')` |
| `PipelineOrchestrator.publish_log` / 316 | `except (TypeError, ValueError)` | `raise ValueError(f'log record must be strict JSON: {error}') from error` |
| `PipelineOrchestrator.drain_logs` / 321 | `maximum is not None and (type(maximum) is not int or maximum < 1)` | `raise ValueError('maximum must be a positive integer or None')` |
| `PipelineOrchestrator._consume_slow_result` / 532 | `self.config.qwen_mode == 'planner_v2' AND result.compiled is None` | `raise ValueError('planner_v2 result is missing compiled steps')` |
| `PipelineOrchestrator._plan_control` / 601 | `normalized_for_constraint not in allowed and behavior not in allowed` | `raise ValueError(f'behavior {behavior} violates allowed_behaviors')` |
| `PipelineOrchestrator._plan_control` / 603 | `request['constraints']['must_stop'] and behavior not in {'STOP', 'HOLD'}` | `raise ValueError('must_stop constraint forbids propulsion plan')` |
| `PipelineOrchestrator._compiled_plan_control` / 640 | `behavior not in {'HOLD', 'STOP'} and normalized not in allowed and (behavior not in allowed)` | `raise ValueError(f'compiled behavior {behavior} violates allowed_behaviors')` |
| `PipelineOrchestrator._model_request` / 742 | `routing is None` | `raise ValueError('Qwen model requests require routing metadata')` |
| `PipelineOrchestrator._enqueue_slow_job` / 1201 | `self._closed` | `raise RuntimeError('orchestrator is closed')` |
| `PipelineOrchestrator._enqueue_slow_job` / 1215 | `except Full AND evicted is None` | `raise RuntimeError('orchestrator is closed')` |
| `PipelineOrchestrator._now` / 1224 | `type(now) is not int or now < 0` | `raise ValueError('now_ns must be a non-negative integer')` |
| `PipelineOrchestrator._put_latest` / 1237 | `self._closed and value is not None` | `raise RuntimeError('orchestrator is closed')` |
