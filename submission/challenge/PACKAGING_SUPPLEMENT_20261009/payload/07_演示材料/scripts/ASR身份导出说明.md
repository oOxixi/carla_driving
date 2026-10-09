# ASR 前端身份离线导出

`export_asr_identity.py` 使用标准库，读取当前源码、配置及明确的模型路径，对真实存在的文件计算 SHA256，缺失项输出 `missing`。不导入 ASR 后端、不加载模型、不下载或安装权重、不运行 250 条音频。

在本目录执行 `python export_asr_identity.py`，默认生成同目录 `asr_identity.json`。也可用 `--package-root <原完整包目录>`；输出路径必须在包内。该文件可直接归档现有 LoRA、级联置信度配置和前端源码身份，减少重复手工提供这些文件及哈希的工作。

源码默认主模型为 `iic/SenseVoiceSmall`，LoRA 位于 `voice_group/lora_dialect`，VAD 默认启用，级联模型为 faster-whisper small。脚本按照 `SENSEVOICE_MODEL_PATH`、`FSMN_VAD_MODEL_PATH` 或源码确切默认缓存路径查找，级联仅检查明确模型路径或 Hugging Face 的 `Systran/faster-whisper-small` main 缓存引用。若使用其他非路径级联模型名称，本脚本不会推测对应缓存映射。

2026-10-09 本机有边界检查：包内 `adapter_model.safetensors`、`adapter_config.json` 和 `models/faster_whisper_small_confidence.json` 存在；SenseVoice、FSMN-VAD 的源码默认 ModelScope 缓存，以及相应明确 hub 目录均未找到；Hugging Face faster-whisper-small 明确目录未找到。相关模型路径环境变量未设置。因此可以导出现有适配器／配置身份，但不能在本机完成完整 ASR 前端权重绑定，也不能据此声称离线识别可运行。

导出的身份仅表示当前文件和环境，不自动绑定历史 250 条 ASR 成绩，也不等于当前 Student 同批语音测试结果。需要在实际运行机器再次导出，并与该次原始转写、运行配置及日志一起保存，才有可追溯的同次证据。源码注释中的准确率不会被本脚本当作成绩采纳。
