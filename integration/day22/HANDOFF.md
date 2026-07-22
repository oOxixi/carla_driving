# Day22 第一组技术交接

## 1. 交接范围

Day22 完成 Qwen2.5-VL 多模态高层决策稳定化、真实模型运行验证、CARLA RGB 场景验证、输出接口冻结和第二组控制链接口适配。

本交接只涉及：

```text
integration/day22/
```

不修改 Day20、Day21，也不改变第二组 A/B/C/D 的职责边界。

---

## 2. 职责边界

第一组负责：

- 用户命令与场景语义理解；
- Qwen 提示词构造；
- Qwen 原始 JSON 解析与校验；
- 高层动作候选生成；
- 防止编造目标；
- 禁止底层控制字段；
- 结构化 SafetyState 一致性检查；
- 输出统一 `decision` 和 `command`；
- 生成 smoke、safety、真实 Qwen 和多模态报告。

第一组不负责：

- 输出底层 `throttle/brake/steer`；
- 调用 `vehicle.apply_control()`；
- 替代 B/C 纵横向控制；
- 替代 D 最终安全仲裁；
- 上传 Qwen 模型权重。

---

## 3. 数据流

```text
用户语音文本
    +
RGB / perception
    +
第二组 SafetyState
    +
可选 scene_state
        |
        v
Day22Context
        |
        v
Qwen2.5-VL 候选动作
        |
        v
JSON/schema 校验
        |
        v
结构化状态一致性检查
        |
        +-- 危险程度被低估 -> SAFETY_RULE
        |
        +-- 无依据保守动作 -> QWEN_UNGROUNDED_REJECTED
        |
        v
最终 decision
        |
        v
command_adapter
        |
        v
统一 command envelope
        |
        v
A/B/C/D车辆控制链
        |
        v
D最终安全仲裁
```

第二组只消费最终 `command`。

---

## 4. 冻结输入接口

```python
from integration.day22.day22_context import Day22Context

context = Day22Context(
    voice_command="继续走",
    safety_state={},
    perception={},
    scene_state={}
)
```

主要 SafetyState 字段：

```text
front_distance_m
closing_speed_mps
ttc_s
object_class
object_confidence
visual_valid
lidar_valid
fused_valid
fusion_mode
recommended_action
traffic_light
distance_to_stop_line_m
input_confidence
```

---

## 5. 冻结输出接口

允许动作：

```text
START
STOP
SLOW_DOWN
SET_SPEED
EMERGENCY_STOP
```

低置信度统一使用：

```json
{
  "action": "STOP",
  "requires_confirmation": true
}
```

不使用 `STOP_CONFIRM`。

禁止：

```text
throttle
brake
steer
steering_angle
wheel_angle
```

---

## 6. command_adapter

```python
from integration.day22.command_adapter import build_command

command = build_command(
    decision,
    source_text=context.voice_command
)
```

关键字段：

```text
schema_version
command_id
source_text
intent
parameters
confidence
intent_confidence
status
ambiguity_type
confirm_required
valid_duration_s
reason_zh
```

---

## 7. 当前验证结果

离线：

```text
DAY22 SMOKE PASS 12
DAY22 SAFETY PASS
```

真实 Qwen：

```text
runtime_success: 12/12
qwen_format_valid: 12/12
qwen_action_valid: 12/12
multimodal_image_cases: 4
text_only_cases: 8
qwen_raw_action_accuracy: 66.7%
final_action_accuracy: 100%
final_confirmation_accuracy: 100%
```

正确表述：

```text
真实Qwen原始高层动作准确率约为66.7%。
经过结构化SafetyState安全覆盖和一致性仲裁后，
最终交给车辆侧的高层动作达到12/12正确。
```

不能表述为“Qwen准确率100%”。

---

## 8. 已知问题

Qwen主要问题：

- 低估 TTC 紧急程度；
- 安全场景中无依据停车；
- 雨天场景过度保守；
- 无行人场景错误声称距离不足。

`hallucination_cases` 同时表示编造目标、结构化矛盾和无依据保守动作。

`QWEN_UNGROUNDED_REJECTED` 只应在结构化状态明确安全、有效且新鲜时使用。状态缺失、过期或不可靠时应停车或请求确认。

---

## 9. 运行方式

无模型回归：

```bash
python -m integration.day22.day22_smoke_test
python -m integration.day22.day22_safety_test
python -m integration.day22.generate_day22_results
python -m integration.day22.generate_day22_validation_report
```

真实 Qwen 文本+状态：

```bash
python -m integration.day22.run_day22_qwen_runtime   --model-path models/Qwen2.5-VL-7B   --allow-text-only

python -m integration.day22.generate_day22_qwen_runtime_report
```

真实 RGB 多模态：

```bash
python -m integration.day22.run_day22_qwen_runtime   --model-path models/Qwen2.5-VL-7B   --image-map integration/day22/day22_runtime_image_map.local.json

python -m integration.day22.generate_day22_qwen_runtime_report
```

---

## 10. CARLA RGB生成

```bash
python -m integration.day22.capture_day22_scene   --scene empty   --output artifacts/day22_runtime/no_pedestrian.png   --spawn-index 10

python -m integration.day22.capture_day22_scene   --scene pedestrian   --output artifacts/day22_runtime/pedestrian.png   --spawn-index 10

python -m integration.day22.capture_day22_scene   --scene red_light   --output artifacts/day22_runtime/red_light.png

python -m integration.day22.capture_day22_scene   --scene front_vehicle   --output artifacts/day22_runtime/front_vehicle.png   --spawn-index 10
```

不要同时运行两个拥有 CARLA world 时钟的 runner。

---

## 11. 模块调用示例

```python
from integration.day22.day22_context import Day22Context
from integration.day22.qwen_day22_adapter import Day22QwenAdapter
from integration.day22.command_adapter import build_command

context = Day22Context(
    voice_command="保持速度",
    safety_state={
        "front_distance_m": 8.0,
        "closing_speed_mps": 1.0,
        "ttc_s": 8.0,
        "lidar_valid": True
    },
    perception={},
    scene_state={}
)

decision = Day22QwenAdapter().infer(context)
command = build_command(decision, context.voice_command)
```

真实模型：

```python
adapter = Day22QwenAdapter(model_infer=my_qwen_infer)
```

```python
def my_qwen_infer(prompt: str) -> str:
    ...
```

必须返回 JSON 字符串。模型输出不能绕过安全覆盖。

---

## 12. GitHub提交范围

应提交：

```text
integration/day22/qwen_runtime.py
integration/day22/run_day22_qwen_runtime.py
integration/day22/generate_day22_qwen_runtime_report.py
integration/day22/capture_day22_rgb.py
integration/day22/capture_day22_scene.py
integration/day22/qwen_prompt_v2.py
integration/day22/qwen_day22_adapter.py
integration/day22/day22_runtime_image_map.example.json
integration/day22/day22_qwen_runtime_results.json
integration/day22/day22_qwen_runtime_report.json
integration/day22/README.md
integration/day22/HANDOFF.md
integration/day22/DAY22_ISSUES.md
```

不要提交：

```text
models/Qwen2.5-VL-7B/
integration/day22/day22_runtime_image_map.local.json
artifacts/day22_runtime/
__pycache__/
```

---

## 13. 干净克隆验证

其他成员 clone 后，无需模型即可执行：

```bash
python -m integration.day22.day22_smoke_test
python -m integration.day22.day22_safety_test
```

真实 Qwen 验证需要本地模型；真实多模态验证还需要 CARLA RGB 图片和 `.local.json` 映射。

只有干净 clone 中 smoke/safety 通过，才能确认没有隐藏本地依赖。
