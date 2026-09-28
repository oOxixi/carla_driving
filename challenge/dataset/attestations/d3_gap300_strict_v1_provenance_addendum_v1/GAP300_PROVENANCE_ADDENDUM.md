# D3 Gap300 Strict v1 — Provenance Addendum

## Purpose

This addendum clarifies provenance for the immutable release:

`challenge/dataset/releases/d3_gap300_strict_v1`

It does **not** modify, relabel, or rewrite the historical release.

Attestation type:

```text
HISTORICAL_PROVENANCE_ADDENDUM_CONTENT_BOUND_UNSIGNED
```

Status:

```text
PASS_WITH_HISTORICAL_IDENTITY_LIMITATION
```

## Immutable Release Binding

```text
dataset_version:
b1_d3_gap300_strict_v1

release_manifest_sha256:
a2fbe23674dfa984bba9e5623b931583f0ed53479ac5846b1fe3535a2a465427

provenance_manifest_sha256:
20ea6be56175808f6dfd923cbd3ad58840f37308a00df946224168bf9a859fc8

release_lock_sha256:
695905864b9133c27c1e9ee7a6b7e57ddfd2219ba8a64bc48a7bf9b81c20c3f7

release image-set canonical sha256:
a31c1b1c1a155ff85b72e97a7b1b38da947567c39f1dde64ba4895e7862bb172

source dataset sha256:
f59db0e16e639f71052ba254f47fc6b96ba44cd3cee6c21ae29f344702b57951

source release manifest sha256:
add470dbb91a9a445cb30bd49062f5308bf67666408250f2efa0f259737f6427

source image-set sha256:
dbbcf43c179b525a9b3e5c7c4d9688782384cf3840f1ceabd7efa1a95978c771
```

## Published Cohort

```text
source runs             = 300
strict-positive runs    = 280
strict-positive samples = 820
train addition          = 697
validation addition     = 123
excluded runs           = 20
```

Historical failed/excluded runs remain immutable and are not retroactively relabeled.

## Sample-Level Identity Actually Recorded

All published Gap300 rows record:

```text
teacher_model_id = Qwen/Qwen3.5-2B
teacher_mode     = planner_v2
```

Observed counts:

```text
Qwen/Qwen3.5-2B = 820
planner_v2      = 820
```

The historical field `metadata.teacher_git_sha` contains two values:

```text
95668ba3a466ae0dfcd73982f5a4a0d210b524c1 = 770 samples
e150ae598d95cb024faebc1699b872d0de899e91 = 50 samples
```

The corresponding acquisition/runtime cohorts are:

```text
770 samples:
service = http://127.0.0.1:18004
scenario_family = qwen_fullchain

50 samples:
service = http://127.0.0.1:18009
scenario_family = regression
D01 pull-over cohort
```

The D01 SHA resolves to:

```text
e150ae5 feat: add validated D01 pull-over support
```

## Important Historical Field Clarification

`metadata.teacher_git_sha` in this historical Gap300 release must not be interpreted as the canonical pinned Teacher-model Git identity.

For this cohort the field varies with the acquisition/runtime checkout.

Therefore it is retained exactly as published and is not rewritten to:

```text
95e97b00def8ec36f12937da34ce8bb9082c4a04
```

## Identity Fields Not Recorded in Gap300 Rows

The Gap300 rows do not directly record:

```text
teacher_profile
model_revision
artifact_fingerprint
dtype
quantization
```

Therefore this addendum does **not** retroactively assert that the 820 historical rows contain sample-level proof of the exact pinned Teacher-v4 revision or artifact fingerprint.

## Current Formal Teacher-v4 Policy

Current pinned Teacher manifest:

```text
challenge/teacher_pinned_manifest_v4.json
```

Manifest SHA256:

```text
82aef8a13649cffdd17c9cd64003e3967448773548c2b5fcb15fd3b0d5b08220
```

Current formal Teacher identity:

```text
profile:
b1-pinned-teacher-v4

Teacher Git SHA:
95e97b00def8ec36f12937da34ce8bb9082c4a04

model:
Qwen/Qwen3.5-2B

model revision:
15852e8c16360a2fea060d615a32b45270f8a8fc

artifact fingerprint:
4bbf183b7b7f1ab9fb9eb325f189f4449d65e9fe664cbfe4bcc58a33888657fa

dtype:
bfloat16

quantization:
null
```

This identity is mandatory for **new formal Teacher work**.

It must not be retroactively attributed to historical rows where the required identifying fields were not recorded.

## Governance Decision

```text
HISTORICAL_GAP300_RELEASE = IMMUTABLE
HISTORICAL_SAMPLE_PROVENANCE = PRESERVED
GAP300_MODEL_ID = VERIFIED_820_OF_820
GAP300_TEACHER_MODE = VERIFIED_820_OF_820
EXACT_V4_REVISION_AT_SAMPLE_LEVEL = NOT_RECORDED
EXACT_V4_ARTIFACT_AT_SAMPLE_LEVEL = NOT_RECORDED
NEW_FORMAL_TEACHER_WORK = PINNED_TEACHER_V4_REQUIRED
```

This addendum closes the provenance ambiguity without modifying the published dataset.
