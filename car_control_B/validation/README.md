# B lateral CARLA validation

This folder records member B's repeatable CARLA lateral-control validation for
the canonical `car_control_B` implementation.

## Baseline checks

Run from the repository root before CARLA tests:

```powershell
python tools\validate_scenarios.py
python -m pytest car_control_A\tests car_control_B\tests car_control_C\tests car_control_D\tests integration\tests -q
```

## CARLA runner pattern

```powershell
py -3.12 -m integration.carla_runner `
  --host 127.0.0.1 --port 2000 `
  --scenario-file scenarios/lateral_B/B01_straight_center.json `
  --scenario-facts-mode fuse `
  --perception-mode world `
  --realtime
```

Use `world` mode for repeatable controller validation, then `sensors` mode for
sensor-linked evidence. Keep the mode in every result and never present world
truth as sensor perception.

Run B01-B09 in order: straight and offset cases first, then curves, turns, and
finally lane changes. A demo candidate should pass at least three repeated runs
with no collision, red-light violation, serious route deviation, wrong turn,
or sustained steering oscillation.

Store run `.jsonl` and `.summary.json` files under `artifacts/` and record their
paths in `lateral_validation_results.csv`.
