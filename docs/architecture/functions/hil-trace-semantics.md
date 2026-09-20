# HIL 的 Runtime 能力、计时阶段与证据范围

上级：[HIL 模块](../modules/challenge-hil.md)。

## Runtime Adapter 是同一 Interface 的不同测量对象

[runtime_adapter.py](../../../challenge/hil/runtime_adapter.py) 中 InProcessStudentRuntime 处理 PyTorch 路径，OnnxModelRuntime 处理 ONNX 路径，BoardCliRuntime 启动 A4 命令子进程。它们是否包含 PlanValidator、预处理和阶段 trace 并不相同，不能只凭 infer 方法同名就合并统计。

StageTrace 记录一次调用的有序时间戳，允许失败前跳过未执行阶段，但拒绝重复、倒序和时间回退；outcome 与 stage_source 是独立信息。READY 表示该 Adapter 完成，不自动代表经过独立评测。

## 已知实现差异

- OnnxModelRuntime 当前 full_chain=True 但 plan_validator=False；消费者应检查具体能力字段，不能把 full_chain 理解为“全部校验都做了”。
- BoardCliRuntime 从 stdout 最后一行解析 JSON；非零退出、超时、非 JSON 均生成对应错误 trace。
- 宿主先 mark input_arrival，再合入板端全部 trace，最后 mark plan_ready。完整板端 trace 会重复标记并抛 StageOrderError，已最小复现。
- 板端 monotonic 与宿主 monotonic 不共享起点，不能直接相减形成可信 E2E。
- InProcess 的 verify_consistency 手工重跑推理，不调用真正带埋点的 self.infer，所以不能覆盖所有 trace 路径缺陷。

## 维护计时功能时的判断依据

先明确测的是模型前向、完整 Planner，还是包含子进程启动/传输的宿主 envelope。再明确时钟域和每阶段是否实测。缺失项应该保持缺失/未插桩，不能填零后计入均值。预热与正式轮次分开，错误/拒绝样本不能混进 READY 延时后掩盖失败率。

相关实现：[stages](../../../challenge/hil/stages.py)、[report](../../../challenge/hil/report.py)、[samplers](../../../challenge/hil/samplers.py)、[identity](../../../challenge/hil/identity.py)、[consistency](../../../challenge/hil/consistency.py)。测试在 [hil/tests](../../../challenge/hil/tests)。真实 J6P 功耗/内存/利用率需要实际硬件采样；本轮没有运行板卡。
