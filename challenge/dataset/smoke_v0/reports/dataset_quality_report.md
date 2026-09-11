# B1 Teacher Dataset Quality Report

Generated at UTC: 2026-09-11T06:15:38.283083+00:00

Dataset version: teacher_distill_v0.1_smoke

## 1. Dataset Overview

- Raw structurally valid Teacher samples: 30
- Target-encoded samples: 30
- Policy-labelled samples: 30
- Train-eligible samples: 28
- Quarantined hard cases: 2
- Rejected collection records: 2
- Unique scenarios: 24
- Unique raw groups: 14

## 2. Teacher Provenance

- Qwen/Qwen3.5-2B: 30

Teacher Git SHAs:

- a05c8b76efcd4c176965223c661f40b153cb1836: 30

## 3. Structural Integrity

- Complete ModelRequest V1: 30/30
- Complete ManeuverPlan V2: 30/30
- request_id + command_id alignment: 30/30
- Target grounding valid: 30/30
- RGB available: 30/30
- RGB SHA256 present: 30/30

## 4. Raw Sample Classes

- COMPLEX: 6
- NORMAL: 17
- SAFETY_CRITICAL: 7

## 5. Target Pointer Encoding

- Smoke TopK: 8
- NO_TARGET index: 8
- Candidate ordering: `PRESERVE_MODEL_REQUEST_ORDER`
- Mapped target steps: 5
- No-target steps: 28
- TARGET_OUTSIDE_TOPK steps: 0
- Invalid target-id steps: 0

TopK=8 is a Smoke-stage validation setting, not a permanently frozen Student contract.

## 6. Training Policy

- Train eligible: 28
- Quarantined hard cases: 2
- Closed-loop command success: 28/30
- Scenario acceptance passed: 28/30
- Safety override samples retained: 7
- Run-status inconsistent but command successful: 2

Training policy classes:

- QUARANTINED_HARD_CASE: 2
- TRAIN_ELIGIBLE: 28

Hard-case reasons:

- CLOSED_LOOP_COMMAND_FAILED: 2
- COMMAND_TERMINAL_FAILED: 2
- PLAN_FAILURE_REASON:LANE_GAP_UNSAFE: 2
- PLAN_TERMINAL_FAILED: 2

Policy semantics:

- `teacher_label_valid`: ModelRequest/RGB/ManeuverPlan supervision is structurally valid.
- `closed_loop_success`: supervision command and Teacher plan both terminate successfully.
- `train_eligible`: teacher_label_valid AND closed_loop_success.
- Failed closed-loop Teacher plans remain in raw/hard-case data and are not silently deleted.
- SafetySupervisor override does not automatically invalidate an otherwise successful supervision sample.

## 7. Rejected Collection Records

- MANEUVER_PLAN_MISSING: 1
- NO_CANONICAL_SUBMIT: 1
- RESOLVE_NOT_READY:REJECTED: 1

Rejected collection records are not part of raw valid Teacher supervision.

## 8. Train / Val Split

- Train samples: 22
- Train groups: 10
- Val samples: 6
- Val groups: 2
- Actual Val ratio over train-eligible data: 0.2143

Train class distribution:

- COMPLEX: 3
- NORMAL: 14
- SAFETY_CRITICAL: 5

Val class distribution:

- COMPLEX: 1
- NORMAL: 3
- SAFETY_CRITICAL: 2

## 9. Leakage Validation

- Group overlap: 0
- Sample ID overlap: 0
- Group definition: `scenario_family + map + route_hash + seed`
- Adjacent/frame-level random splitting: forbidden

**Leakage Validation: PASS**

## 10. Smoke Split Manifest

- Total split source samples: 28
- Total split source groups: 12
- Train samples: 22
- Val samples: 6
- Split seed: 1

## 11. Artifact Integrity

- `artifacts/b1_teacher_smoke/dataset/smoke_valid.jsonl`
  - SHA256: `f92ce6d106829fbd1d1201713f2a8e0d2cc647003b2508ed2520b11f4270a4b1`
- `artifacts/b1_teacher_smoke/dataset/smoke_with_targets.jsonl`
  - SHA256: `b2d8d603fb2ced8de5d2145c2fd7a98688eeab23e3fbd2896ffc50f0892a5031`
- `artifacts/b1_teacher_smoke/dataset/smoke_with_policy.jsonl`
  - SHA256: `51767e46c85ad0f85e1240ea70abf0a07f5e26826efb5690bf4d7f64e6002c89`
- `artifacts/b1_teacher_smoke/dataset/smoke_train_eligible.jsonl`
  - SHA256: `dc2ea5ed2b540f79031460af928416edf10297c16657c84319d9a6dcbb053c03`
- `artifacts/b1_teacher_smoke/dataset/smoke_hard_cases.jsonl`
  - SHA256: `015ab112268d2da0e549e061e16b734b968e95d003734a011b4a6872644ff876`
- `artifacts/b1_teacher_smoke/dataset/smoke_rejected.jsonl`
  - SHA256: `d8f4902d273ad127d4e254d01ba22f30b7cccd8832e0ea6e67278a8a09147af3`
- `artifacts/b1_teacher_smoke/dataset/splits/train.jsonl`
  - SHA256: `b22a6466d1edf59b351c9cfbf0ff5bba44b80e5f397126efc6b7f5f1208cbbc2`
- `artifacts/b1_teacher_smoke/dataset/splits/val.jsonl`
  - SHA256: `4023297473f587b9f1aaf13b69851d6e094fb10ed1f48c94fcec11cb5b6be9fe`
- `artifacts/b1_teacher_smoke/dataset/dataset_manifest_v0.json`
  - SHA256: `29cfe8681405344a18137b463809689097a19f6a3066683a1aa7c91e0c00a4c2`
- `artifacts/b1_teacher_smoke/dataset/splits/split_manifest.json`
  - SHA256: `8f2fece04c4298f76b9ff9328e1f310d3d11228329e502781648bde9dd6195ed`

## 12. Version Policy

- Current Smoke version: `teacher_distill_v0.1_smoke`
- Published dataset versions must not be silently mutated.
- Corrections require a new version or patch version.
- Frozen Test will be created later and must remain immutable after freeze.
- Current Smoke Train/Val are pipeline-validation splits, not final D3 Train/Val/Test.

## 13. Smoke Acceptance

**B1 Smoke Dataset Acceptance: PASS**
