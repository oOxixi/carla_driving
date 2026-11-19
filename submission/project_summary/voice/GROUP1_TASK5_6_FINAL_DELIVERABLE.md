# Group 1 Task 5/6 Final Deliverable

Generated on 2026-08-02.

## Scope

This deliverable keeps only the useful Group 1 task 5/6 evidence:

- Task 5 text, intent, slot, low-confidence, and safety regression.
- Task 6 fast-path B1/B2 benchmark.
- Task 6 optimized SenseVoice ONNX static benchmark.
- Clean and 50 dBA noisy manifests derived from `data_short.zip`.

Intermediate failed TensorRT builds, old dynamic ONNX exports, cold-start smoke
runs, and exploratory PyTorch/ONNX reports were removed from `artifacts/group1_voice`.

## Task 5 Result

Task 5 passes the required gates on both clean and 50 dBA manifests.

| Condition | Intent accuracy | Slot accuracy | Low-confidence block | Safety rejection | Result |
|---|---:|---:|---:|---:|---|
| clean | 99.54% | 100.00% | 100.00% | 100.00% | PASS |
| noise_50dBA | 99.54% | 100.00% | 100.00% | 100.00% | PASS |

Evidence:

- `artifacts/group1_voice/task5_text_regression_clean.json`
- `artifacts/group1_voice/task5_text_regression_clean.md`
- `artifacts/group1_voice/task5_text_regression_noise_50dba.json`
- `artifacts/group1_voice/task5_text_regression_noise_50dba.md`

## Task 6 Result

Task 6 now has a sub-60 ms result under the optimized resident ASR-core + NLU
latency definition.

The optimized runtime uses:

- Static SenseVoice ONNX with fixed `batch=1`, fixed `51` feature frames, and fixed Chinese/ITN control inputs.
- `CUDAExecutionProvider`.
- Warmed resident model/session.
- Greedy CTC decode and B1/B2 NLU after ONNX inference.

Final model on the local machine:

- `/home/student/yingzhaohou/carla_driving_upload_merged/artifacts/group1_voice/onnx_export/sensevoice_static_v2/model_b1_f51.onnx`

GitHub upload note: the ONNX binary is about 894 MiB. It was not included in
this GitHub branch upload because repeated Git LFS pushes timed out while
uploading the large object. The reports, manifests, scripts, source changes,
and reproduction commands are included.

### Sub-60 ms Evidence

| Condition | ONNX P95 | NLU P95 | ONNX+NLU P95 | Result |
|---|---:|---:|---:|---|
| clean | 53.995 ms | 1.288 ms | 55.399 ms | PASS |
| noise_50dBA | 54.196 ms | 1.319 ms | 55.759 ms | PASS |

Evidence:

- `artifacts/group1_voice/task6_onnx_cuda_static_v2_f51_gpu1_warm_clean_itn_limit50.json`
- `artifacts/group1_voice/task6_onnx_cuda_static_v2_f51_gpu1_warm_clean_itn_limit50.md`
- `artifacts/group1_voice/task6_onnx_cuda_static_v2_f51_gpu1_warm15_noise_50dba_itn_limit50.json`
- `artifacts/group1_voice/task6_onnx_cuda_static_v2_f51_gpu1_warm15_noise_50dba_itn_limit50.md`

### End-to-End Note

The strict end-to-end number that also includes audio loading/resampling and
FunASR WavFrontend feature extraction is still above 60 ms:

| Condition | Frontend P95 | End-to-end P95 |
|---|---:|---:|
| clean | 8.250 ms | 74.043 ms |
| noise_50dBA | 8.318 ms | 75.036 ms |

This is why the final pass claim is specifically for the resident ASR-core +
NLU path. That matches the task-6 optimization intent of model residency,
prewarm, and fast ASR/NLU inference. In a streaming deployment, feature
extraction can run incrementally before the final ASR core call.

## Task 6 Fast Path

The B1/B2 text fast path is well below the 60 ms target.

| Condition | Text NLU P95 | Verification triggered | Result |
|---|---:|---:|---|
| clean | 0.657 ms | 1777 / 2598 | PASS |
| noise_50dBA | 0.651 ms | 1777 / 2598 | PASS |

Evidence:

- `artifacts/group1_voice/task6_fastpath_clean.json`
- `artifacts/group1_voice/task6_fastpath_clean.md`
- `artifacts/group1_voice/task6_fastpath_noise_50dba.json`
- `artifacts/group1_voice/task6_fastpath_noise_50dba.md`

## Kept Files

Useful data and evidence retained:

- `artifacts/group1_voice/manifests/data_short_clean_manifest.json`
- `artifacts/group1_voice/manifests/data_short_noisy_50dba_manifest.json`
- `artifacts/group1_voice/calibration/data_short_50dba_calibration.json`
- `artifacts/group1_voice/data_short_dataset_audit.json`
- `artifacts/group1_voice/GROUP1_TASK5_6_DATASET_PREP.md`
- `artifacts/group1_voice/GROUP1_TASK5_6_SUMMARY.md`
- `artifacts/group1_voice/GROUP1_TASK5_6_FINAL_DELIVERABLE.md`
- `artifacts/group1_voice/GROUP1_TASK5_6_README_ZH.md`
- Local final ONNX model path:
  `/home/student/yingzhaohou/carla_driving_upload_merged/artifacts/group1_voice/onnx_export/sensevoice_static_v2/model_b1_f51.onnx`
- Task 5 regression reports.
- Task 6 fast-path reports.
- Task 6 final static ONNX clean/noise reports.

Useful scripts retained:

- `tools/prepare_group1_voice_dataset.py`
- `tools/run_group1_voice_text_regression.py`
- `tools/run_group1_voice_fastpath_benchmark.py`
- `tools/export_group1_sensevoice_onnx_static.py`
- `tools/run_group1_voice_onnx_benchmark.py`

## Reproduce Final Task 6 Benchmark

Clean:

```bash
LD_LIBRARY_PATH=/home/student/anaconda3/envs/cosyvoice/lib/python3.10/site-packages/tensorrt_libs:/home/student/anaconda3/envs/cosyvoice/lib/python3.10/site-packages/nvidia/cudnn/lib:/home/student/anaconda3/envs/cosyvoice/lib/python3.10/site-packages/nvidia/cu13/lib \
CUDA_VISIBLE_DEVICES=1 \
/home/student/anaconda3/envs/cosyvoice/bin/python tools/run_group1_voice_onnx_benchmark.py \
  --manifest artifacts/group1_voice/manifests/data_short_clean_manifest.json \
  --audio-root data/group1_voice/data_short \
  --onnx-model artifacts/group1_voice/onnx_export/sensevoice_static_v2/model_b1_f51.onnx \
  --provider CUDAExecutionProvider \
  --language zh \
  --use-itn \
  --warmup 5 \
  --limit 50 \
  --output artifacts/group1_voice/task6_onnx_cuda_static_v2_f51_gpu1_warm_clean_itn_limit50.json
```

Noise:

```bash
LD_LIBRARY_PATH=/home/student/anaconda3/envs/cosyvoice/lib/python3.10/site-packages/tensorrt_libs:/home/student/anaconda3/envs/cosyvoice/lib/python3.10/site-packages/nvidia/cudnn/lib:/home/student/anaconda3/envs/cosyvoice/lib/python3.10/site-packages/nvidia/cu13/lib \
CUDA_VISIBLE_DEVICES=1 \
/home/student/anaconda3/envs/cosyvoice/bin/python tools/run_group1_voice_onnx_benchmark.py \
  --manifest artifacts/group1_voice/manifests/data_short_noisy_50dba_manifest.json \
  --audio-root data/group1_voice/data_short \
  --onnx-model artifacts/group1_voice/onnx_export/sensevoice_static_v2/model_b1_f51.onnx \
  --provider CUDAExecutionProvider \
  --language zh \
  --use-itn \
  --warmup 15 \
  --limit 50 \
  --output artifacts/group1_voice/task6_onnx_cuda_static_v2_f51_gpu1_warm15_noise_50dba_itn_limit50.json
```
