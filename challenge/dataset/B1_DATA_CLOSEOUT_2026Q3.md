# B1 Data Closeout — 2026 Q3

## Final Status

```text
B1_DATA_COLLECTION = PAUSED
CALIBRATION_V1 = FROZEN
HISTORICAL_RELEASES = IMMUTABLE
FROZEN_TEST = NOT_YET_FROZEN
B2_BENCHMARK_OWNERSHIP = PRESERVED
```

B1 does not continue mass collection solely to reach a nominal training-row target.

Future data collection is demand-driven and may resume only when downstream B2/A3 evaluation identifies a concrete capability, generalization, target-grounding, safety, or deployment weakness that is not adequately represented by the current governed assets.

## Current A3 Dataset View

```text
Train rows = 6007
Dev rows   = 1154
```

Current A3 training inputs:

- `d2_v1_1/train.jsonl`
- `d3_wave1_addon_v1/train_addition.jsonl`
- `d3_wave2_safe_short_v1/train_addition.jsonl`
- `d3_targeted_gap_strict_v1/train_addition.jsonl`
- `d3_turn_gap_60_strict_v1/train_addition.jsonl`
- `d3_gap300_strict_v1/train_addition.jsonl`

Current A3 development inputs:

- `d2_v1_1/val.jsonl`
- `d3_wave1_addon_v1/val_addition.jsonl`
- `d3_wave2_safe_short_v1/val_addition.jsonl`
- `d3_targeted_gap_strict_v1/val_addition.jsonl`
- `d3_turn_gap_60_strict_v1/val_addition.jsonl`
- `d3_gap300_strict_v1/val_addition.jsonl`

## Published Immutable Releases

The following published releases remain immutable:

- `d2_v1`
- `d2_v1_1`
- `d3_wave1_addon_v1`
- `d3_wave2_safe_short_v1`
- `d3_targeted_gap_strict_v1`
- `d3_turn_gap_60_strict_v1`
- `d3_gap300_strict_v1`

## Gap300 Closeout

```text
attempted runs              = 300
strict-positive runs        = 280
excluded runs               = 20
strict-positive samples     = 820
train addition              = 697
validation addition         = 123
```

The excluded 20 runs remain excluded and are not converted into positive training supervision.

## Calibration v1

Frozen release:

`challenge/dataset/releases/calibration_v1`

Source pool:

`challenge/dataset/releases/d2_v1_1/reserved_test_candidates.jsonl`

```text
source samples = 540
source groups  = 540

calibration samples = 300
calibration groups  = 300

unallocated reserved samples = 240
unallocated reserved groups  = 240
```

The remaining 240 samples are not Frozen Test and are not automatically assigned to B2.

Calibration validation result:

```text
calibration_samples  = 300
calibration_groups   = 300
train_sample_overlap = 0
train_group_overlap  = 0
dev_sample_overlap   = 0
dev_group_overlap    = 0
rgb_checked          = 300
unallocated_reserved = 240
error_count          = 0
valid                = true
CALIBRATION_RC       = 0
```

## Teacher Provenance

Historical data keeps its original Teacher provenance.

Current formal Teacher-v4 identity:

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

Pinned manifest:

```text
challenge/teacher_pinned_manifest_v4.json
SHA256 = 82aef8a13649cffdd17c9cd64003e3967448773548c2b5fcb15fd3b0d5b08220
```

Historical releases are not rewritten to create artificial Teacher-version uniformity.

New formal Teacher-v4 work uses the pinned Teacher-v4 provenance contract.

## Gap / Coverage Policy

B1 does not claim that every possible GAP-01 through GAP-12 generalization axis has been exhaustively collected.

Current policy:

- do not expand stable atomic behaviors merely for row count;
- do not use same source text plus many seeds as primary diversity scaling;
- same route with only changed seed/weather is not treated as route novelty;
- HOLD remains deferred where its runtime/contract blocker is unresolved;
- route topology, complex behavior chains, target/distractor cases, language diversity, environment diversity, and independent scenario families remain eligible for future targeted work;
- future collection must be driven by concrete downstream evidence.

Any reopened formal collection must again pass the applicable:

```text
semantic audit
target contract audit
actor-reference audit
Base/GEN parity audit
acceptance audit
route/spawn audit
static validation
3-5 seed closed-loop smoke
provenance/content binding
```

before large formal acquisition.

## Handoff

```text
B1 governed data closeout
        ↓
B2 Independent Validation
        ↓
B2 Frozen Benchmark
        ↓
A3 FP32 Gate
        ↓
real FP32 ONNX
        ↓
A2 PTQ using frozen Calibration v1
```

B2 owns Frozen Benchmark construction and independent evaluation.

A3 must not use Frozen Test feedback for tuning.

A2 must use the frozen Calibration v1 release rather than creating an ad-hoc replacement calibration set.

## Post-Closeout Provenance Addendum

The follow-up B1 governance audit required by the unified execution plan has been completed.

### Gap300 Provenance Addendum

A detached provenance addendum is published at:

```text
challenge/dataset/attestations/
d3_gap300_strict_v1_provenance_addendum_v1/
```

It does not modify the immutable Gap300 release.

Validation result:

```text
GAP300_PROVENANCE_ADDENDUM_GATE = PASS
rows                             = 820
teacher model ID verified        = 820/820 Qwen/Qwen3.5-2B
teacher mode verified            = 820/820 planner_v2
validator errors                 = 0
ADDENDUM_RC                      = 0
```

Content bindings:

```text
gap300_provenance_addendum.json
4369cc767631dc13654d1e433bb933cd2f4a0c3b971d3490997e4f11f355106d

GAP300_PROVENANCE_ADDENDUM.md
9c163ee8db196c897dfdf4eeeafef8076d007d0c326a4e9b20cfcc1fe261c8b9
```

The historical Gap300 field `metadata.teacher_git_sha` is preserved exactly as recorded and is not retroactively interpreted as the canonical pinned Teacher-model Git identity.

Observed historical distribution:

```text
95668ba3a466ae0dfcd73982f5a4a0d210b524c1 = 770 samples
e150ae598d95cb024faebc1699b872d0de899e91 = 50 samples
```

Corresponding service/family mapping:

```text
770:
  service         = http://127.0.0.1:18004
  scenario_family = qwen_fullchain

50:
  service         = http://127.0.0.1:18009
  scenario_family = regression
  cohort          = D01 pull-over
```

The D01 SHA resolves to:

```text
e150ae5 feat: add validated D01 pull-over support
```

Exact pinned Teacher-v4 revision/fingerprint fields were not stored in the historical Gap300 sample rows and are therefore not retroactively asserted.

### Teacher-v4 Governance Audit

```text
B1_TEACHER_V4_GOVERNANCE_GATE = PASS
TEACHER_V4_AUDIT_RC            = 0
```

The current formal surfaces bind to Teacher v4.

The following older Teacher references are intentionally preserved:

```text
challenge/dataset/collect_d2_expansion.py
  historical D2 Wave1 / Teacher-v3 collector
  status = EXPECTED_LEGACY_COLLECTOR
  action = DO_NOT_MODIFY
  action = DO_NOT_USE_FOR_NEW_FORMAL_COLLECTION

challenge/dataset/build_a3_d2_view.py
  historical cohort identity mapping
  status = EXPECTED_HISTORICAL_REFERENCE
  action = PRESERVE
```

They are not current formal Teacher entry points and must not be rewritten to create artificial provenance uniformity.

## Final B1 Checklist

```text
[x] Gap300 provenance addendum
[x] current release closeout
[x] stop unguided data expansion
[x] Teacher v4 governance
```

## Final B1 Decision

```text
B1_DATA_CLOSEOUT = PASS_WITH_DOCUMENTED_DEFERRED_GAPS
B1_CURRENT_TASKS = COMPLETE
DATA_COLLECTION = PAUSED
CALIBRATION_V1 = FROZEN
HISTORICAL_RELEASES = IMMUTABLE
TEACHER_V4_GOVERNANCE = PASS
GAP300_PROVENANCE_ADDENDUM = PASS
FROZEN_TEST = B2_PENDING
NO_CURRENT_B1_ACTION_REQUIRED = TRUE
```

B1 may be reopened only if downstream B2/A3 evidence identifies a concrete data or Teacher-supervision gap that is not adequately covered by the currently governed assets.

---

## Post-Closeout Resolution — Gap300 Exact Teacher Provenance

After the initial B1 closeout, downstream A3 introduced a fail-closed intake gate requiring exact Teacher artifact provenance for the immutable `d3_gap300_strict_v1` release.

B1 resolved this requirement without modifying the published Gap300 rows, release manifest, or release lock.

### Exact Historical Teacher Identity

The Gap300 cohort contains 820 strict-positive samples with the following acquisition-code distribution:

```text
95668ba3a466ae0dfcd73982f5a4a0d210b524c1 = 770 samples
e150ae598d95cb024faebc1699b872d0de899e91 = 50 samples
```

All 820 rows record:

```text
model_id  = Qwen/Qwen3.5-2B
qwen_mode = planner_v2
```

Historical runtime evidence establishes that both acquisition cohorts were served by the same exact Teacher model artifact:

```text
Model:
Qwen/Qwen3.5-2B

Model revision:
15852e8c16360a2fea060d615a32b45270f8a8fc

Artifact fingerprint:
4bbf183b7b7f1ab9fb9eb325f189f4449d65e9fe664cbfe4bcc58a33888657fa

dtype:
bfloat16

quantization:
null
```

The historical model manifest binds the exact revision and artifact fingerprint to:

```text
/home/dcase_task2/dongfeng_voice/carla_driving_challenge_b1/
models/Qwen3.5-2B_15852e8
```

The surviving vLLM process on port `8001` was observed with the same long-lived PID that originally loaded this directory and served:

```text
served_model_name = Qwen/Qwen3.5-2B
dtype             = bfloat16
quantization      = none
```

Both Gap300 Qwen proxy services bind to that same vLLM endpoint:

```text
18004 -> http://127.0.0.1:8001/v1 -> 770 samples
18009 -> http://127.0.0.1:8001/v1 ->  50 samples
```

Therefore:

```text
ALL_820_SAME_ARTIFACT = VERIFIED
```

This conclusion is based on historical runtime lineage and detached content-bound evidence. The original sample rows remain unchanged.

### Detached Exact-Teacher Attestation

The exact provenance supplement is published outside the immutable release at:

```text
challenge/teacher_gap300_manifest.json

challenge/dataset/attestations/
  d3_gap300_strict_v1_teacher_provenance_v1/
    teacher_model_manifest.json
    teacher_provenance_attestation.json
    attestation_lock.sha256
```

Content hashes:

```text
teacher_model_manifest.json
ccf1c2fed7a9bb02f4ae28f0a6326d2fba506277f20e0876519cd2705ccc404d

teacher_provenance_attestation.json
de7a2f1acc33be2f26f4d9480a17ad72e8f9a34b591c580f04e826b5ee194c25

attestation_lock.sha256
63507969dd62c7f7170afb44214dd0da1a623f9941f54368c2d48f4f22530d14

challenge/teacher_gap300_manifest.json
710859ecc436d9f0e709661ba99fbe4fa9daad89e49861a154501f1f53a8e005
```

Immutable source-release bindings remain:

```text
release_manifest.json
a2fbe23674dfa984bba9e5623b931583f0ed53479ac5846b1fe3535a2a465427

b1_release_lock.sha256
695905864b9133c27c1e9ee7a6b7e57ddfd2219ba8a64bc48a7bf9b81c20c3f7
```

Attestation policy:

```text
signature_status                    = CONTENT_BOUND_UNSIGNED
cryptographic_signature_present     = false
supplements_without_mutating_release = true
```

No cryptographic identity signature is claimed.

### A3 Intake Resolution

The formal A3 Gap300 intake verifier now reports:

```text
status                     = READY
eligible_for_a3_final_view = true
blockers                   = []
required_b1_followup       = []
A3_GAP300_INTAKE_RC        = 0
```

The corresponding regression tests now cover both valid and fail-closed behavior:

```text
complete exact Teacher attestation -> READY
missing Teacher attestation        -> BLOCKED
```

Final targeted validation:

```text
3 passed
GAP300_TARGETED_TEST_RC = 0
```

Additional final gates:

```text
B1_ADDENDUM_RC  = 0
CALIBRATION_RC   = 0
DIFF_CHECK_RC    = 0
HISTORICAL_RELEASE_DIFF = empty
```

The original Gap300 rows still do not contain exact revision/fingerprint fields. They were not retroactively rewritten. Exact identity is established by historical runtime evidence plus the detached immutable attestation.

### Final B1 State After Resolution

```text
B1_DATA_CLOSEOUT = PASS_WITH_DOCUMENTED_DEFERRED_GAPS
B1_CURRENT_TASKS = COMPLETE
B1_DATA_COLLECTION = PAUSED
CALIBRATION_V1 = FROZEN
HISTORICAL_RELEASES = IMMUTABLE
TEACHER_V4_GOVERNANCE = PASS
GAP300_PROVENANCE_ADDENDUM = PASS
GAP300_EXACT_TEACHER_PROVENANCE = VERIFIED
GAP300_ALL_820_SAME_ARTIFACT = VERIFIED
A3_GAP300_INTAKE = READY
FROZEN_TEST = B2_PENDING
NO_CURRENT_B1_ACTION_REQUIRED = TRUE
```

B1 is now `COMPLETE / MAINTENANCE_ONLY`. It should reopen only if downstream B2 or A3 provides concrete evidence of a new B1-owned data or Teacher-supervision gap.
