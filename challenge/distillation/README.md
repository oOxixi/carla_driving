# A3 Distillation

This directory owns knowledge distillation and accuracy recovery only.  It does
not modify the frozen CARLA A/B/C/D control chain, dataset splits, benchmark
definitions, or deployment runtime.

The default smoke path uses contract-valid mock records with A1's real
`StudentPlannerV0` and `StudentPreprocessor` to prove this chain:

```text
ModelRequest V1 + ManeuverPlan V2
  -> fixed-shape labels and masks
  -> Student structured heads
  -> risk-weighted multi-head loss
  -> backward/update
  -> validation metrics
  -> checkpoint/resume metadata
  -> validation hard-case records
```

Run the smoke test in a PyTorch training environment:

```bash
python -m challenge.distillation.train \
  --config challenge/distillation/train_config.yaml \
  --smoke
```

Generated checkpoints and logs go under `/artifacts`, which is excluded from
Git. Mock records must never be mixed into B1 production datasets or reported
as Student accuracy.

Production training requires both `dataset.train_path` and `dataset.val_path`.
Before loading them, the trainer validates all records, checks declared split
and dataset version, and rejects duplicate sample IDs, request IDs, exact
records, or Train/Validation overlap. Paths or record metadata containing
`test`/`frozen` are rejected, so A3 cannot accidentally tune on B1's frozen
Test set.

Run dataset preflight without training:

```bash
python -m challenge.distillation.preflight \
  --train data/train.jsonl \
  --val data/validation.jsonl \
  --dataset-version b1-v1 \
  --output artifacts/challenge/distillation/preflight.json
```

After A1 and B1 are connected, run the bounded integration gate first. It
preflights the complete manifests, selects at most 50 records from each split,
then performs no more than two optimizer updates:

```bash
python -m challenge.distillation.train \
  --config challenge/distillation/train_config.yaml \
  --integration-smoke
```

For the committed B1 Smoke v0 delivery, use its dedicated configuration:

```bash
python -m challenge.distillation.train \
  --config challenge/distillation/b1_smoke_config.yaml \
  --integration-smoke
```

This path consumes B1's committed `training_view`, verifies the unified
`Qwen/Qwen3.5-2B` Teacher identity, resolves
packaged RGB by SHA256 instead of stale collector-host paths, checks B1's
recorded target pointers against A1's encoder, and audits quarantined records
without mixing them into ordinary supervision. Integration-smoke candidates
remain `MOCK_ONLY` and cannot pass the production FP32 gate.

A1 V0 r3 is already wired through `a1_student.py`; its frozen class order,
target-pointer convention, Head names and four-modal input shapes are imported
from `challenge.student` rather than duplicated. Every forward call is checked
for required Head names, exact shapes, floating
dtype, device alignment, and finite values before loss calculation. Non-finite
losses or gradients fail closed. See [HANDOFF.md](HANDOFF.md) for the exact A1
and B1 boundaries.

Class balancing is disabled by default. When enabled in YAML, weights are
computed from Train labels only, bounded by `max_weight`, and stored in the
checkpoint metadata. Validation and Test never contribute to those weights.

Each run writes strict JSON logs, a human-readable `training_report.md`, an
atomic best/last checkpoint, and categorized Validation hard cases. Epoch
boundary resume restores model, optimizer, Python/Torch RNG, and DataLoader
shuffle state.

The best checkpoint is also exported as a pure A1-compatible state dictionary
and a candidate manifest. Mock runs are marked `MOCK_ONLY`; real runs remain
`PENDING_A3_FP32_GATE`. Only `promote.py`, supplied with version-matched,
independent Validation evidence for Teacher and Student, can create
`A3_FP32_GATE_PASSED`. Frozen Test evidence is explicitly rejected.

After B1 and B2 deliver version-matched Validation evidence, promotion uses:

```bash
python -m challenge.distillation.promote \
  --candidate artifacts/run/student_v0_fp32_candidate.json \
  --weights artifacts/run/student_v0_fp32_candidate.pt \
  --teacher-evaluation artifacts/eval/teacher_validation.json \
  --student-evaluation artifacts/eval/student_validation.json \
  --output artifacts/run/student_v0_fp32.manifest.json
```

The default core-accuracy drop limit is 1.5 percentage points. Safety-critical
recall may not drop, and Student schema validity must be exactly 100%.
