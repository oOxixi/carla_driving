# 条件 ASR 复核与综合评分策略

## 结论

交付链路以 SenseVoice + LoRA 为主识别器，`faster-whisper small` 只复核可能改变车辆控制的指令。策略优先保证普通话、台湾国语、速度数值和横向方向，不为低权重方言持续支付双模型延迟。

方言仍由主模型支持，250 条本地真实录音上的总体意图准确率为 99.60%，槽位准确率为 99.20%；级联不会用 Whisper 文本替换 SenseVoice 文本。

## 执行策略

- `UNKNOWN` 已被主解析器拒绝，不再启动复核模型。
- `STOP` / `EMERGENCY_STOP` 走快速安全通道，复核模型不能延迟或阻止停车。
- 速度、变道、转向、靠边、避障、加减速等控制指令按需复核。
- 只有校准置信度不低于 0.90 且关键控制语义冲突时才新增确认门。
- 目标名中的同音字不参与控制冲突判定；速度值、单位和左右方向仍严格比较。
- SenseVoice 原生置信度与 Whisper 复核置信度分开记录，禁止用后者冒充前者。
- 模型不可用时，对本应复核的指令保持失败关闭。

可用环境变量：

```text
VOICE_CASCADE_ENABLED=1
VOICE_CASCADE_MODEL=small
VOICE_CASCADE_DEVICE=cuda
VOICE_CASCADE_COMPUTE_TYPE=int8_float16
VOICE_CASCADE_MIN_CONFIDENCE=0.90
SENSEVOICE_MODEL_PATH=<可选的本地 SenseVoice snapshot>
FSMN_VAD_MODEL_PATH=<可选的本地 FSMN-VAD snapshot>
```

若未设置模型路径，Windows 会优先使用用户目录下已经存在的 ModelScope `snapshots/master`，缺失时才使用模型 ID。

## 校准边界

`voice_group/models/faster_whisper_small_confidence.json` 来自普通话和台湾国语、clean 与 10 dB 合成噪声共 200 次本机推理。它不是人工标注的官方 50 dBA 校准集，因此不能替代最终赛场/队友机器上的真人录音与 50 dBA 证据。

CPU tiny 模型虽然更快，但关键语义准确率明显不足，已否决；生产配置固定为 GPU small。

## 自动化证据

```powershell
python -m pytest -q voice_group/tests/test_asr_cascade.py
python -m pytest -q voice_group/tests/test_whisper_calibration.py
```

正式结果必须在目标机器重跑，输出写入 `artifacts/reports/voice/`，不得沿用旧机器摘要。
