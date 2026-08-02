# Group 1 Task 6 ONNX Benchmark

- Generated UTC: `2026-08-02T06:18:07.199666+00:00`
- Manifest: `/home/student/yingzhaohou/carla_driving_upload_merged/artifacts/group1_voice/manifests/data_short_noisy_50dba_manifest.json`
- ONNX model: `/home/student/yingzhaohou/carla_driving_upload_merged/artifacts/group1_voice/onnx_export/sensevoice_static_v2/model_b1_f51.onnx`
- Provider: `CUDAExecutionProvider`
- Samples: `50`
- ASR exact accuracy: `4.00%`
- Intent accuracy: `78.00%`
- Slot accuracy: `38.00%`

| Stage | mean | P95 | P99 | max |
|---|---:|---:|---:|---:|
| Frontend | 7.286 ms | 8.318 ms | 8.636 ms | 8.819 ms |
| ONNX | 53.574 ms | 54.196 ms | 59.828 ms | 64.336 ms |
| NLU | 2.163 ms | 1.319 ms | 33.996 ms | 64.551 ms |
| ONNX+NLU | 55.737 ms | 55.759 ms | 92.889 ms | 119.288 ms |
| End-to-end | 71.549 ms | 75.036 ms | 110.73 ms | 133.074 ms |

## Notes

- Transcript decoding uses greedy CTC collapse plus SenseVoice tag postprocess.
- Frontend uses the same FunASR WavFrontend configuration as the PyTorch baseline.

