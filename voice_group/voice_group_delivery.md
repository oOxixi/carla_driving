# 语音组交付说明（给车辆控制组）

> 语音 → 结构化驾驶命令的代码链路、250 条标准文本回归和 250 条干净音频 GPU 实跑已经完成。
> 50 dBA 环境噪声仍需声级计校准后的录音；本文不沿用缺少原始日志的旧数字。

---

## 一、交付内容

| 模块 | 文件 | 作用 |
|---|---|---|
| A 语音识别 | `asr_vad.py` + `lora_dialect/` | 音频→文字，含 VAD 与当前生产 LoRA |
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

## 三、字段对接

| 我们输出 | 类型 | 说明 |
|---|---|---|
| command_id | str | 唯一 ID，反馈原样带回 |
| intent | str | 见接口规范中的意图表 |
| parameters | dict | 槽位（speed/direction/side/target/mode/action…） |
| status | str | 只有 `valid` 可进入后续执行映射 |
| ambiguity_type / confirm_required | str/bool | 模糊或复杂动作进入确认门控 |
| intent_confidence / asr_confidence | float/null | 置信度 |
| errors / warnings | list | 结构化校验问题 |

## 四、安全兜底（对应评分）
- ASR 置信度低于 0.60 → `LOW_ASR_CONFIDENCE`，禁止执行。
- `status != valid`、`intent == UNKNOWN` 或 `errors` 非空 → 车辆适配器输出未授权 `NO_OP`。
- 相对减速不会再退化成 `NO_OP`，而是映射为保守速度目标。
- 复杂动作必须确认/多模态决策，语音模型不直接输出底层控制量。

## 五、当前验收状态

- 标准文本解析：250/250，五种语言分别 50/50，意图与期望槽位均为 100%。
- 自动化：`python -m pytest -q voice_group/tests`。
- 本机环境：RTX 5060 Laptop 8 GB，PyTorch 2.11.0+cu130。
- 全仓离线测试：360 passed，1 skipped（2026-07-26）。
- 模型完整性：两份 LoRA 权重 SHA-256 已写入 `MODEL_MANIFEST.json` 并可自动校验。
- 干净音频 250 条：ASR 字符准确率 99.24%，意图 99.60%，槽位 99.20%，无推理异常。
- 端到端延迟：mean 91.32 ms、P95 109 ms、P99 172 ms、max 172 ms。
- ASR 置信度覆盖率：0%。当前 SenseVoice/FunASR 高层接口没有返回逐句 score，不能把 `null` 当高置信度。
- 50 dBA：未完成，等待校准录音。

## 六、待联合完成
- 使用声级计录制 50 ± 1 dBA 版本并运行全部 250 条。
- 若评分强制要求 ASR 置信度，接入能输出经过校准 score 的 ASR 后端；CTC 最大后验实验无法可靠区分当前漏字/漏零错误，不能冒充校准置信度。
- 在 CARLA 中联合验证语音 → DrivingCommand → 控车 → ExecutionFeedback。
