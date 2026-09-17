# ONNX Operator Mapping

## Model

Artifact:

    challenge/student_v0_fp32.onnx

The following operators are present in the current ONNX graph.

| ONNX Operator | Role | OpenExplorer Status | J6P Status |
|---|---|---|---|
| AveragePool | Pooling | Pending toolchain verification | Pending |
| Concat | Tensor concatenation | Pending toolchain verification | Pending |
| Constant | Graph constants | Graph utility | Pending |
| Conv | Convolution | Pending toolchain verification | Pending |
| Flatten | Tensor flattening | Pending toolchain verification | Pending |
| Gemm | Linear layer | Pending toolchain verification | Pending |
| Identity | Graph utility | Pending toolchain verification | Pending |
| Mul | Element-wise multiplication | Pending toolchain verification | Pending |
| Relu | Activation | Pending toolchain verification | Pending |
| Reshape | Tensor reshape | Pending toolchain verification | Pending |
| Sigmoid | Activation | Pending toolchain verification | Pending |

## Important Note

Operator support must not be assumed from the ONNX operator name alone.

Final support status must be verified using the actual OpenExplorer/J6P toolchain version supplied for the competition.

The current X86 validation only establishes that the ONNX graph can be inspected and executed using the local ONNX Runtime environment. It does not establish J6P compatibility.
