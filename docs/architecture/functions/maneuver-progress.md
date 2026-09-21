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

`request_replan` 有 cooldown 和每命令次数上限；冷却期抑制重规划并返回SLOW_DOWN建议，超过上限结FAILED并返回STOP建议；实际控制是否消费建议须另查。`on_failure` 决定 REPLAN、CONFIRM、SAFE_STOP 或保持车道后的失败，而不是统一抛异常。

## 修改联动

新增 completion/precondition：先改 [Schema](../../../interfaces/maneuver_plan.schema.json) 与 [PlanValidator](../../../runtime/plan_validator.py)，再改 [PlanCompiler](../../../runtime/plan_compiler.py) 的展开逻辑、FSM 判定和 runner 提供的 snapshot。若 Student 要生成该条件，还要同步 Head/标签/Adapter。不能只在 `_completion_satisfied` 加字符串分支。

测试入口：[test_maneuver_fsm.py](../../../car_control_A/tests/test_maneuver_fsm.py)、[test_plan_compiler.py](../../../integration/tests/test_plan_compiler.py)、[runner helpers](../../../integration/tests/test_carla_runner_helpers.py)。改变上述红灯、让行或条件减速分支时需要专门的时序回归，普通“最终成功”断言不足以证明中途安全。

## 当前未闭合的消费路径

`request_replan`仅记录时间/计数、设置REPLAN_PENDING并发qwen_replan_triggered，没有模型调用。下一帧若触发条件消失，update可继续原计划；重复start同command_id也会清零重规划次数，因而max_replans_per_command不是跨替换计划的累计预算。以上纯函数行为已复现，见[审计M03-02](../AUDIT.md)。

当前`integration/carla_runner.py::_record_maneuver_update`处理replan事件时只调用monitor.record_replan并记录事件；所核对的runner调用点未见据此提交新模型请求，也未读取ManeuverUpdate.safe_behavior。runner仍通过既有交通、路线、C/D安全链处理实际控制，所以不能简单推断所有STOP都未生效；但FSM返回safe_behavior的单元测试不能证明该建议已经执行。这是跨模块接线缺口，不是“FSM不会发事件”。

## 时间与连续帧的实际约束

start/update只校验now_s有限、不强制非负或跨调用单调。FSM不直接比较plan.valid_until_ns，PLAN_EXPIRING依赖snapshot布尔字段。step timeout包含未满足前置条件的等待，红灯分支每次重置step_started_s，解除后重新获得计时窗口。

hold_frames计的是连续满足条件的update调用次数，没有frame ID去重。同帧重复调用也会累计；HOLD_FRAMES缺hold_condition默认True。SLOW_DOWN+TARGET_PASSED的minimum_duration从step_started_s算，未单独累计实际低速观察时间。修改runner调用频率或暂停策略必须回归这些假设。

终态后current_step仍可能非空，消费方必须先看terminal/state再执行；safe_behavior不是持久锁存字段。完整snapshot键、默认容差、锁存继承和事件身份见[逐文件记录](car_control_A--maneuver_fsm--py.md)。
