# Group 1 Task 5 Text/Intent/Slot/Safety Regression

- Generated UTC: `2026-08-02T04:07:52.831153+00:00`
- Manifest: `/home/student/yingzhaohou/carla_driving_upload_merged/artifacts/group1_voice/manifests/data_short_noisy_50dba_manifest.json`
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
| B2 parser | 0.063 ms | 0.078 ms | 0.287 ms | 1.585 ms |
| Text NLU total | 0.468 ms | 0.642 ms | 0.811 ms | 82.163 ms |

## Failure Samples

- `0043__noise_50dba__1` expected `EMERGENCY_STOP` got `STOP` status `valid` text `麻烦停车停车！`
- `0043__noise_50dba__2` expected `EMERGENCY_STOP` got `STOP` status `valid` text `麻烦停车停车！`
- `0043__noise_50dba__3` expected `EMERGENCY_STOP` got `STOP` status `valid` text `麻烦停车停车！`
- `0308__noise_50dba__1` expected `EMERGENCY_STOP` got `STOP` status `valid` text `停下来！快！`
- `0308__noise_50dba__2` expected `EMERGENCY_STOP` got `STOP` status `valid` text `停下来！快！`
- `0308__noise_50dba__3` expected `EMERGENCY_STOP` got `STOP` status `valid` text `停下来！快！`
- `0492__noise_50dba__1` expected `EMERGENCY_STOP` got `STOP` status `valid` text `停车停车！`
- `0574__noise_50dba__1` expected `EMERGENCY_STOP` got `STOP` status `valid` text `刹住车！`
- `0574__noise_50dba__2` expected `EMERGENCY_STOP` got `STOP` status `valid` text `刹住车！`
- `0655__noise_50dba__1` expected `EMERGENCY_STOP` got `STOP` status `valid` text `刹住车！`
- `0655__noise_50dba__2` expected `EMERGENCY_STOP` got `STOP` status `valid` text `刹住车！`
- `0655__noise_50dba__3` expected `EMERGENCY_STOP` got `STOP` status `valid` text `刹住车！`
