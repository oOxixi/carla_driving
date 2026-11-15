# Student Features16 development candidate

Status: frozen development candidate, not a formal FP32 or INT8 Gate package.

The FP32 graph adds a learned first-step speed residual to the robust V3
Student. The compiled variant keeps that graph and weights fixed, and uses
local INT16 on the speed head and residual feature path. The rest of the
model uses the existing OpenExplorer quantization policy.

- Model: `student-v0-r3-numeric-primary-v1-fp32`.
- Training/config ID: `student-v0-r3-numeric-primary-v1-20261112`.
- FP32 source snapshot: `6582dc9909a5298c416d092682e9e6d37224c748`.
- Training: original governed positive view (5,856 Train / 1,108 Dev)
  plus 336 Train / 80 Dev development speed probes bound to source RGB.
  This is not a new Teacher collection or a signed training release.
- PTQ: verified `b1_calibration_v1`, 300 samples. OpenExplorer 3.9.1
  image ID `sha256:cf06f721448e30f8f569cfeb6fc3356c1ad6e77ba180042d0c3babe891b6b5c4`;
  hb_compile 3.5.16, HBDK 4.11.11, target `nash-p`.
- Development: 168/208 complete plan hits; compared with the previous
  mixed-precision iteration's 133/208.
- Exposed regression: 850/850 valid plans, all categorical signatures
  agree with the numeric FP32. MAE against stored Teacher was 0.2842 m/s
  on 472 paired numeric steps (numeric FP32: 0.2455 m/s).
- Compiler placement report: 92 BPU rows, no CPU rows. Not a utilization
  measurement.
- HBM X86 smoke: the official HBRuntime loaded and ran the packaged HBM
  on one hash-verified SET_SPEED development case. All ten outputs were
  exactly equal to the packaged BC; both produced schema-valid plans
  with identical steps. This is one-case inference evidence, not board
  execution or a repeat of the 850-case BC regression.

The manifest hashes every packaged file. The HBM is for deployment checks;
the BC is for X86 simulation and the ONNX is its FP32 reference. Reports
describe scope and measurement limitations. Raw evaluation data, model
training data and the official image are not included. For recompilation,
restore the frozen Calibration v1 four-stream tensors from the input
manifest and the original relative layout of `primary_only/` and
`oe_391_calibration_v1/`. Run `hb_compile -c speed_features16_probe.yaml`
from the latter directory in the official image. The runtime preprocessing
and Graph-to-Plan adapter are from the repository, not a standalone runtime
provided in this archive.

No new independent benchmark or board timing, utilization, power, and
closed-loop evidence is asserted.
