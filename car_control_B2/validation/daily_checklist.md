# B lateral daily checklist

Use this checklist for each validation session.

## Before running CARLA

- [ ] Confirm repository status is clean or record local changes.
- [ ] Record current commit in `lateral_validation_results.csv`.
- [ ] Run `python tools\validate_scenarios.py`.
- [ ] Run pure Python regression tests.
- [ ] Confirm CARLA 0.9.16 is running on `127.0.0.1:2000`.
- [ ] Confirm the selected map is loaded or pass the intended map option.

## Scenario pass

- [ ] Run B01, B02, and B03 first to confirm sign and straight convergence.
- [ ] Run B04 and B05 to check curve stability.
- [ ] Run B06 and B07 only after straight and curve runs pass.
- [ ] Run B08 and B09 only after turns are stable.
- [ ] Repeat the three demo candidate scenarios at least three times.

## After each run

- [ ] Save or locate `.jsonl` and `.summary.json`.
- [ ] Record status, score, max cross-track error, route deviation, and speed.
- [ ] Mark snake oscillation, wrong turn, and D override fields.
- [ ] Add a short failure reason if the run did not pass.

## End of day

- [ ] Identify which scenarios are demo-ready.
- [ ] List blockers by category: route, sign/yaw, speed, safety override, sensor.
- [ ] Do not tune broad parameters unless the evidence points to one cause.
- [ ] Preserve stable logs and exclude failed scratch runs unless they explain a fix.

