# A3 robust FP32 candidate v3 diagnostic evidence (2026-10-06)

## Boundary

This directory records A3 development evaluation and a one-shot replay of the
three B3 cohorts that had already exposed v2 failures.  Its status is
`DIAGNOSTIC_ONLY`.  It is neither B2 Independent Validation nor Frozen Test and
cannot issue `A3_FP32_GATE_PASSED`.

The exact candidate weight SHA256 is
`7f379c78c170228713e3d91b8e2eabd04172010ae0ed0b8cf71afe291fe6e805`.

## Results

| Evidence | Samples | Main result |
|---|---:|---|
| development Validation | 1108 | all discrete heads `1.0`; speed MAE `0.378199 m/s` |
| TURN-gap observed cohort | 29 | plan sequence `1.0`; TURN_LEFT `9/9` |
| Gap300 observed cohort | 123 | plan sequence `1.0`; TURN_LEFT `36/36` |
| MS34 observed cohort | 4 | 3/4-step sequence `4/4`; tail KEEP_LANE restored |

The v2 failure (TURN_LEFT never emitted and the final KEEP_LANE step replaced)
is not reproduced by v3.  MS34 speed remains a concern: MAE `2.14069 m/s`, four
sample IDs above `1 m/s`.

## Files

- `dev_slice_metrics.json`: A3 development-only slice report;
- `diagnostic_turn_gap.json`: observed TURN-gap cohort replay;
- `diagnostic_gap300.json`: observed Gap300 cohort replay;
- `diagnostic_ms34.json`: observed three/four-step cohort replay.

