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

The rows currently record one model ID but two acquisition Git SHAs:

```text
model_id = Qwen/Qwen3.5-2B
95668ba3a466ae0dfcd73982f5a4a0d210b524c1 = 770 rows (C01/C02/C03)
e150ae598d95cb024faebc1699b872d0de899e91 = 50 rows (D01/PULL_OVER)
```

The release-level provenance manifest declares only `95668...`, so it does not
currently explain or bind the 50 D01 rows collected at `e150...`.

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
- both observed acquisition/Teacher Git SHAs and their covered row sets;
- `Qwen/Qwen3.5-2B`;
- exact Hugging Face revision;
- model artifact fingerprint SHA256;
- dtype and quantization;
- source `release_manifest.json` SHA256;
- source `b1_release_lock.sha256` SHA256;
- an explicit statement whether all 820 samples share the same model artifact
  identity despite the two acquisition code revisions.

For direct compatibility with the committed A3 verifier, use these fields:

```text
teacher_provenance_attestation.json:
  status = PASS
  signature_status = CONTENT_BOUND_UNSIGNED
  supplements_without_mutating_release = true
  teacher.model_id / model_revision / artifact_fingerprint_sha256
  teacher.dtype / quantization / qwen_mode
  coverage.canonical_samples = 820
  coverage.all_samples_share_teacher_identity = true
  coverage.acquisition_git_sha_counts = {95668...: 770, e150...: 50}
  source_release.release_manifest_sha256 / b1_release_lock_sha256
  repository_teacher_manifest.path / sha256
  binding.payload.all_820_samples_share_teacher_identity = true
  binding.payload.acquisition_git_sha_counts = the same two-cohort mapping

teacher_gap300_manifest.json:
  teacher.model_id / model_revision / model_artifact_sha256
  teacher.dtype / quantization / qwen_mode
  acquisition_git_sha_counts = the same two-cohort mapping
```

Do not rewrite the published rows or release lock.  The addendum must supplement
the immutable release.  Once it arrives, A3 can admit Gap300 into a new view of
5,826 strict-positive Train rows and 1,104 development-Validation rows, then
start a separately versioned FP32 candidate without overwriting v3.

## Count clarification

B1's closeout document reports 6,007 raw Train rows by summing the six release
files.  The A3 formal positive-supervision view is 5,826 because 181 D2
hard-negative rows remain audit-only.  Those rows must not be silently trained
as ordinary successful Teacher plans.
