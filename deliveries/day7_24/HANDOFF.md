# Group 1 Day 7/24 交接文档

基于 `feat/day23-qwen-finalization`。

## 任务完成对照

| # | 任务 | 对应文件 |
|---|------|------|
| 1 | 最终演示：视觉识别+Qwen决策 | `FINAL_DEMO.md` 一(视觉) + 二(Qwen) |
| 2 | Qwen输入/输出/中文解释对应检查 | `CASE_VERIFICATION.md` (12案例) + `FINAL_DEMO.md` 四(清单) |
| 3 | 现场Q&A | `FINAL_DEMO.md` 五 (5题, 含Day22实测数据) |
| 4 | 多模态决策链路 | `FINAL_DEMO.md` 三 (时间线 + 安全覆写流程) |
| 5 | 答辩口径 | `FINAL_DEMO.md` 六 |
| 6 | 第一组成果说明 | `FINAL_DEMO.md` 七 (架构图 + 7项指标) |
| 7 | 高层决策可被Group2接管 | Day23协议 + Day22 100% 安全仲裁验证 |

## Day23 已完成

- `DAY23_HANDOFF.md`: Group1↔Group2 集成协议
- `DAY23_MODEL_AND_BOUNDARY.md`: 模型选型、边界、答辩应答
- 17 个测试通过
- Prompt 冻结 `day23-final-v1`, 10 动作白名单冻结
- 冻结代码: `integration/day20/` (prompt/schemas/parser/decision_trace)
- Qwen 运行时: `integration/day22/` (12 真实案例验证)

## Day22 真实 Qwen 验证

- 12/12 runtime, 100% 安全仲裁后准确率
- 原始准确率 66.7% → 仲裁后 100%
- 4 幻觉被拦截, 4 安全覆写正确触发
- 平均延迟 1.83s

## Day24 最终交付 ✅

- 3 演示脚本全部测试通过:
  - `demo_qwen_decision.py`: 加载 Day22 12 案例, 展示 Qwen 决策 + 安全仲裁流程
  - `demo_visual.py`: CARLA + ONNX YOLO11 检测, 实测检出 person + car
  - `demo_full_chain.py`: CARLA 视觉识别 + Day22 真实 Qwen 决策完整链路
- 4 文档定稿: README.md, FINAL_DEMO.md, CASE_VERIFICATION.md, HANDOFF.md
- 证据输出: `evidence/` 目录 (RGB帧, 标注图, SafetyState JSON, Qwen摘要)
