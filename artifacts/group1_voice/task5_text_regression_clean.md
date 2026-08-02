# Group 1 Task 5 Text/Intent/Slot/Safety Regression

- Generated UTC: `2026-08-02T04:07:39.069887+00:00`
- Manifest: `/home/student/yingzhaohou/carla_driving_upload_merged/artifacts/group1_voice/manifests/data_short_clean_manifest.json`
- Samples: `2598`
- Intent accuracy: `99.54%`
- Slot accuracy: `100.00%`
- Safety contract accuracy: `100.00%`
- Low-confidence block rate: `100.00%`
- Safety rejection probe pass rate: `100.00%`

## Gates

- Intent >= `98.00%`: `True`
- Slot >= `98.00%`: `True`
- Low-confidence block = `100%`: `True`
- Safety rejection = `100%`: `True`
- Overall pass: `True`

## Latency

| Stage | mean | P95 | P99 | max |
|---|---:|---:|---:|---:|
| B1 intent | None ms | None ms | None ms | None ms |
| B2 parser | 0.064 ms | 0.077 ms | 0.294 ms | 1.583 ms |
| Text NLU total | 0.461 ms | 0.638 ms | 0.764 ms | 75.864 ms |

## Failure Samples

- `0043__clean__1` expected `EMERGENCY_STOP` got `STOP` status `valid` text `麻烦停车停车！`
- `0043__clean__2` expected `EMERGENCY_STOP` got `STOP` status `valid` text `麻烦停车停车！`
- `0043__clean__3` expected `EMERGENCY_STOP` got `STOP` status `valid` text `麻烦停车停车！`
- `0308__clean__1` expected `EMERGENCY_STOP` got `STOP` status `valid` text `停下来！快！`
- `0308__clean__2` expected `EMERGENCY_STOP` got `STOP` status `valid` text `停下来！快！`
- `0308__clean__3` expected `EMERGENCY_STOP` got `STOP` status `valid` text `停下来！快！`
- `0492__clean__1` expected `EMERGENCY_STOP` got `STOP` status `valid` text `停车停车！`
- `0574__clean__1` expected `EMERGENCY_STOP` got `STOP` status `valid` text `刹住车！`
- `0574__clean__2` expected `EMERGENCY_STOP` got `STOP` status `valid` text `刹住车！`
- `0655__clean__1` expected `EMERGENCY_STOP` got `STOP` status `valid` text `刹住车！`
- `0655__clean__2` expected `EMERGENCY_STOP` got `STOP` status `valid` text `刹住车！`
- `0655__clean__3` expected `EMERGENCY_STOP` got `STOP` status `valid` text `刹住车！`
