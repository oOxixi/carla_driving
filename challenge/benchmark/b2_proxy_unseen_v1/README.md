# B2 proxy prospective benchmark v1

This directory freezes the policy and acquisition design for a new 240-case
prospective holdout. It does **not** claim that the benchmark cases or a Gate
decision already exist.

The exact V3 FP32 weights, ONNX and Adapter V3.1 identity are bound before any
new Student result is read. The acquisition has 80 `seen`, 80 `variant` and 80
`unseen` slots. Seeds and event ordinals are deterministic, and every final
case must be disjoint from governed Train, Development, Calibration v1 and the
prior 240-case Independent Validation set.

The team owner explicitly authorized A2 to act as a B2 proxy on 2026-10-08.
That authorizes execution but does not create third-party role separation. The
result must therefore state `A2_ACTING_AS_B2_PROXY` and
`PROSPECTIVE_TEMPORAL_HOLDOUT`; it must not claim an external B2 signature.

Run the pre-inference freeze materializer with:

```powershell
python tools/prepare_b2_proxy_unseen_v1.py `
  --output artifacts/b2_proxy_unseen_v1_freeze
```

The materializer performs no model inference. It verifies the candidate,
rebuilds and hashes the policy manifest, audits exposure identities, creates
and validates all 240 scenario contracts, writes the frozen acquisition slots,
and closes the directory with `SHA256SUMS` plus `FREEZE_LOCK.json`.

Actual case collection remains fail-closed until a reachable CARLA host and
the exact pinned Teacher v4 service are available. No stored Teacher plan or
different local Qwen model may be substituted.
