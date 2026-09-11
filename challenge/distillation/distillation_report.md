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

## Remaining external handoffs

- B1: newly recollected, pinned-Teacher, versioned and disjoint Train and
  Validation JSONL manifests
- B2: independent, version-matched Teacher and Student Validation metrics

Until both arrive, no production weight can truthfully receive
`A3_FP32_GATE_PASSED`.
