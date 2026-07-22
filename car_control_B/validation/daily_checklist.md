# B lateral daily checklist

## Before running CARLA

- [ ] Record the current commit and local changes.
- [ ] Run `python tools\validate_scenarios.py`.
- [ ] Run the pure Python regression tests.
- [ ] Confirm CARLA 0.9.16 is listening on `127.0.0.1:2000`.
- [ ] Confirm the intended map and perception mode.

## Scenario pass

- [ ] Run B01-B03 to confirm steering sign and straight convergence.
- [ ] Run B04-B05 to check curve stability.
- [ ] Run B06-B07 only after straight and curve runs pass.
- [ ] Run B08-B09 only after turns are stable.
- [ ] Repeat each demo candidate at least three times.

## After each run

- [ ] Save the JSONL and summary evidence.
- [ ] Record status, score, cross-track error, route deviation, and speed.
- [ ] Record oscillation, wrong-turn, and D-override observations.
- [ ] Give every failure one specific category and reason.
