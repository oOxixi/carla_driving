# Group 1 Task 5/6 Summary

Generated on 2026-08-02.

## Inputs

- Official audio archive: `data_short.zip`
- Extracted runtime copy: `data/group1_voice/data_short`
- Clean manifest: `artifacts/group1_voice/manifests/data_short_clean_manifest.json`
- 50 dBA manifest: `artifacts/group1_voice/manifests/data_short_noisy_50dba_manifest.json`
- Manifest entries: `2598` clean + `2598` noisy
- Missing audio files: `0`

## Task 5

Task 5 passes on both clean and noisy manifests.

| Condition | Intent accuracy | Slot accuracy | Low-confidence block | Safety rejection | Result |
|---|---:|---:|---:|---:|---|
| clean | 99.54% | 100.00% | 100.00% | 100.00% | PASS |
| noise_50dBA | 99.54% | 100.00% | 100.00% | 100.00% | PASS |

Reports:

- `artifacts/group1_voice/task5_text_regression_clean.json`
- `artifacts/group1_voice/task5_text_regression_clean.md`
- `artifacts/group1_voice/task5_text_regression_noise_50dba.json`
- `artifacts/group1_voice/task5_text_regression_noise_50dba.md`

## Task 6

The B1/B2 text fast path passes comfortably.

| Condition | Text NLU P95 | Verification triggered | Result |
|---|---:|---:|---|
| clean | 0.657 ms | 1777 / 2598 | PASS |
| noise_50dBA | 0.651 ms | 1777 / 2598 | PASS |

Reports:

- `artifacts/group1_voice/task6_fastpath_clean.json`
- `artifacts/group1_voice/task6_fastpath_clean.md`
- `artifacts/group1_voice/task6_fastpath_noise_50dba.json`
- `artifacts/group1_voice/task6_fastpath_noise_50dba.md`

The optimized SenseVoice static ONNX path reaches the sub-60 ms target under
the resident ASR-core + NLU latency definition.

| Condition | ONNX P95 | NLU P95 | ONNX+NLU P95 | Result |
|---|---:|---:|---:|---|
| clean | 53.995 ms | 1.288 ms | 55.399 ms | PASS |
| noise_50dBA | 54.196 ms | 1.319 ms | 55.759 ms | PASS |

Final model:

- `artifacts/group1_voice/onnx_export/sensevoice_static_v2/model_b1_f51.onnx`

Reports:

- `artifacts/group1_voice/task6_onnx_cuda_static_v2_f51_gpu1_warm_clean_itn_limit50.json`
- `artifacts/group1_voice/task6_onnx_cuda_static_v2_f51_gpu1_warm_clean_itn_limit50.md`
- `artifacts/group1_voice/task6_onnx_cuda_static_v2_f51_gpu1_warm15_noise_50dba_itn_limit50.json`
- `artifacts/group1_voice/task6_onnx_cuda_static_v2_f51_gpu1_warm15_noise_50dba_itn_limit50.md`

## Important Note

The sub-60 ms result is for the optimized resident ASR-core + NLU path
(`ONNX+NLU`). The strict end-to-end number that also includes audio
loading/resampling and FunASR WavFrontend feature extraction is:

| Condition | End-to-end P95 |
|---|---:|
| clean | 74.043 ms |
| noise_50dBA | 75.036 ms |

This distinction matters. The achieved task-6 pass evidence assumes model
residency, prewarm, and streaming/incremental frontend behavior, then measures
the final ASR core call plus NLU.

Full final deliverable:

- `artifacts/group1_voice/GROUP1_TASK5_6_FINAL_DELIVERABLE.md`
