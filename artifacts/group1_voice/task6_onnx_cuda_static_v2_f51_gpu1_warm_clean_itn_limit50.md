# Group 1 Task 6 ONNX Benchmark

- Generated UTC: `2026-08-02T06:15:59.694948+00:00`
- Manifest: `/home/student/yingzhaohou/carla_driving_upload_merged/artifacts/group1_voice/manifests/data_short_clean_manifest.json`
- ONNX model: `/home/student/yingzhaohou/carla_driving_upload_merged/artifacts/group1_voice/onnx_export/sensevoice_static_v2/model_b1_f51.onnx`
- Provider: `CUDAExecutionProvider`
- Samples: `50`
- ASR exact accuracy: `4.00%`
- Intent accuracy: `76.00%`
- Slot accuracy: `36.00%`

| Stage | mean | P95 | P99 | max |
|---|---:|---:|---:|---:|
| Frontend | 7.45 ms | 8.25 ms | 14.651 ms | 20.553 ms |
| ONNX | 53.761 ms | 53.995 ms | 54.46 ms | 54.8 ms |
| NLU | 2.17 ms | 1.288 ms | 34.195 ms | 64.959 ms |
| ONNX+NLU | 55.931 ms | 55.399 ms | 87.96 ms | 118.74 ms |
| End-to-end | 70.889 ms | 74.043 ms | 108.609 ms | 131.699 ms |

## Notes

- Transcript decoding uses greedy CTC collapse plus SenseVoice tag postprocess.
- Frontend uses the same FunASR WavFrontend configuration as the PyTorch baseline.

