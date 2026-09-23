# 全项目追踪矩阵

返回[总索引](README.md)，定位流程见[诊断入口](DIAGNOSIS.md)。基线fe1ba839，2026-09-20。覆盖20个业务模块；证据列是定位需要的对象，不承诺全部字段已经持久化。静态清单不是完整动态调用图。

| 模块 | 证据与当前限制 | 语义功能入口 |
|---|---|---|
| [语音→命令](modules/support-voice.md) | 音频、ASR/NLU envelope、confidence/errors；关联同一输入 | [ASR、NLU、复核与命令交付](functions/voice-command-production.md) |
| [接口转换](modules/vehicle-interfaces.md) | 原始JSON、schema版本、单位/坐标转换；合法JSON不等于语义正确 | [版本、时间、坐标与适配语义](functions/interface-versioning.md) |
| [感知→targets](modules/vehicle-perception.md) | 同帧时间、track ID、来源、request目标；历史关联需实际日志 | [同帧感知、目标身份与来源](functions/perception-authority.md) |
| [异步计划](modules/vehicle-planner.md) | command/request/plan身份、返回时间、拒绝原因；检查旧结果和超时 | [异步等待、旧结果拒绝与多层命令ID](functions/async-plan-dispatch.md) |
| [Teacher响应](modules/support-qwen.md) | profile/SHA、原始响应、构造后Plan；health恒真见AUDIT A04 | [服务模式、动作组装与health](functions/qwen-service-semantics.md) |
| [步骤与终态](modules/vehicle-behavior.md) | 授权、step、feedback、terminal原因；单步成功不等于任务完成 | [授权、确认、过期与停车保持](functions/command-lifecycle.md) |
| [路线与横向](modules/vehicle-lateral.md) | 路线身份、progress/remaining、CTE、steer；区分累计里程 | [路线、跟踪控制与完成里程](functions/route-control-progress.md) |
| [纵向控制](modules/vehicle-longitudinal.md) | 速度/距离/TTC、C/D输出；核对单位和最终执行值 | [目标速度、跟车风险与D交接](functions/longitudinal-safety-contract.md) |
| [安全覆盖](modules/vehicle-safety.md) | 首次runtime_alerts、锁存/复位、brake；long首故障待证 | [C/D分工与实时仲裁](functions/longitudinal-safety-contract.md) |
| [逐帧执行](modules/vehicle-entry.md) | 模拟/墙钟、预算、最终control、异常；D后覆盖见AUDIT R05 | [一帧控制的实际顺序与执行值](functions/control-frame.md) |
| [验收](modules/vehicle-scenarios.md) | scenario哈希、failed_keys、actual/required；A03实际证据缺失 | [场景触发、车辆行为与验收分离](functions/scenario-evidence-contract.md) |
| [配置与派生](modules/support-config-scenarios.md) | CLI/env/场景覆盖、GEN来源参数；19 GEN发现9项语义差异 | [具体参数的装载和覆盖](functions/policy-precedence.md) |
| [数据发布](modules/challenge-data.md) | run/sample/cohort、split/hash、excluded原因；Wave2原始证据缺失 | [原始样本、冻结发布与派生训练视图](functions/dataset-release-view.md) |
| [输入张量](modules/challenge-structure.md) | contract、目标排序、截断、dtype/shape；shape一致不足以验收 | [预处理真实变换与信息损失](functions/student-preprocessing.md) |
| [Student计划](modules/challenge-planner.md) | head、pointer/NONE、修复原因、权重身份；需对应真实输入 | [Head解码、约束修复和就绪判定](functions/student-plan-decoding.md) |
| [训练与晋级](modules/challenge-training.md) | dataset/checkpoint/RNG、权重SHA与评估身份；A01已关闭，真实B2证据仍缺 | [各Head损失、mask与加权](functions/distillation-objective.md) |
| [部署产物](modules/challenge-export.md) | 权重SHA、ONNX IO、数值对齐、编译配置；随机导出见AUDIT R01 | [随机结构导出、来源SHA与报告](functions/onnx-delivery.md) |
| [性能测量](modules/challenge-hil.md) | 原始trace、阶段次数、时钟域；重复mark见AUDIT A02，未硬件验收 | [Adapter能力、时钟域与测量范围](functions/hil-trace-semantics.md) |
| [环境交付](modules/support-delivery.md) | 镜像依赖、cwd、模型路径/manifest；确认宿主容器映射 | [运行入口、依赖和产物维护](functions/environment-delivery.md) |
| [工具产物](modules/support-tools.md) | 参数、cwd、返回码、原始输出；工具成功不等于业务验收 | [维护工具的运行上下文和证据范围](functions/environment-delivery.md) |

## 功能页的维护标准

职责/上级 → 实际入口与调用者 → 输入输出（单位、空值、身份、时间）→ 分支与失败 → 配置覆盖 → 证据位置与关联方法 → 联动修改与回归 → 基线/验证范围/未知项。已有页面不能回答时沿源码补充，不以套模板作为完成。

改动前后用git diff文件列表查SOURCE_INDEX所属模块；Schema、配置和生成器还需反查消费者与派生产物。重名字段先区分语义，重复实现先查实际入口，未实现部分记录交付缺口与验收条件。问题状态集中在AUDIT，其他页面引用稳定ID。

根因闭合要求输入、转换、判据和实际run证据对应；文档链接与源码覆盖仅是最低导航检查。原inventory是静态源码快照，本轮不重新生成，不把人工新增页伪装为自动扫描结果。
