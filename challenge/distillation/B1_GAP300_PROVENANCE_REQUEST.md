# A3 request: Gap300 Teacher provenance addendum

## Current status: BLOCKED_FOR_FINAL_TRAINING

B1's `d3_gap300_strict_v1` transport and data contract pass independently:

- 820/820 strict-positive samples and RGB assets;
- 697 Train rows and 123 development-Validation rows;
- 238 Train groups and 42 Validation groups;
- zero sample/group overlap with the prior A3 cumulative partition;
- behavior additions include 230 `TURN_LEFT`, 75 `YIELD` and 50 `PULL_OVER`
  steps across Train + Validation.

These labels directly address the vocabulary failure found by B3 on the old v3
candidate.  They are not yet eligible for the next formal A3 FP32 run because
the immutable release does not bind an exact Teacher revision or artifact
fingerprint.

The rows currently record:

```text
model_id = Qwen/Qwen3.5-2B
acquisition_git_sha = 95668ba3a466ae0dfcd73982f5a4a0d210b524c1
```

They do not record or content-bind:

```text
model_revision
artifact_fingerprint_sha256
```

No repository Teacher manifest currently matches the acquisition Git SHA.
A3 must not infer these values from an earlier cohort.

## Requested immutable addendum

Please follow the already accepted targeted-gap addendum pattern and publish:

```text
challenge/dataset/attestations/
  d3_gap300_strict_v1_teacher_provenance_v1/
    teacher_model_manifest.json
    teacher_provenance_attestation.json
    attestation_lock.sha256

challenge/teacher_gap300_manifest.json
```

The content binding must cover:

- dataset version and all 820 samples;
- acquisition/Teacher Git SHA;
- `Qwen/Qwen3.5-2B`;
- exact Hugging Face revision;
- model artifact fingerprint SHA256;
- dtype and quantization;
- source `release_manifest.json` SHA256;
- source `b1_release_lock.sha256` SHA256;
- an explicit statement that all 820 samples share the identity.

Do not rewrite the published rows or release lock.  The addendum must supplement
the immutable release.  Once it arrives, A3 can admit Gap300 into a new view of
5,826 strict-positive Train rows and 1,104 development-Validation rows, then
start a separately versioned FP32 candidate without overwriting v3.

## Count clarification

B1's closeout document reports 6,007 raw Train rows by summing the six release
files.  The A3 formal positive-supervision view is 5,826 because 181 D2
hard-negative rows remain audit-only.  Those rows must not be silently trained
as ordinary successful Teacher plans.
