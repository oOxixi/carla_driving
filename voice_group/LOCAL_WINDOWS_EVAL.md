# Windows 本机语音评测环境

已验证机器：RTX 5060 Laptop GPU 8 GB，NVIDIA Driver 591.86，Python 3.12。

## VSCode 环境

项目使用独立环境 `.venv-voice`，不要改 CARLA 自带 Python。

```powershell
python -m venv .venv-voice
.\.venv-voice\Scripts\python.exe -m pip install `
  torch==2.11.0 torchaudio==2.11.0 `
  --index-url https://download.pytorch.org/whl/cu130
.\.venv-voice\Scripts\python.exe -m pip install -r voice_group\requirements.txt
.\.venv-voice\Scripts\python.exe -m pip install "Pillow>=10,<13"  # 全仓 RGB 测试
```

验证：

```powershell
.\.venv-voice\Scripts\python.exe -c `
  "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))"
.\.venv-voice\Scripts\python.exe tools\verify_voice_weights.py
```

期望输出包含 `2.11.0+cu130`、`True` 和显卡名称。

## 运行 250 条干净音频

```powershell
.\.venv-voice\Scripts\python.exe tools\evaluate_voice_audio.py `
  --condition clean `
  --output artifacts\voice\local_clean_250.json
```

## 重要限制

- SenseVoiceSmall 当前 FunASR 高层接口只返回 `key` 和 `text`，没有逐句置信度，因此报告必须显示 ASR 置信度覆盖率；不能把 `null` 宣称为高置信度。
- faster-whisper 的校准分数必须写入 `verification_confidence` / `asr_verification`，不能覆盖或伪装成 SenseVoice 原生 `asr_confidence`。当前综合评分策略见 `CASCADE_ASR_EVAL_20260726.md`。
- 50 dBA 是声压级，必须使用声级计、固定播放/采集距离并保留校准记录；数字幅度或“50 dB SNR”不能替代官方 50 dBA 证据。
- `.venv-voice/` 已加入 `.gitignore`，不得提交数 GB Python/CUDA 环境。
