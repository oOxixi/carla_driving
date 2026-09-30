# A3 Final FP32 Development-Slice Evidence

This directory records A3-owned diagnostics for the exact pending candidate
published in `releases/a3_final_fp32_candidate_v1/`.  It is not an independent
B2 evaluation and cannot issue `A3_FP32_GATE_PASSED`.

## Bound identity

- weights SHA256:
  `eaee4402197fb3fed53ed82bc2fbaceef62e5ed2d4cde86e8aa1a55dc6d46515`
- final view manifest SHA256:
  `2840b7dc22bd0be56f1c26517b7b1e8a37ac4e7cf7111929def40dfc6daa8330`
- development Validation samples: `1,104`
- evaluation device: CUDA

The evaluator fails closed on weight, config, dataset, view-manifest and
candidate-state mismatches.  It also refuses Test/Frozen paths.

## Results

| Slice | Denominator | Result |
|---|---:|---:|
| TURN_LEFT | 67 steps | behavior accuracy 1.0000 |
| YIELD | 22 steps | behavior accuracy 1.0000 |
| PULL_OVER | 6 steps | behavior accuracy 1.0000 |
| 2-step plan | 95 samples | sequence accuracy 1.0000 |
| multi-step lane change | 71 samples | sequence accuracy 1.0000 |
| target grounding | 257 steps | accuracy 1.0000 |
| target with distractors | 134 steps | accuracy 1.0000 |
| target speed | 1,199 steps | MAE 0.4433 m/s; P95 1.2970 m/s |

`SLOW_DOWN` is the weakest speed slice at 1.1095 m/s MAE.  This is diagnostic
evidence, not a threshold decision, because B2 has not frozen that slice's
acceptance threshold.

## Required coverage gap

The governed final view contains no 3-step or 4-step plan in either Train or
development Validation:

| Plan length | Train | Development Validation |
|---:|---:|---:|
| 1 | 5,430 | 1,009 |
| 2 | 396 | 95 |
| 3 | 0 | 0 |
| 4 | 0 | 0 |

Therefore 3/4-step performance is **not evaluated and not passed**.  It cannot
be repaired by duplicating rows or manually extending Teacher plans.  B1 must
provide contract-valid, pinned-Teacher 3/4-step development cohorts before A3
can train and report these slices.

## Reproduce

```bash
CUDA_VISIBLE_DEVICES=7 python -m challenge.distillation.final_slice_eval \
  --output artifacts/challenge/distillation/a3_final_fp32_dev_slice_metrics_v1.json
```

The machine-readable output is `dev_slice_metrics.json`.  B2 must independently
evaluate the exact weight SHA on its frozen benchmark and publish the final
PASS/FAIL decision.
