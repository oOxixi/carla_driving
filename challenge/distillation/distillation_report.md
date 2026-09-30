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

### B3 real-weight diagnostic evidence

B3 has now independently verified that same v3 package and run its real
weights through replay, scratch ONNX/INT8 and a 30-minute x86 soak.  A3's
`audit_b3_v3_diagnostic.py` binds the publication to the frozen candidate
identity and accepts it only as `DIAGNOSTIC_EVIDENCE_ACCEPTED`, always with
`eligible_for_promotion=false`.

The useful signals are:

- D2 v1.1 behavior/target match: `0.951763 / 0.971243`;
- targeted-gap behavior/target match: `0.919192 / 0.919192`;
- targeted-gap output coverage: 6 Student combinations versus 9 Teacher;
- torch↔scratch-ONNX maximum absolute error: `7.62939453125e-06`;
- real-weight x86 soak: 77,653 iterations, zero failures;
- INT8 `target_speed_mps` minimum cosine changes from `0.999835` on
  targeted-gap to `0.989066` on D3 Wave2, with 8/56 below 0.99.

These development sets have known lookup shortcuts and every B3 replay remains
`DIAGNOSTIC_ONLY`.  The candidate therefore remains unchanged and pending.
The speed head and 6-versus-9 output coverage are improvement/calibration
signals for a future versioned candidate, not permission to tune on B2 data.

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

## D3 targeted-gap intake

B1 subsequently published `b1_d3_targeted_gap_strict_v1`.  A3's fail-closed
intake independently verified the transport/data layer:

- 672 locked files and 660/660 RGB assets pass;
- 561 Train + 99 development Validation rows are strict-positive;
- Train/Validation group overlap is zero;
- sample overlap with the existing D2 + D3 Wave1 + D3 Wave2 partition is zero.

The original release lacked exact Teacher revision and artifact fingerprint,
so A3 initially blocked it.  B1 has now published a cohort-specific immutable
provenance addendum covering all 660 samples.  A3 verified:

- exact Teacher revision `15852e8c16360a2fea060d615a32b45270f8a8fc`;
- artifact fingerprint
  `4bbf183b7b7f1ab9fb9eb325f189f4449d65e9fe664cbfe4bcc58a33888657fa`;
- acquisition Git SHA `a6743feb52015031f70e2c21a94aef0abae0a65a`;
- attestation SHA256
  `24c2690d8590fe2e1ecff48f75d391b03941e3405f08cd306aba6e99e6f878c5`;
- content-binding SHA256
  `505051b1c764a1f464dc31a6e44ea705d21693d4eb935cd99ffd289ff7b428b2`.

The declared provenance class is `CONTENT_BOUND_UNSIGNED`: all byte and
identity bindings pass, but no cryptographic signer identity is claimed.  A3's
explicit development-input policy accepts this class without misreporting it
as detached/GPG signed.  `audit_targeted_gap_intake.py` now returns `READY`.

## D3 recovery cumulative preparation

B1's additional `d3_turn_gap_60_strict_v1` release also passed full validation:
200/200 RGB assets, 171 Train rows, 29 development Validation rows, exact
pinned Teacher identity, strict-positive terminal success and zero split/group
overlap.  Its provenance is likewise explicitly `CONTENT_BOUND_UNSIGNED`.

A3 combines the previously verified Wave2 base, targeted-gap and turn-gap only
through the new immutable view identity:

```text
b1_d2_v1_1_plus_d3_wave1_plus_d3_wave2_plus_targeted_gap_plus_turn_gap_a3_strict_positive_v1
```

The complete `tiaozhansai` checkout at `challenge@fdf53348` built and then
read-only reconstructed this view with image checks enabled.  Results:

- Train: 5,129 (targeted-gap +561, turn-gap +171);
- development Validation: 981 (targeted-gap +99, turn-gap +29);
- audit-only excluded: 539;
- view manifest SHA256:
  `63f26554a52e270447e7cca977e2df9b31e05753fee96859e8d0a701874f166b`;
- source evidence SHA256:
  `0867e9acfba5271b4af566a7ee9db34fa52248d052ebb093c5a38b5bfee5221d`;
- Train JSONL SHA256:
  `039a78c96ed13f6fa0af754e67a66c74dfff65631ad58556e707eeeeae82bcf7`;
- development Validation JSONL SHA256:
  `2c943825b2a10f65f9e30d88a5aab1a994c266fcab16e6c08ec6797778877868`;
- full audit: `PASS`; relevant regression suite: 7 passed.

After adding the dedicated fail-closed integration policy, the combined suite
passed 8/8 and the clean server checkout completed a CUDA integration smoke
using 50 Train + 50 Validation records and exactly two optimizer updates.  It
exercised preflight, four-modal input, loss/backward, evaluation, checkpoint and
candidate export.  The exported status is correctly `MOCK_ONLY`; its bounded
metrics are not Student accuracy evidence.

This proves input integrity and reproducibility, not Student accuracy.  It does
not alter or promote v3.  Any training decision must create a new config,
checkpoint, candidate identity and B2 comparison.  Exact commands and evidence
are in `D3_RECOVERY_CUMULATIVE_PREP.md`.

## B3 TURN finding and Gap300 intake

B3's diagnostic replay confirms why a new candidate is necessary: over 87
turn-gap replay instances the old v3 candidate never emitted `TURN_LEFT` or
`YIELD`; all 27 `TURN_LEFT` and 6 `YIELD` targets were predicted as
`SET_SPEED`.  This is a training-distribution vocabulary gap, not evidence that
the newly collected labels failed.

B1's new `d3_gap300_strict_v1` release adds 697 Train and 123 development
Validation rows.  Across both partitions it contributes 230 `TURN_LEFT`, 75
`YIELD` and 50 `PULL_OVER` steps.  Full byte/RGB/split validation passes and
the release has zero overlap with prior A3 partitions.  B1 subsequently
published an immutable exact-Teacher attestation proving that both acquisition
paths used the same pinned Qwen3.5-2B revision and artifact fingerprint.  The
two retained acquisition SHAs are:
770 rows use `95668ba3a466ae0dfcd73982f5a4a0d210b524c1`, while the 50 D01/PULL_OVER
rows use `e150ae598d95cb024faebc1699b872d0de899e91`; the release-level provenance
attestation binds both distributions without rewriting the historical rows.
The full-server Gap300 intake now returns `READY` with all 820 RGB assets
checked and no cross-partition overlap.

The final A3 development view contains 5,826 strict-positive Train and 1,104
development-Validation rows.  B1's 6,007 raw Train count includes 181 D2 hard
negatives, which remain audit-only rather than being mislabeled as successful
Teacher supervision; the raw 1,154 Dev count likewise includes 50 audit-only
rows.  The reproducible view audit passes with 539 total exclusions, and the
two-update CUDA integration smoke completes the full train/export chain.  A
new formal FP32 run may now start from the dedicated final config, while B2
remains the sole owner of independent Gate approval.

## Current external handoffs and blockers

- B1 data required for the prepared Wave2 view has arrived and its detached
  signature, release hashes, Teacher provenance and 374-image set validate.
  The targeted-gap provenance addendum and the turn-gap release have also
  arrived; both content-bound development cohorts now pass A3 intake and are
  available through a separately versioned cumulative view.
- Gap300 exact Teacher provenance has arrived and the final 5,826/1,104 A3
  view is reproducible with full RGB verification.  A3 data/provenance intake
  is no longer blocked.
- B2's evaluator, comparison, decision and evidence-publication tooling is in
  Git.  A fresh server readiness run still reports six blockers: benchmark and
  case manifest are not frozen; formal policy and policy version are not
  frozen; slice minimum denominators and multi-run merge rule are missing.
  Actual paired evaluation JSON and Gate PASS/FAIL evidence for the exact v3
  weights are still absent, while `student_candidate.ready=true`.
- B3 has independently verified and exercised the exact v3 weights.  This
  removes transfer-integrity uncertainty but none of B2's six formal blockers.
- A1/A4 may consume the verified v3 package for true FP32 ONNX export work,
  but an ONNX artifact is not an A3 accuracy approval.
- A2's required real-weight export interface and nested-manifest compatibility
  are specified in `A2_REAL_WEIGHT_EXPORT_HANDOFF.md`.  B3's scratch ONNX is
  diagnostic, not the formal A2 artifact.
- A2 PTQ and any A3 QAT decision remain downstream of a valid B2 FP32 Gate,
  true ONNX export and the B1/B2 calibration release.

Until B2 returns independent, identity-matched evidence, no production weight
can truthfully receive `A3_FP32_GATE_PASSED`.
