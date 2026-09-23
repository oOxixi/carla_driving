# A3 FP32 Candidate → B2 Handoff

## Current frozen candidate

The current A3-owned deliverable is a pending candidate, not an accuracy approval:

| Field | Value |
|---|---|
| package status | `PENDING_B2_INDEPENDENT_VALIDATION` |
| gate status | `PENDING_A3_FP32_GATE` |
| model ID | `student-v0-r3-fp32` |
| config ID | `student-v0-r3-structure-20260911` |
| training Git SHA | `a299169c8bf5c2a2cdd4adf800c655bd14cd5db8` |
| weights SHA256 | `896562058948175ac21fd8d26b45a244aeb40f37ec0a7a88b1f03fe4ff9f65ca` |
| dataset | `b1_d2_v1_1_a3_strict_positive_v1` |
| release manifest SHA256 | `cf153d2f536f9180241f02a9d644aca6da2a508beb785591399dbb75b847462f` |
| A3 view manifest SHA256 | `f797725014f297bf1ca43444b95a9aa43bf566abb4fcaebfc1841b4851cd8fcf` |
| train/development Val | `2332 / 489` |
| development hard cases | `217`, all categorized as target-speed errors |

The Development Val plan accuracy is not independent generalization evidence. It must not be
quoted as the B2 score or used to rename this package as passed.

## Durable server package

The verified package is stored outside Git because the pure state dict is about 92 MB:

```text
/home/tiaozhansai/carla-driving-challenge/
  artifacts/challenge/distillation/a3_fp32_candidate_handoff_v1/
```

It contains the exact pure state dict, original candidate manifest, training summary/report/log,
dataset preflight, hard-case summary, training config extracted from the training commit, a
human-readable README and `handoff_manifest.json` with per-file SHA256 and sizes. The source
checkpoint itself is verified against `source_checkpoint_sha256` but is not duplicated into the
B2 package.

Rebuild only into a new versioned output directory:

```bash
python -m challenge.distillation.candidate_handoff \
  --source <formal-training-run-directory> \
  --output <new-versioned-handoff-directory> \
  --repo-root <repository-containing-the-training-commit>
```

The command refuses to overwrite an existing directory. Do not delete or mutate the current
package in place; a replacement candidate requires a new package version and new weights SHA.

## What B2 must return

B2 evaluates these exact weights against Teacher v4 on one frozen independent Validation case
manifest and policy. The paired evaluation JSON files must satisfy the promotion contract in
`artifacts.py`, including benchmark/policy/case-set/evaluator/sample identities, per-side
predictions SHA and Student model/config/weights identity. A3 consumes only the approved evidence;
it does not receive Frozen Test labels or use B2 cases for training.

