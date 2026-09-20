# Student 输出解码、约束修复与后端就绪

上级：[Student Planner 模块](../modules/challenge-planner.md)。

## 网络预测与最终 Plan 的区别

[StudentPlanAdapter.decode](../../../challenge/planner/student_adapter.py) 不直接把 argmax 原样交给车辆。它先检查十个输出名称，取 plan_length，按请求允许行为与场景能力筛选可行动作；must_stop 强制单步 STOP。最终 Plan 的部分字段是确定性约束组装结果，不全是模型独立预测。

target_pointer 映射当前请求 targets，FOLLOW/AVOID 在有效目标范围选择；速度受请求 speed_limit/max_target_speed 和代码上限约束。行为决定相容 completion、车道和前置条件；STOP/HOLD/PULL_OVER 后截断序列。confirmation 由模型 logit、置信度阈值及无可行动作的安全兜底共同决定。

## Backend 的实际调用顺序

[StudentBackend](../../../challenge/planner/student_backend.py) 验证 ModelRequest → 固定预处理 → torch inference_mode 前向 → Adapter 解码 → PlanValidator 校验。Backend 使用 `allow_confirmation=True` 保留需确认计划，调用者仍需按确认语义处理，不能看返回了 Plan 就直接执行。

构造时可加载纯 state_dict。没有 weights/合格 manifest 时 production_ready=False；有清单才校验 model_id、config_id、完整 git_sha、非空数据身份、Gate 字符串与实际权重 SHA，再加载模型。清单验证不检查远端数据库是否真实存在该 Gate，因此仍不是 B2/B3 最终验收。

## 修改时的具体影响

- 改阈值可能改变 confirmation 分布，需检查下游拒绝/等待而不仅是 Head 精度。
- 改可行动作筛选需同步 Teacher 约束和评测口径；Adapter 修复不能掩盖模型错误。
- 改 completion 固定组装可能让某 Head 的预测不再影响最终 Plan，评测应分别看原始 Head 与最终输出。
- 不应将 Adapter 的临时 Python 控制流误算成 ONNX 网络算子；部署包含前后处理时要单独计时。

测试：[test_a1_student.py](../../../challenge/tests/test_a1_student.py)、[test_delivery.py](../../../challenge/tests/test_delivery.py)、[HIL tests](../../../challenge/hil/tests)。至少核对目标 grounding、缺失目标、must_stop、终止步骤截断、非法清单和需确认输出。
