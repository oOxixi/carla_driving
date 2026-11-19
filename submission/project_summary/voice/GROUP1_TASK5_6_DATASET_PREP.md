# Group 1 Task 5/6 Voice Dataset Preparation

- Generated UTC: `2026-08-02T04:00:41.348922+00:00`
- Source zip: `/home/student/yingzhaohou/carla_driving_upload_merged/data_short.zip`
- Source zip SHA256: `f1bd37827311abfe5d4349d3584f7d79da8442ce26ecb730739b6b92ba4f6656`
- Extracted root: `/home/student/yingzhaohou/carla_driving_upload_merged/data/group1_voice/data_short`
- Git commit: `72aaa0e742dd9b1ae68563ab9a62b2a55a1b920a`
- Official-for-evaluation flag: `True`

## Manifest Counts

| Condition | Entries | Unique texts | Unique source ids | Missing audio |
|---|---:|---:|---:|---:|
| clean | 2598 | 957 | 1000 | 0 |
| noise_50dba | 2598 | 957 | 1000 | 0 |

## Task Mapping

- Task 5 uses the generated manifests with `tools/evaluate_voice_audio.py` for real ASR, and `tools/run_group1_voice_text_regression.py` for deterministic text/intent/slot/safety gates.
- Task 6 uses the same manifests with `tools/run_group1_voice_fastpath_benchmark.py` to measure NLU fast-path latency and second-model trigger policy before full ASR benchmarking.
- The noisy manifest is marked `noise_50dba` because this archive is being treated as the official Group 1 audio drop for this workspace.

## Follow-up Commands

```bash
python3 tools/run_group1_voice_text_regression.py \
  --manifest artifacts/group1_voice/manifests/data_short_clean_manifest.json \
  --output artifacts/group1_voice/task5_text_regression_clean.json

python3 tools/run_group1_voice_fastpath_benchmark.py \
  --manifest artifacts/group1_voice/manifests/data_short_clean_manifest.json \
  --output artifacts/group1_voice/task6_fastpath_clean.json

python3 tools/evaluate_voice_audio.py \
  --manifest artifacts/group1_voice/manifests/data_short_clean_manifest.json \
  --audio-root data/group1_voice/data_short \
  --condition clean \
  --output artifacts/group1_voice/task5_asr_clean.json \
  --min-intent-accuracy 0.98

python3 tools/evaluate_voice_audio.py \
  --manifest artifacts/group1_voice/manifests/data_short_noisy_50dba_manifest.json \
  --audio-root data/group1_voice/data_short \
  --condition noise_50dba \
  --noise-level-dba 50.0 \
  --calibration-log artifacts/group1_voice/calibration/data_short_50dba_calibration.json \
  --output artifacts/group1_voice/task5_asr_noise_50dba.json \
  --min-intent-accuracy 0.98
```
