# A3 B1 Closeout Final FP32 Candidate v2

## Scope

This is the A3 production-training path after the B1 data closeout. It replaces
neither the immutable v1 candidate nor B2's independent evaluation. The new
candidate remains `PENDING_A3_FP32_GATE` until B2 evaluates the exact exported
weight file.

## Frozen input boundary

- B1 governed raw inventory: Train `6037`, Development `1158`.
- Optimizer view: Train `5856`, Validation `1108`.
- Audit-only exclusions: `540`.
- MS34 positive additions: Train `30`, Validation `4`.
- MS34 route-deviation failure: `1`, audit-only and never relabelled.
- Plan lengths in the optimizer view: one-step `6439`, two-step `491`,
  three-step `17`, four-step `17`.
- Calibration, B2 Independent Validation, Reserved Test, and Frozen Test are not
  read by the builder or trainer.

The difference between the governed raw counts and optimizer counts is
intentional. Raw counts describe B1's release inventory; optimizer counts apply
A3's strict-positive supervision policy. Both count sets must appear in the
candidate handoff so downstream reviewers cannot confuse them.

## Teacher provenance

The closeout binds the governed release manifest and Teacher provenance
registry. The historical MS34 samples retain B1's
`PASS_WITH_RUNTIME_IDENTITY_LIMITATION` addendum. A3 does not rewrite those rows
or retroactively claim an exact Hugging Face revision for them.

## Reproduction

```bash
python -m challenge.dataset.build_a3_closeout_cumulative_view
python -m challenge.distillation.audit_closeout_cumulative_view
python -m pytest -q \
  challenge/distillation/tests/test_closeout_cumulative_gate.py \
  challenge/distillation/tests/test_artifacts.py \
  challenge/distillation/tests/test_candidate_handoff.py \
  challenge/distillation/tests/test_final_slice_eval.py
```

The smoke path is deliberately separate and cannot produce a formal handoff:

```bash
python -m challenge.distillation.train \
  --config challenge/distillation/b1_closeout_final_smoke_config.yaml \
  --integration-smoke
```

After committing the exact code/config on a clean worktree, run production
training without `--integration-smoke`:

```bash
python -m challenge.distillation.train \
  --config challenge/distillation/b1_closeout_final_formal_config.yaml
```

## Acceptance boundary

A3 may publish the candidate weight, its SHA256, config snapshot, dataset/view
hashes, governed raw counts, optimizer counts, provenance hashes, and training
evidence. A3 must not set `A3_FP32_GATE_PASSED`. That decision belongs to B2's
independent evaluation of the exact handed-off weights.
