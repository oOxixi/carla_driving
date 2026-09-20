# 按开发任务定位上下文

返回[项目入口](README.md)。这是阅读和维护记录，不自动授权任何代码改动。下列顺序按现有调用关系组织，避免只改生产端或只改消费者。

## 开发任务索引

| 你要改什么 | 先读的功能文档 | 实际需要联动的范围 | 容易漏掉的验证 |
|---|---|---|---|
| 新增语音意图/槽位 | [音频到命令](functions/voice-command-production.md)、[命令生命周期](functions/command-lifecycle.md) | NLU → envelope → voice/canonical Adapter → Router/模型 → 执行能力 | 模糊命令、参数缺失、低 confidence、文本/音频差异 |
| 增加模型可表达动作 | [计划校验/编译](functions/plan-validation-compilation.md)、[步骤执行](functions/maneuver-progress.md) | Schema → Teacher 构造 → Validator → Compiler → FSM → runner；Student 还需 Head/标签/Adapter | 模型 JSON 合法但执行器不认识、第一步成功误结算整任务 |
| 只改变内部执行步骤 | [计划校验/编译](functions/plan-validation-compilation.md) | Compiler → FSM → snapshot 生产端 → 生命周期/评分 | 不一定需要加 Student 类别；检查 source_step_id 和完成条件 |
| 更换 Qwen 接入方式 | [Qwen 服务](functions/qwen-service-semantics.md)、[异步规划](functions/async-plan-dispatch.md) | server/client/Backend → 模式与 profile → 超时/队列 → Plan 校验 | 健康恒真、旧结果覆盖新命令、配置与真实模型身份不符 |
| 增加感知字段/改目标排序 | [感知来源](functions/perception-authority.md)、[Student 输入](functions/student-preprocessing.md) | acquire/detector/tracker → PerceptionFrame → canonical/Schema → C/D/模型/标签 → 日志 | 同帧、缺失值、坐标、pointer、目标切换 TTC |
| 改横向跟踪或路线规划 | [路线进度](functions/route-control-progress.md)、[一帧控制](functions/control-frame.md) | geometry/route manager → B → 曲率限速 C → route progress/验收 | 回环跳段、旧索引、路线无效仍 OK、里程指标混用 |
| 改跟车/刹车阈值 | [C/D 交接](functions/longitudinal-safety-contract.md)、[配置生效](functions/policy-precedence.md) | 参数来源 → C 风险与 PID → D → 停车保持/命令终态 | override 更严格、目标切换、停车后蠕动、watchdog 未复位 |
| 新增 Student 输入/输出 | [预处理](functions/student-preprocessing.md)、[loss](functions/distillation-objective.md)、[解码](functions/student-plan-decoding.md) | contract/model/config → label/loss/eval → Adapter → export/Runtime/HIL | Shape 不变但槽位语义改变、padding、输出顺序、旧权重误加载 |
| 接入新 Teacher 数据批次 | [发布与视图](functions/dataset-release-view.md) | collector/governance → release/cohort → view → preflight → train config | D2 硬编码误用于 D3、源版本/派生版本混淆、Test 泄漏 |
| 改训练恢复/模型选择 | [checkpoint 与晋级](functions/checkpoint-and-promotion.md) | train → checkpoint/RNG → best candidate → evaluate → manifest | 恢复未还原 RNG、best 权重与报告不一致、checkpoint 当 state_dict |
| 部署实际训练权重 | [ONNX 交付](functions/onnx-delivery.md)、[晋级](functions/checkpoint-and-promotion.md) | 当前随机导出能力扩展 → 权重身份 → 数值对齐 → A4 编译 → HIL | 随机模型被误称蒸馏产物、SHA 来源错误、前后处理不一致 |
| 改板端性能统计 | [HIL 计时](functions/hil-trace-semantics.md) | Runtime trace → 时钟域 → stages → collectors → report | 重复 mark、缺失项填零、model-only 与 E2E 混算 |
| 增加/调整场景 | [场景证据](functions/scenario-evidence-contract.md) | JSON/schema/index → builder/extensions → execution → acceptance/scoring | expected 反向控制、world 真值冒充 sensors、帧数耗尽误成功 |
| 改镜像/依赖/发布包 | [环境交付](functions/environment-delivery.md) | requirements → Docker/入口/cwd/env → weights/profile → manifest/报告 | 环境分层、旧启动脚本、主机/容器路径、版本不一致 |

## 读到什么程度才足以开始修改

至少能回答：哪个入口触发它；输入是谁产生、单位和时钟是什么；输出谁消费；失败时车辆或任务处于什么状态；配置在哪里覆盖；哪项测试验证该语义；历史兼容逻辑保护了什么。
如果文档只给签名而无法回答，应沿模块链接读取实现，并把查到的实际语义补回功能页。未查明的理由保持“未证实”，不要让推测演变成新的约束。

## 当前文档如何分工

- 功能语义页解释业务与维护依据，例如为什么锁存、何时暂停、哪些身份不同。
- 逐文件页保存字段、签名、显式异常和静态引用，辅助定位，不用它证明运行分支正确。
- [接口矩阵](INTERFACES.md) 记录跨模块交接；[台账](AUDIT.md) 记录已知问题而不自动修复；[验证记录](VALIDATION.md) 区分测试发现、实际测试和硬件证据。
- 冻结 manifest、Schema、配置及源码是执行权威；文档描述当前版本，历史报告不追溯改写。

## 真实故障验收

按[诊断流程](DIAGNOSIS.md)找到判据和生产者，再按[追踪矩阵](TRACEABILITY.md)核对消费者。修改base需查全部GEN/selection，修改target需查Teacher/Student/验收，修改终态需查collector资格。代码机制、局部复现、实际run因果分别记录。
