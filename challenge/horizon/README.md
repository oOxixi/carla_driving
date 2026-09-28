# A4 Horizon Deployment

## 1. Scope

A4 is responsible for the deployment and runtime layer of the Student model.

The intended deployment pipeline is:

```text
A2 INT8 Gate-passed Student
        ->
Fixed-shape INT8 ONNX
        ->
OpenExplorer compilation
        ->
J6P compiled artifact
        ->
J6P runtime
```

The current repository also contains an FP32 ONNX artifact and an X86
ONNX Runtime smoke-test path. These are development and diagnostic artifacts
only.

A4 does not train the Student model and does not decide the FP32 or INT8
accuracy gate.

## 2. Current ONNX Artifact

Current repository artifact:

```text
challenge/student_v0_fp32.onnx
```

This file is a fixed-shape FP32 ONNX smoke artifact.

It was generated for structural and toolchain validation. It is not the final
accuracy-approved deployment model.

### Inputs

| Name | Shape | Dtype |
|---|---|---|
| rgb | [1, 3, 224, 224] | float32 |
| text_tokens | [1, 32] | float32 |
| targets | [1, 8, 14] | float32 |
| state | [1, 64] | float32 |

### Outputs

| Name | Shape |
|---|---|
| plan_length_logits | [1, 4] |
| behavior_logits | [1, 4, 14] |
| target_pointer_logits | [1, 4, 9] |
| target_lane_logits | [1, 4, 6] |
| target_speed_mps | [1, 4] |
| completion_type_logits | [1, 4, 8] |
| on_failure_logits | [1, 4, 4] |
| confidence | [1, 1] |
| requires_confirmation_logits | [1, 1] |
| replan_condition_logits | [1, 7] |

### ONNX Operators

The current ONNX graph contains:

- AveragePool
- Concat
- Constant
- Conv
- Flatten
- Gemm
- Identity
- Mul
- Relu
- Reshape
- Sigmoid

Operator compatibility must be verified with the actual OpenExplorer and J6P
toolchain. X86 ONNX Runtime execution does not prove J6P compatibility.

## 3. A3 FP32 Candidate Package

The A3 candidate package has been copied to the local WSL environment:

```text
artifacts/challenge/distillation/a3_d2_d3_fp32_candidate_handoff_v3
```

The package was verified using:

```bash
python -m challenge.distillation.candidate_handoff \
  --verify-package \
  artifacts/challenge/distillation/a3_d2_d3_fp32_candidate_handoff_v3
```

Verification result:

```text
valid: true
files_checked: 9
```

Candidate identity:

```text
model_id:
student-v0-r3-fp32

config_id:
student-v0-r3-structure-20260911

weights_sha256:
1afb8ebd11e401d4d7e6181d244ed39438421183c5303f1ce4a4391cee8cc68c
```

Current candidate status:

```text
gate_status:
PENDING_A3_FP32_GATE

package_status:
PENDING_B2_INDEPENDENT_VALIDATION
```

The package is a valid and complete A3 candidate handoff package. It is not
yet an accuracy approval and must not be described as a production-ready
deployment model.

A4 formal conversion must use the exact A2 INT8 Gate-passed artifact, together
with its model identity, quantization configuration, calibration information
and manifest.

## 4. X86 Runtime

The X86 runtime entry point is:

```text
challenge/runtime/student_x86.py
```

The shell entry point is:

```text
challenge/runtime/x86_run.sh
```

The runtime uses:

```text
ONNX Runtime
CPUExecutionProvider
```

Run the X86 smoke test with:

```bash
source .venv/bin/activate
./challenge/runtime/x86_run.sh
```

The current X86 runtime profile is:

```text
challenge/runtime/runtime_profile_x86.json
```

Current X86 smoke-test configuration:

```text
warmup runs:
5

benchmark runs:
20

average latency:
13.8156 ms

minimum latency:
11.7047 ms

maximum latency:
23.1584 ms
```

The profile records the FP32 ONNX smoke test on the local CPU. It is a
diagnostic X86 result and must not be reported as J6P performance.

## 5. OpenExplorer Toolchain

The repository contains the OpenExplorer deployment information in:

```text
challenge/hil/j6p_deployment_inputs.md
challenge/hil/pc_deployment_plan.md
```

Current toolchain information:

```text
OpenExplorer version:
3.9.1

Docker image:
openexplorer/ai_toolchain_ubuntu_22_j6_cpu:v3.9.1

J6P compiler target:
nash-p
```

Model inspection command:

```bash
hb_compile --model <model>.onnx --march nash-p
```

Formal conversion command:

```bash
hb_compile -c <config>.yaml
```

The CPU Docker image is sufficient for PC-side model inspection, compilation
and X86 simulation. A J6P board is not required for the PC compilation step.

The Docker image and OpenExplorer package should be obtained from the official
OpenExplorer download package. The image tag and package version must be
recorded in the conversion manifest.

## 6. OpenExplorer Conversion Requirements

A formal A4 conversion requires:

- A2 INT8 Gate-passed model;
- exact source model SHA256;
- model and configuration identity;
- OpenExplorer version;
- Docker image tag or digest;
- J6P compiler target;
- calibration data and quantization configuration;
- conversion command;
- conversion log;
- operator and CPU/BPU fallback report;
- compiled artifact SHA256.

The following files are not currently available for the Student model:

```text
compiled_model.*
compile.log
operator_mapping.json
runtime_manifest.json
```

The existing OpenExplorer evidence in the repository includes demonstration
and toolchain validation material. It does not represent a final Student
compiled artifact.

## 7. J6P Runtime

The official J6P runtime examples include:

```bash
hrt_model_exec model_info --model_file=xxx.hbm

hrt_model_exec infer \
  --model_file=xxx.hbm \
  --input_file=xxx.bin \
  --enable_dump=true

hrt_model_exec perf \
  --model_file=xxx.hbm \
  --thread_num 1 \
  --frame_count=1000

hrt_ucp_monitor -b -e bpu -d 1000
```

The repository currently does not contain:

```text
j6p_run.sh
runtime_profile_j6p.json
```

No J6P board is currently available to A4. Therefore the following items are
not claimed:

- J6P model loading;
- J6P functional inference;
- J6P latency;
- J6P memory usage;
- J6P power consumption;
- BPU utilization;
- temperature;
- long-running stability;
- board-side output consistency.

## 8. Current Delivery Status

| Item | Status |
|---|---|
| `challenge/horizon/README.md` | Completed and updated |
| `challenge/horizon/operator_mapping.md` | Initial version completed; actual toolchain verification pending |
| `challenge/runtime/student_x86.py` | Completed |
| `challenge/runtime/x86_run.sh` | Completed |
| `challenge/runtime/runtime_profile_x86.json` | Completed; diagnostic X86 result |
| A3 candidate weight package | Copied and integrity verified |
| A3 FP32 Gate | Pending |
| B2 independent validation | Pending |
| Final `student.onnx` | Pending A2 INT8 Gate-passed artifact |
| `compiled_model.*` | Pending final A2 input and OpenExplorer conversion |
| `j6p_run.sh` | Pending J6P runtime SDK and board access |
| A4 Dockerfile | Pending final OpenExplorer environment definition |
| J6P runtime profile | Blocked because no J6P board is available |

## 9. Evidence Level

The current repository state supports:

```text
L0: structural and toolchain smoke validation
```

The current state does not yet support:

```text
L1: final Student X86 deployment
L2: final OpenExplorer compiled artifact
L3: J6P functional validation
L4: J6P measured performance
L5: release candidate approval
```

A higher evidence level requires the exact approved model artifact, conversion
manifest, compiled model, runtime entry point and corresponding validation
evidence.
