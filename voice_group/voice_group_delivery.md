# 语音组交付说明（给车辆控制组）

> 语音组已完成"语音 → 结构化驾驶命令"全链路，端到端 135ms（≤150ms 达标），
> 解析延时 7.6ms（≤50ms 达标），普通话识别 99%+。本文档说明交付内容与对接方式。

---

## 一、交付内容

| 模块 | 文件 | 作用 |
|---|---|---|
| A 语音识别 | `asr_vad.py` + `lora_finetuned/` | 音频→文字，含 VAD 截静音、LoRA 微调（普通话99%+） |
| B1 意图识别 | `vehicle_nlu/src/` | 文字→意图 |
| B2 槽位提取 | `nlu_b2/parser.py` | 意图→槽位 + 安全校验 |
| D 集成 | `pipeline.py` | 串起全链路，输出 DrivingCommand |
| 接口规范 | `voice_group_interface_spec.md` | 字段定义 |

## 二、对外接口：DrivingCommand（我们的输出 = 你们的输入）

一次真实输出示例（"进入隧道了，减速哈"）：
```json
{
  "schema_version": "1.0",
  "command_id": "cmd_4679fc8e",
  "source_text": "进入隧道了，减速哈。",
  "intent": "SLOW_DOWN",
  "parameters": {"mode": "RELATIVE", "action": "DECELERATE"},
  "asr_confidence": null,
  "intent_confidence": 0.95,
  "status": "valid",
  "ambiguity_type": "NONE",
  "confirm_required": false,
  "errors": [],
  "warnings": [{"code":"MISSING_OPTIONAL_SLOT","message":"未给出目标速度"}],
  "valid_duration_s": 3.0,
  "confidence": 0.95
}
```

## 三、字段对接（★ 需与车辆控制组逐条确认）

| 我们输出 | 类型 | 你们期望的字段名？ | 说明 |
|---|---|---|---|
| command_id | str | ? | 唯一 ID，反馈请原样带回 |
| intent | str | ? | 11 类之一（见规范） |
| parameters | dict | ? | 槽位（speed/direction/side/target/mode/action…） |
| status | str | ? | valid / unknown / missing_slot / unsafe / conflict … |
| ambiguity_type / confirm_required | str/bool | ? | 模糊/歧义→需安全兜底 |
| intent_confidence / asr_confidence | float | ? | 置信度 |
| errors / warnings | list | ? | 校验问题 |

**请车辆控制组确认**：字段名是否一致？`parameters` 里各意图的槽位键是否对齐？`status` 取值是否吻合你们的处理逻辑？

## 四、安全兜底（对应评分）
- `status != valid` 或 `intent == UNKNOWN` → `confirm_required = true`，请勿直接执行，做减速/停车/请求确认。

## 五、性能实测
- 普通话识别：干净 99.55% / 带噪 99.20%（去数据泄露）
- 解析延时（B1+B2）：7.6ms（目标≤50ms）✅
- 端到端：135ms（目标≤150ms）✅
- 含 VAD（语音活动检测），支持从连续音频切分指令

## 六、待联合完成
- 在 CARLA 中：你们接入 DrivingCommand → 驱动车辆执行 → 返回 ExecutionFeedback
- 两组联合验证"语音→CARLA 控车"全链路
