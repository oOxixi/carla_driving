"""Export Student V0 with fixed shapes and no dynamic axes."""

from __future__ import annotations

import argparse
from pathlib import Path

import torch

from challenge.student.contract import OUTPUT_NAMES, StudentShapeContract
from challenge.student.model import StudentPlannerV0


def export_student_v0(output: str | Path, *, seed: int = 20260911) -> Path:
    torch.manual_seed(seed)
    contract = StudentShapeContract()
    model = StudentPlannerV0(contract).eval()
    inputs = tuple(torch.zeros(shape, dtype=torch.float32) for shape in contract.input_shapes.values())
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(
        model,
        inputs,
        path,
        input_names=list(contract.input_shapes),
        output_names=list(OUTPUT_NAMES),
        opset_version=17,
        do_constant_folding=True,
        dynamic_axes=None,
    )
    try:
        import onnx
    except ImportError as error:
        raise RuntimeError("onnx is required to verify the exported model") from error
    graph = onnx.load(path)
    onnx.checker.check_model(graph)
    for value, expected in zip(graph.graph.input, contract.input_shapes.values()):
        actual = tuple(dimension.dim_value for dimension in value.type.tensor_type.shape.dim)
        if actual != expected:
            raise RuntimeError(f"dynamic or wrong ONNX shape for {value.name}: {actual} != {expected}")
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="challenge/student_v0_fp32.onnx")
    args = parser.parse_args()
    path = export_student_v0(args.output)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

