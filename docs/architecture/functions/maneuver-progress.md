# 多步计划执行、前置条件锁存与重规划

上级：[命令与状态机模块](../modules/vehicle-behavior.md)；关联：[规划模块](../modules/vehicle-planner.md)。

## 输入与输出

[ManeuverFSM](../../../car_control_A/maneuver_fsm.py) 接收 `CompiledManeuverPlan`，不是原始模型 JSON。`start(plan, now_s)` 建立步骤游标；`update(snapshot, now_s)` 返回状态、当前步骤、事件和必要的 safe_behavior。snapshot 来自执行事实，不是模型预测完成标志。

## 单步处理顺序

`无计划/已终态 → 紧急风险 → 重规划条件 → 步骤超时 → 前置条件 → 完成条件连续帧 → 步骤推进`。

- 新计划开始时，旧非终态计划发 `SUPERSEDED_BY_NEW_PLAN`，初始化 step_index、计时、前置条件锁存、连续完成帧及重规划计数。
- 前置条件用于进入步骤。满足后锁存，不能每帧用“相邻车道”事实重新检查：变道过程中原相邻车道会变成当前车道，持续检查会把正常进展误判为条件失效。
- 紧急风险在锁存之前始终检查，因此锁存不等于关闭安全监测。
- 完成条件需要连续满足 `hold_frames`，任何不满足帧都会清零计数。计时到达不自动代表任务成功。

## 历史修正形成的语义，不应随意合并

| 分支 | 当前行为 | 原因 |
|---|---|---|
| `RED_LIGHT_STOP_LINE_GUARD` | `WAIT_TRAFFIC_SIGNAL`，STOP，重置 step_started_s/完成计数 | 等红灯暂停语义步骤，不消耗普通步骤超时 |
| YIELD / SLOW_DOWN 遇紧急风险 | 保持计划，输出 EMERGENCY_STOP；危险不解除仍会超时失败 | 让行中的制动可能正是任务正确响应，不能一律终结计划 |
| 其他紧急风险 | SAFETY_OVERRIDE 终态 | 不能因有计划而绕过安全抢占 |
| SLOW_DOWN + TARGET_PASSED | 目标通过、实际降速、最短观察时间同时满足 | 定时器到点不代表已越过行人或公交车 |
| WAIT_SAFE_GAP 接同 source_step 的变道 | 可继承已满足前置条件 | 防止逻辑步骤拆分后重复等待同一安全间隙 |

`request_replan` 有 cooldown 和每命令次数上限；冷却期抑制重规划并保守减速，超过上限失败停车。`on_failure` 决定 REPLAN、CONFIRM、SAFE_STOP 或保持车道后的失败，而不是统一抛异常。

## 修改联动

新增 completion/precondition：先改 [Schema](../../../interfaces/maneuver_plan.schema.json) 与 [PlanValidator](../../../runtime/plan_validator.py)，再改 [PlanCompiler](../../../runtime/plan_compiler.py) 的展开逻辑、FSM 判定和 runner 提供的 snapshot。若 Student 要生成该条件，还要同步 Head/标签/Adapter。不能只在 `_completion_satisfied` 加字符串分支。

测试入口：[test_maneuver_fsm.py](../../../car_control_A/tests/test_maneuver_fsm.py)、[test_plan_compiler.py](../../../integration/tests/test_plan_compiler.py)、[runner helpers](../../../integration/tests/test_carla_runner_helpers.py)。改变上述红灯、让行或条件减速分支时需要专门的时序回归，普通“最终成功”断言不足以证明中途安全。
