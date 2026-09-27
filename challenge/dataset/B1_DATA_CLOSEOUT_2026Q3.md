# B1 Data Closeout — 2026 Q3

## Final Status

```text
B1_DATA_COLLECTION = PAUSED
CALIBRATION_V1 = FROZEN
HISTORICAL_RELEASES = IMMUTABLE
FROZEN_TEST = NOT_YET_FROZEN
B2_BENCHMARK_OWNERSHIP = PRESERVED
```

B1 does not continue mass collection solely to reach a nominal training-row
target.

Future data collection is demand-driven and may resume only when downstream
B2/A3 evaluation identifies a concrete capability, generalization, target
grounding, safety, or deployment weakness that is not adequately represented
by the current governed assets.

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

Gap300 formal acquisition:

```text
attempted runs              = 300
strict-positive runs        = 280
excluded runs               = 20
strict-positive samples     = 820
train addition              = 697
validation addition         = 123
```

The excluded 20 runs remain excluded and are not converted into positive
training supervision.

## Calibration v1

Frozen release:

`challenge/dataset/releases/calibration_v1`

Source pool:

`challenge/dataset/releases/d2_v1_1/reserved_test_candidates.jsonl`

Source pool:

```text
samples = 540
groups  = 540
```

Frozen Calibration v1:

```text
samples = 300
groups  = 300
```

Remaining unallocated reserved pool:

```text
samples = 240
groups  = 240
```

The remaining 240 samples are not Frozen Test and are not automatically
assigned to B2.

### Calibration Source Distribution

```text
D1           = 8
D2_WAVE1    = 85
D2_WAVE2   = 207
```

### Calibration Scenario-Family Distribution

```text
lateral_B       = 59
qwen_fullchain  = 9
qwen_routing    = 20
regression      = 74
safety_D       = 114
smoke           = 24
```

### Calibration Published D2 Role Distribution

```text
POSITIVE       = 274
HARD_NEGATIVE  = 18
LEGACY_D1      = 8
```

### Calibration Selection Contract

Calibration selection is deterministic.

Joint stratification dimensions:

```text
source
x scenario_family
x published D2 training role
```

Allocation uses proportional largest-remainder rounding.

Selection inside each joint stratum uses deterministic SHA256 ranking with
the frozen selection salt recorded in `calibration_manifest.json`.

Historical D2 rows are not rewritten.

For legacy D1 rows without inline `quality.training_role`, Calibration follows
the published D2 validator convention and records them as `LEGACY_D1`.

### Calibration Isolation

Formal validator result:

```text
calibration_samples     = 300
calibration_groups      = 300
unallocated_reserved    = 240

train_sample_overlap    = 0
train_group_overlap     = 0
dev_sample_overlap      = 0
dev_group_overlap       = 0

rgb_checked             = 300
error_count             = 0

CALIBRATION_VALIDATOR_RC = 0
```

Calibration v1 is:

- not training data;
- not development data;
- not Frozen Test;
- frozen for downstream PTQ calibration;
- not replaceable based on PTQ outcome.

Future B2 Frozen Benchmark construction must exclude every Calibration v1
`sample_id` and `group_key`.

### Calibration Content Binding

```text
calibration_manifest.json
659c5e8210ee95cf835be685da1deb55bc1990874ba3e120955d6bdf392d8059

calibration.jsonl
e7520afc683b4545ca0981c549d0aebef50a90962a0d95378d89c1ca4bfbe8cc
```

## D2 v1.1 Integrity

D2 v1.1 was validated again after Calibration construction.

Result:

```text
valid = true
error_count = 0
referenced_images = 3592
```

Calibration construction does not modify D2 v1.1.

## Teacher Provenance

Historical data keeps its original Teacher provenance.

Observed D2 v1.1 Teacher Git SHAs include:

```text
D1
2f04764d7eb08ed78ef81eadca8ddeae3c427392

D2 Wave1
1a363c15b9b1790534358c11acbd100a3011fa93

D2 Wave2 / Teacher v4
95e97b00def8ec36f12937da34ce8bb9082c4a04
```

Historical releases are not rewritten to create artificial Teacher-version
uniformity.

New formal Teacher-v4 work uses the pinned Teacher-v4 provenance contract.

## Gap / Coverage Policy

B1 does not claim that every possible GAP-01 through GAP-12 generalization
axis has been exhaustively collected.

Current policy:

- do not expand stable atomic behaviors merely for row count;
- do not use same source text plus many seeds as primary diversity scaling;
- same route with only changed seed/weather is not treated as route novelty;
- HOLD remains deferred where its runtime/contract blocker is unresolved;
- route topology, complex behavior chains, target/distractor cases,
  language diversity, environment diversity, and independent scenario
  families remain eligible for future targeted work;
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

Current critical path:

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

A2 must use the frozen Calibration v1 release rather than creating an
ad-hoc replacement calibration set.

## Closeout Decision

```text
B1_DATA_CLOSEOUT = PASS_WITH_DOCUMENTED_DEFERRED_GAPS
DATA_EXPANSION = PAUSED
CALIBRATION_V1 = FROZEN
FROZEN_TEST = B2_PENDING
NEXT_STAGE = B2 / A3
```

This closeout freezes the currently governed B1 assets for downstream work.
Remaining gaps stay explicit and may be reopened only when justified by
concrete downstream evidence.
