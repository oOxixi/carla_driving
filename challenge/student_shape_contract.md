# Student V0 固定 Shape 契约

## 输入

| 名称 | dtype | Shape | 来源 |
|---|---|---:|---|
| `rgb` | float32 | `1×3×224×224` | `ModelRequest.rgb_ref`，缺失时全零 |
| `text_tokens` | float32 | `1×32` | `source_text` 的固定长度 Unicode 数值编码 |
| `targets` | float32 | `1×8×8` | 当前请求中前 8 个目标，顺序不变 |
| `state` | float32 | `1×32` | 灯态、风险、速度约束、车道能力和允许行为 |

`targets` 每项为：5 维类别 one-hot、归一化距离、归一化相对速度、置信度。所有维度
固定，超长文本和目标只在预处理边界确定性截断，不进入模型动态控制流。

## 输出

顺序固定为：

```text
plan_length_logits          1×4
behavior_logits             1×4×14
target_pointer_logits       1×4×9
target_lane_logits          1×4×6
target_speed_mps            1×4
completion_type_logits      1×4×8
on_failure_logits           1×4×4
confidence                  1×1
requires_confirmation_logits 1×1
replan_condition_logits     1×7
```

`target_pointer` 的 0–7 只指向**当前** `ModelRequest.targets`，8 表示无目标。Adapter
再映射为本次请求里的 `target_id`，模型不保存也不生成动态字符串。所有枚举均由
`challenge/student/contract.py` 固定。

模型永远不输出 `steer/throttle/brake`。Adapter 负责速度上限、必停约束、车道可用性、
目标存在性和低置信度确认；输出随后再次经过既有 `PlanValidator`。

