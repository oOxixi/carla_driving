# 模块文档索引

本目录把跨文件、跨成员的工程职责整理成可执行模块文档。模块文档不是代码清单的重复，
而是回答五个问题：模块负责什么、接收什么、输出什么、怎样判定通过、当前还缺什么。

## 已细化模块

| 模块 | 文档 | 当前结论 |
|---|---|---|
| B1 数据发布 → A3 蒸馏接入 | [`B1_TO_A3_DATA_PIPELINE.md`](B1_TO_A3_DATA_PIPELINE.md) | D2 v1.1 已形成训练路径；D3 Wave1 仅可审计，尚不能正式训练 |
| 模型与权重生命周期 | [`MODEL_AND_WEIGHT_LIFECYCLE.md`](MODEL_AND_WEIGHT_LIFECYCLE.md) | Teacher 与 Student 结构已固定；真实 FP32 Gate、INT8 和 J6P 仍未完成 |
| A3 训练与 Hard-case 闭环 | [`A3_TRAINING_AND_HARD_CASES.md`](A3_TRAINING_AND_HARD_CASES.md) | D2 baseline 链路已运行；泛化证据、B3 回流接入与真实 FP32 Gate 仍未完成 |
| B2 独立评测与 A3 FP32 Gate | [`B2_EVALUATION_AND_FP32_GATE.md`](B2_EVALUATION_AND_FP32_GATE.md) | promotion 基础规则已实现；B2 评价包、冻结 Benchmark 与真实 Gate 证据仍未交付 |
| A2 INT8 量化与 QAT | [`A2_INT8_QUANTIZATION_AND_QAT.md`](A2_INT8_QUANTIZATION_AND_QAT.md) | 通用检查工具部分就绪；真实 FP32 导出、Calibration、PTQ/QAT 与 INT8 产物均未交付 |
| A4 OpenExplorer 与 J6P Runtime | [`A4_OPENEXPLORER_J6P_RUNTIME.md`](A4_OPENEXPLORER_J6P_RUNTIME.md) | X86 结构 Smoke 已有；生产 Runtime、固定工具链、J6P 产物与实机证据均未交付 |

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
