# A3 → A2: real-weight export interface handoff

## Frozen input identity

A2 must consume the unchanged A3 v3 candidate package and recompute the real
weight digest before export:

```text
model_id       = student-v0-r3-fp32
config_id      = student-v0-r3-structure-20260911
dataset_version= b1_d2_v1_1_plus_d3_wave1_a3_strict_positive_v1
weights_sha256 = 1afb8ebd11e401d4d7e6181d244ed39438421183c5303f1ce4a4391cee8cc68c
gate_status    = PENDING_A3_FP32_GATE
```

The package uses the canonical nested `candidate_identity` layout.  A2 must
not ask A3 to rewrite the immutable v3 manifest or publish a second flat
identity.  Its exporter should use
`challenge.hil.identity.identity_from_weight_manifest`, which already accepts
both flat and nested layouts and verifies the digest against the actual `.pt`
file.

## Required exporter behavior

The merged exporter must:

1. accept explicit `--weights` and `--weights-manifest` paths;
2. load the exact state dict rather than exporting seeded random weights;
3. accept nested `candidate_identity` without copying values into a temporary
   unsigned manifest;
4. reject model/config/dataset/digest mismatches before ONNX export;
5. preserve the pending Gate state in ONNX metadata;
6. emit the ONNX SHA256, source weight SHA256, manifest SHA256, fixed input and
   output shapes, opset and torch↔ONNX comparison report;
7. keep the formal ONNX artifact versioned and separate from B3's scratch
   diagnostic artifact.

## Evidence already available, but not formal delivery

B3 proved that a scratch export of these exact real weights can pass 10/10
torch↔ONNX comparisons with a maximum absolute difference of
`7.62939453125e-06`.  That is useful interface evidence, but the artifact was
produced through a temporary flat-manifest workaround outside the repository.
It must not be renamed as A2's formal ONNX delivery.

The same B3 diagnostic found the INT8 `target_speed_mps` cosine minimum changed
from `0.999835` on targeted-gap Validation to `0.989066` on D3 Wave2, with
8/56 D3 Wave2 samples below 0.99.  The formal calibration release should cover
multiple deployment distributions and report this head separately.  A3 QAT is
not authorized unless A2's formal PTQ Gate fails under the frozen policy.
