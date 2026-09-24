"""Fail-closed ONNX Runtime QDQ PTQ entry point for A2 development.

This provides a portable smoke path while the official OpenExplorer/J6P
toolchain is unavailable. Its output is never labelled J6P-ready.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import platform
from typing import Any, Mapping

from .calibration import CalibrationDataset, OrtCalibrationReader, sha256_file


def _metadata(path: Path) -> dict[str, str]:
    import onnx

    graph = onnx.load(str(path), load_external_data=False)
    return {item.key: item.value for item in graph.metadata_props}


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def quantize_qdq(
    repo_root: str | Path,
    *,
    source_onnx: str | Path,
    calibration_jsonl: str | Path,
    calibration_manifest: str | Path,
    output_onnx: str | Path,
    allow_smoke: bool = False,
    allow_candidate: bool = False,
) -> dict[str, Any]:
    """Generate an INT8 QDQ candidate with strict provenance labelling."""
    # Keep the spelling of an ASCII junction instead of calling resolve().
    # ONNX Runtime 1.30 creates a sibling "-inferred.onnx" file and its
    # Windows path handling corrupts non-ASCII paths in this environment.
    repo = Path(repo_root).absolute()
    source = (repo / source_onnx).absolute() if not Path(source_onnx).is_absolute() else Path(source_onnx)
    output = (repo / output_onnx).absolute() if not Path(output_onnx).is_absolute() else Path(output_onnx)
    manifest_path = (repo / calibration_manifest).absolute() if not Path(calibration_manifest).is_absolute() else Path(calibration_manifest)
    calibration = _load_json(manifest_path)
    metadata = _metadata(source)
    source_status = metadata.get("weights_status", "UNRESOLVED")
    formal_source = source_status == "A3_FP32_GATE_PASSED"
    pending_candidate = source_status == "PENDING_A3_FP32_GATE"
    formal_calibration = calibration.get("formal_release") is True
    if pending_candidate and not allow_candidate:
        raise ValueError("pending A3 candidate requires explicit --allow-candidate")
    if not formal_source and not pending_candidate and not allow_smoke:
        raise ValueError("unapproved source ONNX requires --allow-smoke for toolchain smoke")
    if formal_source and not formal_calibration:
        raise ValueError("formal FP32 input requires a B1/B2-signed formal Calibration release")

    try:
        import onnx
        import onnxruntime
        from onnxruntime.quantization import (
            CalibrationMethod, QuantFormat, QuantType, quantize_static,
        )
    except ImportError as error:
        raise RuntimeError("onnx and onnxruntime with quantization support are required") from error

    dataset = CalibrationDataset.open(repo, calibration_jsonl)
    output.parent.mkdir(parents=True, exist_ok=True)
    quantize_static(
        str(source),
        str(output),
        OrtCalibrationReader(dataset),
        quant_format=QuantFormat.QDQ,
        activation_type=QuantType.QInt8,
        weight_type=QuantType.QInt8,
        calibrate_method=CalibrationMethod.MinMax,
        per_channel=True,
        reduce_range=False,
        extra_options={
            "ActivationSymmetric": True,
            "WeightSymmetric": True,
            "DedicatedQDQPair": False,
        },
    )
    graph = onnx.load(str(output))
    props = {item.key: item.value for item in graph.metadata_props}
    props.update({
        "quantization_status": (
            "FORMAL_INT8_CANDIDATE" if formal_source else
            "A3_CANDIDATE_PRE_PTQ" if pending_candidate else "SMOKE_ONLY"
        ),
        "quantization_method": "onnxruntime_static_qdq_int8_minmax_symmetric_per_channel",
        "source_fp32_sha256": sha256_file(source),
        "calibration_manifest_sha256": sha256_file(manifest_path),
    })
    del graph.metadata_props[:]
    onnx.helper.set_model_props(graph, props)
    onnx.checker.check_model(graph)
    onnx.save(graph, str(output))

    nodes = [node.op_type for node in graph.graph.node]
    artifact_sha = sha256_file(output)
    def tensor_shape(value: Any) -> list[int]:
        return [int(item.dim_value) for item in value.type.tensor_type.shape.dim]

    structure = {
        "schema_version": "1.0",
        "status": (
            "FORMAL_INT8_CANDIDATE_PENDING_B2_GATE" if formal_source else
            "A3_CANDIDATE_PRE_PTQ" if pending_candidate else "SMOKE_ONLY"
        ),
        "artifact": output.name,
        "artifact_sha256": artifact_sha,
        "model_id": props.get("model_id"),
        "config_id": props.get("config_id"),
        "source_fp32_sha256": sha256_file(source),
        "opset": next((item.version for item in graph.opset_import if not item.domain), None),
        "input_shapes": {item.name: tensor_shape(item) for item in graph.graph.input},
        "output_names": [item.name for item in graph.graph.output],
        "output_shapes": {item.name: tensor_shape(item) for item in graph.graph.output},
        "onnx_operators": sorted(set(nodes)),
        "quantization_method": props["quantization_method"],
    }
    _write_json(output.parent / "int8_structure.json", structure)
    result = {
        "schema_version": "1.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": (
            "FORMAL_INT8_CANDIDATE_PENDING_B2_GATE" if formal_source else
            "A3_CANDIDATE_PRE_PTQ" if pending_candidate else "SMOKE_ONLY"
        ),
        "j6p_ready": False,
        "source": {
            "path": str(source.relative_to(repo)),
            "sha256": sha256_file(source),
            "weights_status": source_status,
            "metadata": metadata,
        },
        "calibration": {
            "jsonl": str(Path(calibration_jsonl)),
            "jsonl_sha256": sha256_file((repo / calibration_jsonl).resolve()),
            "manifest": str(manifest_path.relative_to(repo)),
            "manifest_sha256": sha256_file(manifest_path),
            "formal_release": formal_calibration,
            "sample_count": len(dataset.records),
        },
        "quantization": {
            "format": "QDQ",
            "activation": "QInt8 symmetric",
            "weight": "QInt8 symmetric per-channel",
            "calibration_method": "MinMax",
            "quantize_linear_nodes": nodes.count("QuantizeLinear"),
            "dequantize_linear_nodes": nodes.count("DequantizeLinear"),
        },
        "output": {
            "path": str(output.relative_to(repo)),
            "sha256": artifact_sha,
            "size_bytes": output.stat().st_size,
            "structure": str((output.parent / "int8_structure.json").relative_to(repo)),
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "onnx": onnx.__version__,
            "onnxruntime": onnxruntime.__version__,
        },
        "remaining_gates": [
            "FP32_vs_INT8_raw_output_drift",
            "B2_INT8_accuracy_gate",
            "A4_OpenExplorer_compile",
            "B3_J6P_HIL_measurement",
        ],
        "toolchain_note": (
            "A3 candidate pre-PTQ diagnostic; not formal INT8 approval. "
            if pending_candidate else "Portable ONNX Runtime QDQ smoke only. "
        ) + "OpenExplorer operator support, fallbacks and J6P performance remain A4/B3-owned.",
    }
    _write_json(output.parent / "int8_manifest.json", result)
    return result


__all__ = ["quantize_qdq"]
