# 比赛提交材料入口

本目录用于把评分要求、运行证据和最终提交包建立一一对应关系。

1. `SCORING_TRACEABILITY_0725.md`：评分项、当前证据、缺口和完成定义。
2. `SUBMISSION_CHECKLIST_0725.md`：冻结版本前逐项勾选。
3. `EVIDENCE_INDEX_TEMPLATE.json`：机器可读证据索引，复制后填入真实路径、哈希和结果。
4. `DEMO_RECORD_TEMPLATE.md`：每个正式场景一次一份，禁止只用口头结论。
5. `OFFLINE_VALIDATION_0725.md`：Qwen 严格边界、语言代理集、数据集构建和回放的本机验证记录。
6. `REAL_CLOSED_LOOP_EVIDENCE_20260727.md`：真实 Qwen、RGB/LiDAR、CARLA 控制闭环及三个代表场景证据。
7. `BATCH_QWEN_SCENARIO_EVIDENCE_20260728.md`：真实 Qwen 冻结代理集批测和三场景 60 次多 seed 实跑。
8. `QWEN_TARGET_ASSOCIATION_EVIDENCE_20260728.md`：5 张真实 CARLA RGB、
   10 条多目标指令及两轮 100% 目标关联复测证据。
9. `QWEN_ROBUSTNESS_EVIDENCE_20260728.md`：天气、行人和遮挡目标的 10 张
   RGB、20 条指令及失败保留/修复复测证据。
10. `LONG_STABILITY_EVIDENCE_20260728.md`：30 分钟 RGB+LiDAR、周期 Qwen、
    GPU 显存/利用率、掉帧和结束后恢复证据。

比赛细则来源：<https://acndoaymjsa1.feishu.cn/docx/QVlodTanIo1IRhx7AcMcvA7RndQ>，本次核对日期为 2026-07-25，页面显示最新修改日期为 07 月 17 日。

注意：官网明确主办方不提供公开训练/测试集，最终使用隐藏评测集；因此本地通过只能证明实现和代理场景有效，不能写成“已通过官方测试”。
