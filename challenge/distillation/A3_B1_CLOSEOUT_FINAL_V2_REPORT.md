# A3 B1 Closeout Final FP32 Candidate v2 Report

## Result

A3 completed production training on the B1 closeout dataset and published an
immutable candidate handoff. The package is verified but deliberately remains
`PENDING_B2_INDEPENDENT_VALIDATION` / `PENDING_A3_FP32_GATE`.

## Reproducible identities

| Item | Value |
|---|---|
| training Git SHA | `ec3b57c369f0dbcc728019076cd2c2cf670d9e61` |
| model | `student-v0-r3-fp32` |
| model config | `student-v0-r3-structure-20260911` |
| dataset view | `b1_governed_closeout_v1_a3_strict_positive_v1` |
| candidate weights SHA256 | `6b6ec1d8e815866aaccb3981d7a7a74efaa971e2a0d0bf8a9b42cbf7af0b8546` |
| best checkpoint SHA256 | `de95541a9ce04da359f77aa4a9eb9aeca01e8528bbcfdfd58a5768a05e73b434` |
| handoff manifest SHA256 | `f6a0ed27f5481cc4472935070ac456d2199f8499db47a46df91e045623ca4b7e` |
| B1 governed release SHA256 | `07d3a82502005646d8f29d0c493fa8a5b0270a5194fd5c802a04b4870ba7d37d` |
| view manifest SHA256 | `d07178a15a2cc3e66e190100060d426043a18bc1478387fcc4a3f3210d542258` |

## Data boundary

- governed raw inventory: Train `6037`, Development `1158`;
- strict-positive optimizer view: Train `5856`, Validation `1108`;
- audit-only exclusions: `540`;
- MS34 additions: `30` Train, `4` Validation, `1` failed route-deviation
  hard negative retained only for audit;
- plan-length coverage: `6439 / 491 / 17 / 17` for lengths `1 / 2 / 3 / 4`;
- Independent Validation, Reserved Test, and Frozen Test were not used.

## Verification performed

- full RGB-bound view rebuild and reproducibility audit: PASS;
- integration smoke on CUDA: PASS;
- distillation regression suite: `103 passed`;
- production training: 3 epochs, 2196 updates, clean worktree;
- development slice evaluation: complete 1/2/3/4-step and TURN_LEFT/YIELD/
  PULL_OVER coverage;
- handoff verifier: `valid=true`, 9 signed payload files checked.

## B2 next action

B2 must consume `releases/a3_final_fp32_candidate_v2/` without changing the
weight bytes, verify the handoff manifest, evaluate the exact weight SHA on the
isolated B2 package, and publish the paired Teacher/Student evidence plus the
formal PASS/FAIL conclusion. Development metrics in this report are diagnostic
only and must not be copied into the independent Gate result.
