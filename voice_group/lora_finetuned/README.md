---
library_name: peft
base_model: iic/SenseVoiceSmall
license: other
license_name: FunASR-Model-License-1.1
tags:
- lora
- automatic-speech-recognition
- chinese
---

# SenseVoiceSmall 车载语音 LoRA（备用）

这是仓库保留的备用 PEFT LoRA 适配器。当前生产入口 `voice_group/asr_vad.py` 加载的是 `lora_dialect/`，不会加载本目录；切换前必须重新运行完整真实音频与噪声评测。

## 模型信息

- 基础模型：`iic/SenseVoiceSmall`
- 架构：SenseVoiceSmall + PEFT LoRA
- PEFT：0.19.1
- LoRA：`r=8`，`alpha=16`，`dropout=0.05`
- 目标模块：`linear_q_k_v`、`linear_out`
- 权重：`adapter_model.safetensors`
- SHA-256：`87cea17b9208e009e2e306fd8000ec14edbbc3a1835b65fd3bd85ec043062ff5`
- 大小：6,922,192 bytes

## 已知限制

当前仓库没有保留该权重的训练数据、训练脚本、超参数记录和独立评测报告，因此不能推断它优于生产适配器，也不能把其他版本的成绩归因于它。模型输出必须经过 B1/B2 和安全适配边界，不得直接控制车辆。

## 许可证

基础模型和该微调衍生权重适用 [FunASR Model Open Source License Agreement 1.1](https://github.com/modelscope/FunASR/blob/main/MODEL_LICENSE)。使用或分享时必须注明 FunASR / SenseVoiceSmall 来源、作者并保留模型名称。详见 `voice_group/LICENSES.md`。
