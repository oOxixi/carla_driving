# A3 targeted-gap Teacher provenance addendum receipt

## Status: FULFILLED

B1 has published the immutable addendum requested below.  A3 independently
verified the release bytes, all 660 RGB assets, the addendum lock and the
content binding before admitting this cohort to a new versioned development
view.

Verified identity:

```text
model_id = Qwen/Qwen3.5-2B
model_revision = 15852e8c16360a2fea060d615a32b45270f8a8fc
artifact_fingerprint_sha256 = 4bbf183b7b7f1ab9fb9eb325f189f4449d65e9fe664cbfe4bcc58a33888657fa
acquisition_git_sha = a6743feb52015031f70e2c21a94aef0abae0a65a
teacher_attestation_sha256 = 24c2690d8590fe2e1ecff48f75d391b03941e3405f08cd306aba6e99e6f878c5
teacher_content_binding_sha256 = 505051b1c764a1f464dc31a6e44ea705d21693d4eb935cd99ffd289ff7b428b2
signature_status = CONTENT_BOUND_UNSIGNED
```

`CONTENT_BOUND_UNSIGNED` means that every declared file/hash binding validates,
but there is no cryptographic signer identity.  A3 accepts that explicit
provenance class for development training inputs; it must not be described as
a detached/GPG-signed release or independent Test evidence.  The executable
intake result is now `READY`, not `BLOCKED`.

The accepted cohort is consumed only by
`build_a3_recovery_cumulative_view.py`; the current v3 candidate and its B2
handoff are unchanged.

## What already passes

`challenge/dataset/releases/d3_targeted_gap_strict_v1` is a valid immutable
byte release: 672 locked files, 660 RGB files, 561 Train rows, 99 development
Validation rows, zero hard negatives, zero Train/Validation group overlap and
zero overlap with the existing D2 + D3 Wave1 + D3 Wave2 partition.

This was sufficient for release transport/integrity but was not sufficient for
A3 formal distillation until the addendum above arrived.

## Original missing evidence (resolved)

The release currently records:

```text
model_id = Qwen/Qwen3.5-2B
acquisition_git_sha = a6743feb52015031f70e2c21a94aef0abae0a65a
```

The original release did not provide or bind:

- an exact Teacher model revision;
- a Teacher artifact fingerprint SHA256;
- a repository Teacher manifest matching the acquisition Git SHA;
- a `teacher` identity block in `B1_SIGNED_PASS.json`.

The values above are now attributed through B1's cohort-specific addendum,
not by retroactive inference from another cohort.

## Original requested B1 addendum

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

The published addendum explicitly covers all 660 samples.  A3 bound its exact
hash into the recovery cumulative view and reran the full RGB/partition audit
on `tiaozhansai`; that audit passed.
