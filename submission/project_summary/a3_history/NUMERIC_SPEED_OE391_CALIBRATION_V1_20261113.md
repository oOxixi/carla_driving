# Numeric speed Head: OpenExplorer 3.9.1 real-data PTQ

The frozen numeric-primary FP32 candidate compiled successfully for J6P
(`nash-p`) with `hb_compile -c student_j6p_oe391.yaml`. Unlike the model-only
inspection, this run used all 300 samples of the verified `b1_calibration_v1`
release. The compiler logged 300 distinct inputs per tensor stream (1,200 total)
and selected max-percentile (0.99995). All tensor hashes were verified after
transfer. No sample-ID or RGB-hash matches were found with the candidate
Train/Dev views, the numerical supplements or the exposed 850-case replay.

- Source ONNX SHA256: `79327f40e65a58dd484f7c614aa5c964df360455475c919528173388021f5f31`.
- Calibration JSONL SHA256: `e7520afc683b4545ca0981c549d0aebef50a90962a0d95378d89c1ca4bfbe8cc`.
- Docker image ID: `sha256:cf06f721448e30f8f569cfeb6fc3356c1ad6e77ba180042d0c3babe891b6b5c4`.
- Compiler: hb_compile 3.5.16, HMCT 2.8.4, HBDK 4.11.11.
- HBM: 23,623,592 bytes, SHA256 `30618babadc9aeed18bfd72807ba9891f94b348fcc5472469f351a2a2daecf46`.
- Quantized BC: 23,193,563 bytes, SHA256 `23ba164958e312cf9966a1303f51889bc14612804c942c94c7af59c85f4fb7fb`.
- Node report: 92 BPU mapping rows, 0 CPU rows. Compiler minimum
  memory requirement: 24,262,312 bytes (estimate, not measured on a board).
- Local evidence: `artifacts/numeric_speed_conditioned_20261112/oe_391_calibration_v1/`.

## X86 replay: the speed gain did not survive this PTQ build

The official image ran HBRuntime on the exact compiled BC, and ONNX Runtime
on the frozen FP32 source. Both used the same preprocessor, adapter and 850
exposed requests with verified RGB. Comparison is against stored Teacher
plans; no Teacher inference was performed.

| Metric | Numeric FP32 | Calibrated BC |
| --- | ---: | ---: |
| Schema-valid plans | 850/850 | 850/850 |
| Complete categorical plan match to stored Teacher | 843/850 | 843/850 |
| Behavior / target ID matches | 927/931 / 931/931 | 927/931 / 931/931 |
| Paired target speed MAE (472 steps) | 0.2455 m/s | 0.5003 m/s |

Categorical plans matched between builds for all 850 cases. For the same
paired speed subset, the prior old FP32 replay was 0.4930 m/s. Thus the new BC
does not retain the numeric FP32 improvement in this regression. This does
not isolate calibration/quantization from backend lowering or simulation;
compare the saved calibrated/quantized ONNX with BC on development probes
before selecting any precision changes. Keep the 850-case result as regression
evidence, not as a tuning target or blind Gate.

The report is `exposed_850_bc_regression.json` (SHA256
`e2ace663d47a13f86e1f2effcdb3e9e46f61d28dc04a16a6f85318b9ce4860f2`).

This is a real-data PTQ development build, not a formal INT8 release. The
FP32 source still has `DEVELOPMENT_NOT_GATE` status. No board utilization,
latency, closed-loop result or formal independent Gate is inferred here.
