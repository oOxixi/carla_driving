# 一帧控制的组合顺序与最终执行值

上级：[运行入口模块](../modules/vehicle-entry.md)；关联：[纵向控制](../modules/vehicle-longitudinal.md)、[安全仲裁](../modules/vehicle-safety.md)。

## 维护入口

[ControlRuntime.step](../../../integration/runtime_loop.py) 负责组合，不直接拥有 CARLA world。它输入同帧 vehicle、PerceptionFrame、RouteReference、dt_s 和可选速度上限/安全原因，输出 FrameResult。真正的 tick、apply_control 与 Actor 清理由 [carla_runner.run](../../../integration/carla_runner.py) 持有。

## 实际数据流

1. 收集 pending feedback 并推进 BehaviorFSM；处理 watchdog 与活动命令的失败/过期。
2. B `step_any(vehicle, route)` 得到 steer/路线进展。非 OK 会锁存横向告警、清目标速度并结束活动命令。
3. 根据交通灯停止策略形成 control_scene，确定 effective_requested_speed，再叠加外部 speed_cap。
4. 计算前方局部曲率，通过 perception_bridge 建 LongitudinalRequest；需要确认时先经过 FuzzyCommandPolicy，否则调用 C `step`。
5. 停车保持可把 C 输出约束成 throttle=0、brake 至少 hold_brake；与横向 steer 合成 raw control。
6. raw_control_override 若存在仍送 D。SafetySupervisor 使用状态/风险/watchdog 最终仲裁；semantic safety reason 可补充安全覆盖与命令生命周期信息。
7. 安全覆盖可能终结活动命令并锁存停车；否则判定命令完成，返回 FrameResult 供 runner 执行和记录。

## 调试时必须同时看哪些值

不能只看 throttle/brake：同时看 requested_speed、effective cap、C 的 target_speed/reason、raw control、D reason/category、final_control 和 feedback。车没有前进可能来自确认、停车保持、感知限速、C 制动、D 覆盖或 watchdog，分别修改不同模块。

集成异常会走统一兜底并锁存 `INTEGRATION_FAILURE`。仅让下一帧不再抛异常，不等于已解除安全锁存。

## runner 的后置例外

当前 runner 启动宽限期还可在 D 之后强制全制动。因此“所有输出最终只由 D 写一次”不能按字面理解为没有后置写入；修改日志或证据时必须记录实际执行的 final_control。该例外是安全方向，不是模型直接控制。

验证入口：[runtime loop tests](../../../integration/tests/test_runtime_loop.py)、[runtime stages](../../../integration/tests/test_runtime_stages.py)、[runner helpers](../../../integration/tests/test_carla_runner_helpers.py)。后续调整控制顺序时，应检查故障注入仍经过 D、失败后不保留推进以及实际执行值与日志一致。
