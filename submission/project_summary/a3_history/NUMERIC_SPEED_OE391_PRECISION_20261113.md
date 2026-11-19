# OpenExplorer speed quantization: attribution and local precision trials

Only the existing 128 controlled CARLA development probes and 80 bound
development validation cases were used to choose precision. The 850-case
historical replay and independent evaluation data were not loaded. All
variants keep the exact source FP32 ONNX, 300-sample Calibration v1 and
OpenExplorer 3.9.1/nash-p O2. The reference is the same FP32 candidate.

The figures are decoded full-plan hits under the existing probe contract
(action sequence, applicable target ID and ±2 km/h or the FOLLOW cap),
and raw speed MAE versus FP32 at the expected speed step.

| Stage / variant | Hits / 208 | Raw speed MAE vs FP32 (km/h) |
| --- | ---: | ---: |
| FP32 | 168 | 0 |
| Calibrated ONNX | 87 | 2.236 |
| PTQ ONNX | 87 | 2.236 |
| Original compiled BC | 87 | 2.240 |
| Local INT16 speed Gemm + residual MatMul + Add | 126 | 0.991 |
| Local INT16 Sigmoid and final scaling | 91 | 2.181 |
| Combined INT16 head and output | 124 | 0.842 |

The original error is already present in the calibrated graph. The 208
calibrated speed outputs lie within 0.002 km/h of a 1.412 km/h grid
(consistent with the reported Sigmoid threshold and INT8 resolution).
That final grid alone does not explain the directional bias: mean signed
SET_SPEED and SLOW_DOWN errors are +2.82 and +3.32 km/h. In the 24 km/h
SET_SPEED trace, the residual before Add changes from 0.0568 to 0.2078
and the combined logit from -1.862 to -1.671 before final Sigmoid
quantization. This points to quantization at both the numeric residual
and output, not primarily backend compilation. The trace does not
isolate the error to a single weight or activation.

Both local INT16 builds retain 92 BPU mapping rows and no CPU rows. The
head-local build recovers 39 hits, compared to 4 for the output-only
build. This supports prioritizing the upstream speed path; it does not
establish on-board utilization or latency.

The combined variant also compiles with 92 BPU rows and no CPU rows.
Its average raw drift is lower than head-only, but on the bound
development subset SET_SPEED hits drop from 13/20 to 9/20 (the other
SET_SPEED subset gains two hits). Keep head-only as the current
development candidate for the full-plan hit objective. It has not
recovered FP32's 168 hits. Candidate BC SHA256:
`c895ea7a5c9c4d93648cc2d41c9803fa435d7d079e08e07fc5fb6b28d6a8c6ab`;
HBM SHA256: `4cd156727ecd3d8ea771df66a50e195c8c869660f9346dceee28e58fa09bcebc`.
The next attribution target is the speed residual's activation/weight
quantization before Add; don't expand mixed precision across unrelated heads.

Reproduction: `python -m challenge.distillation.oe_speed_stage_probe`
inside the official image. The probe verifies case manifests and RGB
hashes; reports record model SHA256. Artifacts and YAML are under
`artifacts/numeric_speed_conditioned_20261112/oe_391_calibration_v1/`.
No release replacement, retraining, formal Gate or board test.

## Follow-up: split activation and weight error

The selected head-local calibrated ONNX uses INT16 for the residual Conv
activation in/out, but its 9 weights are still INT8 (scale 0.0237361).
On the same 208 development probes, bypassing individual fake-quant
nodes in copies of that calibrated ONNX gave:

| Calibrated ONNX ablation | Hits / 208 | Raw speed MAE vs FP32 (km/h) |
| --- | ---: | ---: |
| Unchanged | 125 | 0.966 |
| Bypass residual input, output, or both activation boundaries | 125 | 0.966 |
| Bypass residual weight only | 134 | 0.912 |
| Bypass weight and both activation boundaries | 134 | 0.912 |

These are counterfactual ONNX runs, not deployment artifacts. Weight
rounding is a demonstrated contributor to the remaining error, not its
only source (134 vs 168 FP32 hits). The 125-hit calibrated ONNX baseline
is distinct from the 126-hit compiled BC. Results are in
`dev_speed_residual_ablation.json` (SHA256
`d515fc12051742651b76f417c4cd29ac9d2d3e49e507dbbb8774c83c7b9acd96`).

## Compiled follow-up: residual weights in INT16

`speed_weight16_probe.yaml` adds only `InputType1: int16` for
`/model/numeric_speed_head/MatMul` to the head-local settings (and uses
a separate output directory). The calibrated graph confirms the weight
qtype changed from INT8 (scale 0.0237361) to INT16 (scale 0.0000920).
The same 300-sample Calibration v1 and frozen FP32 weights were used.
The compiler completed, with 92 BPU rows and no CPU rows.

| Compiled variant | Full-plan hits | SET_SPEED | SLOW_DOWN | FOLLOW | Compound | Raw speed MAE vs FP32 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Previous head-local | 126/208 | 36/52 | 26/52 | 52/52 | 12/52 | 0.991 km/h |
| Residual weight INT16 | 133/208 | 36/52 | 33/52 | 52/52 | 12/52 | 0.963 km/h |

The seven additional matches are all SLOW_DOWN. Aggregate SET_SPEED is
unchanged, and raw FOLLOW MAE versus FP32 worsened in both subsets even
though all decoded plans still met the FOLLOW cap. Keep this build as
the development candidate for the complete-plan objective, not as a
production replacement. The next question is where the remaining
SET_SPEED error arises upstream of the residual; further increasing
its precision alone did not recover the FP32 result.

- BC SHA256: `3ed46380d45addd6b29b89bdb5ca362eb934d394c6f6d2928b3cf9cb81904c72`.
- HBM SHA256: `d7727381c3656cbcd3bdb4377d0256f220e938a789dbe39db2882368693aae6a`.
- `dev_speed_weight16.json` SHA256: `50de9372bc25aa43f731d7e62a0745f9ae9f05fb6c3b2aeF2ea9d28f3d7b69f3`.

No tuning on the 850-case replay or independent evaluation data, no
retraining, no board measurement and no formal Gate.

## Follow-up: test the base-speed hypothesis

On the 208 development probes, bypassing base-speed Gemm weight quantization
did not improve SET_SPEED (36/52). Bypassing its output activation had no
effect. Bypassing the later Sigmoid quantizer reduced raw drift from 0.912
to 0.766 km/h but still left SET_SPEED at 36/52. See
`dev_speed_base_head_ablation.json`.

The compiled `speed_base_weight16_probe.yaml` changes only the base-speed
Gemm's weight type from the residual-weight16 configuration. It again maps
92 rows to BPU and none to CPU. It gives 133/208 hits, 36/52 SET_SPEED,
33/52 SLOW_DOWN and 0.958 km/h raw drift. The prior 133-hit candidate
(0.963 km/h) remains selected; the extra precision is not justified by
this difference. See `dev_speed_base_weight16.json`.

## Follow-up: residual feature construction before MatMul

On the same development probes, bypassing fake quantization of the raw
numeric hint and its scaling had no effect (134/208 hits). Bypassing the
calibrators after `Mul_4`, `Mul_5`, and `Concat_1` (the gated features
before the residual MatMul) gave 168/208, with both SET_SPEED and
SLOW_DOWN increasing to 52/52. Raw speed drift fell from 0.912 to
0.419 km/h. Bypassing both groups gave the same result as the feature
group alone. This is evidence for a joint effect, not attribution to
one node. The concatenation mixes a binary gate, normalized speed and
an unbounded base logit; a common INT8 scale can coarsen the small
numeric feature. See `dev_speed_hint_path_ablation.json` (SHA256
`c8694671b25f07e124edc35be9c21461f82a80038c836182967d8982c7b33ca1`).

The actual `speed_features16_probe.yaml` build uses the same FP32 and
300 Calibration v1 cases as residual-weight16. Only the three feature
operators are additionally configured for INT16. OpenExplorer compiled
the HBM and BC, maps all three as BPU si16, and reports 92 BPU / 0 CPU
mapping rows overall. The BC reproduced the development gains:

| Compiled variant | Hits / 208 | SET_SPEED | SLOW_DOWN | FOLLOW | Compound | Raw speed MAE vs FP32 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Residual weight INT16 | 133 | 36/52 | 33/52 | 52/52 | 12/52 | 0.963 km/h |
| Residual features INT16 (selected) | 168 | 52/52 | 52/52 | 52/52 | 12/52 | 0.452 km/h |

This matches the FP32 hit count by family, not exact FP32 speed outputs.
Compound performance is unchanged and still incomplete. Keep this as a
frozen development build pending evaluation, not a deployed replacement.

- YAML SHA256: `2dfe61fb640f1a355b275c3fba974e0571e7e0e9239a59fb06cd7a4f2f7c5516`.
- HBM SHA256: `93808ea50c7832d0580a2186deb2048d4ef9990ca454fa8d9282f2af91816409`.
- BC SHA256: `8dd24c3a291d8f6c05737a8f00df9aabe9c98ec959f91205ed7028284b7322d9`.
- `dev_speed_features16.json` SHA256: `f76e4b9c98e75154b9959bbe209195913cbdb6ccf5f66fb1c8919ee4a7e3dbfb`.

## Frozen candidate: exposed 850-case regression

The selected BC ran in the official 3.9.1 image with HBRuntime; the same
FP32 source was replayed in ONNX Runtime. Case file and adapter hashes
matched the earlier quantitative replay. Every RGB was hash-verified.
Both runs decoded 850/850 valid plans; the full categorical signatures
(behavior, completion, lane and target ID) matched FP32 on all 850.
Agreement with stored Teacher signatures remained 843/850.

| Build | Target-speed MAE against stored Teacher (472 paired steps) |
| --- | ---: |
| Old FP32 re-export | 0.4930 m/s |
| Numeric FP32 | 0.2455 m/s |
| Original calibrated BC | 0.5003 m/s |
| Features16 calibrated BC | 0.2842 m/s |

Features16 reduces this error by 43.2% versus the original calibrated BC.
It improves or ties all six cohort averages; it does not exactly match FP32.
The result is `exposed_850_features16_regression.json` (SHA256
`0bdb504ffad65650e03fd3c570b0dfcddb5c06284c51cb0e60695f78b3a6e4a6`).
No candidate tuning used this replay. The prospective readiness check
still finds no frozen new case manifest and no verified candidate package
for the formal Gate. No fresh Teacher, closed-loop or board evaluation
was performed.
