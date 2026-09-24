from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import onnx
from onnx import TensorProto, helper
from PIL import Image
import pytest

from challenge.quantization.calibration import build_development_calibration
from challenge.quantization.openexplorer import prepare_openexplorer_bundle
from challenge.student.contract import StudentShapeContract


def _record(rgb: Path) -> dict[str, object]:
    import hashlib

    return {
        "sample_id": "oe-sample-001",
        "sample_class": "NORMAL",
        "model_request": {
            "rgb_ref": rgb.name,
            "source_text": "保持车道",
            "targets": [],
            "scene_summary": {
                "traffic_light": "GREEN", "risk_level": "LOW", "min_gap_m": 20.0, "ttc_s": 8.0,
            },
            "constraints": {
                "speed_limit_mps": 10.0, "max_target_speed_mps": 8.0,
                "must_stop": False, "allowed_behaviors": ["KEEP_LANE"],
            },
        },
        "teacher_plan": {"steps": [{"behavior": "KEEP_LANE"}]},
        "visual_input": {"rgb_sha256": hashlib.sha256(rgb.read_bytes()).hexdigest()},
        "metadata": {"scenario_family": "unit"},
    }


def _onnx(path: Path, weights_status: str = "random_initialization_for_export_smoke_only") -> None:
    contract = StudentShapeContract()
    inputs = [
        helper.make_tensor_value_info(name, TensorProto.FLOAT, list(shape))
        for name, shape in contract.input_shapes.items()
    ]
    outputs = [helper.make_tensor_value_info("rgb_out", TensorProto.FLOAT, list(contract.input_shapes["rgb"]))]
    graph = helper.make_graph([helper.make_node("Identity", ["rgb"], ["rgb_out"])], "student", inputs, outputs)
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 17)])
    helper.set_model_props(model, {"weights_status": weights_status})
    onnx.save(model, path)


def test_prepare_openexplorer_bundle_exports_aligned_inputs(tmp_path: Path) -> None:
    rgb = tmp_path / "rgb.png"
    Image.new("RGB", (16, 8), (20, 40, 60)).save(rgb)
    source = tmp_path / "train.jsonl"
    source.write_text(json.dumps(_record(rgb), ensure_ascii=False) + "\n", encoding="utf-8")
    build_development_calibration(
        tmp_path, source_jsonl=source, output_directory="cal", count=1, seed=1,
    )
    model = tmp_path / "student.onnx"
    _onnx(model)

    result = prepare_openexplorer_bundle(
        tmp_path,
        source_onnx=model,
        calibration_jsonl="cal/calibration.jsonl",
        calibration_manifest="cal/calibration_manifest.json",
        output_directory="oe",
        allow_smoke=True,
    )

    assert result["status"] == "SMOKE_ONLY"
    assert result["toolchain"]["march"] == "nash-p"
    yaml_text = (tmp_path / "oe/student_j6p_oe391.yaml").read_text(encoding="utf-8")
    assert "input_name: 'rgb;text_tokens;targets;state'" in yaml_text
    assert "march: 'nash-p'" in yaml_text
    expected = StudentShapeContract().input_shapes
    for name, shape in expected.items():
        files = list((tmp_path / "oe/calibration_data" / name).glob("*.npy"))
        assert len(files) == 1
        value = np.load(files[0], allow_pickle=False)
        assert value.dtype == np.float32
        assert value.shape == shape


def test_prepare_openexplorer_rejects_nonformal_by_default(tmp_path: Path) -> None:
    rgb = tmp_path / "rgb.png"
    Image.new("RGB", (4, 4)).save(rgb)
    source = tmp_path / "train.jsonl"
    source.write_text(json.dumps(_record(rgb), ensure_ascii=False) + "\n", encoding="utf-8")
    build_development_calibration(tmp_path, source_jsonl=source, output_directory="cal", count=1)
    model = tmp_path / "student.onnx"
    _onnx(model)
    with pytest.raises(ValueError, match="A3_FP32_GATE_PASSED"):
        prepare_openexplorer_bundle(
            tmp_path,
            source_onnx=model,
            calibration_jsonl="cal/calibration.jsonl",
            calibration_manifest="cal/calibration_manifest.json",
            output_directory="oe",
        )


def test_pending_candidate_requires_explicit_candidate_mode(tmp_path: Path) -> None:
    rgb = tmp_path / "rgb.png"
    Image.new("RGB", (4, 4)).save(rgb)
    source = tmp_path / "train.jsonl"
    source.write_text(json.dumps(_record(rgb), ensure_ascii=False) + "\n", encoding="utf-8")
    build_development_calibration(tmp_path, source_jsonl=source, output_directory="cal", count=1)
    model = tmp_path / "student.onnx"
    _onnx(model, "PENDING_A3_FP32_GATE")
    with pytest.raises(ValueError, match="--allow-candidate"):
        prepare_openexplorer_bundle(
            tmp_path, source_onnx=model,
            calibration_jsonl="cal/calibration.jsonl",
            calibration_manifest="cal/calibration_manifest.json",
            output_directory="rejected",
        )
    result = prepare_openexplorer_bundle(
        tmp_path, source_onnx=model,
        calibration_jsonl="cal/calibration.jsonl",
        calibration_manifest="cal/calibration_manifest.json",
        output_directory="accepted", allow_candidate=True,
    )
    assert result["status"] == "A3_CANDIDATE_OPENEXPLORER_INPUT_READY"
