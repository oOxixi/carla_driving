# A3 D3 Wave2 Derived-View Preparation

## Purpose and boundary

This preparation adds B1's signed D3 Wave2 safe-short release to the existing
D2 v1.1 + D3 Wave1 A3 development inputs.  It does not change the current v3
candidate, does not consume Independent/Frozen Test, and does not authorize a
new formal training run by itself.

New view version:

```text
b1_d2_v1_1_plus_d3_wave1_plus_d3_wave2_safe_short_a3_strict_positive_v1
```

Default output directory:

```text
artifacts/a3_d2_d3_wave2_cumulative_positive_view_v1/
```

## Inputs

| Source | Role | Integrity authority |
|---|---|---|
| `challenge/dataset/releases/d2_v1_1` | existing strict-positive base | signed D2 release |
| `challenge/dataset/releases/d3_wave1_addon_v1` | existing additive development data | detached B1 signature |
| `challenge/dataset/releases/d3_wave2_safe_short_v1` | new additive development data | detached `B1_SIGNED_PASS.json` |

D3 Wave2 contains 318 Train and 56 development Validation rows.  Its 374 RGB
files, release lock, release manifest, B1 signature, integrity report and
pinned Teacher-v4-wave2-sync manifest pass the release validator.

## Build and audit

Run this only in a complete checkout containing every referenced RGB file:

```bash
python -m challenge.dataset.build_a3_wave2_cumulative_view
```

Then run the read-only audit in an environment with the project dependencies:

```bash
python -m challenge.distillation.audit_wave2_cumulative_view
```

Expected counts:

| Partition | Count |
|---|---:|
| Train | 4,397 |
| development Validation | 853 |
| audit-only excluded | 539 |
| D3 Wave2 Train addition | 318 |
| D3 Wave2 Validation addition | 56 |
| D3 Wave2 hard negatives | 0 |

The builder fails closed on release/signature failure, unsupported Teacher
cohorts, non-success terminal state, non-positive rows, duplicate IDs, missing
group keys, Train/Validation sample overlap, group overlap, or excluded samples
reentering supervision.  The audit reconstructs the base view and verifies
the exact input partition, file hashes, portable source paths and Teacher
manifest hashes.

For metadata-only development checks, `--skip-images` is available on both
commands.  Outputs produced that way are never formal training evidence.

## Local preparation evidence

The local partial checkout validated the full D3 Wave2 release, including
374/374 images.  Some historical D3 Wave1 images are absent locally, so the
combined preparation used metadata-only mode and produced:

```text
view_manifest_sha256 = 20d15be92c7f4bf2681d6e1a20be9da45acd99569ce78c5f3cf7290ed579c296
source_evidence_sha256 = c8f179c67369d598b156ae1dbea68fb912613808958c29b466a6944f47774995
audit_status = PASS
```

These hashes are a reproducibility target for the full server regeneration,
not a claim that the local metadata-only view is ready for formal training.

## Promotion rule

If Wave2 is selected for training, create a new candidate directory and new
model/config identity.  Do not overwrite `student-v0-r3-fp32`, reuse its
weights SHA, or retarget its B2 handoff.  Any later candidate must independently
pass the same B2 Teacher/Student comparison and A3 FP32 Gate.
