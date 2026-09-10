"""Fail closed when A1 code, reports, contracts and ONNX drift apart."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import onnx

from challenge.planner.frozen_contracts import assert_frozen_contracts
from challenge.student.contract import OUTPUT_NAMES, StudentShapeContract
from challenge.student.model import StudentPlannerV0
from runtime.interface_registry import InterfaceRegistry


FORBIDDEN_ONNX_OPS = frozenset({"Shape", "NonZero", "Scatter", "Loop", "If"})


def validate_artifacts(root: str | Path) -> dict[str, Any]:
    root_path = Path(root).resolve()
    registry = InterfaceRegistry(root_path / "interfaces")
    assert_frozen_contracts(registry)
    challenge_path = root_path / "challenge"
    structure = json.loads((challenge_path / "model_structure.json").read_text(encoding="utf-8"))
    flops = json.loads((challenge_path / "flops_report.json").read_text(encoding="utf-8"))
    artifact = challenge_path / structure["artifact"]
    artifact_sha256 = hashlib.sha256(artifact.read_bytes()).hexdigest()
    if artifact_sha256 != structure["artifact_sha256"]:
        raise RuntimeError("ONNX SHA256 does not match model_structure.json")

    graph = onnx.load(artifact)
    onnx.checker.check_model(graph)
    contract = StudentShapeContract()
    input_shapes = {
        value.name: [dimension.dim_value for dimension in value.type.tensor_type.shape.dim]
        for value in graph.graph.input
    }
    expected_shapes = {name: list(shape) for name, shape in contract.input_shapes.items()}
    if input_shapes != expected_shapes:
        raise RuntimeError(f"ONNX input contract drift: {input_shapes} != {expected_shapes}")
    output_names = [value.name for value in graph.graph.output]
    if output_names != list(OUTPUT_NAMES):
        raise RuntimeError("ONNX structured output order drift")
    operators = sorted({node.op_type for node in graph.graph.node})
    forbidden = sorted(FORBIDDEN_ONNX_OPS.intersection(operators))
    if forbidden:
        raise RuntimeError(f"forbidden dynamic/control-flow ONNX operators: {forbidden}")
    metadata = {item.key: item.value for item in graph.metadata_props}
    if metadata.get("model_id") != StudentPlannerV0.model_id:
        raise RuntimeError("ONNX model_id metadata drift")
    if metadata.get("source_git_sha") != structure.get("source_git_sha"):
        raise RuntimeError("ONNX source_git_sha metadata drift")

    parameters = sum(parameter.numel() for parameter in StudentPlannerV0().parameters())
    if structure["parameters"] != parameters or flops["parameters"] != parameters:
        raise RuntimeError("parameter report drift")
    for key in ("model_id", "source_git_sha", "dataset_version", "config_id"):
        if structure.get(key) != flops.get(key):
            raise RuntimeError(f"candidate identity drift: {key}")
    if structure["input_shapes"] != expected_shapes or flops["input_shapes"] != expected_shapes:
        raise RuntimeError("reported input shape drift")
    return {
        "status": "PASS",
        "artifact": str(artifact.relative_to(root_path)),
        "artifact_sha256": artifact_sha256,
        "parameters": parameters,
        "operators": operators,
        "input_shapes": expected_shapes,
        "output_names": output_names,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    print(json.dumps(validate_artifacts(args.root), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
