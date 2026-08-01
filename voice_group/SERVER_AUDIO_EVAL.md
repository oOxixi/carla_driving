# 服务器音频验收步骤

## 1. 前置检查

管理员修复驱动并重启后，以下两条必须成功：

```bash
nvidia-smi
python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())"
```

要求：`nvidia-smi` 不再出现 `Driver/library version mismatch`，且 Python 输出 `True`。随后在项目环境安装：

```bash
pip install -r voice_group/requirements.txt
python tools/verify_voice_weights.py
```

## 2. 干净音频 250 条

```bash
mkdir -p artifacts/voice
python tools/evaluate_voice_audio.py \
  --condition clean \
  --output artifacts/voice/clean_250.json \
  2>&1 | tee artifacts/voice/clean_250.console.log
```

必须保留：

- `clean_250.json`：逐条原始结果；
- `clean_250.md`：逐语言准确率和延迟摘要；
- `clean_250.console.log`：控制台运行日志。

## 3. 50 dBA 环境噪声 250 条

50 dBA 是声压级，不能只靠调整 MP3 数字音量来证明。用声级计把播放/采集位置校准到 `50 ± 1 dBA`，保存设备、距离、时间、读数和照片/视频编号到 `calibration.txt`；录制后的数据目录须保持 manifest 的相对路径，例如 `mandarin/0001.mp3`。

```bash
python tools/evaluate_voice_audio.py \
  --condition noise_50dba \
  --audio-root /data/voice_50dba \
  --noise-level-dba 50 \
  --calibration-log /data/voice_50dba/calibration.txt \
  --output artifacts/voice/noise_50dba_250.json \
  2>&1 | tee artifacts/voice/noise_50dba_250.console.log
```

## 4. 验收项

- 每个条件必须是 250 条、每种语言 50 条，无 `--limit`；
- 干净音频意图准确率至少 95%；
- 50 dBA 条件按比赛要求检查成功率，目标至少 90%；
- 报告必须包含每种语言的 ASR 完全匹配率、字符准确率、意图准确率、槽位准确率；
- 延迟必须包含 ASR、NLU、端到端各自的 mean/P95/P99/max；
- JSON 中的 `git_commit`、模型 SHA-256 校验日志、GPU/驱动信息必须一起归档。
