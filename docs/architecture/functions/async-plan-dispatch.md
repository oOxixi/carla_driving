# 异步规划等待、过期结果与命令替换

上级：[规划模块](../modules/vehicle-planner.md)。

## 要避免的实际错误

Qwen 处理期间车辆继续逐帧运行。模型返回时用户可能已发新命令，感知目标可能消失，原计划也可能过期。因此“HTTP 成功返回 JSON”不能直接触发车辆动作。

## 当前主链

[CanonicalRuntimeBridge.submit](../../../integration/second_group_runtime.py) 发布当前状态，将语音 envelope 转 canonical DrivingCommand，记录 latest_command_id，并送 [PipelineOrchestrator](../../../runtime/orchestrator.py)。车辆同时收到等待用的安全 envelope。SLOW_PENDING 在 bridge 的 pending 表保留原始文字、等待命令 ID 和已落地目标信息。

`poll` 使用新的感知帧接收完成结果，处理顺序包括：

1. 非 SLOW_READY 或没有 control_command，终结仍匹配的等待命令并报告原因。
2. 返回 command_id 已不是最新命令，拒绝为 SUPERSEDED_BY_NEWER_COMMAND。
3. 对control_command中首个执行目标检查最新感知或提交时保留的合法 grounding；这不是对V2全部后续步骤的最新帧复验。不将 targetless STOP/HOLD/EMERGENCY_STOP 因瞬态目标消失而拒绝。
4. 将 control_command 转回车辆 envelope。多步计划使用内部 `qwen-step-...` ID，原用户指令的整体生命周期由 ManeuverFSM 持有。
5. 多步执行 TTL 至少覆盖各编译步骤超时之和加余量，避免模型有效期与已经授权的执行期限混淆。

## 两个 ID 层级不能合并

用户 command_id 标识整体任务；内部 step ID 标识车辆正在执行的一步。如果第一步 SLOW_DOWN 很快成功就把原 command_id 结算，后面的变道/绕障会失去正确生命周期。这是内部命令 ID 存在的原因，不是无意义包装。

## 路由与模型模式

[ComplexityRouter](../../../runtime/complexity_router.py) 当前输出 QWEN_PLAN 或 CONFIRM_SAFE，决定附加约束，不直接授予控制权；文件说明明确有效语音请求提交 Qwen。不能沿用旧文档“简单命令必走无模型快路径”的推断。
runner 的 `--qwen-mode` 默认仍是 atomic_v1；planner_v2 才处理 ManeuverPlan。运行脚本显式参数与代码默认值必须一起看。

后续改异步行为应验证：旧结果晚到、最新目标消失、targetless 停车、请求截止边界、worker 超时未释放/容量边界、多步第一步成功不终结整体计划。对应 [second_group_runtime tests](../../../integration/tests/test_second_group_runtime.py)、[orchestrator tests](../../../integration/tests/test_qwen_planner_orchestrator.py)、[async tests](../../../integration/tests)。

## 排队、取消与时间域的具体边界

canonical等待队列默认1，不包括已经执行的请求。满队列淘汰旧等待项并产生QUEUE_OVERFLOW；active超时生成TIMED_OUT、撤销request_id，但不会取消HTTP/模型回调，单worker可能继续占用。迟到结果按撤销集合丢弃以避免双终态。

消费成功结果时，以模型完成时刻判断request.deadline_ns与plan.valid_until_ns，边界为>=过期；不是以本次poll时刻重做该判断。submitted_wall_ns与created_at_ns相差<=60秒视为同epoch，否则以实测耗时加到请求时间域。排队、回调、校验编译拆分计时见[逐入口说明](runtime--orchestrator--py.md#fn-pipelineorchestrator--model-timing)。

旧AsyncQwenDecisionBridge是另一套协议：默认3仿真秒有效期，age>ttl判STALE；推理超时默认5墙钟秒，从submit开始；车辆命令TTL默认30秒。latest产生的STALE副本不覆盖内存READY，因此仿真时间回退可能再次读到READY；不得混用两条链的时间边界或解释其状态。

## 接线索引

runner的canonical路径导入`qwen_service.client.QwenServiceClient`，request_transform连接QwenImageStager.prepare_request；`integration.qwen_service_client.QwenServiceClient`接收QwenInputContext并要求READY包装响应，不能互换。完整默认值、时钟与目标来源见[模块参数索引](../modules/vehicle-planner.md)。
