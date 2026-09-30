from __future__ import annotations

import json
from pathlib import Path

import onnx
from onnx import TensorProto, helper
import pytest

from challenge.quantization.calibration import load_formal_calibration_v1
from challenge.quantization.config import DEFAULT_QUANT_CONFIG, load_quant_config
from challenge.quantization.ptq import quantize_qdq
from challenge.quantization.sensitivity import discover_candidate_nodes
from challenge.quantization.manifest import bind_b2_gate_result, validate_int8_manifest


REPO = Path(__file__).resolve().parents[3]


def _tiny_model(path: Path, *, status: str = "A3_FP32_GATE_PASSED") -> None:
    state = helper.make_tensor_value_info("state", TensorProto.FLOAT, [1, 4])
    output = helper.make_tensor_value_info("output", TensorProto.FLOAT, [1, 4])
    weight = helper.make_tensor("weight", TensorProto.FLOAT, [4, 4], [1.0] * 16)
    graph = helper.make_graph(
        [helper.make_node("MatMul", ["state", "weight"], ["output"], name="fusion.matmul")],
        "tiny", [state], [output], [weight],
    )
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 17)])
    helper.set_model_props(model, {
        "weights_status": status,
        "model_id": "unit",
        "config_id": "unit",
        "dataset_version": "unit",
        "source_weights_sha256": "1" * 64,
    })
    onnx.save(model, path)


def test_frozen_calibration_v1_is_the_only_formal_release() -> None:
    release = load_formal_calibration_v1(REPO)
    assert release.identity["status"] == "VERIFIED_FROZEN_CALIBRATION"
    assert release.identity["sample_count"] == 300
    assert release.identity["group_count"] == 300
    governance = release.identity["governance_validation"]
    assert governance["valid"] is True
    assert governance["train_sample_overlap"] == 0
    assert governance["dev_sample_overlap"] == 0


def test_quant_config_is_frozen_and_reviewable() -> None:
    config = load_quant_config(DEFAULT_QUANT_CONFIG)
    assert config["backend"]["quant_format"] == "QDQ"
    assert config["weights"]["granularity"] == "per_channel"
    assert config["calibration"]["release"] == "b1_calibration_v1"


def test_sensitive_node_discovery_uses_real_node_names(tmp_path: Path) -> None:
    model = tmp_path / "tiny.onnx"
    _tiny_model(model)
    assert discover_candidate_nodes(model, op_types=["MatMul"]) == [{
        "name": "fusion.matmul", "op_type": "MatMul", "index": "0",
    }]


def test_formal_ptq_rejects_noncanonical_calibration_before_quantizing(tmp_path: Path) -> None:
    model = tmp_path / "tiny.onnx"
    _tiny_model(model)
    calibration = tmp_path / "calibration.jsonl"
    calibration.write_text("{}\n", encoding="utf-8")
    manifest = tmp_path / "calibration_manifest.json"
    manifest.write_text(json.dumps({"status": "FROZEN_CALIBRATION"}), encoding="utf-8")
    with pytest.raises(ValueError, match="must use challenge/dataset/releases/calibration_v1"):
        quantize_qdq(
            REPO,
            source_onnx=model,
            calibration_jsonl=calibration,
            calibration_manifest=manifest,
            output_onnx=tmp_path / "student_int8.onnx",
            quant_config=DEFAULT_QUANT_CONFIG,
        )


def test_b2_result_binding_is_identity_bound(tmp_path: Path) -> None:
    import hashlib

    artifact = tmp_path / "student_int8.onnx"
    artifact.write_bytes(b"int8-unit")
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    manifest = {
        "quantization_id": "a2-ptq-unit",
        "git_sha": "1" * 40,
        "source_fp32_weights_sha256": "2" * 64,
        "source_fp32_onnx_sha256": "3" * 64,
        "calibration_manifest_sha256": "4" * 64,
        "quant_config_sha256": "5" * 64,
        "int8_artifact_sha256": digest,
        "model_id": "student-unit",
        "config_id": "config-unit",
        "dataset_version": "dataset-unit",
        "gate_status": "PENDING_B2_INT8_GATE",
        "B2_result": {"status": "PENDING_B2_INT8_GATE"},
    }
    manifest_path = tmp_path / "int8_manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    validate_int8_manifest(manifest)

    decision = {
        "gate_status": "A2_INT8_GATE_PASSED",
        "quantization_id": "a2-ptq-unit",
        "int8_artifact_sha256": digest,
        "benchmark_manifest_sha256": "6" * 64,
        "policy_manifest_sha256": "7" * 64,
    }
    decision_path = tmp_path / "decision.json"
    decision_path.write_text(json.dumps(decision), encoding="utf-8")
    result = bind_b2_gate_result(
        int8_manifest=manifest_path,
        int8_artifact=artifact,
        b2_decision=decision_path,
    )
    assert result["gate_status"] == "A2_INT8_GATE_PASSED"
    assert result["B2_result"]["decision_manifest_sha256"]
