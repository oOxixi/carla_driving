# Day22：Qwen 多模态高层决策稳定化与场景验证

## 目标
Day22 在 Day21 已冻结接口上，用 smoke 和 safety 场景继续验证红灯、前车、行人、低置信度、TTC、传感器缺失和冲突命令。

Qwen/决策层只输出高层动作，不输出 `throttle`、`brake`、`steer`。底层控制由 A/B/C 生成，D 保留最终安全否决权。

## 冻结输出接口
允许动作：
- `START`
- `STOP`
- `SLOW_DOWN`
- `SET_SPEED`
- `EMERGENCY_STOP`

低置信度不新增 `STOP_CONFIRM` 动作，统一表示为：

```json
{
  "action": "STOP",
  "requires_confirmation": true,
  "confidence": 0.4,
  "reason_zh": "安全输入置信度不足"
}
```

这样第二组仍只消费已知动作 `STOP`，并通过 `requires_confirmation` 进入确认/安全保持流程。

输出字段：
- `action`
- `confidence`
- `requires_confirmation`
- `reason_zh`
- `target_speed_mps`（可选）

禁止字段：
- `throttle`
- `brake`
- `steer`

## 第二组 SafetyState 兼容字段
兼容 C 组：
`frame`、`sim_time_s`、`front_distance_m`、`closing_speed_mps`、`ttc_s`、`object_class`、`object_confidence`、`visual_valid`、`lidar_valid`、`fused_valid`、`fusion_mode`、`recommended_action`、`reason`、`source_by_field`。

兼容 A/D：
`traffic_light`、`distance_to_stop_line_m`、`input_confidence`、`weather`。

没有 `object_class` 时不得猜测目标类别；LiDAR-only 只能解释距离/TTC风险。

## 运行
```bash
python -m integration.day22.day22_smoke_test
python -m integration.day22.day22_safety_test
python -m integration.day22.generate_day22_results
python -m integration.day22.generate_day22_validation_report
```

预期：
```text
DAY22 SMOKE PASS 12
DAY22 SAFETY PASS
```

## 第二组调用
```python
from integration.day22.day22_context import Day22Context
from integration.day22.qwen_day22_adapter import Day22QwenAdapter
from integration.day22.command_adapter import build_command

context = Day22Context(
    voice_command="继续走",
    safety_state={
        "traffic_light": "RED",
        "distance_to_stop_line_m": 5.0
    },
    perception={}
)

decision = Day22QwenAdapter().infer(context)
command = build_command(decision, context.voice_command)
```
