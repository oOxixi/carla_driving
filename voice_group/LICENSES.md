# 语音模型与数据许可证说明

## SenseVoiceSmall 与 LoRA 衍生权重

基础模型为 `iic/SenseVoiceSmall`。其模型卡声明采用 **FunASR Model Open Source License Agreement 1.1**：

- 模型页：<https://www.modelscope.cn/models/iic/SenseVoiceSmall>
- 官方协议：<https://github.com/modelscope/FunASR/blob/main/MODEL_LICENSE>

该协议把微调衍生模型也纳入“FunASR 软件”，允许在遵守协议的前提下使用、复制、修改和分享；使用或分享时必须注明来源、作者并保留模型名称。本项目保留名称 **FunASR / SenseVoiceSmall**，并声明两个 LoRA 适配器均为其衍生权重。

FunASR/SenseVoice 代码仓库与模型权重的协议并不相同。代码仓库当前为 MIT License，模型及衍生权重以以上 FunASR Model License 1.1 为准。

## 测试音频

`test_samples/` 是通过 Edge TTS 合成的比赛内部回归样本，不代表真实方言说话人分布，也不能单独支撑真实语音或 50 dB 环境噪声成绩。对外分发或商业使用前，提交方仍需复核所使用 TTS 服务的届时条款。

## 项目源代码

仓库目前没有由版权所有者明确选择的项目级开源许可证。本文件不会替版权所有者擅自授权源代码。最终公开提交前，应由仓库所有者选择并添加项目级 `LICENSE`；在此之前默认保留全部权利。
