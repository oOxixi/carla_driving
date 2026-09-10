# A1 Student 模型接口交付

本文是 A1 向 A2/A3/A4 交付的单一入口。代码中的 `contract.py`、
`training_contract.py` 和 `StudentModelConfig` 为权威定义，本文只作可读说明。

## 1. 模型入口与调用链

- PyTorch 模型：`challenge/student/model.py::StudentPlannerV0`
- 固定输入预处理：`challenge/student/preprocess.py::StudentPreprocessor`
- Head 到 ManeuverPlan V2：`challenge/planner/student_adapter.py::StudentPlanAdapter`
- 运行入口：`challenge/planner/student_backend.py::StudentBackend.infer`
- ONNX 导出入口：`python -m challenge.export.export_onnx`
- 训练 padding/mask：`challenge/student/training_contract.py`
- 机器可读配置：`challenge/student_config.json`

Python 调用方式：

```python
from challenge.student import StudentPlannerV0, StudentPreprocessor

model = StudentPlannerV0().eval()
tensors = StudentPreprocessor()(model_request)
outputs = model(*tensors.as_tuple())  # dict[str, torch.Tensor]
```

## 2. `forward` 输入

签名为 `forward(rgb, text_tokens, targets, state) -> dict[str, Tensor]`。Python
实现中的首维可取 `B`；交付的 ONNX 为 J6P 工具链固定 `B=1`。四个输入均为
`torch.float32`，ONNX 类型均为 `tensor(float)`。

| 字段 | 固定 ONNX shape | 内容 |
|---|---:|---|
| `rgb` | `[1,3,224,224]` | RGB、CHW、ImageNet mean/std 归一化；等比例缩放和 letterbox |
| `text_tokens` | `[1,32]` | `source_text` 前 32 个 Unicode 字符的固定数值编码，不足补 0 |
| `targets` | `[1,8,14]` | 最多 8 个目标；5 维类别 one-hot、距离、相对速度、置信度、6 维相对位置 |
| `state` | `[1,64]` | 灯态、风险、间距/TTC、速度约束、行为许可、意图/方向、车道与路由能力 |

输入张量由 `StudentPreprocessor` 从冻结的 `ModelRequest V1` 生成。超出 32 字符或
8 个目标时按原顺序确定性截断；缺少图像或图像文件不存在时 `rgb` 全 0。不能把
原始可变长字符串、对象 ID 或 JSON 直接传入 `forward`。

## 3. `forward` 输出

Python 返回以下具名 `dict`；所有值均为 `torch.float32`。ONNX 因部署接口限制通过
`StudentOnnxExportWrapper` 按下表顺序导出，但名称和 shape 不变。

| key | shape（B=1） | 含义/解码 |
|---|---:|---|
| `plan_length_logits` | `[1,4]` | 类别 0..3 对应实际 1..4 步 |
| `behavior_logits` | `[1,4,14]` | 每步 behavior 分类 |
| `target_pointer_logits` | `[1,4,9]` | 0..7 指当前请求中的目标；8=`NONE` |
| `target_lane_logits` | `[1,4,6]` | 每步目标车道分类 |
| `target_speed_mps` | `[1,4]` | sigmoid 后的 m/s，范围 `[0,50]` |
| `completion_type_logits` | `[1,4,8]` | 每步完成条件分类 |
| `on_failure_logits` | `[1,4,4]` | 每步失败策略分类 |
| `confidence` | `[1,1]` | sigmoid 后计划置信度，范围 `[0,1]` |
| `requires_confirmation_logits` | `[1,1]` | `>=0` 判定需确认；Adapter 还会执行安全兜底 |
| `replan_condition_logits` | `[1,7]` | 多标签，逐项 `>=0` 激活重规划条件 |

模型不输出 `steer`、`throttle`、`brake` 或轨迹点；输出经 Adapter 约束修复后形成
`ManeuverPlan V2`，再由既有控制组执行。

## 4. 类别映射（index → label）

### behavior（14 类）

| ID | 类别 | ID | 类别 |
|---:|---|---:|---|
| 0 | `KEEP_LANE` | 7 | `TURN_RIGHT` |
| 1 | `SET_SPEED` | 8 | `CHANGE_LANE_LEFT` |
| 2 | `SLOW_DOWN` | 9 | `CHANGE_LANE_RIGHT` |
| 3 | `STOP` | 10 | `AVOID_OBSTACLE` |
| 4 | `YIELD` | 11 | `RETURN_TO_LANE` |
| 5 | `FOLLOW` | 12 | `PULL_OVER` |
| 6 | `TURN_LEFT` | 13 | `HOLD` |

### target_lane（6 类）

`0=CURRENT`，`1=LEFT_ADJACENT`，`2=RIGHT_ADJACENT`，`3=ROUTE_BRANCH`，
`4=SHOULDER`，`5=NONE`。

### completion（8 类）

`0=SPEED_BELOW`，`1=SPEED_REACHED`，`2=LANE_CENTERED`，
`3=JUNCTION_EXITED`，`4=TARGET_GAP_REACHED`，`5=TARGET_PASSED`，
`6=STOPPED`，`7=HOLD_FRAMES`。

### on_failure（4 类）

`0=SAFE_STOP`，`1=HOLD_CURRENT_LANE`，`2=REPLAN`，`3=CONFIRM`。

### replan（7 个独立二分类标签）

`0=TARGET_LOST`，`1=LANE_BLOCKED`，`2=ROUTE_MISMATCH`，
`3=NEW_EMERGENCY_OBJECT`，`4=PROGRESS_STALLED`，`5=ROUTE_DEVIATION`，
`6=PLAN_EXPIRING`。

## 5. 1–4 步 Plan 的 padding 与 mask

`ManeuverPlan V2` 约束计划长度为 1–4，因此 Student 固定为 4 个 step slot：

```text
plan_length: int64[B]，合法值 1..4
plan_length_class = plan_length - 1
step_mask[b,i] = (i < plan_length[b])，dtype=bool，shape=[B,4]
```

例：长度 `[1,3]` 的 mask 为 `[[1,0,0,0],[1,1,1,0]]`。padding slot 写入中性值：

- `behavior=HOLD(13)`
- `target_pointer=NONE(8)`
- `target_lane=NONE(5)`
- `target_speed_mps=0.0`
- `completion=HOLD_FRAMES(7)`
- `on_failure=HOLD_CURRENT_LANE(1)`

所有逐步 Head 的 loss 必须乘 `step_mask`，padding slot 的 loss 权重为 0；
`plan_length`、`confidence`、`requires_confirmation` 和计划级多标签 `replan` 不使用
step mask。推理先由 `argmax(plan_length_logits)+1` 取有效步数；若有效区域中出现
`STOP`、`HOLD` 或 `PULL_OVER`，Adapter 在该终止动作后立即截断。

可执行实现为 `build_step_mask`、`plan_length_to_class`、`masked_step_mean`；非法长度、
非整数 dtype 或 shape 错误均直接抛异常。

## 6. 当前配置与初始化

- `model_id`: `student-v0-r3-fp32`
- `config_id`: `student-v0-r3-structure-20260911`
- 视觉分支：通道 `3→32→64→128→256→384`，5 个 stride-2 3×3 Conv/ReLU，
  固定 2×2 AveragePool 将 7×7 保留为 3×3，再投影到 512 维
- 文本/目标/状态分支：各两层 512 维 Linear/ReLU
- 融合：`2048→3072→3072→1024` Linear/ReLU
- Head：10 个，参数量 23,006,581，FP32
- Conv：Kaiming normal（ReLU）；Linear：Xavier uniform；全部 bias=0
- 可复现结构导出前调用 `torch.manual_seed(20260911)`，然后实例化模型
- 最大预测速度：50 m/s；batch 固定 1；ONNX opset 17；无 dynamic axes

当前 `student_v0_fp32.onnx` 是**随机初始化的结构/工具链冒烟产物**，不是可申报准确率
的训练权重。A3 必须用同一 `model_id/config_id` 训练并生成含权重 SHA256、数据集版本、
Git SHA 和 `A3_FP32_GATE_PASSED` 的 manifest，运行后端才会报告 production-ready。

## 7. 最小验收

```powershell
py -3.12 -m pytest -q challenge/tests/test_a1_student.py
py -3.12 -m challenge.export.export_onnx --output challenge/student_v0_fp32.onnx
py -3.12 -m challenge.export.validate_artifacts --root .
```

验收覆盖：输入/输出 shape 与 dtype、dict key、类别与 padding ID、mask、初始化可复现、
Python dict 到 ONNX 固定顺序一致性、ONNX 数值一致性和产物 SHA/元数据一致性。
