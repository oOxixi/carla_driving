"""Fail-closed ONNX Runtime QDQ PTQ entry point for A2 development.

This provides a portable smoke path while the official OpenExplorer/J6P
toolchain is unavailable. Its output is never labelled J6P-ready.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import shutil
from typing import Any, Mapping, Sequence

from challenge.hil.identity import git_head

from .calibration import (
    CalibrationDataset,
    FORMAL_CALIBRATION_RELATIVE,
    OrtCalibrationReader,
    load_formal_calibration_v1,
    sha256_file,
)
from .config import DEFAULT_QUANT_CONFIG, load_quant_config, quant_config_identity
from .manifest import validate_int8_manifest


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


def _path_label(path: Path, repo: Path) -> str:
    """Prefer a repository-relative label, tolerating Windows junctions."""
    try:
        return str(path.relative_to(repo))
    except ValueError:
        return str(path)


def quantize_qdq(
    repo_root: str | Path,
    *,
    source_onnx: str | Path,
    calibration_jsonl: str | Path,
    calibration_manifest: str | Path,
    output_onnx: str | Path,
    quant_config: str | Path = DEFAULT_QUANT_CONFIG,
    excluded_nodes: Sequence[str] = (),
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
    jsonl_path = (repo / calibration_jsonl).absolute() if not Path(calibration_jsonl).is_absolute() else Path(calibration_jsonl)
    config_path = (repo / quant_config).absolute() if not Path(quant_config).is_absolute() else Path(quant_config)
    calibration = _load_json(manifest_path)
    config = load_quant_config(config_path)
    config_identity = quant_config_identity(config_path)
    metadata = _metadata(source)
    source_status = metadata.get("weights_status", "UNRESOLVED")
    formal_source = source_status == "A3_FP32_GATE_PASSED"
    pending_candidate = source_status == "PENDING_A3_FP32_GATE"
    formal_calibration = False
    if pending_candidate and not allow_candidate:
        raise ValueError("pending A3 candidate requires explicit --allow-candidate")
    if not formal_source and not pending_candidate and not allow_smoke:
        raise ValueError("unapproved source ONNX requires --allow-smoke for toolchain smoke")
    canonical_release = (repo / FORMAL_CALIBRATION_RELATIVE).resolve()
    requested_formal_calibration = (
        manifest_path.parent.resolve() == canonical_release
        and jsonl_path.parent.resolve() == canonical_release
    )
    if formal_source or requested_formal_calibration:
        release = load_formal_calibration_v1(repo, release_directory=manifest_path.parent)
        if manifest_path.resolve() != release.manifest_path.resolve():
            raise ValueError("formal PTQ calibration manifest must be Calibration v1")
        if jsonl_path.resolve() != release.jsonl_path.resolve():
            raise ValueError("formal PTQ calibration JSONL must be Calibration v1")
        dataset = release.dataset
        calibration_identity = release.identity
        formal_calibration = True
    else:
        actual_jsonl_sha = sha256_file(jsonl_path)
        if calibration.get("calibration_jsonl_sha256") != actual_jsonl_sha:
            raise ValueError("calibration JSONL SHA256 does not match its manifest")
        dataset = CalibrationDataset.open(repo, jsonl_path)
        calibration_identity = {
            "status": calibration.get("status", "UNRESOLVED"),
            "dataset_version": calibration.get("calibration_id", "DEVELOPMENT"),
            "sample_count": len(dataset.records),
            "calibration_jsonl_sha256": actual_jsonl_sha,
            "calibration_manifest_sha256": sha256_file(manifest_path),
        }
    closeout_identity = calibration_identity.get("b1_closeout")
    if formal_source:
        if metadata.get("a2_upstream_readiness") != "READY_FOR_A2_FORMAL":
            raise ValueError(
                "formal PTQ requires an ONNX with a2_upstream_readiness=READY_FOR_A2_FORMAL"
            )
        if not isinstance(closeout_identity, Mapping):
            raise ValueError("formal PTQ has no verified B1 closeout identity")
        for metadata_key, identity_key in {
            "b1_closeout_report_sha256": "closeout_report_sha256",
            "b1_governed_release_manifest_sha256": "governed_release_manifest_sha256",
            "b1_calibration_identity_sha256": "calibration_identity_sha256",
            "b1_independent_validation_identity_sha256": (
                "independent_validation_identity_sha256"
            ),
        }.items():
            if metadata.get(metadata_key) != closeout_identity.get(identity_key):
                raise ValueError(f"formal PTQ ONNX/B1 closeout mismatch for {metadata_key}")
    calibration_manifest_digest = calibration_identity["calibration_manifest_sha256"]

    try:
        import onnx
        import onnxruntime
        from onnxruntime.quantization import (
            CalibrationMethod, QuantFormat, QuantType, quantize_static,
        )
    except ImportError as error:
        raise RuntimeError("onnx and onnxruntime with quantization support are required") from error

    # Create directories through the physical target of an ASCII junction.
    # pathlib/os.mkdir can report WinError 183 for a missing child directly
    # below a directory junction, even with exist_ok=True.
    output.parent.resolve().mkdir(parents=True, exist_ok=True)
    options = config["options"]
    all_excluded = sorted(set(options.get("excluded_nodes", [])) | set(excluded_nodes))
    calibration_method = getattr(CalibrationMethod, config["calibration"]["method"])
    quantize_static(
        str(source),
        str(output),
        OrtCalibrationReader(dataset),
        quant_format=QuantFormat.QDQ,
        activation_type=QuantType.QInt8,
        weight_type=QuantType.QInt8,
        calibrate_method=calibration_method,
        per_channel=config["weights"]["granularity"] == "per_channel",
        reduce_range=bool(options["reduce_range"]),
        nodes_to_exclude=all_excluded,
        extra_options={
            "ActivationSymmetric": bool(config["activations"]["symmetric"]),
            "WeightSymmetric": bool(config["weights"]["symmetric"]),
            "DedicatedQDQPair": bool(options["dedicated_qdq_pair"]),
        },
    )
    graph = onnx.load(str(output))
    props = {item.key: item.value for item in graph.metadata_props}
    props.update({
        "quantization_status": (
            "FORMAL_INT8_CANDIDATE" if formal_source else
            "A3_CANDIDATE_PRE_PTQ" if pending_candidate else "SMOKE_ONLY"
        ),
        "quantization_method": config["config_id"],
        "source_fp32_sha256": sha256_file(source),
        "calibration_manifest_sha256": calibration_manifest_digest,
        "quant_config_sha256": config_identity["sha256"],
        "mixed_precision_excluded_nodes": json.dumps(all_excluded, separators=(",", ":")),
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
    identity_material = "|".join((
        sha256_file(source), calibration_manifest_digest, config_identity["sha256"],
        ",".join(all_excluded),
    ))
    quantization_id = "a2-ptq-" + hashlib.sha256(identity_material.encode("utf-8")).hexdigest()[:16]
    source_fp32_manifest = {
        "schema_version": "1.0",
        "status": source_status,
        "model_id": metadata.get("model_id", "UNRESOLVED"),
        "config_id": metadata.get("config_id", "UNRESOLVED"),
        "dataset_version": metadata.get("dataset_version", "UNRESOLVED"),
        "source_weights_git_sha": metadata.get("source_weights_git_sha", "UNRESOLVED"),
        "source_fp32_weights_sha256": metadata.get("source_weights_sha256", "UNRESOLVED"),
        "source_weights_manifest_sha256": metadata.get("weights_manifest_sha256", "UNRESOLVED"),
        "source_fp32_onnx_sha256": sha256_file(source),
        "source_fp32_onnx": _path_label(source, repo),
        "onnx_metadata": metadata,
    }
    _write_json(output.parent / "source_fp32_manifest.json", source_fp32_manifest)
    copied_manifest = output.parent / "calibration_manifest.json"
    copied_config = output.parent / "quant_config.yaml"
    if copied_manifest.resolve() != manifest_path.resolve():
        shutil.copyfile(manifest_path, copied_manifest)
    if copied_config.resolve() != config_path.resolve():
        shutil.copyfile(config_path, copied_config)

    result = {
        "schema_version": "1.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "quantization_id": quantization_id,
        "git_sha": git_head(repo),
        "status": (
            "FORMAL_INT8_CANDIDATE_PENDING_B2_GATE" if formal_source else
            "A3_CANDIDATE_PRE_PTQ" if pending_candidate else "SMOKE_ONLY"
        ),
        "gate_status": "PENDING_B2_INT8_GATE" if formal_source else "NOT_FORMAL",
        "j6p_ready": False,
        "model_id": metadata.get("model_id", "UNRESOLVED"),
        "config_id": metadata.get("config_id", "UNRESOLVED"),
        "dataset_version": metadata.get("dataset_version", "UNRESOLVED"),
        "source_fp32_weights_sha256": metadata.get("source_weights_sha256", "UNRESOLVED"),
        "source_fp32_onnx_sha256": sha256_file(source),
        "calibration_manifest_sha256": calibration_manifest_digest,
        "quant_config_sha256": config_identity["sha256"],
        "int8_artifact_sha256": artifact_sha,
        "B2_result": {
            "status": "PENDING_B2_INT8_GATE" if formal_source else "NOT_APPLICABLE_DEVELOPMENT",
            "decision_manifest": None,
            "decision_manifest_sha256": None,
        },
        "upstream_governance": {
            "a2_upstream_readiness": metadata.get("a2_upstream_readiness", "UNRESOLVED"),
            "b1_closeout": closeout_identity,
        },
        "source": {
            "path": _path_label(source, repo),
            "sha256": sha256_file(source),
            "weights_status": source_status,
            "metadata": metadata,
        },
        "calibration": {
            "jsonl": _path_label(jsonl_path, repo),
            "jsonl_sha256": calibration_identity["calibration_jsonl_sha256"],
            "jsonl_worktree_sha256": sha256_file(jsonl_path),
            "manifest": _path_label(manifest_path, repo),
            "manifest_sha256": calibration_manifest_digest,
            "manifest_worktree_sha256": sha256_file(manifest_path),
            "formal_release": formal_calibration,
            "sample_count": len(dataset.records),
            "identity": calibration_identity,
        },
        "quantization": {
            "format": "QDQ",
            "activation": "QInt8 symmetric",
            "weight": "QInt8 symmetric per-channel",
            "calibration_method": config["calibration"]["method"],
            "config_id": config["config_id"],
            "config_path": "quant_config.yaml",
            "config_sha256": config_identity["sha256"],
            "excluded_nodes": all_excluded,
            "quantize_linear_nodes": nodes.count("QuantizeLinear"),
            "dequantize_linear_nodes": nodes.count("DequantizeLinear"),
        },
        "output": {
            "path": _path_label(output, repo),
            "sha256": artifact_sha,
            "size_bytes": output.stat().st_size,
            "structure": _path_label(output.parent / "int8_structure.json", repo),
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
    validate_int8_manifest(result)
    _write_json(output.parent / "int8_manifest.json", result)
    return result


__all__ = ["quantize_qdq"]
