# A3 D3 Recovery Cumulative-View Preparation

## Purpose and boundary

This preparation admits B1's targeted-gap and turn-gap recovery cohorts on top
of the already verified D2 v1.1 + D3 Wave1 + D3 Wave2 development view.  It
does not change the current v3 candidate, consume Reserved/Frozen Test, prove
Student accuracy or authorize promotion.

New view version:

```text
b1_d2_v1_1_plus_d3_wave1_plus_d3_wave2_plus_targeted_gap_plus_turn_gap_a3_strict_positive_v1
```

Default output directory:

```text
artifacts/a3_d2_d3_recovery_cumulative_positive_view_v1/
```

## Inputs and provenance

| Source | Addition | Provenance authority |
|---|---:|---|
| verified Wave2 cumulative view | 4,397 Train + 853 Val | canonical view/source hashes |
| `d3_targeted_gap_strict_v1` | 561 Train + 99 Val | immutable Teacher addendum |
| `d3_turn_gap_60_strict_v1` | 171 Train + 29 Val | release content binding |

Both new cohorts identify `Qwen/Qwen3.5-2B` at exact revision
`15852e8c16360a2fea060d615a32b45270f8a8fc` and artifact fingerprint
`4bbf183b7b7f1ab9fb9eb325f189f4449d65e9fe664cbfe4bcc58a33888657fa`.
Their declared signature status is `CONTENT_BOUND_UNSIGNED`.  This means the
immutable file set and Teacher identity are content-bound and validated, but
no detached/GPG signer identity is claimed.  The builder records this policy
choice explicitly rather than silently treating the cohorts as signed.

## Build, audit and tests

Run in a complete checkout containing every referenced RGB asset:

```bash
python -m challenge.distillation.audit_targeted_gap_intake
python -m challenge.dataset.validate_d3_turn_gap_release
python -m challenge.dataset.build_a3_recovery_cumulative_view
python -m challenge.distillation.audit_recovery_cumulative_view
```

The builder rejects failed provenance, missing images, unsupported Teacher
identities, non-positive/failed terminal states, duplicate IDs, missing group
keys, Train/Validation overlap or excluded samples reentering supervision.  The
read-only audit reconstructs the complete view and compares canonical
manifest, source-evidence, partition and file hashes.

Relevant regression suite:

```bash
python -m pytest -q \
  challenge/dataset/tests/test_build_a3_recovery_cumulative_view.py \
  challenge/dataset/tests/test_validate_d3_turn_gap_release.py \
  challenge/dataset/tests/test_a3_targeted_gap_intake.py \
  challenge/dataset/tests/test_build_a3_wave2_cumulative_view.py \
  challenge/dataset/tests/test_build_a3_cumulative_view.py \
  challenge/dataset/tests/test_build_a3_d2_view.py
```

## Full-server evidence

The commands above ran on the complete `tiaozhansai` checkout at
`challenge@fdf533480cb0543c151b08febebe7b40de3962cf` with image checks enabled.
The read-only audit returned `PASS`, and the regression suite returned
`7 passed`.

```text
train = 5129
development_validation = 981
audit_only_excluded = 539
targeted_gap_addition = 561 train + 99 val
turn_gap_addition = 171 train + 29 val
view_manifest_sha256 = 63f26554a52e270447e7cca977e2df9b31e05753fee96859e8d0a701874f166b
source_evidence_sha256 = 0867e9acfba5271b4af566a7ee9db34fa52248d052ebb093c5a38b5bfee5221d
train_jsonl_sha256 = 039a78c96ed13f6fa0af754e67a66c74dfff65631ad58556e707eeeeae82bcf7
val_jsonl_sha256 = 2c943825b2a10f65f9e30d88a5aab1a994c266fcab16e6c08ec6797778877868
excluded_jsonl_sha256 = ec4c6aa55d255535313fac1833a3c197fd8300943756680ce69e5e9380c3ccc9
audit_status = PASS
image_check_enabled = true
current_v3_candidate_identity_unchanged = true
```

The server artifacts are:

```text
artifacts/a3_d2_d3_recovery_cumulative_positive_view_v1/
artifacts/challenge/distillation/a3_recovery_cumulative_audit_v1.json
```

## Next decision

If the team elects to train on this view, create a new versioned training
config and output directory.  The resulting checkpoint must receive a new
candidate ID and weights SHA, then undergo independent B2 paired evaluation.
Never overwrite, rename or reinterpret the current v3 package.  Until B2
publishes identity-matched evaluation and Gate evidence, neither v3 nor a
future recovery candidate may be labelled `A3_FP32_GATE_PASSED`.
