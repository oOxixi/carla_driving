# A3 Distillation

> 当前 B1 数据接入状态、D2 v1.1 与 D3 Wave1 的边界以及正式训练前必须满足的门禁，
> 统一见 [`docs/architecture/modules/B1_TO_A3_DATA_PIPELINE.md`](../../docs/architecture/modules/B1_TO_A3_DATA_PIPELINE.md)。
> D3 Wave1 的不可变 manifest 仍保留 `B1_RELEASE_CANDIDATE`，但 B1 已通过独立
> `B1_SIGNED_PASS.json` 对其精确字节签发。D2 单发布与 D2+D3 累积配置互不覆盖。
> A3 的运行等级、Loss、checkpoint 选择、恢复语义和 Hard-case 闭环统一见
> [`docs/architecture/modules/A3_TRAINING_AND_HARD_CASES.md`](../../docs/architecture/modules/A3_TRAINING_AND_HARD_CASES.md)。
> 独立 Validation、FP32 promotion 与 B2 Frozen Benchmark 的边界统一见
> [`docs/architecture/modules/B2_EVALUATION_AND_FP32_GATE.md`](../../docs/architecture/modules/B2_EVALUATION_AND_FP32_GATE.md)。

For the current signed B1 D2 v1.1 release, the active data-preparation and
integration-smoke procedure is in [D2_A3_PREP.md](D2_A3_PREP.md). Run
`python -m challenge.distillation.audit_d2_view` to produce the fixed
Train/Validation label-coverage report before comparing experiments. Run
`python -m challenge.distillation.validate_a1_inputs` to decode and pack every
Train/Validation RGB through A1's real four-modal input path. The targeted B1
follow-up is in [B1_D2_COVERAGE_REQUEST.md](B1_D2_COVERAGE_REQUEST.md). The
D2 mixed-cohort formal training entry now has its own signed-release policy
and configuration; its first baseline and shortcut diagnostics are recorded in
[D2_FP32_BASELINE_FINDINGS.md](D2_FP32_BASELINE_FINDINGS.md). It requires a
clean commit and does not authorize weight promotion. The promotion gate described below
supports this mixed-cohort candidate while requiring an independently frozen Teacher v4
evaluation package; no current artifact is promoted merely by satisfying the schema.

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
Test set. Formal B1 records must also match the frozen Teacher identity in
`challenge/teacher_baseline_manifest.json` exactly:

- model: `Qwen/Qwen3.5-2B`
- revision: `15852e8c16360a2fea060d615a32b45270f8a8fc`
- artifact fingerprint: `4bbf183b7b7f1ab9fb9eb325f189f4449d65e9fe664cbfe4bcc58a33888657fa`

Missing or mismatched per-record provenance fails preflight before a batch is
created.

The pinned B1 D1 collector uses the explicit metadata names
`teacher_baseline_git_sha` and `teacher_model_artifact_sha256`; A3 accepts
those as the authoritative equivalents of its historical field names. D1
records enter the Student view only when the Teacher label is structurally
valid and both command and plan terminal states are `SUCCEEDED`. Missing
closed-loop evidence is quarantined, not trained.

Run dataset preflight without training:

```bash
python -m challenge.distillation.preflight \
  --train data/train.jsonl \
  --val data/validation.jsonl \
  --dataset-version b1-v1 \
  --teacher-git-sha a05c8b76efcd4c176965223c661f40b153cb1836 \
  --teacher-model-id Qwen/Qwen3.5-2B \
  --teacher-model-revision 15852e8c16360a2fea060d615a32b45270f8a8fc \
  --teacher-artifact-fingerprint-sha256 4bbf183b7b7f1ab9fb9eb325f189f4449d65e9fe664cbfe4bcc58a33888657fa \
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
`Qwen/Qwen3.5-2B` Teacher model ID, resolves
packaged RGB by SHA256 instead of stale collector-host paths, checks B1's
recorded target pointers against A1's encoder, and audits quarantined records
without mixing them into ordinary supervision. Integration-smoke candidates
remain `MOCK_ONLY` and cannot pass the production FP32 gate. That historical
Smoke did not record an exact model revision or artifact fingerprint; its
dedicated config preserves `NOT_RECORDED_BY_B1_SMOKE` and cannot be used for a
formal run. It is deliberately not retroactively attributed to the pinned
Teacher.

A1 V0 r3 is already wired through `a1_student.py`; its frozen class order,
target-pointer convention, Head names and four-modal input shapes are imported
from `challenge.student` rather than duplicated. Every forward call is checked
for required Head names, exact shapes, floating
dtype, device alignment, and finite values before loss calculation. Non-finite
losses or gradients fail closed. See [HANDOFF.md](HANDOFF.md) for the exact
A1/B1/B2/B3 boundaries.

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

Before B2 evaluation, package one exact pending candidate with a config snapshot
from its training commit and hash-bound training evidence:

```bash
python -m challenge.distillation.candidate_handoff \
  --source artifacts/challenge/distillation/d2_v1_1_fp32_baseline_v4 \
  --output artifacts/challenge/distillation/a3_fp32_candidate_handoff_v1 \
  --repo-root .
```

The output is deliberately marked `PENDING_B2_INDEPENDENT_VALIDATION` and
`PENDING_A3_FP32_GATE`. It cannot overwrite an existing package and rejects
Smoke runs, dirty sources, mismatched weights/checkpoints, failed preflight,
or inconsistent hard-case counts. Current candidate identity and the external
server package record are in [A3_CANDIDATE_HANDOFF.md](A3_CANDIDATE_HANDOFF.md).

After transfer, the receiver verifies the complete signed payload, rejects
missing or unsigned extra files, recomputes every file hash and size, and
cross-checks the candidate identity and weight digest:

```bash
python -m challenge.distillation.candidate_handoff \
  --verify-package artifacts/challenge/distillation/a3_fp32_candidate_handoff_v1
```

Successful transfer verification keeps both pending statuses unchanged; it is
not an FP32 Gate decision and cannot create `A3_FP32_GATE_PASSED`.

B3's independently published real-weight replay/ONNX/INT8/soak evidence can be
accepted without weakening that boundary:

```bash
python challenge/distillation/audit_b3_v3_diagnostic.py \
  --output artifacts/challenge/distillation/a3_b3_v3_diagnostic_intake.json
```

The audit binds all evidence to the exact v3 identity and requires every replay
to remain fail-closed.  Its successful state is
`DIAGNOSTIC_EVIDENCE_ACCEPTED`, never `A3_FP32_GATE_PASSED`.  The formal
real-weight export requirements exposed by that exercise are recorded in
[A2_REAL_WEIGHT_EXPORT_HANDOFF.md](A2_REAL_WEIGHT_EXPORT_HANDOFF.md).

The signed D3 add-on is consumed only through the cumulative fail-closed path:

```bash
python -m challenge.dataset.validate_d3_release
python -m challenge.dataset.build_a3_cumulative_view
python -m challenge.distillation.audit_cumulative_view
python -m challenge.distillation.validate_a1_inputs \
  --release-dir challenge/dataset/releases/d2_v1_1 \
  --d3-release-dir challenge/dataset/releases/d3_wave1_addon_v1 \
  --view-dir artifacts/a3_d2_d3_cumulative_positive_view_v1 \
  --asset-root . \
  --output artifacts/a3_d2_d3_cumulative_a1_inputs.json
```

The cumulative formal config is
`d2_d3_cumulative_formal_config.yaml`; the bounded two-update check uses
`d2_d3_cumulative_smoke_config.yaml --integration-smoke`. Its strict-positive view contains 4079
Train and 797 development-Validation records. The 308 D3 hard negatives stay
in the audit-only exclusion index; they are not silently treated as ordinary
supervision. D3 adds development coverage and is not independent unseen Test
evidence.
The exact server-side preparation evidence and hashes are recorded in
[D2_D3_CUMULATIVE_PREP.md](D2_D3_CUMULATIVE_PREP.md).

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
For `signed_d2_release_formal` and `signed_cumulative_release_formal`
candidates, both evaluations must additionally
bind the candidate release/view hashes, the same B2 benchmark and policy
manifest hashes, case-set digest, evaluator Git SHA and positive sample count. Each side
must bind its predictions SHA, the Student must bind its weights hash, and both evaluations
must identify the exact frozen Teacher v4 baseline.
The cumulative policy also binds the D2 release, detached B1 D3 signature and
canonical multi-release source-evidence digest.
The smoke identity policy is never promotable.
