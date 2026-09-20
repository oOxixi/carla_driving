# 高层计划校验与语义步骤展开

上级：[规划模块](../modules/vehicle-planner.md)。

## 校验与编译分工

[PlanValidator](../../../runtime/plan_validator.py) 判断模型计划能否被接受；[PlanCompiler](../../../runtime/plan_compiler.py) 把已接受的语义步骤展开为执行步骤。Compiler 不生成油门、刹车和方向盘，也不能替代 Validator。

Validator 先递归拒绝低层字段，再验证 Schema、request/command 身份、有效期、确认约束、感知新鲜度、step_id 唯一性、目标存在性、速度及车道可行性。`now >= valid_until_ns` 即过期。`allow_confirmation=True` 允许保留低置信或需确认的计划，不能被理解为已批准其执行。

## 编译后为何可能多于四步

Schema 的 1–4 步约束作用于模型语义计划。一个 AVOID_OBSTACLE 在 Compiler 中展开为：降速 → WAIT_SAFE_GAP → CHANGE_LANE → PASS_TARGET；步骤通过 source_step_id 保留来源。这些内部步骤不要求在 Student behavior Head 中增加对应分类。

| 原动作 | 编译关键逻辑 |
|---|---|
| CHANGE_LANE_LEFT/RIGHT | 强制对应 adjacent lane，并补 PERCEPTION_FRESH、LANE_EXISTS、GAP_SAFE |
| AVOID_OBSTACLE | 核对可用邻接车道；未指定速度时用当前代码的 3m/s；降速、等间隙、变道、通过目标分别设 completion |
| RETURN_TO_LANE | 利用前一次避障方向推导返回方向，否则从场景上下文判断；不能随意默认左/右 |
| 其他动作 | 复制为 CompiledPlanStep，保留 timeout/on_failure/completion |

## 扩展行为时的最小完整链

先定义它是模型可表达的语义动作还是仅内部执行步骤。前者需要 Schema、Validator、Teacher 构造、Student 标签/Head/Adapter；后者通常只涉及 Compiler、FSM 与 runner 执行能力。两者混淆会造成训练标签永远无法生成或 Schema 放行但执行器不认识。

测试：[test_plan_compiler.py](../../../integration/tests/test_plan_compiler.py)、[test_maneuver_fsm.py](../../../car_control_A/tests/test_maneuver_fsm.py)、[接口与 planner 测试](../../../integration/tests)。修改编译时应验证 source_step_id、等待/完成条件、返回方向、超时和整体用户指令终态。

## 校验通过的精确含义

`_validate_preconditions`对LEFT_GAP_SAFE等条件主要检查scene中是否有对应观测键；值为False仍可通过并交FSM等待，不等于间隙当前安全。PERCEPTION_FRESH/NO_EMERGENCY_RISK在该循环跳过，场景新鲜度等由validate其他分支检查。目标集合同时包含objects.track_id和grounded_target_ids，后者不是视觉检测记录。Validator对所有非空目标检查存在性，包括带目标的STOP；编排消费阶段跳过停车目标的检查不能覆盖前一阶段的拒绝。

worker的validate以request.created_at_ns为now，然后编排consume按实际完成时间再检查期限；单独调用QwenPlannerV2Adapter不能据其通过推断回调已经在预算内完成。QwenPlannerV2Adapter.infer返回PlannerV2Result，包含plan和compiled，并非可直接作为所有infer回调的dict返回值。

## 展开后的默认与边界

AVOID_OBSTACLE未指定合法邻道时按已知左道、右道优先选择，无可确定邻道时报错；默认速度3m/s。slow/gap步骤timeout=min(5,原timeout)，lane/pass保留原timeout；hold_frames为3/3/8/3，降速completion阈值为目标速度+0.3m/s。RETURN的gap最多8秒、3帧；moving步骤移除相对左右邻道exists/gap条件，保留原completion.hold_frames并要求回到CURRENT。详见[compiler函数索引](runtime--plan_compiler--py.md)。

文本parse_maneuver_plan的NaN/Infinity常量限制弱于Mapping输入分支，后续InterfaceRegistry的allow_nan=False深复制仍是必要关口。已复现的独立解析差异见[审计台账M02-01](../AUDIT.md)，不能删掉后续校验或把解析成功当作Schema成功。
