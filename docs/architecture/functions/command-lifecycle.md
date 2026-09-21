# 指令授权、确认、过期与停车保持

上级：[命令与状态机模块](../modules/vehicle-behavior.md)。这是维护行为语义的入口；函数签名见该模块的逐文件索引。

## 这个功能解决什么问题

NLU 识别出一句话不等于车辆已有执行授权。系统需要区分“解析失败”“需要确认”“正在执行”“执行成功”和“被安全系统终止”。这些结果既决定下一帧的目标速度，也进入日志与评分。

## 当前执行关系

1. [VoiceCommandAdapter](../../../integration/voice_adapter.py) 解析 envelope，校验版本、command_id、intent、parameters、confidence、status 和 diagnostics，完成速度单位转换。
2. [ControlRuntime.submit_voice](../../../integration/runtime_loop.py) 接纳合法命令，调用 [BehaviorFSM.submit](../../../car_control_A/behavior_fsm.py)，记录 active command、requested speed 和确认状态。
3. 外部确认调用 `confirm_voice`。确认表示用户批准，不凭空补足复杂动作所需的路线或感知决策。
4. 每帧 `ControlRuntime.step` 先 `fsm.tick`，再组合 B/C/D。过期、超时或失败的活动命令清除驱动授权，不保留旧速度继续推进。
5. `_completion_feedback` 根据实际车速等条件报告完成；停止成功后 `_stop_hold` 继续保持制动。成功事件与每帧执行状态不是同一个对象。

## 维护时必须保留的区别

| 情况 | 当前语义 | 容易引入的回归 |
|---|---|---|
| 非法 envelope | 未授权 NO_OP / REJECTED，用于审计 | 不能因为新非法消息复用了 command_id 就终结旧合法命令 |
| 合法新指令替换旧指令 | 旧指令需要唯一终态，新指令开始生命周期 | 只覆盖 active 字段会丢失旧指令的结算事件 |
| 需要确认 | 未取得运动授权，执行保守策略 | 把 confidence 默认写成 1 会放过真实的 0.0 |
| 命令过期/超时 | 清除旧推进授权，D 接收相应告警 | 只更新反馈、不清 requested_speed 会残留推进 |
| watchdog / 集成异常 | 告警锁存，全制动，需显式复位 | 下一个正常帧不能自动解除故障锁存 |
| 停车完成 | 发完成事件，并继续停车保持 | “终态”不能理解为立即恢复巡航 |

时间要分开：车侧 `now_s` 使用仿真秒；canonical 请求的 `deadline_ns` 使用其约定的单调纳秒。不要拿 wall-clock 时间直接与仿真秒比较。

## 修改案例：新增或调整停车意图

先看 voice envelope 是否已有可表达字段，再看 Adapter 输出的 `DrivingCommand.action`；然后检查 `submit_voice` 的 requested_speed/stop_hold、BehaviorFSM 的确认/终态以及 `_completion_feedback`。最后检查 D 是否仍可抢占。只改 NLU 枚举不能算功能完成。

验证定位：[voice adapter tests](../../../integration/tests/test_voice_adapter.py)、[runtime loop tests](../../../integration/tests/test_runtime_loop.py)、[A tests](../../../car_control_A/tests)。至少区分合法命令、非法命令撞 ID、需确认、超时后不推进、停车成功后保持这几条路径。此处是后续修改的验证清单，不表示本轮新加了测试。

## 第3模块精读补充：确认、去重与两种完成语义

HighLevelCommandAdapter先将action JSON变成voice envelope，再由VoiceCommandAdapter变成A命令；canonical规划则有独立桥接，不应把高层adapter不支持FOLLOW误报为整个系统不支持FOLLOW。高层adapter的visual_valid=False只加warning，target_track_id不透传；目标执行与alias证据需独立追踪，详见M03-03。

A命令绝对到期为now>=expires，相对FSM timeout为now-started>timeout，前者优先。confirm不重置计时；BehaviorFSM.confirm只改变全局状态，不更新不可变DrivingCommand的确认标志。ControlRuntime.confirm_voice另行替换授权副本、更新voice确认字段；若还是MULTIMODAL_DECISION，确认后会FAILED并停车，而不是自动生成复杂路线。

重复活动ID在BehaviorFSM层不更新payload/计时；重复终态返回原反馈。ControlRuntime在调用FSM后还会保存自己的active_command，因此这两份状态必须一起核对，不能只根据FSM重复ID短路就推断全运行时payload完全未变。终态对象幂等也不等于外层日志一定只写一次。

BehaviorFSM.complete只接收调用者判定，所有SUCCEEDED使全局状态STOPPED。真实车速并不由这个标签定义：ControlRuntime的SET_SPEED达到误差0.25m/s连续3帧也可成功，KEEP_LANE连续3次完成检查即成功；停车保持由stop_hold另管。ManeuverFSM.CONFIRMING是终态，与BehaviorFSM.CONFIRMING活动状态不同。

直接使用BehaviorFSM时，提交过期新ID会将全局状态改RECOVERING却仍保留旧活动ID，已用纯函数复现（M03-01）。ControlRuntime通常先处理旧owner再提交，故该复现不证明生产入口同样残留；仍需保留直接接口的真实边界说明。

详细参数、异常与跨模块接线见[模块3参数索引](../modules/vehicle-behavior.md)。
