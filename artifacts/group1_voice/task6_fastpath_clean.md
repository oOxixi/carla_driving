# Group 1 Task 6 Fast-Path Benchmark

- Generated UTC: `2026-08-02T04:07:16.641409+00:00`
- Manifest: `/home/student/yingzhaohou/carla_driving_upload_merged/artifacts/group1_voice/manifests/data_short_clean_manifest.json`
- Samples: `2598`
- Fast path: `821`
- Verification triggered: `1777` (`68.40%`)
- Text NLU P95: `0.657 ms`
- Text NLU <= `60.0 ms`: `True`

## Latency

| Stage | mean | P95 | P99 | max |
|---|---:|---:|---:|---:|
| B1 intent | None ms | None ms | None ms | None ms |
| B2 parser | 0.062 ms | 0.076 ms | 0.097 ms | 1.409 ms |
| Text NLU total | 0.473 ms | 0.657 ms | 0.772 ms | 74.619 ms |

## Trigger Reasons

| Reason | Count |
|---|---:|
| fast_path | 821 |
| risky_intent | 1777 |

## ASR+NLU Note

- This benchmark validates the resident B1/B2 fast path and cascade policy only.
- Final ASR+NLU P95 evidence should be produced by `tools/evaluate_voice_audio.py` on a machine with SenseVoice/FunASR runtime available.
