"""Prepare the fixed-shape Student for OpenExplorer 3.9.1 PTQ.

The proprietary toolchain is not invoked here. This module creates aligned
multi-input calibration tensors and a reviewable ``hb_compile`` YAML for A4/B3.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from challenge.student.contract import StudentShapeContract

from .calibration import CalibrationDataset, sha256_file


INPUT_NAMES = ("rgb", "text_tokens", "targets", "state")
OPENEXPLORER_VERSION = "3.9.1"
J6P_MARCH = "nash-p"


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _onnx_identity(path: Path) -> dict[str, Any]:
    try:
        import onnx
    except ImportError as error:
        raise RuntimeError("onnx is required to prepare OpenExplorer inputs") from error
    graph = onnx.load(path)
    onnx.checker.check_model(graph)
    expected = StudentShapeContract().input_shapes
    actual_names = tuple(value.name for value in graph.graph.input)
    if actual_names != INPUT_NAMES:
        raise ValueError(f"ONNX input order mismatch: {actual_names} != {INPUT_NAMES}")
    actual_shapes: dict[str, list[int]] = {}
    for value in graph.graph.input:
        shape = [int(item.dim_value) for item in value.type.tensor_type.shape.dim]
        if tuple(shape) != expected[value.name]:
            raise ValueError(
                f"ONNX input shape mismatch for {value.name}: {tuple(shape)} != {expected[value.name]}"
            )
        if value.type.tensor_type.elem_type != onnx.TensorProto.FLOAT:
            raise ValueError(f"ONNX input {value.name} must be float32")
        actual_shapes[value.name] = shape
    metadata = {item.key: item.value for item in graph.metadata_props}
    return {
        "sha256": sha256_file(path),
        "input_names": list(actual_names),
        "input_shapes": actual_shapes,
        "weights_status": metadata.get("weights_status", "UNRESOLVED"),
        "source_weights_sha256": metadata.get("source_weights_sha256", "UNRESOLVED"),
        "model_id": metadata.get("model_id", "UNRESOLVED"),
        "config_id": metadata.get("config_id", "UNRESOLVED"),
        "dataset_version": metadata.get("dataset_version", "UNRESOLVED"),
    }


def prepare_openexplorer_bundle(
    repo_root: str | Path,
    *,
    source_onnx: str | Path,
    calibration_jsonl: str | Path,
    calibration_manifest: str | Path,
    output_directory: str | Path,
    limit: int | None = None,
    allow_smoke: bool = False,
    allow_candidate: bool = False,
) -> dict[str, Any]:
    """Write aligned NPY inputs, hb_compile YAML and an identity manifest."""
    repo = Path(repo_root).resolve()
    onnx_path = (repo / source_onnx).resolve() if not Path(source_onnx).is_absolute() else Path(source_onnx)
    jsonl_path = (
        (repo / calibration_jsonl).resolve()
        if not Path(calibration_jsonl).is_absolute()
        else Path(calibration_jsonl)
    )
    calibration_manifest_path = (
        (repo / calibration_manifest).resolve()
        if not Path(calibration_manifest).is_absolute()
        else Path(calibration_manifest)
    )
    output = (
        (repo / output_directory).resolve()
        if not Path(output_directory).is_absolute()
        else Path(output_directory)
    )
    if not onnx_path.is_file() or not calibration_manifest_path.is_file():
        raise FileNotFoundError("source ONNX and calibration manifest must exist")
    calibration_identity = json.loads(calibration_manifest_path.read_text(encoding="utf-8"))
    if not isinstance(calibration_identity, dict):
        raise ValueError("calibration manifest must be a JSON object")
    actual_jsonl_sha = sha256_file(jsonl_path)
    if calibration_identity.get("calibration_jsonl_sha256") != actual_jsonl_sha:
        raise ValueError("calibration JSONL SHA256 does not match its manifest")
    onnx_identity = _onnx_identity(onnx_path)
    formal = (
        onnx_identity["weights_status"] == "A3_FP32_GATE_PASSED"
        and calibration_identity.get("formal_release") is True
    )
    pending_candidate = onnx_identity["weights_status"] == "PENDING_A3_FP32_GATE"
    if pending_candidate and not allow_candidate:
        raise ValueError("pending A3 candidate requires explicit --allow-candidate")
    if not formal and not pending_candidate and not allow_smoke:
        raise ValueError(
            "formal OpenExplorer preparation requires A3_FP32_GATE_PASSED ONNX "
            "and a formal Calibration release; pass --allow-smoke only for development"
        )

    dataset = CalibrationDataset.open(repo, jsonl_path)
    declared_ids = calibration_identity.get("sample_ids")
    actual_ids = [str(item.get("sample_id", "")) for item in dataset.records]
    if declared_ids != actual_ids:
        raise ValueError("calibration sample order/identity does not match its manifest")
    available = len(dataset.records)
    if formal and not 300 <= available <= 500:
        raise ValueError("formal Calibration release must contain 300..500 samples")
    if formal and limit is not None and limit != available:
        raise ValueError("formal OpenExplorer preparation must use the complete Calibration release")
    sample_count = available if limit is None else min(limit, available)
    if sample_count < 1:
        raise ValueError("at least one calibration sample is required")
    calibration_root = output / "calibration_data"
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"OpenExplorer output directory must be empty: {output}")
    for name in INPUT_NAMES:
        (calibration_root / name).mkdir(parents=True, exist_ok=True)

    expected_shapes = StudentShapeContract().input_shapes
    samples: list[dict[str, Any]] = []
    for index, (record, feed) in enumerate(zip(dataset.records, dataset.feeds())):
        if index >= sample_count:
            break
        sample_id = str(record.get("sample_id", f"sample-{index:05d}"))
        safe_stem = f"{index:05d}_{hashlib.sha256(sample_id.encode('utf-8')).hexdigest()[:16]}"
        files: dict[str, Any] = {}
        for name in INPUT_NAMES:
            value = np.asarray(feed[name], dtype=np.float32)
            if value.shape != expected_shapes[name]:
                raise ValueError(f"calibration shape mismatch for {name}: {value.shape}")
            if not np.isfinite(value).all():
                raise ValueError(f"non-finite calibration tensor for {sample_id}/{name}")
            path = calibration_root / name / f"{safe_stem}.npy"
            np.save(path, value, allow_pickle=False)
            files[name] = {
                "path": path.relative_to(output).as_posix(),
                "sha256": sha256_file(path),
                "shape": list(value.shape),
                "dtype": str(value.dtype),
            }
        samples.append({"sample_id": sample_id, "files": files})

    onnx_for_yaml = Path(os.path.relpath(onnx_path, output))
    dirs = ";".join(f"./calibration_data/{name}" for name in INPUT_NAMES)
    shapes = ";".join("x".join(str(item) for item in expected_shapes[name]) for name in INPUT_NAMES)
    repeated = ";".join("featuremap" for _ in INPUT_NAMES)
    layouts = ";".join("NCHW" for _ in INPUT_NAMES)
    yaml_text = f"""# Generated by A2 for OpenExplorer {OPENEXPLORER_VERSION}; verify in the official image.
model_parameters:
  march: '{J6P_MARCH}'
  onnx_model: '{onnx_for_yaml.as_posix()}'
  output_model_file_prefix: 'student_v0_j6p'
  working_dir: './model_output'

input_parameters:
  input_name: '{';'.join(INPUT_NAMES)}'
  input_shape: '{shapes}'
  input_type_rt: '{repeated}'
  input_type_train: '{repeated}'
  input_layout_train: '{layouts}'

calibration_parameters:
  cal_data_dir: '{dirs}'

compiler_parameters:
  compile_mode: 'latency'
  core_num: 1
  optimize_level: 'O2'
  jobs: 8
  input_source:
    {{'rgb': 'ddr', 'text_tokens': 'ddr', 'targets': 'ddr', 'state': 'ddr'}}
"""
    config_path = output / "student_j6p_oe391.yaml"
    config_path.write_text(yaml_text, encoding="utf-8", newline="\n")
    manifest = {
        "schema_version": "1.0",
        "status": (
            "A2_OPENEXPLORER_FORMAL_INPUT_READY" if formal else
            "A3_CANDIDATE_OPENEXPLORER_INPUT_READY" if pending_candidate else "SMOKE_ONLY"
        ),
        "formal_release": formal,
        "toolchain": {
            "openexplorer_version": OPENEXPLORER_VERSION,
            "container": "openexplorer/ai_toolchain_ubuntu_22_j6_cpu:v3.9.1",
            "march": J6P_MARCH,
            "check_command": f"hb_compile --model {onnx_for_yaml.as_posix()} --march {J6P_MARCH}",
            "compile_command": f"hb_compile -c {config_path.name}",
        },
        "source_onnx": onnx_identity,
        "calibration": {
            "jsonl_sha256": actual_jsonl_sha,
            "manifest_sha256": sha256_file(calibration_manifest_path),
            "manifest_status": calibration_identity.get("status", "UNRESOLVED"),
            "sample_count": len(samples),
        },
        "config": {"path": config_path.name, "sha256": sha256_file(config_path)},
        "samples": samples,
        "notes": [
            "ORT QDQ output is diagnostic only; hb_compile consumes the FP32 ONNX.",
            "The YAML must pass OpenExplorer verification before any J6P compatibility claim.",
        ],
    }
    _write_json(output / "openexplorer_input_manifest.json", manifest)
    return manifest


__all__ = [
    "INPUT_NAMES", "J6P_MARCH", "OPENEXPLORER_VERSION", "prepare_openexplorer_bundle",
]
