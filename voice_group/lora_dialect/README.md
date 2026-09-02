---
library_name: peft
base_model: iic/SenseVoiceSmall
license: other
license_name: FunASR-Model-License-1.1
tags:
- lora
- automatic-speech-recognition
- chinese
- cantonese
- dialect
---

# SenseVoiceSmall 车载方言 LoRA

这是生产链路 `voice_group/asr_vad.py` 当前加载的 PEFT LoRA 适配器，用于车载中文、粤语及方言语音识别。它必须与基础模型 `iic/SenseVoiceSmall` 一起加载，不能独立推理。

## 模型信息

- 基础模型：`iic/SenseVoiceSmall`
- 架构：SenseVoiceSmall + PEFT LoRA
- PEFT：0.19.1
- LoRA：`r=8`，`alpha=16`，`dropout=0.05`
- 目标模块：`linear_q_k_v`、`linear_out`
- 权重：`adapter_model.safetensors`
- SHA-256：`38d541099157ba5c35d8256f2ebd8a374cae85a5ca7eb9b2a7cb8a033c624de1`
- 大小：6,922,192 bytes

## 用途与限制

预期用途是比赛车载语音命令的 ASR 前端。输出必须继续经过 B1/B2 解析、安全阈值和车辆适配器；模型不得直接输出油门、刹车或方向盘控制量。

当前仓库没有保留此权重的训练数据清单、训练脚本、训练轮次、随机种子和完整训练指标，因此不能声明可独立复现训练过程。`test_samples/` 是 Edge TTS 合成回归集，不是训练数据证据，也不代表真实方言人群。

正式准确率与延迟必须在目标机器重跑，并把原始报告写入
`artifacts/reports/voice/` 后再建立哈希索引；本目录不保存历史机器的生成结果。

50 dBA 环境噪声尚未完成；该条件必须使用声级计校准录音。当前 FunASR 接口没有返回逐句 score，报告中的 ASR 置信度覆盖率为 0%，不得宣称已完成置信度校准。

## 加载

```python
from funasr import AutoModel
from peft import PeftModel

model = AutoModel(model="iic/SenseVoiceSmall", device="cuda:0")
model.model = PeftModel.from_pretrained(
    model.model,
    "voice_group/lora_dialect",
).to("cuda:0")
model.model.eval()
```

## 许可证

基础模型和该微调衍生权重适用 [FunASR Model Open Source License Agreement 1.1](https://github.com/modelscope/FunASR/blob/main/MODEL_LICENSE)。使用或分享时必须注明 FunASR / SenseVoiceSmall 来源、作者并保留模型名称。详见 `voice_group/LICENSES.md`。
