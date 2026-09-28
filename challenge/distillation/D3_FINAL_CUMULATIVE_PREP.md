# A3 Final FP32 Cumulative-View Preparation

## Decision

Gap300 exact Teacher provenance is closed.  A3 may train a new FP32 candidate
from the governed final development view.  This authorizes training only; B2
still owns independent validation and `A3_FP32_GATE_PASSED`.

## Count policy

The B1 release-level inventory and A3 optimizer input are intentionally
different:

| Scope | Train | Dev | Meaning |
|---|---:|---:|---|
| governed raw releases | 6,007 | 1,154 | includes D2 hard negatives |
| A3 strict-positive view | 5,826 | 1,104 | ordinary supervised loss |
| audit-only exclusions | 181 | 50 | never relabelled as success |

Together with earlier D3 hard negatives, the final exclusion manifest contains
539 unique samples.  Reserved and Frozen Test data are not used.

## Reproducible commands

```bash
python -m challenge.dataset.validate_gap300_provenance_addendum
python -m challenge.distillation.audit_gap300_intake
python -m challenge.dataset.build_a3_final_cumulative_view
python -m challenge.distillation.audit_final_cumulative_view
python -m challenge.distillation.train \
  --config challenge/distillation/d3_final_cumulative_smoke_config.yaml \
  --integration-smoke
```

Formal training uses a separate fail-closed identity policy:

```bash
python -m challenge.distillation.train \
  --config challenge/distillation/d3_final_cumulative_formal_config.yaml
```

The formal run requires a clean committed worktree and cannot be invoked with
`--integration-smoke`.  The smoke policy cannot produce a promotable candidate.

## Full-server evidence

Verified on `tiaozhansai` with all RGB checks enabled:

```text
Gap300 intake                       READY
Gap300 RGB checked                  820
Gap300 overlap                      0
final train                         5826
final development validation        1104
audit-only exclusions               539
final view manifest SHA256          2840b7dc22bd0be56f1c26517b7b1e8a37ac4e7cf7111929def40dfc6daa8330
source evidence SHA256              c56eded3f646c4316d8635e771c6c7f555d52ddf248b15174ab75629256dc055
train JSONL SHA256                  50c4d2d47371b2a80abab27cc438114abcd5a872a477c1b0d02619d9cd77d53e
dev JSONL SHA256                    00cfa7f844fc6b33f9e8c30d617f12b70a05e3278b42c456853ab422617db7f7
targeted regression tests           5 passed
training/promotion regression tests 49 passed
```

The CUDA integration smoke completed two optimizer updates, validation,
checkpointing and candidate export.  Its candidate status is `MOCK_ONLY`; its
accuracy numbers are not a performance claim.

## Formal candidate focus

The new run enables bounded behavior-class balancing and must report at least:

- `TURN_LEFT` and `YIELD` behavior metrics;
- 3-step and 4-step plan sequence metrics;
- multi-step lane-change behavior;
- target grounding and distractor slices;
- target-speed MAE;
- safety-critical recall.

The old v3 package stays immutable as the baseline.  The new output directory,
candidate ID, config ID and weight SHA must remain distinct, and the exact
pending candidate must be handed to B2 without Frozen Test labels returning to
A3.
