# 语音链路接口规范

版本：`DrivingCommand 1.0`

入口：

```python
from voice_group.pipeline import audio_to_command

envelope = audio_to_command(audio)
```

`audio` 可以是音频文件路径，或 16 kHz 单声道 `float32` NumPy 数组。返回值必须是普通 Python `dict`，并由 `integration.voice_adapter.VoiceCommandAdapter` 做最终安全校验。

## 输出字段

| 字段 | 类型 | 必需 | 约束 |
|---|---|---:|---|
| `schema_version` | string | 是 | 固定为 `"1.0"` |
| `command_id` | string | 是 | 单次命令唯一，非空 |
| `source_text` | string | 是 | ASR 输出，非空才可能执行 |
| `intent` | string | 是 | 见下方意图表 |
| `parameters` | object | 是 | 意图槽位 |
| `asr_confidence` | number/null | 是 | `[0,1]`；低于 `0.60` 禁止执行 |
| `intent_confidence` | number | 是 | `[0,1]` |
| `status` | string | 是 | 只有 `valid` 允许进入执行映射 |
| `ambiguity_type` | string | 是 | 无歧义为 `NONE` |
| `confirm_required` | boolean | 是 | `true` 时不得直接执行 |
| `errors` / `warnings` | array | 是 | 元素为 `{"code","message"}` |
| `t_audio_start_ns` | integer/null | 是 | 单调时钟纳秒 |
| `t_asr_end_ns` | integer/null | 是 | 单调时钟纳秒 |
| `t_intent_end_ns` | integer/null | 是 | 单调时钟纳秒 |
| `valid_duration_s` | number | 是 | 正数，默认 `3.0` |
| `confidence` | number | 是 | 执行侧使用的 `[0,1]` 置信度 |
| `_latency` | object | 否 | `asr_ms`、`nlu_ms`、`total_ms` |

## 意图与槽位

| 意图 | 必需槽位 | 执行边界 |
|---|---|---|
| `EMERGENCY_STOP` | 无 | 紧急制动 |
| `STOP` | 无 | 正常停车 |
| `SET_SPEED` | `speed`, `unit="km/h"` | 转换为 m/s 后执行 |
| `SLOW_DOWN` | 目标速度，或 `mode=RELATIVE, action=DECELERATE` | 相对减速映射为保守 `2.0 m/s` 目标 |
| `KEEP_LANE` | `mode=KEEP_CURRENT_LANE` | 保持当前车道 |
| `SPEED_UP`、`PULL_OVER`、`AVOID_OBSTACLE`、`CHANGE_LANE`、`FOLLOW_ROUTE`、`TURN` | 依意图而定 | 复杂动作必须进入确认/多模态决策链路 |
| `UNKNOWN` | 无 | 永不授权控制 |

## 安全规则

满足任一条件时，适配器必须输出未授权的 `NO_OP` 和拒绝反馈：

- `status != "valid"`；
- `intent == "UNKNOWN"`；
- `errors` 非空；
- ASR 置信度存在且低于 `0.60`；
- schema、字段类型、速度或单位不合法。

低 ASR 置信度的标准错误码为 `LOW_ASR_CONFIDENCE`，状态为 `low_confidence`。复杂动作即使解析成功，也必须带确认门控，不能由语音模型直接产生油门、刹车或方向盘数值。

## 兼容性

- 时间延迟使用主机单调时钟；命令过期时间由 CARLA 仿真时间重新建立，两者不得混算。
- 当前 ASR 后端无法可靠提供置信度时会返回 `null`。这是兼容路径，不等价于“高置信度”；比赛部署前应确认所用后端能稳定输出可校准分数。
