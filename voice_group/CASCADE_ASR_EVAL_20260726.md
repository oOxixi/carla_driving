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

## 本机实测

文件：`artifacts/voice/local_clean_250_cascade_priority_20260726.json`

| 指标 | 结果 |
|---|---:|
| 样本 | 250 |
| ASR 完全匹配 | 95.60% |
| 字符准确率 | 99.24% |
| 意图准确率 | 99.60% |
| 槽位准确率 | 99.20% |
| 条件复核触发 | 155 / 250（62.00%） |
| ASR 均值延迟 | 92.02 ms |
| 条件复核均值延迟（仅触发样本） | 315.79 ms |
| 端到端均值 / P95 / P99 / max | 287.88 / 438.00 / 508.16 / 593.00 ms |

策略调整前复核触发 236 次，端到端均值 391.50 ms。调整后准确率不变，复核触发减少 81 次，平均端到端延迟下降约 26.5%。

该轮报告中 42 个总确认门包括 27 条非驾驶指令、13 条超速指令、1 条粤语漏识别，以及 1 条由“障碍物”同音字引起的模型分歧。最后一项已由关键控制语义比较修复并加入自动化测试；正式证据生成前应在最终提交机上重跑一次完整评测。

## 校准边界

`voice_group/models/faster_whisper_small_confidence.json` 来自普通话和台湾国语、clean 与 10 dB 合成噪声共 200 次本机推理。它不是人工标注的官方 50 dBA 校准集，因此不能替代最终赛场/队友机器上的真人录音与 50 dBA 证据。

CPU tiny 模型虽然更快，但关键语义准确率明显不足，已否决；生产配置固定为 GPU small。

## 自动化证据

```powershell
python -m pytest -q voice_group/tests/test_asr_cascade.py
python -m pytest -q voice_group/tests/test_whisper_calibration.py
```

全仓核心测试结果：372 passed，1 skipped。跳过项是需要外部运行环境的测试，不是级联逻辑失败。
