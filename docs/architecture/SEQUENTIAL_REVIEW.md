# 按20模块顺序逐项精读

返回[总索引](README.md)。本记录专门区分“全量静态清单核对”和“逐入口读实现、改正占位说明”；不能把前者当后者完成。

| 顺序 | 模块 | 精读状态 |
|---|---|---|
| 1 | [运行入口与帧控制](modules/vehicle-entry.md) | 本轮完成：参数索引及98处占位补正；运行缺口仍保留 |
| 2 | [异步规划](modules/vehicle-planner.md) | 本轮完成：21份实现页、189处占位改写、具体参数索引；两项边界问题保留 |
| 3 | [命令与状态机](modules/vehicle-behavior.md) | 本轮完成：10份实现页、137处占位改写、参数/状态/snapshot索引；M03问题保留 |
| 4 | [路线与横向控制](modules/vehicle-lateral.md) | 待按顺序精读；保留既有静态复核结果 |
| 5 | [纵向控制](modules/vehicle-longitudinal.md) | 待按顺序精读；保留既有静态复核结果 |
| 6 | [感知](modules/vehicle-perception.md) | 待按顺序精读；保留既有静态复核结果 |
| 7 | [安全仲裁](modules/vehicle-safety.md) | 待按顺序精读；保留既有静态复核结果 |
| 8 | [场景执行与评分](modules/vehicle-scenarios.md) | 待按顺序精读；保留既有静态复核结果 |
| 9 | [接口与坐标转换](modules/vehicle-interfaces.md) | 待按顺序精读；保留既有静态复核结果 |
| 10 | [Student 结构与预处理](modules/challenge-structure.md) | 待按顺序精读；保留既有静态复核结果 |
| 11 | [Student Planner](modules/challenge-planner.md) | 待按顺序精读；保留既有静态复核结果 |
| 12 | [Teacher 数据治理](modules/challenge-data.md) | 待按顺序精读；保留既有静态复核结果 |
| 13 | [蒸馏与晋级](modules/challenge-training.md) | 待按顺序精读；保留既有静态复核结果 |
| 14 | [导出与部署](modules/challenge-export.md) | 待按顺序精读；保留既有静态复核结果 |
| 15 | [HIL 与测量](modules/challenge-hil.md) | 待按顺序精读；保留既有静态复核结果 |
| 16 | [语音链](modules/support-voice.md) | 待按顺序精读；保留既有静态复核结果 |
| 17 | [Qwen 后端](modules/support-qwen.md) | 待按顺序精读；保留既有静态复核结果 |
| 18 | [配置与场景合同](modules/support-config-scenarios.md) | 待按顺序精读；保留既有静态复核结果 |
| 19 | [运行环境与交付](modules/support-delivery.md) | 待按顺序精读；保留既有静态复核结果 |
| 20 | [维护工具](modules/support-tools.md) | 待按顺序精读；保留既有静态复核结果 |

## 第1模块完成记录

- 11份逐文件实现页逐项核对；有占位的9页共98处已按函数体改写。两份语义页control-frame/watchdog继续承担跨文件导航。
- 模块页索引全部67个runner CLI参数，以及ControlRuntime、policy、麦克风10项、回放记录、运行清单和probe参数；稳定函数锚点可从模块参数行直接跳入说明。
- 说明覆盖正常返回、None/缺失、默认与覆盖、时钟/单位、状态变化、线程/文件副作用，不再用“需阅读函数体”代替当前已知行为。
- 实际函数mock边界复现M01-01：probe预热全失败仍success=true；只记录，不修业务代码。实际CARLA/模型运行未做。
- 下一模块按原总索引是“异步规划”，不会跳过或把其他模块批量标为精读完成。

## 第2模块完成记录

- 21份逐文件页及2份跨文件语义页核对；19页共189处占位说明按当前实现改写，另外2页补转换/导出边界；对原来仅一句docstring的关键方法也补充参数消费、返回、副作用及失败条件。
- 模块页增加具体参数索引，区分canonical/旧remote/同名HTTP客户端协议；包含队列容量、模型/HTTP/仿真TTL、时钟、速度/置信度、图像路径与编码、profile、故障注入、终态统计、Schema缓存及延迟指标。
- 源码签名/默认字段保留，方法说明有稳定锚点；目标提交快照与最新帧、前置条件可观测与实际满足、推理超时与后台取消明确分开。
- 实际纯函数调用复现M02-01 parser NaN分支差异、M02-02多命令缺终态仍passed=True；仅登记问题，不改业务实现。未运行CARLA/GPU/远端服务。
- 下一项是第3模块“命令与状态机”，本轮不提前标记其他模块完成。

### 第2模块文档校验结果

21份实现页的源码SHA256均与本轮基线记录一致；189个有签名入口按Python AST核对参数、注解和默认表达式无差异。模块、逐文件、语义页与进度/审计页的745条本地链接检查无缺失（后续补入的3个参数锚点也已检查）；21页无原占位句。`git diff --check`对已跟踪差异无错误；architecture仍为已有未跟踪目录，因此另外直接检查文档文件与锚点。以上为文档/静态契约校验和两项纯函数复现，未宣称运行整套回归或真实服务验收。

## 第3模块完成记录

- 覆盖10份实现记录、2份跨文件语义页，核对4份命令示例和A目录README/RUN的历史适用范围；9页137处占位按函数体改写，无占位的包导出页补实际导出/初始化边界。
- 模块页补参数索引、两Adapter与两FSM的协议差异、状态迁移、完整snapshot字段来源及跨模块接线；区分建议输出与真实执行、直接FSM与ControlRuntime外层保护。
- 已复现M03-01过期新ID影响全局状态、M03-02待重规划恢复原计划及计数重置、M03-03目标字段不透传；runner重规划/安全建议消费为静态核查，不宣称已重现实车后果。
- 离线验证：`python -m pytest car_control_A/tests/test_behavior_fsm.py car_control_A/tests/test_maneuver_fsm.py car_control_A/tests/test_contracts.py car_control_A/tests/test_high_level_command.py car_control_A/tests/test_routing.py car_control_A/tests/test_simulator.py car_control_A/tests/test_telemetry.py car_control_A/tests/test_watchdog.py integration/tests/test_voice_adapter.py -q` → **113 passed**。未运行CARLA烟测或模型服务。
- 下一项为第4模块“路线与横向控制”，本轮仅文档修改，不提前标记其他模块完成。

### 第3模块文档校验结果

10份实现页的来源SHA256与当前源码一致；132个已登记函数签名（含局部回调）经Python AST核对参数、注解和默认表达式无差异。模块/逐文件/语义/审计/进度页522条本地链接与函数锚点检查无缺失；10页无原占位句，`git diff --check`通过。4份examples实际依次经过HighLevelCommandAdapter与VoiceCommandAdapter：变道示例为valid/MULTIMODAL_DECISION/需确认，其余分别KEEP_LANE、SET_SPEED、SET_SPEED且无需确认；均只是适配成功，不是车辆执行验收。工作树改动仅16份文档，未提交。
