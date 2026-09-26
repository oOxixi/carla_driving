# A3 request: targeted-gap Teacher provenance addendum

## What already passes

`challenge/dataset/releases/d3_targeted_gap_strict_v1` is a valid immutable
byte release: 672 locked files, 660 RGB files, 561 Train rows, 99 development
Validation rows, zero hard negatives, zero Train/Validation group overlap and
zero overlap with the existing D2 + D3 Wave1 + D3 Wave2 partition.

This is sufficient for release transport/integrity.  It is not yet sufficient
for A3 formal distillation because the A3 training gate requires the exact
Teacher revision and model artifact fingerprint for every cohort.

## Missing evidence

The release currently records:

```text
model_id = Qwen/Qwen3.5-2B
acquisition_git_sha = a6743feb52015031f70e2c21a94aef0abae0a65a
```

It does not currently provide or sign:

- an exact Teacher model revision;
- a Teacher artifact fingerprint SHA256;
- a repository Teacher manifest matching the acquisition Git SHA;
- a `teacher` identity block in `B1_SIGNED_PASS.json`.

The known revision/fingerprint from earlier Teacher-v4 cohorts must not be
retroactively assigned to this release without B1 evidence.

## Requested B1 addendum

Please publish an immutable, versioned addendum rather than rewriting the 660
historical rows.  The addendum should contain and sign at least:

```text
dataset_version
teacher_profile
teacher_git_sha / acquisition_git_sha
model_id
model_revision
artifact_fingerprint_sha256
dtype
quantization
source release_manifest SHA256
source b1_release_lock SHA256
```

It must explicitly state whether all 660 samples share this identity.  A3 can
then bind the addendum hash into a new cumulative view manifest and rerun its
full RGB/partition audit.  Until then, the intake status is intentionally
`BLOCKED`, while the byte-integrity status remains `PASS`.
