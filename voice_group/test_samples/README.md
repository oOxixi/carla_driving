# 测试样本使用说明（车辆控制组）

本目录提供语音链路的测试样本，供你们验证 `audio_to_command` 是否正常工作。

## 内容
- `mandarin/` — 普通话 50 条
- `dialect/dongbei|shaanxi|yueyu|taiwan/` — 东北/陕西/粤语/台湾国语 各 50 条
- `manifest.json` — 标准答案（每条的正确文本、意图、槽位）

音频均为 edge-tts 合成，16kHz 单声道 mp3，可自由使用。

## 用法：标准文本自动化回归

```bash
python -m pytest -q voice_group/tests/test_manifest_regression.py
```

该测试读取全部 250 条，而不是抽取 README 示例；总体及每种语言的意图、期望槽位子集均要求至少 95%。

## 说明
- `intent` 判对即算成功（识别文本可能有语气词/同音字差异，不影响意图）。
- `UNKNOWN` 类是故意放的"不可执行指令"（如"帮我订外卖"），应触发安全兜底（confirm_required=true）。
- 音频数组输入：也可用 soundfile 读成 16kHz 数组后传入 `audio_to_command(数组)`，更接近实时场景。
- 真实 ASR 与延迟证据使用 `tools/evaluate_voice_audio.py`；标准文本回归不能替代真实音频成绩。
