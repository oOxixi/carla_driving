# 跨模块 Interface 与联动修改

返回[项目导航](README.md)。本页规定阅读路径，不替代源码中的字段表。

## 权威定义和生产/消费关系

| Interface | 权威定义 | 生产者 → 消费者 | 修改联动 |
|---|---|---|---|
| 语音 envelope | [voice adapter](../../integration/voice_adapter.py)、[voice pipeline](../../voice_group/pipeline.py) | ASR/NLU → 车辆命令接入 | status/errors/confidence、单位、确认语义及文本回归 |
| 驾驶指令 | [driving_command Schema](../../interfaces/driving_command.schema.json) | 命令转换 → 编排 | command_id、有效期、意图枚举、异常拒绝 |
| 感知状态 | [perception_state Schema](../../interfaces/perception_state.schema.json)、[车侧类型](../../integration/contracts.py) | 传感器/融合 → 路由、控制、安全 | 同帧、有效性、真值来源、目标 ID、TTC 单位 |
| ModelRequest V1 | [Schema](../../interfaces/model_request.schema.json) | 编排 → Qwen/Student | capability/targets/约束、32 字文本截断、8 目标映射、冻结指纹 |
| DecisionPlan V1 | [Schema](../../interfaces/decision_plan.schema.json) | atomic 模式 Qwen → 编排 | atomic_v1 与 planner_v2 路径不得混用 |
| ManeuverPlan V2 | [Schema](../../interfaces/maneuver_plan.schema.json)、[validator](../../runtime/plan_validator.py) | Qwen / Student Adapter → compiler/FSM | 1–4 步、完成条件、失败策略、请求身份、过期判断 |
| 控制命令 | [Schema](../../interfaces/control_command.schema.json)、[compiler](../../runtime/plan_compiler.py) | 编排/计划编译 → 车辆执行 | 单位、授权、优先级、终态及 D 抢占 |
| 执行反馈 | [Schema](../../interfaces/execution_feedback.schema.json) | 执行/D → 编排/证据 | terminal、重规划、stale feedback、成功与安全覆盖区别 |
| Student 张量 | [contract](../../challenge/student/contract.py)、[config](../../challenge/student/model.py) | preprocess → Student / ONNX / X86 | 输入顺序、dtype、固定 Shape、输出名称/顺序、类别 ID |
| 训练监督 | [training_contract](../../challenge/student/training_contract.py)、[label_encoder](../../challenge/distillation/label_encoder.py) | Teacher Plan → 标签/loss | plan_length 1..4→class 0..3、step mask、NONE 指针、head loss |
| 权重候选身份 | [backend](../../challenge/planner/student_backend.py)、[artifacts](../../challenge/distillation/artifacts.py) | A3 → A1/A4/HIL | 权重 SHA、model/config/dataset/git、Gate 声明及评估身份绑定 |
| 数据治理 | [dataset schema](../../challenge/dataset/dataset_schema.md)、[validator](../../challenge/dataset/validate_dataset.py) | B1 → A3 / calibration / benchmark | Train/Val/Test 分离、Teacher cohort、签名、哈希、质量门 |
| 板端阶段计时 | [stages](../../challenge/hil/stages.py)、[runtime adapter](../../challenge/hil/runtime_adapter.py) | Runtime → HIL 统计 | 阶段唯一性、时钟域、E2E 包含范围、原始 trace |
| 控制策略 | [strategy](../../config/strategy.py)、[driving policy](../../integration/driving_policy.py) | 配置 + 运行参数/场景覆盖 → C/D/感知 | 区分全局默认与覆盖，必须记录实际生效值 |

## 不能只改一端的规则

1. 修改 Schema：查所有 `InterfaceRegistry` 消费者、示例、冻结指纹、Teacher/Student Adapter 和测试。冻结版本变更必须明确版本化，不能只更新 hash 让测试变绿。
2. 修改目标排序：查 `target_pointer` 监督、截断、NONE 类、目标追踪 ID 与 Plan grounding。字符串 ID 不得当作网络记忆标签。
3. 修改 Head/Shape：查 A3 label/loss/evaluate、ONNX 名称顺序、X86/HIL 和量化输入；代码与模型配置/权重必须匹配。
4. 修改策略阈值：查配置装载、CLI/env 覆盖、C/D 实际使用和报告中的生效配置。数值相同不证明语义相同。
5. 修改训练/晋级：查数据划分、Teacher 身份、权重 SHA、评估候选身份、Gate 状态与消费者；局部 production_ready 不能替代 B2/B3。
6. 修改阶段时间戳：查生产/消费时钟、trace 单调性、是否包含预处理/搬运/后处理；不可拼接两台机器的 monotonic ns。
7. 修改成功条件：查 FSM、runner、ScenarioEvidenceRecorder、评分汇总与测试；安全停车不自动等于任务完成。

## 不同版本的处理

Qwen 默认 profile、当前 Teacher manifest、历史实验的 pinned manifest 是不同对象。选择时必须根据运行入口与实验 cohort，不能统一替换所有历史模型字符串。
同样，原始传感器数据结构、内部 dataclass 和跨进程 JSON Schema 可以共存；应检查 Adapter 的转换完整性，而不是仅因字段相似删除其中一套。

## 专项契约

[场景来源](functions/scenario-lineage.md)关联base/GEN/selection；[目标身份](functions/target-grounding.md)区分track/actor/Plan；[验收合成](functions/acceptance-diagnosis.md)区分completion与各层passed；[watchdog](functions/watchdog-diagnosis.md)追首次上游故障。
