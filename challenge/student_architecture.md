# Student V0 架构与结构压缩记录

## 结构

```text
RGB 1×3×224×224 ─ Tiny CNN ───────────────┐
Text 1×32 ─────── two-layer MLP ──────────┤
Targets 1×8×14 ── two-layer MLP ──────────┼─ Fusion MLP ─ 10 structured heads
State 1×64 ────── two-layer MLP ──────────┘
```

视觉分支采用 5 层 stride-2 Conv2D、ReLU 和固定 3×3 空间池化，保留粗粒度左右/前后
位置；其余分支只使用 Linear/ReLU。
Fusion 使用固定宽度 `2048→3072→3072→1024`。模型中没有动态 Shape、动态循环、
NonZero、Scatter、自定义 Attention、3D 算子或 Python 数据相关控制流。

## V0 结果

- 参数量：23,006,581（FP32 权重约 87.76 MiB）。
- 固定 batch 单次：249,320,448 MAC，按 1 MAC=2 FLOPs 为 498,640,896 FLOPs。
- 相对冻结 2B Teacher 的极端保守下界（只算 28 层文本主干的单个 token，排除视觉、
  序列和嵌入计算）：约 0.177，仍满足 `≤0.5`。
- 该比例是结构 FLOPs 边界，不是 J6P 时延、功耗或异构利用率实测。

Student 已远低于 0.5 FLOPs 目标，因此 V0 不做表演性剪枝。后续仅当 A3 精度或 A4
算子转换证明确有必要时才调整宽度/层数，并必须产生新 `model_id` 和重新训练。

## 版本记录

| 版本 | 结构变化 | 状态 |
|---|---|---|
| `student-v0-fp32` | 首次交付；全局池化、关系/提示信息缺失 | 已撤销，不得用于 A2/A3 |
| `student-v0-r2-fp32` | 固定 Shape、3×3 空间网格、关系/命令/路由特征、安全 Adapter | 已由 r3 接替 |
| `student-v0-r3-fp32` | 具名 dict Head、显式配置/初始化、可执行 padding/mask 契约 | 当前 A1 结构候选，待 A3 蒸馏 |

随机初始化 ONNX 仅用于 A2/A4 提前打通工具链，不能用于宣称模型准确率。
