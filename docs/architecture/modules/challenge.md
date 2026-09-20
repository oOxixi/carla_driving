# 挑战赛道模块

本页为可选分组索引。正常开发按 [项目入口](../README.md) 直接进入具体业务模块，再进入功能文档，共三级。

返回[项目架构索引](../README.md)。审查日期：2026-09-20；本页描述当前代码，不把历史实验结论视为部署验收。

## 边界与主链路

挑战赛道只替换高层规划器，沿用根目录 runtime 的接口注册、计划验证和 A/B/C/D 执行链。权威外部边界为 [ModelRequest Schema](../../../interfaces/model_request.schema.json) 与 [ManeuverPlan Schema](../../../interfaces/maneuver_plan.schema.json)，冻结校验见 [frozen_contracts.py](../../../challenge/planner/frozen_contracts.py)。修改 Schema 必须同时版本化更新冻结指纹。

Teacher/CARLA 日志 → B1 数据采集与治理 → A3 严格正样本视图 → Student 训练 → FP32 候选及 Gate → A1 ONNX → A4 工具链 → B3 HIL 证据。当前 ONNX 导出器只支持随机初始化；训练权重到 ONNX 尚未接通，板端工具链仍待确认。

## 功能索引

- [结构、预处理、训练张量契约](../modules/challenge-structure.md)
- [Planner 适配与就绪校验](../modules/challenge-planner.md)
- [数据采集、治理、发布和训练视图](../modules/challenge-data.md)
- [训练、评测、候选晋级](../modules/challenge-training.md)
- [ONNX、FLOPs 与部署](../modules/challenge-export.md)
- [HIL 测量、回放和证据](../modules/challenge-hil.md)

## 统一化规则

张量枚举与维度以 challenge/student/contract.py 为源；训练 mask 与输出约束以 training_contract.py 及 A3 校验为准。模型配置以 StudentModelConfig 为执行源，JSON/Markdown 为交付快照。数据必须选择明确 release_manifest 和训练视图；D1/D2/D3 是不同冻结或累计阶段，不能把多个 release 目录自动合并。实验报告与 evidence 是历史记录，不覆盖接口定义。

模型身份同时包含 git_sha、model_id、config_id、权重/产物 SHA256 和 dataset_version。PyTorch 权重 SHA 与 ONNX SHA 是不同产物身份，不能互换。A3_FP32_GATE_PASSED 不替代 B2/B3 验收。

## 已确认待处理

A3 Gate 未绑定 Student 评测的权重身份；板端完整 trace 与宿主标记发生重复；HIL 一致性验证未调用实际埋点 infer。详见功能页。此轮仅做文档审查，没有修复这些业务行为。
