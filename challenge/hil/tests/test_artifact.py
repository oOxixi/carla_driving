from __future__ import annotations

import json
from pathlib import Path

import pytest

from ..artifact import FORBIDDEN_OPS, verify_onnx_artifact
from ..identity import sha256_file
from ..runtime_adapter import AdapterError


onnx = pytest.importorskip("onnx")


def _build_model(path: Path, *, dynamic: bool = False) -> None:
    from onnx import TensorProto, helper, numpy_helper
    import numpy as np

    weights = numpy_helper.from_array(
        np.zeros((3,), dtype=np.float32), name="w"
    )
    node = helper.make_node("Add", ["input", "w"], ["output"], name="n")
    outputs = [helper.make_tensor_value_info("output", TensorProto.FLOAT, [1, 3])]
    extra_ops = []
    if dynamic:
        extra_ops.append(helper.make_node("Shape", ["input"], ["shape_out"], name="shape"))
        outputs.append(
            helper.make_tensor_value_info("shape_out", TensorProto.INT64, [1])
        )
    graph = helper.make_graph(
        [node, *extra_ops],
        "g",
        [helper.make_tensor_value_info("input", TensorProto.FLOAT, [1, 3])],
        outputs,
        [weights],
    )
    model = helper.make_model(
        graph, opset_imports=[helper.make_opsetid("", 17)], ir_version=8
    )
    model.metadata_props.add(key="model_id", value="test-model")
    model.metadata_props.add(key="config_id", value="cfg")
    onnx.save(model, str(path))


def test_artifact_passes_for_a_fixed_shape_model(tmp_path: Path):
    path = tmp_path / "m.onnx"
    _build_model(path)
    report = verify_onnx_artifact(path)
    assert report["passed"] is True
    assert report["failed"] == []
    assert report["sha256"] == sha256_file(path)
    assert "Add" in report["operators"]
    assert report["opset"] == {"ai.onnx": 17}


def test_artifact_flags_board_hostile_operators(tmp_path: Path):
    path = tmp_path / "m.onnx"
    _build_model(path, dynamic=True)
    report = verify_onnx_artifact(path)
    assert report["passed"] is False
    assert "Shape" in report["forbidden_operators"]
    assert "no_board_hostile_operators" in report["failed"]
    assert FORBIDDEN_OPS.issuperset({"Shape", "Loop"})


def test_artifact_flags_an_unexpected_opset(tmp_path: Path):
    path = tmp_path / "m.onnx"
    _build_model(path)
    report = verify_onnx_artifact(path, expected_opset=15)
    assert report["passed"] is False
    assert "opset" in report["failed"]


def test_artifact_cross_checks_the_producer_structure(tmp_path: Path):
    path = tmp_path / "m.onnx"
    _build_model(path)
    structure = tmp_path / "model_structure.json"
    structure.write_text(
        json.dumps(
            {
                "artifact_sha256": sha256_file(path),
                "onnx_operators": ["Add"],
            }
        ),
        encoding="utf-8",
    )
    report = verify_onnx_artifact(path, reference_structure=structure)
    assert report["passed"] is True

    structure.write_text(
        json.dumps({"artifact_sha256": "0" * 64, "onnx_operators": ["Add"]}),
        encoding="utf-8",
    )
    report = verify_onnx_artifact(path, reference_structure=structure)
    assert report["passed"] is False
    assert "structure_sha256_matches" in report["failed"]


def test_artifact_reports_operator_set_drift(tmp_path: Path):
    path = tmp_path / "m.onnx"
    _build_model(path)
    structure = tmp_path / "model_structure.json"
    structure.write_text(
        json.dumps(
            {
                "artifact_sha256": sha256_file(path),
                "onnx_operators": ["Add", "Relu"],
            }
        ),
        encoding="utf-8",
    )
    report = verify_onnx_artifact(path, reference_structure=structure)
    assert report["passed"] is False
    assert "structure_operator_set_matches" in report["failed"]


def test_artifact_missing_file_is_an_adapter_error(tmp_path: Path):
    with pytest.raises(AdapterError):
        verify_onnx_artifact(tmp_path / "nope.onnx")
