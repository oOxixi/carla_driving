# 按20模块顺序逐项精读

返回[总索引](README.md)。本记录专门区分“全量静态清单核对”和“逐入口读实现、改正占位说明”；不能把前者当后者完成。

| 顺序 | 模块 | 精读状态 |
|---|---|---|
| 1 | [运行入口与帧控制](modules/vehicle-entry.md) | 本轮完成：参数索引及98处占位补正；运行缺口仍保留 |
| 2 | [异步规划](modules/vehicle-planner.md) | 本轮完成：21份实现页、189处占位改写、具体参数索引；两项边界问题保留 |
| 3 | [命令与状态机](modules/vehicle-behavior.md) | 本轮完成：10份实现页、137处占位改写、参数/状态/snapshot索引；M03问题保留 |
| 4 | [路线与横向控制](modules/vehicle-lateral.md) | 本轮完成：14份实现页、119处占位改写、全局路线/恢复/横向有效参数索引；RLC问题保留 |
| 5 | [纵向控制](modules/vehicle-longitudinal.md) | **本轮完成**：13份实现页、83处占位改写、生产链/参数/缺测/重置索引；M05-01与A07保留 |
| 6 | [感知](modules/vehicle-perception.md) | **本轮完成**：12份实现页、10页96处占位改写、生产/参考链与来源索引；M06-01/M06-02保留 |
| 7 | [安全仲裁](modules/vehicle-safety.md) | **本轮完成**：13份实现页、12页82处占位改写、双入口/仲裁/终态/评分证据索引；M07-01保留 |
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

21份实现页的Git blob SHA256均与本轮基线记录一致；189个有签名入口按Python AST核对参数、注解和默认表达式无差异。模块、逐文件、语义页与进度/审计页的745条本地链接检查无缺失（后续补入的3个参数锚点也已检查）；21页无原占位句。`git diff --check`对已跟踪差异无错误；architecture仍为已有未跟踪目录，因此另外直接检查文档文件与锚点。以上为文档/静态契约校验和两项纯函数复现，未宣称运行整套回归或真实服务验收。

## 第3模块完成记录

- 覆盖10份实现记录、2份跨文件语义页，核对4份命令示例和A目录README/RUN的历史适用范围；9页137处占位按函数体改写，无占位的包导出页补实际导出/初始化边界。
- 模块页补参数索引、两Adapter与两FSM的协议差异、状态迁移、完整snapshot字段来源及跨模块接线；区分建议输出与真实执行、直接FSM与ControlRuntime外层保护。
- 已复现M03-01过期新ID影响全局状态、M03-02待重规划恢复原计划及计数重置、M03-03目标字段不透传；runner重规划/安全建议消费为静态核查，不宣称已重现实车后果。
- 离线验证：`python -m pytest car_control_A/tests/test_behavior_fsm.py car_control_A/tests/test_maneuver_fsm.py car_control_A/tests/test_contracts.py car_control_A/tests/test_high_level_command.py car_control_A/tests/test_routing.py car_control_A/tests/test_simulator.py car_control_A/tests/test_telemetry.py car_control_A/tests/test_watchdog.py integration/tests/test_voice_adapter.py -q` → **113 passed**。未运行CARLA烟测或模型服务。
- 下一项为第4模块“路线与横向控制”，本轮仅文档修改，不提前标记其他模块完成。

### 第3模块文档校验结果

10份实现页的Git blob SHA256与当前源码一致；132个已登记函数签名（含局部回调）经Python AST核对参数、注解和默认表达式无差异。模块/逐文件/语义/审计/进度页522条本地链接与函数锚点检查无缺失；10页无原占位句，`git diff --check`通过。4份examples实际依次经过HighLevelCommandAdapter与VoiceCommandAdapter：变道示例为valid/MULTIMODAL_DECISION/需确认，其余分别KEEP_LANE、SET_SPEED、SET_SPEED且无需确认；均只是适配成功，不是车辆执行验收。第3模块精读完成时改动仅16份文档；发布同步另行统一了全体系哈希口径。

## 第4模块完成记录

- 覆盖14份实现记录和2份跨文件语义/专题页；13页共119处泛用占位按函数体改写，无占位的包导出页保留实际导出边界。
- 模块页补全 RouteManager、场景兼容合同、两类 progress tracker、恢复策略和生产 Pure Pursuit 有效值；明确 `docs/architecture/modules/04_ROUTE_AND_LATERAL_CONTROL.md` 是专题证据，20模块页仍是统一入口。
- 区分终点 A*、距离覆盖、验收局部路线、纯几何变道和 CARLA 拓扑变道；区分路线投影、实际累计里程、任务绝对里程与重规划 local s。
- RLC-01～RLC-05 继续作为接口重复、配置分散、长时状态上界、实车证据和浅不可变风险；本轮未修改实现，也未把历史 CARLA 报告升级为当前验收。
- 下一项为第5模块“纵向控制”，本轮不提前标记后续模块完成。

### 第4模块文档校验结果

14份实现页记录186个类/函数入口；119处旧占位清零，14个来源 Git blob SHA256 与当前源码一致，模块/实现/审计/进度文档中的471条本地链接无缺失。直接离线回归 `python -m pytest car_control_B/tests integration/tests/test_route_geometry.py integration/tests/test_route_manager.py integration/tests/test_route_planner.py integration/tests/test_runtime_stages.py -q` → **81 passed in 1.31s**；`git diff --check`通过。以上不包含CARLA闭环、远端模型或硬件验收。专题文档现已迁入 `docs/architecture/modules/04_ROUTE_AND_LATERAL_CONTROL.md`。

## 第5模块完成记录

- 逐项核对 `car_control_C` 13份有声明的实现页，83处泛用占位已改为当前函数的参数消费、返回、状态、副作用、异常和调用关系；对应页面已无原占位句。
- 纵向模块页补齐生产调用顺序、五类速度约束、停止状态边界、跟车/TTC缺测语义、融合确认、PID/episode重置、默认参数与 C→D 控制权。
- 纯 Python 静态/边界核对确认 M05-01：DrivingPolicy 构造的五个动态包络字段未传入 `dynamic_safety_distance`，当前仍由 `DEFAULT_STRATEGY` 决定；只登记，不修改控制代码。
- A07 重名测试发现问题继续保留。本机未提供 pytest，故本轮不声称离线套件或 CARLA 已重新运行。
- 下一项是第6模块“感知”；本轮没有提前把后续模块标为完成。

## 第6模块完成记录

- 核对12份实现页；10页共96处泛用占位按函数体改写，包导出和shell页保留无占位的实际入口说明。
- 模块页补齐三种sensor profile、同帧获取、LiDAR/Radar门限、前车短时保持、RGB控制走廊、地图灯态、目标ID和来源审计；明确生产bridge与独立perception benchmark管线的边界。
- 纯Python复现M06-01重复上游track ID导致同帧身份冲突，以及M06-02 canonical按列表首项绑定lead speed导致目标速度/TTC错配；只登记问题，未修改业务代码。
- 感知相关7份测试入口执行结果 **79 passed in 0.91s**；该结果不包含CARLA、真实ONNX、雨夜或真实传感器质量。
- 下一项是第7模块“安全仲裁”；本轮不提前标记后续模块完成。

## 第7模块完成记录

- 核对13份 `car_control_D` 实现页；其中12页共82处泛用占位按函数体改写，包导出页保留实际导出边界。
- 模块页明确生产 `ControlRuntime → SafetySupervisor` 与 canonical `DControlRuntime` 的适用范围，补齐 adapter/validator、仲裁优先级、动态安全距离、路线恢复、反馈终态、日志/benchmark/计分证据等级。
- 纯 Python 定点复现 M07-01：同一 canonical command 首帧终态 safety override 后，次帧可恢复推进控制但 feedback 仍是旧终态；只登记边界，未修改业务代码，且不扩大为当前 live runner 故障。
- D 相关测试入口执行结果 **35 passed in 0.53s**；不包含 CARLA、Qwen、真实传感器或官方评分一致性验收。
- 下一项是第8模块“场景执行与评分”；本轮不提前标记后续模块完成。
