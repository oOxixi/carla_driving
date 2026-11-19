# Numerical primary speed Head: B2 and A4 precheck (2026-11-12)

Status: **development candidate frozen for handoff; no formal B2 Gate or J6P result**.
This run did not change the model, evaluator, thresholds, or evaluation inputs.

## Historical paired regression

On `tiaozhansai`, the existing B1 integrity verifier checked the four historical
ledger entries and all 240 RGB file hashes and sizes. The old and new FP32 ONNX
exports were replayed on the same 240 ModelRequests and RGBs with CPU ONNX Runtime,
the same preprocessor and adapter, and the existing B2 metric implementation.
The stored Teacher plans are the reference, not a fresh Teacher replay. This
exposed historical set is for regression only, not a blind set or a tuning source.

| Metric | Baseline | Numeric primary |
| --- | ---: | ---: |
| Schema-valid decoded plans | 240/240 | 240/240 |
| Behavior, target lane, completion (each) | 260/262 | 260/262 |
| Target pointer | 262/262 | 262/262 |
| Action sequence | 238/240 | 238/240 |
| Safety-critical behavior recall | 28/28 | 28/28 |
| Paired target speed MAE (127 steps, m/s) | 0.610 | 0.258 |
| SET_SPEED target speed MAE (76 steps, m/s) | 0.669 | 0.269 |
| FOLLOW target speed MAE (29 steps, m/s) | 0.646 | 0.155 |
| SLOW_DOWN target speed MAE (4 steps, m/s) | 1.132 | 1.132 |

Speed MAE compares steps where both models matched the reference behavior and
both decoded a numeric target speed, with a numeric reference available. Each
model had 127 eligible steps and all 127 overlapped. This is not actual vehicle
speed, closed-loop accuracy, or a scored Gate metric.

## Artifact identity

- Candidate: `student-v0-r3-numeric-primary-v1-fp32`; config:
  `student-v0-r3-numeric-primary-v1-20261112`.
- Candidate weight SHA256: `20be5f643b54e584beb983e39393c5d4e83f7e6baabaeec5aa58ce68c159c3ef`.
- Candidate diagnostic ONNX SHA256: `79327f40e65a58dd484f7c614aa5c964df360455475c919528173388021f5f31`.
- Baseline weight SHA256: `7f379c78c170228713e3d91b8e2eabd04172010ae0ed0b8cf71afe291fe6e805`.
- Baseline diagnostic re-export SHA256: `8dfc20a8b7a3d9dc196b145425d9a7f7be117219637cf950fd9b20af69825ad2`.
  This is not the historical A2 ONNX artifact.
- Replay source SHA: `6582dc9909a5298c416d092682e9e6d37224c748`.
- Historical case-set digest: `da1d032f7d20147a26e4426c10a97def8b470a780b854ea852143697292f7dec`.
- Aggregate evidence: `artifacts/numeric_speed_conditioned_20261112/historical_proxy_240/{regression,formal_readiness}.json`.

## Handoff

- **B2: blocked.** The checked formal configuration does not bind a frozen
  independent case manifest, policy version, slice minima, or multi-run merge
  rule. The new 240-slot collection design is not a frozen case release.
  Supply the frozen inputs, authorized Teacher reference, finalized policy and
  verified candidate handoff to the independent evaluator. Do not promote the
  historical result to `A3_FP32_GATE_PASSED`.
- **A4: compiler not run.** Docker is reachable on the workstation, but the
  configured `openexplorer/ai_toolchain_ubuntu_22_j6_cpu:v3.9.1` image is not
  installed locally; no compiler was found on the server. In the configured
  image, run `hb_compile --model student_numeric_primary_diagnostic.onnx --march nash-p`
  against the hashed diagnostic ONNX. Inspect placement and CPU fallback,
  especially for the added Add/Cast/Greater/MatMul/Slice/Sub node types. ONNX
  parity is not evidence of BPU placement or official utilization.
