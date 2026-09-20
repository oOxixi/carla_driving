# A4 Horizon Deployment

> A2 的 INT8 输入产物、Calibration、PTQ/QAT 和精度 Gate 合同见
> [`docs/modules/A2_INT8_QUANTIZATION_AND_QAT.md`](../../docs/modules/A2_INT8_QUANTIZATION_AND_QAT.md)。
> A4 只接收通过该门禁且身份完整的候选；当前随机初始化 FP32 ONNX 仅用于工具链冒烟。
> A4 的完整部署顺序、Runtime 接口、性能口径、证据等级和完成定义见
> [`docs/modules/A4_OPENEXPLORER_J6P_RUNTIME.md`](../../docs/modules/A4_OPENEXPLORER_J6P_RUNTIME.md)。

## 1. Scope

A4 is responsible for the deployment/runtime layer of the Student model.

Current deployment pipeline:

PyTorch Student
    ->
Fixed-shape FP32 ONNX
    ->
ONNX Runtime on X86
    ->
Horizon/OpenExplorer conversion
    ->
J6P runtime

The current stage focuses on PC/X86 deployment validation.

## 2. Current Model

Current ONNX artifact:

    challenge/student_v0_fp32.onnx

The current model is a fixed-shape FP32 ONNX artifact.

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

## 3. ONNX Operators

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

OpenExplorer/J6P operator compatibility must be verified against the actual toolchain version supplied by the competition.

## 4. X86 Runtime

The X86 smoke-test entry point is:

    challenge/runtime/student_x86.py

The shell entry point is:

    challenge/runtime/x86_run.sh

The runtime uses ONNX Runtime with CPUExecutionProvider.

## 5. J6P Status

J6P deployment is pending the official hardware/toolchain information.

The following items must be confirmed before generating a final J6P artifact:

- Target J6P model
- OpenExplorer version
- J6P SDK version
- Conversion command
- Conversion configuration
- Board-side runtime example
- Compiled model format

No J6P conversion result is claimed until the official toolchain and hardware are available.

## 6. Current Status

- A1 structural tests: passed
- Fixed-shape ONNX export: completed
- ONNX input/output inspection: completed
- X86 ONNX Runtime validation: in progress
- OpenExplorer conversion: pending
- J6P runtime validation: pending
