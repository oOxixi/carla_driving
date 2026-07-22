# Town03 topology sensor acceptance

Final passing CARLA 0.9.16 `Town03_Opt` sensor-mode evidence generated on
2026-07-21 after replacing scenario-local free-space routes with CARLA driving
topology routes.

Common runner settings:

- `--perception-mode sensors`
- `--scenario-facts-mode fuse`
- `--use-current-map`
- `--sensor-timeout-s 1`
- `--sensor-warmup-frames 30`
- `--watchdog-timeout-s 3`

Each scenario below finished with `status=SUCCEEDED`, official
`final_score=25.0`, no collision, no red-light violation, and no serious route
deviation:

- B01-B09
- REG_001, REG_003, REG_004, REG_005, REG_009, REG_010

The matching `.jsonl` and `.summary.json` files are retained for frame-level
audit. Failed tuning iterations remain local and are intentionally excluded.
