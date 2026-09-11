# A3 × B1 Smoke v0 Integration

## Identity and scope

- Teacher model ID: `Qwen/Qwen3.5-2B`
- Teacher source SHA: `a05c8b76efcd4c176965223c661f40b153cb1836`
- Teacher revision: not recorded by B1 Smoke and must be pinned before final D3
- Dataset: `teacher_distill_v0.1_smoke`
- Student: `student-v0-r3-fp32`
- Train / Validation / quarantined: `22 / 6 / 2`
- Training view: `smoke_v0/training_view` (`a3_view_v1`)

This run is an integration check, not D3 training, an accuracy claim, or Frozen
Test evidence. The challenge Teacher manifest, B1 data and A3 configuration now
use the same model ID. Historical GPTQ INT4 reproduction evidence is not treated
as the current Teacher identity.

## Verified boundary

- B1's canonical data remains lossless; A3 consumes its committed derived
  `training_view` while retaining canonical provenance.
- Every Train/Validation row matches the configured Teacher SHA and model ID.
- Sample ID, request ID, canonical record and `group_key` do not cross splits.
- B1 TopK=8 pointers exactly match A1's frozen pointer encoder.
- Packaged RGB is resolved by SHA256 and size/hash checked before preprocessing.
- Training eligibility and valid-supervision fields fail closed.
- Two `LANE_GAP_UNSAFE` rows remain outside Train/Validation and are audited.

## Smoke result

The full 22/6 manifests passed preflight. The real A1 Student completed two CPU
optimizer updates and produced an A1-loadable pure state dict marked
`MOCK_ONLY`. Validation contains only six rows and the Student started from
random weights, so its metrics are pipeline diagnostics only.

Meaningful A3 training still depends on B1's larger versioned Train/Validation
delivery and B2's independent Teacher/Student Validation evidence. Frozen Test
remains excluded from training and tuning.
