# A3 Final FP32 Candidate v2 Development Evidence

This evidence belongs to the exact pending candidate in
`releases/a3_final_fp32_candidate_v2/`. It uses A3 Development Validation only;
it is not B2 independent evidence and cannot issue `A3_FP32_GATE_PASSED`.

## Bound identity

- training Git SHA: `ec3b57c369f0dbcc728019076cd2c2cf670d9e61`
- weights SHA256:
  `6b6ec1d8e815866aaccb3981d7a7a74efaa971e2a0d0bf8a9b42cbf7af0b8546`
- view manifest SHA256:
  `d07178a15a2cc3e66e190100060d426043a18bc1478387fcc4a3f3210d542258`
- B1 governed release manifest SHA256:
  `07d3a82502005646d8f29d0c493fa8a5b0270a5194fd5c802a04b4870ba7d37d`
- optimizer Train / Development Validation: `5856 / 1108`
- B1 governed raw Train / Development: `6037 / 1158`

## Development results

The exact candidate achieved `1.0000` behavior, target grounding, plan-length,
plan-sequence, completion, and safety-critical recall on Development Validation.
Target-speed MAE was `0.5285 m/s`, with P95 absolute error `1.5810 m/s`.

The previously missing long-plan coverage is now present and evaluated:

| Plan length | Train | Development Validation | Dev sequence accuracy |
|---:|---:|---:|---:|
| 1 | 5430 | 1009 | 1.0000 |
| 2 | 396 | 95 | 1.0000 |
| 3 | 15 | 2 | 1.0000 |
| 4 | 15 | 2 | 1.0000 |

Required recovery slices on Development Validation:

| Slice | Steps | Behavior accuracy | Speed MAE (m/s) |
|---|---:|---:|---:|
| TURN_LEFT | 67 | 1.0000 | 0.8501 |
| YIELD | 24 | 1.0000 | 0.1047 |
| PULL_OVER | 6 | 1.0000 | 0.1503 |

The machine-readable report is `dev_slice_metrics.json`. B2 must evaluate the
exact weight SHA on its isolated benchmark before any promotion decision.
