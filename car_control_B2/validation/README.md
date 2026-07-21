# B lateral CARLA validation

This folder records member B's CARLA lateral-control validation without
modifying the original `car_control_B` implementation.

## Purpose

Use this folder to collect repeatable evidence for the 2026-07-24 demo target:

- confirm CARLA steering sign and yaw units;
- validate straight, offset, curve, turn, and lane-change lateral scenarios;
- record cross-track error, route deviation, steering smoothness, and D override
  behavior;
- keep clear evidence for pass/fail decisions and tuning changes.

## Important boundary

The current integration runner imports `car_control_B`, not `car_control_B2`.
Use `car_control_B2` for notes, templates, and experiments unless the integration
imports are deliberately changed.

Do not change `voice_group/` for B validation.

## Baseline checks

Run these from the repository root before CARLA tests:

```powershell
python tools\validate_scenarios.py
python -m pytest car_control_A\tests car_control_B\tests car_control_C\tests car_control_D\tests integration\tests -q
python -m pytest car_control_B2\tests -q
```

Note: the copied `car_control_B2/tests` may still import `car_control_B` until
B2 is made a fully independent package. If testing B2 itself becomes necessary,
update those imports first.

## CARLA runner pattern

Start CARLA 0.9.16 first, then run one scenario from the repository root:

```powershell
python -m integration.carla_runner `
  --host 127.0.0.1 --port 2000 `
  --scenario-file scenarios/lateral_B/B01_straight_center.json `
  --scenario-facts-mode fuse `
  --perception-mode world `
  --realtime
```

Recommended order:

1. `world` or `fuse` mode for repeatable controller validation.
2. `sensors` mode after the route and lateral parameters are stable.
3. Keep mode names in the result table. Do not present world/fuse truth as
   real perception evidence.

## B scenario set

Run each scenario at least three times before calling it demo-ready:

| Scenario | Focus |
| --- | --- |
| `B01_straight_center` | center-line steady tracking |
| `B02_straight_left_offset` | sign and convergence from one side |
| `B03_straight_right_offset` | sign and convergence from the other side |
| `B04_smooth_left_curve` | smooth left curve |
| `B05_smooth_right_curve` | smooth right curve |
| `B06_left_turn` | left turn route continuity |
| `B07_right_turn` | right turn route continuity |
| `B08_lane_change_left` | left lane-change path |
| `B09_lane_change_right` | right lane-change path |

## Pass criteria

A lateral scenario is passable for the demo only when:

- the run completes with no collision, red-light violation, or severe route
  deviation;
- steering sign is correct and the vehicle converges toward the route;
- no sustained snake-like oscillation is visible;
- `max_cross_track_error_m` and route deviation stay within the scenario's
  expected limit;
- D override, if any, is explainable from safety rules rather than B instability;
- logs and summaries are saved and referenced in `lateral_validation_results.csv`.

## Failure triage

| Symptom | Check first |
| --- | --- |
| Turns the wrong way | `steer_sign`, yaw degrees/radians, route point order |
| Snake-like motion | lookahead too small, speed too high, steering rate too loose |
| Cuts or overshoots turns | lookahead too large or C target speed too high |
| Tracks the wrong branch | route planner branch selection or path discontinuity |
| Error sign flips | nearest point jumps, sparse route points, yaw unit mismatch |
| D reports route deviation | inspect route geometry, speed, and cross-track curve |

## Evidence locations

Put runner-generated `.jsonl` and `.summary.json` files under `artifacts/` or
the runner's configured log directory. Copy only stable final evidence into git.
Record the exact path in `lateral_validation_results.csv`.

