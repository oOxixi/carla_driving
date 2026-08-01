# Group 1 Day 7/24 最终交付 ✅

分支: `feat/day23-qwen-finalization` | Day23 协议冻结版 | 全部脚本已测试通过

## 文档文件

| 文件 | 作用 |
|------|------|
| `FINAL_DEMO.md` | 答辩材料：视觉架构(YOLO11 ONNX)、Qwen决策流程、完整链路时间线、12案例清单、5项Q&A、答辩口径、团队总结 |
| `CASE_VERIFICATION.md` | 8案例逐项检查：Qwen输入-输出-中文解释-真实场景对应-安全仲裁结果 |
| `HANDOFF.md` | 交接清单：7项任务完成对照、Day22/23上下文、Group1↔Group2协议 |
| `README.md` | 本文件 — 交付总览与运行指南 |

## 演示脚本 (全部 ✅ 已测试)

| 文件 | 作用 | 需CARLA | 实测结果 |
|------|------|:--:|------|
| `demo_visual.py` | 连接CARLA生成前车+行人，采集RGB帧(800×450, FOV=100°)，ONNX YOLO11检测，输出标注图+SafetyState JSON | ✅ | 检出2目标: person(0.89) + car(0.85), 337ms |
| `demo_qwen_decision.py` | 加载Day22真实Qwen2.5-VL运行时结果(12案例)，展示输入→Qwen输出→校验→安全仲裁→最终决策 | ❌ | 8/8案例正确，SAFETY_RULE + QWEN_UNGROUNDED_REJECTED仲裁 |
| `demo_full_chain.py` | 完整链路：CARLA视觉(ONNX检测) + Day22真实Qwen决策 + 安全仲裁汇总 | ✅ | 视觉2目标 + Qwen 12/12安全(100%) |

## 输出物

所有演示脚本输出到 `evidence/` 目录：

| 输出文件 | 来源 |
|------|------|
| `demo_carla_raw.png` | CARLA 原始 RGB 帧 |
| `demo_carla_detected.png` | ONNX 检测标注图 (bbox + 类别 + 置信度) |
| `demo_carla_safety_state.json` | 结构化 SafetyState |
| `demo_qwen_summary.json` | Day22 Qwen 12案例摘要 |
| `full_chain_raw.png` | 完整链路 CARLA RGB 帧 |

## 运行

```powershell
cd "d:\nana\carla_driving-refs-pull-6-head\carla_driving-refs-pull-6-head"
$py = "C:\Users\吴奕铭\AppData\Local\Programs\Python\Python312\python.exe"

# 1. Qwen决策演示 (无需CARLA, 立即可跑)
& $py deliveries\day7_24\demo_qwen_decision.py

# 2. 视觉识别演示 (需CARLA运行中)
& $py deliveries\day7_24\demo_visual.py

# 3. 完整链路演示 (需CARLA运行中)
& $py deliveries\day7_24\demo_full_chain.py
```

## 技术栈

| 组件 | 说明 |
|------|------|
| 目标检测 | YOLO11n ONNX (`artifacts/models/yolo11n.onnx`), 默认置信度0.35, 6类道路参与者 |
| 多模态决策 | Qwen2.5-VL-7B, Day22: `day22_v2` prompt (5动作) / Day23: `day23-final-v1` (10动作白名单) |
| 安全仲裁 | SAFETY_RULE 优先, QWEN_UNGROUNDED_REJECTED 拦截幻觉 |
| 模拟器 | CARLA, Town10HD, 同步模式, 800×450 RGB, FOV=100° |

## 前期完成

| 日期 | 交付 | 指标 |
|------|------|------|
| 7/20 | Qwen-VL 原型 (`integration/day20/`) | 基础多模态推理 |
| 7/21 | 安全决策 (`integration/day21/`) | 10/10 测试 |
| 7/22 | Qwen2.5-VL 实测 (`integration/day22/`) | 12/12 runtime, 安全仲裁后 100% |
| 7/23 | 协议冻结 | 17 测试, day23-final-v1, 10 动作白名单 |
| 7/24 | **最终交付** (本目录) | 3 演示脚本, 4 文档, 全部 ✅ 通过 |
