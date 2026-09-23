# A3 FP32 Candidate → B2 Handoff

## Current frozen candidate

The current A3-owned deliverable is a pending candidate, not an accuracy approval:

| Field | Value |
|---|---|
| package status | `PENDING_B2_INDEPENDENT_VALIDATION` |
| gate status | `PENDING_A3_FP32_GATE` |
| model ID | `student-v0-r3-fp32` |
| config ID | `student-v0-r3-structure-20260911` |
| training Git SHA | `151efbbfa0c8920bfc78e29262d984bcfae1877f` |
| weights SHA256 | `1afb8ebd11e401d4d7e6181d244ed39438421183c5303f1ce4a4391cee8cc68c` |
| source checkpoint SHA256 | `ff97125de1010d3c3949cac596571ab7479e2627d626aa44111d3f38784503a1` |
| dataset | `b1_d2_v1_1_plus_d3_wave1_a3_strict_positive_v1` |
| D2 release SHA256 | `cf153d2f536f9180241f02a9d644aca6da2a508beb785591399dbb75b847462f` |
| D3 release SHA256 | `dcd1bd1d0a34683e62e70a206760e691c0cd04b779f063d58a1fcf98837554bd` |
| D3 B1 signature SHA256 | `10d9892551dbfe4e61377f9f835bd89d8043209f32a459ab92028ee1d93c7228` |
| source evidence SHA256 | `6ec35d771df36b63864efd3c3e06f9a0ab2991bd53a60f44740cf19a0f7fe827` |
| A3 view manifest SHA256 | `e07112b52ae8ecf8dd944d562e30304478fc8c22ef9cb86f4585181281fc2ff9` |
| train/development Val | `4079 / 797` |
| development hard cases | `310`, all categorized as target-speed errors |

The Development Val plan accuracy is not independent generalization evidence. It must not be
quoted as the B2 score or used to rename this package as passed.

## Durable server package

The verified package is stored outside Git because the pure state dict is about 92 MB:

```text
/home/tiaozhansai/carla-driving-challenge/
  artifacts/challenge/distillation/a3_d2_d3_fp32_candidate_handoff_v3/
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

The earlier D2-only package `a3_fp32_candidate_handoff_v1` and cumulative v2 package
`a3_d2_d3_fp32_candidate_handoff_v2` remain historical and are not deleted. V2 had lower aggregate
speed MAE but regressed safety-critical speed on the common D2 Validation split; v3 is the current
risk-balanced candidate. None of these packages is promoted before B2 evidence.

## What B2 must return

B2 evaluates these exact weights against Teacher v4 on one frozen independent Validation case
manifest and policy. The paired evaluation JSON files must satisfy the promotion contract in
`artifacts.py`, including benchmark/policy/case-set/evaluator/sample identities, per-side
predictions SHA and Student model/config/weights identity. A3 consumes only the approved evidence;
it does not receive Frozen Test labels or use B2 cases for training.

