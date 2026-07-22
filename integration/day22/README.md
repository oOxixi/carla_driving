# Day22：Qwen2.5-VL 多模态高层决策稳定化与安全验证

## 1. 工作目标

Day22 在已有 Day20/Day21 高层决策接口基础上，完成：

- smoke 与 safety 场景验证，覆盖红灯、前车、行人、低置信度、TTC、传感器失效；
- 优化 Qwen 提示词，减少编造目标、忽略 SafetyState、输出底层控制量和解释过长；
- 分开统计 Qwen 原始动作与最终安全覆盖动作；
- 整理第二组需要补充的距离、TTC、停止线距离和状态有效性字段；
- 提供可供第二组批量验证的统一高层命令；
- 提供 CARLA RGB 场景截图生成和真实多模态验证流程。

Qwen 只负责高层语义理解和候选动作。最终动作必须经过结构化状态校验和安全策略覆盖。第二组只消费最终 `command`，不直接消费未经校验的 Qwen 原始文本。

---

## 2. 当前完成情况

### 2.1 确定性回归

```text
DAY22 SMOKE PASS 12
DAY22 SAFETY PASS
```

已验证：

- 红灯近停止线：`STOP`
- 可靠行人：`STOP`
- 前车距离不足：`SLOW_DOWN`
- 低 TTC：`EMERGENCY_STOP`
- 低置信度：`STOP + requires_confirmation=true`
- 传感器失效：安全停车
- LiDAR-only：只根据距离/TTC决策，不猜测类别
- 无行人场景：不生成行人原因
- 输出不含 `throttle/brake/steer`
- 中文原因不超过 20 个汉字

### 2.2 真实 Qwen2.5-VL 验证

当前真实运行结果：

```text
真实 Qwen 推理成功：12/12
真实 CARLA RGB 多模态场景：4
文本+结构化状态场景：8
Qwen JSON 格式有效：12/12
Qwen 动作字段合法：12/12
底层控制字段违规：0
最终安全动作正确：12/12
最终确认状态正确：12/12
```

Qwen 原始动作正确率约为 66.7%。主要错误：

- 低估 TTC 紧急风险；
- 在结构化状态明确安全时无依据停车；
- 雨天场景动作过度保守；
- 无行人场景错误声称距离不足。

这些错误保留在：

```text
integration/day22/day22_qwen_runtime_report.json
```

经过 `SAFETY_RULE` 和 `QWEN_UNGROUNDED_REJECTED` 仲裁后，最终高层动作达到 12/12 正确。

> Qwen 原始准确率和最终安全动作准确率必须分开报告，不能把最终 100% 描述为模型自身准确率。

---

## 3. 已知但可接受的问题

### 3.1 Qwen 原始动作并非全部正确

这是模型高层语义判断误差，不是最终控制链错误。

```text
危险程度被低估
    -> SAFETY_RULE

无结构化证据的保守动作
    -> QWEN_UNGROUNDED_REJECTED
```

### 3.2 `hallucination_cases` 范围较宽

该字段不仅表示“编造行人”，还包括：

- 与结构化距离矛盾的风险描述；
- 无依据的保守停车；
- 无红灯状态却声称红灯；
- 传感器有效却声称传感器失效。

### 3.3 无依据停车不能在所有状态下直接改为前进

Day22 固定测试只在结构化状态明确安全时拒绝 Qwen 无依据停车。正式车辆链还应保证：

- 状态时间戳新鲜；
- SafetyState 有效；
- 感知来源可用；
- D 未触发接管；
- 用户命令允许继续。

状态缺失、过期或不可靠时应停车或请求确认。

---

## 4. 目录结构

```text
integration/day22/
├── __init__.py
├── day22_context.py
├── safety_adapter.py
├── qwen_prompt_v2.py
├── qwen_day22_adapter.py
├── command_adapter.py
├── day22_cases.py
├── day22_smoke_test.py
├── day22_safety_test.py
├── generate_day22_results.py
├── generate_day22_validation_report.py
├── qwen_runtime.py
├── run_day22_qwen_runtime.py
├── generate_day22_qwen_runtime_report.py
├── capture_day22_rgb.py
├── capture_day22_scene.py
├── day22_runtime_image_map.example.json
├── day22_results.json
├── day22_validation_report.json
├── day22_qwen_runtime_results.json
├── day22_qwen_runtime_report.json
├── README.md
├── HANDOFF.md
├── DAY22_ISSUES.md
├── REQUIRE_SECOND_GROUP_STATE.md
└── DEMO_FLOW.md
```

实际 RGB 图片、模型权重和本地映射属于本地依赖或运行产物，不默认提交 GitHub。

---

## 5. 统一输入接口

```python
from integration.day22.day22_context import Day22Context

context = Day22Context(
    voice_command="继续走",
    safety_state={
        "traffic_light": "RED",
        "distance_to_stop_line_m": 5.0
    },
    perception={},
    scene_state={}
)
```

- `voice_command`：用户语音转文本；
- `safety_state`：第二组 C/A/D 的结构化安全状态；
- `perception`：视觉语义结果；
- `scene_state`：可选车辆和场景补充状态。

缺失目标类别时不得猜测车辆或行人。

---

## 6. 统一输出接口

允许动作：

```text
START
STOP
SLOW_DOWN
SET_SPEED
EMERGENCY_STOP
```

示例：

```json
{
  "action": "STOP",
  "confidence": 0.98,
  "requires_confirmation": false,
  "reason_zh": "红灯安全约束优先",
  "decision_source": "SAFETY_RULE"
}
```

低置信度：

```json
{
  "action": "STOP",
  "confidence": 0.4,
  "requires_confirmation": true,
  "reason_zh": "安全输入置信度不足",
  "decision_source": "SAFETY_RULE"
}
```

不新增 `STOP_CONFIRM`。

禁止 Qwen 输出：

```text
throttle
brake
steer
steering_angle
wheel_angle
```

---

## 7. 第二组 command 接口

```python
from integration.day22.command_adapter import build_command

command = build_command(decision, source_text="继续走")
```

输出关键字段：

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

第二组只消费最终 `command`。

---

## 8. 离线 smoke 与 safety 回归

```bash
python -m integration.day22.day22_smoke_test
python -m integration.day22.day22_safety_test
python -m integration.day22.generate_day22_results
python -m integration.day22.generate_day22_validation_report
```

查看：

```bash
cat integration/day22/day22_validation_report.json
```

该测试不加载 Qwen 权重，其他成员 clone 后可直接执行。

---

## 9. 真实 Qwen2.5-VL 文本+状态测试

模型目录：

```text
models/Qwen2.5-VL-7B
```

模型权重不上传 GitHub。

运行：

```bash
python -m integration.day22.run_day22_qwen_runtime   --model-path models/Qwen2.5-VL-7B   --allow-text-only

python -m integration.day22.generate_day22_qwen_runtime_report
```

---

## 10. 获取真实 CARLA RGB 图片

```bash
mkdir -p artifacts/day22_runtime

python -m integration.day22.capture_day22_scene   --scene empty   --output artifacts/day22_runtime/no_pedestrian.png   --spawn-index 10

python -m integration.day22.capture_day22_scene   --scene pedestrian   --output artifacts/day22_runtime/pedestrian.png   --spawn-index 10

python -m integration.day22.capture_day22_scene   --scene red_light   --output artifacts/day22_runtime/red_light.png

python -m integration.day22.capture_day22_scene   --scene front_vehicle   --output artifacts/day22_runtime/front_vehicle.png   --spawn-index 10
```

不要同时运行两个拥有 CARLA world 时钟的 runner。

---

## 11. 真实 RGB 多模态验证

```bash
cp   integration/day22/day22_runtime_image_map.example.json   integration/day22/day22_runtime_image_map.local.json

python -m integration.day22.run_day22_qwen_runtime   --model-path models/Qwen2.5-VL-7B   --image-map integration/day22/day22_runtime_image_map.local.json

python -m integration.day22.generate_day22_qwen_runtime_report
cat integration/day22/day22_qwen_runtime_report.json
```

当前正式结果：

```json
{
  "runtime_success": 12,
  "multimodal_image_cases": 4,
  "text_only_cases": 8,
  "qwen_raw_action_accuracy": 0.6666666666666666,
  "final_action_accuracy": 1.0,
  "forbidden_control_field_cases": []
}
```

---

## 12. 供其他成员调用

### 不加载模型

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

### 接入自定义 Qwen

```python
adapter = Day22QwenAdapter(model_infer=my_qwen_infer)
decision = adapter.infer(context)
```

```python
def my_qwen_infer(prompt: str) -> str:
    ...
```

返回 JSON 字符串，仍会经过 schema 校验、安全覆盖和结构化一致性仲裁。

---

## 13. 第二组需要提供的关键字段

红灯：

```text
traffic_light
distance_to_stop_line_m
```

前车：

```text
front_distance_m
closing_speed_mps
ttc_s
```

行人：

```text
object_class
object_confidence
visual_valid
front_distance_m
lidar_valid
```

状态有效性：

```text
visual_valid
lidar_valid
fused_valid
fusion_mode
recommended_action
reason
source_by_field
```

建议补充时间一致性：

```text
frame
sim_time_s
source_timestamps_s
```

---

## 14. GitHub提交边界

应提交：

```text
integration/day22/*.py
integration/day22/*.md
integration/day22/day22_runtime_image_map.example.json
integration/day22/day22_results.json
integration/day22/day22_validation_report.json
integration/day22/day22_qwen_runtime_results.json
integration/day22/day22_qwen_runtime_report.json
```

不要提交：

```text
models/Qwen2.5-VL-7B/
integration/day22/day22_runtime_image_map.local.json
artifacts/day22_runtime/
__pycache__/
```

其他人 clone 后无需模型即可运行 smoke/safety；真实 Qwen 验证需要自行准备模型权重和 CARLA 图片。
