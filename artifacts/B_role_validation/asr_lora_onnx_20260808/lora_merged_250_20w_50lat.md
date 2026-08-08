# Group 1 Task 6 ONNX Benchmark

- Generated UTC: `2026-08-07T18:55:11.373419+00:00`
- Manifest: `voice_group/test_samples/manifest.json`
- ONNX model: `/workspace/results/asr_lora_onnx_20260808/model_f51/model_b1_f51.onnx`
- Provider: `CUDAExecutionProvider`
- Samples: `250`
- ASR exact accuracy: `1.20%`
- Intent accuracy: `99.20%`
- Slot accuracy: `99.20%`

| Stage | mean | P95 | P99 | max |
|---|---:|---:|---:|---:|
| Frontend | 1.732 ms | 2.091 ms | 2.26 ms | 2.348 ms |
| ONNX | 19.423 ms | 20.752 ms | 21.177 ms | 21.241 ms |
| NLU | 0.423 ms | 0.312 ms | 6.118 ms | 11.545 ms |
| ONNX+NLU | 19.847 ms | 21.153 ms | 26.532 ms | 31.414 ms |
| End-to-end | 23.23 ms | 24.616 ms | 29.723 ms | 34.397 ms |

## Notes

- Transcript decoding uses greedy CTC collapse plus SenseVoice tag postprocess.
- Frontend uses the same FunASR WavFrontend configuration as the PyTorch baseline.
