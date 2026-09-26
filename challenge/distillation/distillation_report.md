# A3 Distillation Report

## A1 V0 r3 integration

- Branch baseline: `challenge@047c659744a526a73ba1e9326ee7d78d65a15205`
- Teacher baseline SHA: `a05c8b76efcd4c176965223c661f40b153cb1836`
- Teacher model: `Qwen/Qwen3.5-2B`
- Formal Teacher revision: `15852e8c16360a2fea060d615a32b45270f8a8fc`
- Formal Teacher artifact fingerprint:
  `4bbf183b7b7f1ab9fb9eb325f189f4449d65e9fe664cbfe4bcc58a33888657fa`
- Historical B1 Smoke provenance: exact revision/fingerprint not recorded and
  not retroactively attributed
- Student: `student-v0-r3-fp32`
- Student config: `student-v0-r3-structure-20260911`
- Local environment: Python 3.12, PyTorch 2.6.0 CPU
- A1+A3 joint tests: 45 passed
- Frozen Test access: forbidden in the A3 trainer and promotion gate

The default smoke used A1's real 23,006,581-parameter Student, its four-modal
preprocessor, six Train mock records and two Validation mock records. One
optimizer update, validation, backward, checkpoint and pure-state-dict export
completed successfully.

- The run-specific checkpoint SHA-256 and source Git SHA are recorded together
  in the ignored artifact's `training_summary.json`; they are intentionally
  not hard-coded into this versioned report.
- Candidate weights SHA-256:
  `77fe0b31a8a8dcbc2e29c975b3f9a76bf8ca8bc28d6f847359f1086eb3a4bab4`
- Candidate status: `MOCK_ONLY`

These values prove pipeline health only. Random initialization plus synthetic
records are not Student accuracy and cannot pass the A3 FP32 Gate.

## Completed A3 boundary

- A1 authoritative vocabularies, zero-based target pointers and output names
- ModelRequest V1 / ManeuverPlan V2 validation and four-step masks
- A1 RGB/text/targets/state batch packing
- risk-weighted multi-head hard-label loss and optional soft probability loss
- finite output/loss/gradient gates and exact Student Head checks
- Train-only optional class balancing
- per-head Validation metrics and categorized hard-case export
- atomic checkpoint, exact epoch-boundary resume and SHA-256 provenance
- A1-loadable pure state_dict candidate export
- evidence-driven FP32 promotion gate with <=1.5% core drop, no safety drop,
  100% schema validity and frozen-Test rejection
- fail-closed formal Teacher identity checks at config, per-record preflight,
  candidate export and FP32 promotion

## Current frozen v3 candidate

The current B2 handoff remains the risk-balanced v3 candidate.  Preparing a
new development view does not mutate or silently replace this identity.

| Field | Frozen value |
|---|---|
| model ID | `student-v0-r3-fp32` |
| config ID | `student-v0-r3-structure-20260911` |
| training Git SHA | `151efbbfa0c8920bfc78e29262d984bcfae1877f` |
| dataset version | `b1_d2_v1_1_plus_d3_wave1_a3_strict_positive_v1` |
| weights SHA256 | `1afb8ebd11e401d4d7e6181d244ed39438421183c5303f1ce4a4391cee8cc68c` |
| handoff manifest SHA256 | `966e16c78457e4022fb1a3eaab11eb6da9ee23d8231e50631437808f03bf7e92` |
| status | `PENDING_B2_INDEPENDENT_VALIDATION` |
| Gate | `PENDING_A3_FP32_GATE` |

The package verifier checks nine signed payload files.  The package and pure
state dict are server artifacts rather than Git blobs; the immutable archive
identity is documented in `A3_CANDIDATE_HANDOFF.md`.

## D3 Wave2 derived-view preparation

B1's detached-signed `b1_d3_wave2_safe_short_v1` release is now available.
Its complete local release validation passed for 374/374 RGB files and pinned
Teacher-v4-wave2-sync provenance:

- Teacher model: `Qwen/Qwen3.5-2B`
- Teacher revision: `15852e8c16360a2fea060d615a32b45270f8a8fc`
- Teacher artifact fingerprint:
  `4bbf183b7b7f1ab9fb9eb325f189f4449d65e9fe664cbfe4bcc58a33888657fa`
- Teacher collection Git SHA: `252984d37e49ddc11eaddcde2bfb26d0d6f2086b`
- B1 release manifest SHA256:
  `b8056484a3c5b7345d59536edbae5516a602d29811151fb3736ce25aff4fa57b`
- Additive samples: 318 Train + 56 development Validation; zero hard negatives

The new builder creates the separately versioned development identity
`b1_d2_v1_1_plus_d3_wave1_plus_d3_wave2_safe_short_a3_strict_positive_v1`.
It adds Wave2 without changing the v3 files or dataset version.  The prepared
partition contains 4,397 Train, 853 development Validation and 539 audit-only
excluded samples.  Sample IDs and group keys are disjoint across Train and
Validation; Reserved/Frozen Test use is explicitly false.

The initial local partial clone lacked some historical D3 Wave1 RGB blobs, so
its first preparation run was metadata-only.  The same committed builder was
then run on the complete `tiaozhansai` checkout at `challenge@5604b48a`
without `--skip-images`.  All source release/image gates, view reconstruction
and the read-only audit passed.  The server reproduced the expected identity:

- view manifest canonical SHA256:
  `20d15be92c7f4bf2681d6e1a20be9da45acd99569ce78c5f3cf7290ed579c296`
- source evidence SHA256:
  `c8f179c67369d598b156ae1dbea68fb912613808958c29b466a6944f47774995`
- Train JSONL SHA256:
  `7c8abb984047779c208e1154009e869085cda2ac56ef952f45ec6392959dc5b6`
- development Validation JSONL SHA256:
  `24d45ea6dab5e325d075e017a806969c052083cd23cbabbff3349b02a2289167`
- full server audit: `PASS`; D3 Wave2 images checked: 374/374

This proves the prepared view's input integrity, not Student accuracy.  If the
team chooses to train on this view, the output must be a new candidate version
with a new config ID, dataset identity and weights SHA; it must not overwrite
or rename v3.

## Current external handoffs and blockers

- B1 data required for the prepared Wave2 view has arrived and its detached
  signature, release hashes, Teacher provenance and 374-image set validate.
- B2's evaluator, comparison, decision and evidence-publication tooling is in
  Git, but the independent Validation case manifest and formal policy are not
  frozen.  Actual Teacher/Student paired evaluation JSON and Gate PASS/FAIL
  evidence for the exact v3 weights are still absent.
- A1/A4 may consume the verified v3 package for true FP32 ONNX export work,
  but an ONNX artifact is not an A3 accuracy approval.
- A2 PTQ and any A3 QAT decision remain downstream of a valid B2 FP32 Gate,
  true ONNX export and the B1/B2 calibration release.

Until B2 returns independent, identity-matched evidence, no production weight
can truthfully receive `A3_FP32_GATE_PASSED`.
