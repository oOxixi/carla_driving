# HANDOFF xky 2026-08-04

## Branch scope

Target branch: `8.4-xky-3B`.

This branch preserves the current Qwen2.5-VL-3B implementation and the latest
local integration work. It also carries the frozen `CARLA-Language-Benchmark
v1` content from `main`; existing `main`, `new`, `7.25` and
`carla_driving_rstar` branches are not modified.

## New work included

- Qwen2.5-VL-3B independent CUDA 13 runtime, prompt optimization and validation
  report.
- Four-modal full-chain remote OpenAI-compatible Qwen endpoint support.
- Target-scene language repair for legacy far-ahead/adjacent pedestrian labels,
  including regression coverage and repair provenance.
- P50/P95/P99/max full-chain latency metrics.
- CARLA runner behavior inferred from actors, expected contracts and command
  intent instead of hard-coded scenario IDs.
- ScenarioRunner 0.9.16 `--agent` adapter with RGB/LiDAR/GNSS input, route
  following, GNSS motion estimation, D safety arbitration and fail-closed input
  handling.
- Unseen scenario-ID and official interface generalization tests.

## Validation

- Repository regression: `446 passed, 1 skipped`.
- The skipped test is the opt-in simulator smoke requiring `CARLA_SMOKE=1`.
- Python compile check, `git diff --check`, PowerShell script parsing and the
  hard-coded scenario-ID branch audit passed.
- Windows CARLA 0.9.16, DX12 Low, `Town03_Opt`, real low-profile RGB/LiDAR:
  `S01_set_speed_20` completed 600/600 frames, score 25/25, final speed
  5.483 m/s, maximum cross-track error 0.00943 m, zero collisions and zero
  route deviations.

Evidence:

- `artifacts/windows_0804_full_chain/S01_set_speed_20_20260804_104431_953262.jsonl`
- `artifacts/windows_0804_full_chain/S01_set_speed_20_20260804_104431_953262.summary.json`

## Remaining live work

- The Windows host has a working CARLA server but no local PyTorch/Qwen weights.
- Restore authenticated access to the Ubuntu Qwen endpoint, then run the same
  code with real Qwen inference for S01, D03 and D08.
- Repeat real-model physical runs across multiple seeds before freezing final
  submission evidence.
