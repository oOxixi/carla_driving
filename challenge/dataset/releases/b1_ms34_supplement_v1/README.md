# B1 MS34 Targeted Supplemental Release

Dataset version: `b1_ms34_supplement_v1`

This additive release contains **34 strict-positive single-call
multi-step Teacher samples** and **1 hard-negative closed-loop
route-deviation sample** derived from 35 CARLA runs.

Positive supervision:

- 3-step AVOID_OBSTACLE -> RETURN_TO_LANE -> KEEP_LANE:
  17 samples
- 4-step YIELD -> AVOID_OBSTACLE -> RETURN_TO_LANE -> KEEP_LANE:
  17 samples

Split:

- train: 30 positive samples / 2 groups
- validation: 4 positive samples / 4 groups
- hard negative: 1 sample / 1 group
- train/validation group overlap: 0

The original 30-run targeted acquisition consists of two fixed
scenario/seed groups repeated 15 times each. Four additional
successful groups were acquired specifically as validation holdout.

Seed 253002 is not positive supervision. It is published only in
`hard_negative_addition.jsonl` because closed-loop route deviation
caused scenario acceptance failure.

Teacher:

- model: `Qwen/Qwen3.5-2B`
- mode: `planner_v2`
- acquisition Git SHA: `4a900a86c23f901f9ab4a49ba6f2ce3266c3f1a3`

Canonicalization:

- collector commit: `912989f5bab4a864136f3774515e7cbd28e8dc24`
- collector SHA256: `792528d5564130ed8982f552e1207e3fa97eaaea3b992cdaaeea0370de002485`
- canonical source SHA256: `6bc8720515304cc7f872e37c62f7844ce24a3a1e4a0dae4725ec93d681a73c4e`

This release is additive and does not mutate any previously frozen
release.
