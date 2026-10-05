# A3 B1 Closeout Robust FP32 Candidate v3 Report

## Result

A3 completed a clean production retraining run on the governed B1 closeout
view.  The exported candidate is immutable and its handoff package passes the
repository verifier.  The candidate remains
`PENDING_B2_INDEPENDENT_VALIDATION` / `PENDING_A3_FP32_GATE`: A3 development
metrics and the previously observed B3 cohorts are useful diagnostics, but are
not a substitute for B2's independently frozen evaluation.

## Reproducible identities

| Item | Value |
|---|---|
| training Git SHA | `18a95de9702fe7baa5e89aa74a93dcd86d88d537` |
| run config | `a3-b1-closeout-robust-fp32-v3` |
| model | `student-v0-r3-fp32` |
| model config | `student-v0-r3-structure-20260911` |
| Teacher | `Qwen/Qwen3.5-2B` |
| Teacher revision | `15852e8c16360a2fea060d615a32b45270f8a8fc` |
| dataset view | `b1_governed_closeout_v1_a3_strict_positive_v1` |
| candidate weights SHA256 | `7f379c78c170228713e3d91b8e2eabd04172010ae0ed0b8cf71afe291fe6e805` |
| best checkpoint SHA256 | `97951b3a7d0e346f53f7d332fca94c226a7a56c09b3cb54366f8cd0a720415f0` |
| handoff manifest SHA256 | `5bb09248289872632270f8aada8201c8ffe1150bea153311f18aaf698a5e9d01` |
| view manifest SHA256 | `d07178a15a2cc3e66e190100060d426043a18bc1478387fcc4a3f3210d542258` |

## Training and development result

- governed raw inventory: Train `6037`, Development `1158`;
- strict-positive optimizer view: Train `5856`, Validation `1108`;
- five epochs, `3660` optimizer updates, deterministic seed `20261006`;
- development behavior, plan length, plan sequence, target lane and target
  pointer accuracy: `1.0`;
- development safety-critical recall: `1.0`;
- development target-speed MAE: `0.378198881 m/s`;
- remaining hard cases: `113`, all caused by target-speed absolute error above
  `1 m/s`.

Train-only input augmentation was used to reduce dependence on repeated command
templates: full text dropout `0.35`, token dropout `0.15`, RGB dropout `0.10`.
State and target modalities were retained.  No augmentation is active in
Validation or evaluation.

## One-shot known-cohort diagnostic

The exact candidate was evaluated once on the same B3 cohorts already used to
diagnose v2.  These rows are therefore **observed diagnostics**, not independent
Gate evidence and not a basis for further tuning.

| Cohort | Samples | v2 result | v3 result |
|---|---:|---:|---:|
| TURN-gap | 29 | TURN_LEFT `0/9` per pass | all behavior steps `29/29` |
| Gap300 | 123 | TURN_LEFT `0/36` per pass | all behavior steps `123/123` |
| MS34 | 4 | tail step wrong | all 3/4-step sequences `4/4` |

The old missing-symbol and plan-tail failures are no longer reproduced.  The
MS34 target-speed MAE is still `2.14069 m/s`; B2 should retain a speed-error
slice in its independent decision.

## B2 next action

B2 must verify
`releases/a3_b1_closeout_robust_fp32_candidate_v3/`, evaluate the exact weight
SHA on its isolated frozen package, and publish the paired Teacher/Student
evidence and PASS/FAIL decision.  Only a PASS bound to the exact SHA above can
authorize an `A3_FP32_GATE_PASSED` manifest.

