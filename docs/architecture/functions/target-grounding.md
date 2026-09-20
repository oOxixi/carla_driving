# 目标身份、空值与验收归因

上级：[感知](../modules/vehicle-perception.md)、[Qwen](../modules/support-qwen.md)；消费者：[场景验收](../modules/vehicle-scenarios.md)。基线fe1ba839，2026-09-20。

scenario actor ID是角色（blocker_001），sensor track ID是感知对象（C-0001），Plan target_id是模型选择。不能将oracle角色直接注入模型输入来满足验收。

[runner._sensor_evidence_target_aliases](../../../integration/carla_runner.py)通过_bind_scenario_actor_ids建立证据专用映射，与提交帧关联，存入qwen_target_aliases_by_command；结果返回后交给[extension.note_qwen_plan](../../../integration/scenario_extensions.py)。后者收集字符串target_actor_id/actor_id/target_id并应用alias，expected_target_actor_id检查收集集合。空target不能由alias补成目标。

## Teacher构造契约

[VllmQwenPlannerBackend._step](../../../qwen_service/service.py)只对FOLLOW、AVOID_OBSTACLE、YIELD、SLOW_DOWN绑定target；STOP不绑定，速度目标为0。此结论限当前构造路径。

局部复现：同一request含C-0001（center_ahead），grounded_target_ids含blocker_001，调用实际_step得到STOP.target_id=None、FOLLOW.target_id=C-0001；未运行模型/CARLA。这证明局部机制，不证明历史run使用该版本。

## 定位与联动

实际服务SHA/路径 → 原始Plan target → request候选 → 同command的alias捕获/回传 → extension目标集合 → required actor。必须关联同一请求与提交帧。

STOP原本无target时，先明确验收需要控制目标还是停止原因归属；target有值却无法归因时再查alias。改动需联动Teacher/Schema、Student标签和解码、compiler/FSM、扩展验收。[Qwen tests](../../../qwen_service/tests)与[integration tests](../../../integration/tests)是回归入口，未宣称本轮全量通过。
