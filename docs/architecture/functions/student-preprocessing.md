# Student 四路输入打包与信息损失边界

上级：[Student 结构模块](../modules/challenge-structure.md)。

## 实际行为

[StudentPreprocessor](../../../challenge/student/preprocess.py) 把一个 ModelRequest 转成 `TensorizedRequest`；`as_tuple()` 按 rgb/text_tokens/targets/state 顺序供模型调用。这里不仅是 reshape，还定义了网络能看到什么、哪些信息被丢弃。

| 输入 | 当前转换 | 维护风险 |
|---|---|---|
| rgb_ref | 文件存在时转 RGB、thumbnail 等比例缩放、居中填充到 224×224，CHW，除 255 后 ImageNet mean/std；缺失/不存在返回全零 | thumbnail 不会把小图放大成全幅。缺图全零与真实黑图归一化后的值不同；训练与部署必须同实现 |
| source_text | 前 32 个字符，各值 `(ord(c) % 65535) / 65535`，不足补零 | 不是 tokenizer/embedding，也不保证长组合指令尾部被保留；不能将模型能力等同于语言大模型 |
| targets | 原顺序最多 8 个，每个 14 维：类别 one-hot、距离、相对速度、置信度、关系标记 | 没有重新按风险排序。改变排序必须同步 pointer 标签和 Adapter grounding |
| state | 64 维固定槽位，填灯态、风险、gap/TTC、速度约束、允许行为、command_hint、车道与路由能力 | 不是任意车辆状态字典；新增键不自动进入网络，必须分配槽位并训练 |

距离/速度特征有裁剪归一化；目标关系由字符串中 left/right/center/ahead/front/behind/rear 等内容转为标志。具体槽位由 `_targets/_state` 代码决定，不能仅凭总 Shape 判断接口未变。

## 上下游一致性

A3 的 [a1_student.py](../../../challenge/distillation/a1_student.py) 使用真实 packer；HIL/部署路径也必须遵守相同转换。网络输出 target_pointer 是当前 targets 的索引，NONE=8。截断后看不到的第九个目标不能保留旧监督索引继续训练。

## 典型改动的完成范围

若改文本编码、RGB resize、目标排序或 state 槽位，即使 tensor Shape 不变也属于语义接口改变。需要同步模型配置/版本、A3 输入核验与训练数据、部署预处理、ONNX 比较及报告。只重新导出旧权重不能证明保留精度。

验证入口：[A1 tests](../../../challenge/tests/test_a1_student.py)、[A3 A1 integration](../../../challenge/distillation/tests/test_a1_integration.py)、[validate_a1_inputs](../../../challenge/distillation/validate_a1_inputs.py)。应同时检查缺图、长文本、超过 8 目标、不同关系和不同 speed hint，而不是只断言 Shape。

## 固定槽位明细（当前实现）

下表索引均从0开始；初始张量为0，没有填入的槽位保留0。类别顺序是契约，不能按字母排序。

| targets索引 | 定义 |
|---|---|
| 0–4 | vehicle、pedestrian、cyclist、obstacle、unknown one-hot |
| 5 | min(distance_m,200)/200，缺失取0；非负有效性由上游约束保障 |
| 6 | relative_speed_mps/30，裁剪[-1,1]；None保持0 |
| 7 | confidence，缺失取0 |
| 8–12 | relation包含left、right、center、ahead/front、behind/rear |
| 13 | 上述relation标记均不存在 |

| state索引 | 定义 |
|---|---|
| 0–3 | RED、YELLOW、GREEN、UNKNOWN one-hot |
| 4–8 | LOW、CAUTION、HIGH、EMERGENCY、UNKNOWN one-hot |
| 9–10 | min_gap_m上限100后/100；ttc_s上限20后/20，None保持0 |
| 11–12 | speed_limit_mps、max_target_speed_mps上限50后/50 |
| 13–15 | must_stop、left_gap_safe、right_gap_safe |
| 16–29 | BEHAVIORS契约顺序的allowed标志；TURN/CHANGE_LANE按方向展开，must_stop只允许STOP |
| 30–31 | min(目标数,8)/8；route_available |
| 32–43 | KEEP_LANE、SET_SPEED、SLOW_DOWN、STOP、EMERGENCY_STOP、YIELD、FOLLOW、TURN、CHANGE_LANE、AVOID_OBSTACLE、RETURN_TO_LANE、PULL_OVER意图one-hot |
| 44 | hint.target_speed_mps上限50后/50 |
| 45–47 | hint.direction LEFT、RIGHT、STRAIGHT |
| 48–51 | left_lane_exists、right_lane_exists、intersection_ahead、stop_line_clear |
| 52–53 | routing.disposition是否CONFIRM_SAFE；score/10裁剪[-1,1] |
| 54–57 | safe_wait_behavior为KEEP_LANE_LIMITED、SLOW_DOWN、STOP、EMERGENCY_STOP的one-hot |
| 58 | min(routing.reasons数量,8)/8 |
| 59–60 | return_direction LEFT、RIGHT |
| 61 | current_lane存在且等于original_lane |
| 62 | min(grounded_target_ids数量,8)/8 |
| 63 | 当前未写入，保持0 |

这补充了Shape之外的接口语义；修改任何槽位都需联动训练、Adapter和部署预处理。缺失值编码0与真实0在部分槽位不可区分，不能把这些值当成完整测量。
