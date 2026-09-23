"""Export Student V0 with fixed shapes and no dynamic axes."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import torch

from challenge.student.contract import OUTPUT_NAMES, StudentShapeContract
from challenge.student.model import StudentModelConfig, StudentPlannerV0
from challenge.planner.frozen_contracts import FROZEN_CONTRACT_SHA256
from challenge.export.compute_flops import analyze_model


def _source_git_sha() -> str:
    return subprocess.check_output(
        ("git", "rev-parse", "HEAD"), text=True, encoding="utf-8",
    ).strip()


class StudentOnnxExportWrapper(torch.nn.Module):
    """Convert the public named dict to ONNX's stable positional output list."""

    def __init__(self, model: StudentPlannerV0) -> None:
        super().__init__()
        self.model = model

    def forward(self, *inputs: torch.Tensor) -> tuple[torch.Tensor, ...]:
        outputs = self.model(*inputs)
        return tuple(outputs[name] for name in OUTPUT_NAMES)


def export_student_v0(
    output: str | Path,
    *,
    seed: int = 20260911,
    source_git_sha: str | None = None,
    weights: str | Path | None = None,
    weights_manifest: str | Path | None = None,
) -> Path:
    torch.manual_seed(seed)
    contract = StudentShapeContract()
    config = StudentModelConfig()
    model = StudentPlannerV0(contract, config).eval()
    weight_metadata = _load_verified_weights(
        model,
        weights=weights,
        weights_manifest=weights_manifest,
    )
    export_model = StudentOnnxExportWrapper(model).eval()
    inputs = tuple(torch.zeros(shape, dtype=torch.float32) for shape in contract.input_shapes.values())
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(
        export_model,
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
    onnx.helper.set_model_props(graph, {
        "model_id": model.model_id,
        "weights_status": weight_metadata["weights_status"],
        "export_seed": str(seed),
        "python_version": "3.12",
        "onnx_opset": "17",
        "source_git_sha": source_git_sha or _source_git_sha(),
        "dataset_version": weight_metadata["dataset_version"],
        "config_id": config.config_id,
        "source_weights_sha256": weight_metadata["source_weights_sha256"],
        "weights_manifest_sha256": weight_metadata["weights_manifest_sha256"],
        "model_request_sha256": FROZEN_CONTRACT_SHA256["model_request"],
        "maneuver_plan_sha256": FROZEN_CONTRACT_SHA256["maneuver_plan"],
    })
    onnx.checker.check_model(graph)
    for value, expected in zip(graph.graph.input, contract.input_shapes.values()):
        actual = tuple(dimension.dim_value for dimension in value.type.tensor_type.shape.dim)
        if actual != expected:
            raise RuntimeError(f"dynamic or wrong ONNX shape for {value.name}: {actual} != {expected}")
    onnx.save(graph, path)
    # Publish companion reports from the exact graph just saved, including the
    # same provenance when callers explicitly pin --source-git-sha.
    metadata = {item.key: item.value for item in graph.metadata_props}
    report = analyze_model()
    report["source_git_sha"] = metadata["source_git_sha"]
    structure = {key: report[key] for key in (
        "schema_version", "model_id", "source_git_sha", "dataset_version",
        "config_id", "parameters", "precision", "input_shapes",
    )}
    structure.update({
        "status": (
            "A3_FP32_GATE_PASSED_ONNX_EXPORTED"
            if metadata["weights_status"] == "A3_FP32_GATE_PASSED"
            else "A1_STRUCTURE_READY_A3_WEIGHTS_PENDING"
        ),
        "artifact": path.name,
        "artifact_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "opset": 17,
        "dynamic_axes": False,
        "onnx_operators": sorted({node.op_type for node in graph.graph.node}),
        "modules": {name: str(module) for name, module in model.named_children()},
        "output_names": list(OUTPUT_NAMES),
        "output_shapes": {name: list(shape) for name, shape in contract.output_shapes.items()},
        "input_dtype": "float32",
        "output_dtype": "float32",
        "forbidden_outputs": ["steer", "throttle", "brake", "waypoints"],
        "training_state": metadata["weights_status"],
    })
    for filename, payload in (
        ("model_structure.json", structure), ("flops_report.json", report),
    ):
        (path.parent / filename).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8",
        )
    return path


def _load_verified_weights(
    model: StudentPlannerV0,
    *,
    weights: str | Path | None,
    weights_manifest: str | Path | None,
) -> dict[str, str]:
    """Load a Gate-passed state_dict, or explicitly retain random smoke state."""
    if weights is None and weights_manifest is None:
        return {
            "weights_status": "random_initialization_for_export_smoke_only",
            "dataset_version": "NOT_APPLICABLE_RANDOM_INIT",
            "source_weights_sha256": "UNRESOLVED_RANDOM_INIT",
            "weights_manifest_sha256": "UNRESOLVED_RANDOM_INIT",
        }
    if weights is None or weights_manifest is None:
        raise ValueError("--weights and --weights-manifest must be provided together")
    weights_path = Path(weights)
    manifest_path = Path(weights_manifest)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("weights manifest must be a JSON object")
    if manifest.get("gate_status") != "A3_FP32_GATE_PASSED":
        raise ValueError("formal ONNX export requires gate_status=A3_FP32_GATE_PASSED")
    if manifest.get("model_id") != model.model_id:
        raise ValueError("weights manifest model_id does not match Student")
    if manifest.get("config_id") != model.config.config_id:
        raise ValueError("weights manifest config_id does not match Student")
    actual_sha = hashlib.sha256(weights_path.read_bytes()).hexdigest()
    if manifest.get("weights_sha256") != actual_sha:
        raise ValueError("weights SHA256 does not match manifest")
    state_dict = torch.load(weights_path, map_location="cpu", weights_only=True)
    if not isinstance(state_dict, dict):
        raise ValueError("weights must contain a pure state_dict")
    model.load_state_dict(state_dict, strict=True)
    return {
        "weights_status": "A3_FP32_GATE_PASSED",
        "dataset_version": str(manifest.get("dataset_version", "")),
        "source_weights_sha256": actual_sha,
        "weights_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="challenge/student_v0_fp32.onnx")
    parser.add_argument("--source-git-sha")
    parser.add_argument("--weights")
    parser.add_argument("--weights-manifest")
    args = parser.parse_args()
    path = export_student_v0(
        args.output,
        source_git_sha=args.source_git_sha,
        weights=args.weights,
        weights_manifest=args.weights_manifest,
    )
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["StudentOnnxExportWrapper", "export_student_v0", "_load_verified_weights"]
