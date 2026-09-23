# 模块文档索引

本目录把跨文件、跨成员的工程职责整理成可执行模块文档。模块文档不是代码清单的重复，
而是回答五个问题：模块负责什么、接收什么、输出什么、怎样判定通过、当前还缺什么。

## 已细化模块

| 模块 | 文档 | 当前结论 |
|---|---|---|
| B1 数据发布 → A3 蒸馏接入 | [`B1_TO_A3_DATA_PIPELINE.md`](B1_TO_A3_DATA_PIPELINE.md) | D2+D3 签名累积视图、全量 RGB/输入门禁已接通；正式训练与独立 Gate 尚未执行 |
| 模型与权重生命周期 | [`MODEL_AND_WEIGHT_LIFECYCLE.md`](MODEL_AND_WEIGHT_LIFECYCLE.md) | Teacher 与 Student 结构已固定；真实 FP32 Gate、INT8 和 J6P 仍未完成 |
| A3 训练与 Hard-case 闭环 | [`A3_TRAINING_AND_HARD_CASES.md`](A3_TRAINING_AND_HARD_CASES.md) | D2 baseline 链路已运行；泛化证据、B3 回流接入与真实 FP32 Gate 仍未完成 |
| B2 独立评测与 A3 FP32 Gate | [`B2_EVALUATION_AND_FP32_GATE.md`](B2_EVALUATION_AND_FP32_GATE.md) | promotion 基础规则已实现；B2 评价包、冻结 Benchmark 与真实 Gate 证据仍未交付 |
| A2 INT8 量化与 QAT | [`A2_INT8_QUANTIZATION_AND_QAT.md`](A2_INT8_QUANTIZATION_AND_QAT.md) | 通用检查工具部分就绪；真实 FP32 导出、Calibration、PTQ/QAT 与 INT8 产物均未交付 |
| A4 OpenExplorer 与 J6P Runtime | [`A4_OPENEXPLORER_J6P_RUNTIME.md`](A4_OPENEXPLORER_J6P_RUNTIME.md) | X86 结构 Smoke 已有；生产 Runtime、固定工具链、J6P 产物与实机证据均未交付 |
| B3 HIL 与 J6P 独立实测 | [`B3_HIL_J6P_INDEPENDENT_VALIDATION.md`](B3_HIL_J6P_INDEPENDENT_VALIDATION.md) | 测量工具链和 X86 机制证据已就绪；正式 Runtime、Frozen Test、J6P 和遥测证据未交付 |
| B4 复现与最终交付 | [`B4_REPRODUCTION_RELEASE_AND_SUBMISSION.md`](B4_REPRODUCTION_RELEASE_AND_SUBMISSION.md) | 有基础赛道打包工具可参考；挑战赛道台账、Release schema、Docker 和 Final 包均未建立 |
| 04 路线与横向控制 | [`04_ROUTE_AND_LATERAL_CONTROL.md`](04_ROUTE_AND_LATERAL_CONTROL.md) | 本轮精读完成；主链、合同、失败语义和测试入口已落位，5 项边界/加固工作保留 |

## 按顺序精读进度

本表只记录已经用当前 `challenge` 代码完成实现映射的模块；“本轮完成”不等于遗留阻塞全部关闭。

| 顺序 | 模块 | 精读状态 |
|---:|---|---|
| 1 | 运行入口与帧控制 | 前序精读已完成；后续单独迁入本目录 |
| 2 | 异步规划 | 前序精读已完成；后续单独迁入本目录 |
| 3 | 命令与状态机 | 前序精读已完成；后续单独迁入本目录 |
| 4 | 路线与横向控制 | **本轮完成**：真实调用链、参数、合同、失败语义、测试和 RLC-01～RLC-05 已落文档 |
| 5 | 纵向控制 | **本轮完成**：13份实现页、83处占位改写，生产链、参数、缺测、重置、M05-01/A07 已落文档 |
| 6 | 感知 | **本轮完成**：12份实现页、10页96处占位改写，生产/参考链、同步、目标身份、来源和M06问题已落文档 |
| 7 | 安全仲裁 | **本轮完成**：13份实现页、12页82处占位改写，双入口、仲裁、动态阈值、终态与评分边界及M07-01已落文档 |
| 8 | 场景执行与评分 | **本轮完成**：9份实现页、8页98处占位改写，合同/几何、扩展、证据/验收、外部runner边界及M08-01已落文档 |
| 9 | 接口与坐标转换 | **本轮完成**：7份Schema字段页、Registry/canonical转换、单位/坐标/ID/时钟边界与M09-01已落文档 |
| 10 | Student 结构与预处理 | **本轮完成**：5份实现页、23处占位改写，四路张量/十Head/预处理/mask与M10-01已落文档 |
| 11 | Student Planner | **本轮完成**：8份实现页、22处占位改写，双Backend/解码修复/就绪身份与M11-01已落文档 |
| 12 | Teacher 数据治理 | **本轮完成**：33份实现页、301处占位改写，采集/release/view/切分/身份与M12-01已落文档 |
| 13 | 蒸馏与晋级 | **本轮完成**：25份实现/配置页、103处占位改写，标签/loss/checkpoint/Gate与A01已落文档 |
| 14 | 导出与部署 | **本轮完成**：6份实现页、13处占位改写，随机ONNX/真实权重/X86/J6P及R01/R03已落文档 |
| 15 | HIL 与测量 | **本轮完成**：20份实现/资源页、139处占位改写，Runtime/trace/身份/证据及A02/A03/R02已落文档 |
| 16 | 语音链 | **本轮完成**：14页、50处占位，级联ASR/NLU/授权/声学证据边界；A09保留 |
| 17 | Qwen 后端 | **本轮完成**：8页、78处占位，HTTP/service/backend/规则组装/身份边界；A04/A05保留 |
| 18 | 配置与场景合同 | **本轮完成**：9页、14处占位，生效优先级、坐标、校验和运行证据边界 |
| 19 | 运行环境与交付 | **本轮完成**：37页、4处占位，镜像/模型/数据/发布/提交门禁；A06保留 |
| 20 | 维护工具 | **本轮完成**：70页、342处占位，副作用、参数、cwd、返回码和证据边界；A06/A09保留 |

20项名称以 `docs/architecture/SEQUENTIAL_REVIEW.md` 的全量索引为准；本表与该索引同步更新，不再保留截图截断造成的 `UNKNOWN` 占位。

## 统一结构

后续每个模块按以下顺序编写：

1. **模块目标**：明确包含和不包含的职责。
2. **状态快照**：记录核对日期、Git SHA、数据/模型/配置版本，区分事实和计划。
3. **上下游合同**：列出输入、输出、所有者、schema、单位和失败语义。
4. **实现映射**：把职责映射到当前源码、配置、测试和证据，不写不存在的入口。
5. **可执行流程**：给出从干净环境可复现的最短命令。
6. **门禁**：说明 PASS 条件、失败处理和禁止绕过项。
7. **当前阻塞**：用代码或 manifest 事实说明，不能只写“待完善”。
8. **完成定义**：列出关闭阻塞所需的具体交付物和验证证据。

## 表述规则

- `Smoke`、开发集回归、正式训练、独立 Validation、Frozen Test 和 HIL 是不同证据等级。
- “支持”必须同时有实现入口和测试；只有设计说明时写“计划”或“未接入”。
- “通过”必须能定位到固定提交、配置、输入 manifest、原始输出和哈希。
- 数据集、模型和权重身份不得只写简称；正式证据记录 exact revision 或完整 SHA。
- 占位句必须改成可检查的阻塞项；无法确认的信息写 `UNKNOWN`，不得补造结果。
- 模块文档只描述当前主线；历史过程进入 `docs/reports/`，运行产物进入 `artifacts/`。
