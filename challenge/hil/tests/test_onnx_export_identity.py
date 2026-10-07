"""Identity comparison for two ONNX exports of the same graph.

The submission ledger asks A4/B3 to resolve "A2's ONNX bytes differ from B3's".
These tests pin the property the resolution relies on: provenance metadata can
differ (so the file SHA differs) while the weights, the topology and the
numerics stay identical.
"""
from __future__ import annotations

import numpy as np
import onnx
from onnx import TensorProto, helper, numpy_helper

from ..harness.x86_sim.onnx_export_equivalence import describe, numeric_equivalence


def _build(path, git_sha: str) -> None:
    weight = numpy_helper.from_array(np.arange(6, dtype=np.float32).reshape(2, 3), name="w")
    node = helper.make_node("MatMul", ["x", "w"], ["y"], name="matmul")
    graph = helper.make_graph(
        [node],
        "tiny",
        [helper.make_tensor_value_info("x", TensorProto.FLOAT, [1, 2])],
        [helper.make_tensor_value_info("y", TensorProto.FLOAT, [1, 3])],
        [weight],
    )
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 17)])
    model.producer_name = "pytorch"
    model.producer_version = "2.6.0"
    helper.set_model_props(model, {"source_git_sha": git_sha, "export_seed": "20260911"})
    onnx.checker.check_model(model)
    onnx.save(model, str(path))


def test_provenance_change_keeps_weights_and_topology(tmp_path) -> None:
    left, right = tmp_path / "left.onnx", tmp_path / "right.onnx"
    _build(left, "a" * 40)
    _build(right, "b" * 40)

    left_report, right_report = describe(left), describe(right)
    assert left_report["sha256"] != right_report["sha256"]
    assert left_report["size_bytes"] == right_report["size_bytes"]
    assert left_report["initializer_digest"] == right_report["initializer_digest"]
    assert left_report["graph"]["topology_digest"] == right_report["graph"]["topology_digest"]
    assert left_report["metadata_props"]["source_git_sha"] != right_report["metadata_props"]["source_git_sha"]


def test_numeric_equivalence_is_bit_identical_for_metadata_only_change(tmp_path) -> None:
    left, right = tmp_path / "left.onnx", tmp_path / "right.onnx"
    _build(left, "a" * 40)
    _build(right, "b" * 40)
    dumps = tmp_path / "dumps"
    case = dumps / "case_0000"
    case.mkdir(parents=True)
    np.save(case / "x.npy", np.ones((1, 2), dtype=np.float32))
    (dumps / "dump_index.json").write_text(
        '{"dumps": [{"case_id": "c0", "directory": "%s"}]}' % str(case).replace("\\", "\\\\"),
        encoding="utf-8",
    )

    result = numeric_equivalence(left, right, dumps, tmp_path, limit=1)
    assert result["cases"] == 1
    assert result["worst_max_abs_diff"] == 0.0
    assert result["per_output"]["y"]["argmax_agreement"] == "1/1"
