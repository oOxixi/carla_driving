"""Decide whether two FP32 ONNX exports of the same weights are interchangeable.

The submission ledger carries an open item: A2's export is
``681a5d4b...`` while B3's export of the same weights is ``b76b5a32...``.  The
repository exporter stamps provenance strings into ``metadata_props`` (for
example ``source_git_sha``, which defaults to the exporting checkout's HEAD) and
``producer_version`` records the torch version, so two teams exporting the same
``state_dict`` legitimately produce different bytes for the same graph.  The
round asks A4/B3 to "resolve the ONNX identity difference"; this tool answers
the question that actually matters:

* are the file bytes identical?
* if not, is the difference confined to provenance metadata (are the weights
  and the graph the same)?
* do the two files decode to the same numerics on frozen inputs?

Usage:
    python3 onnx_export_equivalence.py --left <a.onnx> --right <b.onnx> \
        [--dumps <dump_dir> --frozen <snapshot_dir> --limit N] [--out <json>]
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import onnx


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tensor_sha(tensor) -> str:
    payload = tensor.raw_data if tensor.raw_data else b""
    return hashlib.sha256(payload).hexdigest()


def _canonical_graph(model: onnx.ModelProto) -> dict:
    nodes = []
    for node in model.graph.node:
        attributes = {}
        for attribute in node.attribute:
            if attribute.type == onnx.AttributeProto.INT:
                attributes[attribute.name] = int(attribute.i)
            elif attribute.type == onnx.AttributeProto.FLOAT:
                attributes[attribute.name] = float(attribute.f)
            elif attribute.type == onnx.AttributeProto.STRING:
                attributes[attribute.name] = attribute.s.decode("utf-8", "replace")
            elif attribute.type == onnx.AttributeProto.INTS:
                attributes[attribute.name] = list(attribute.ints)
            else:
                attributes[attribute.name] = f"<{attribute.type}>"
        nodes.append({
            "op": node.op_type,
            "inputs": list(node.input),
            "outputs": list(node.output),
            "attributes": attributes,
        })
    digest = hashlib.sha256(
        json.dumps(nodes, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {"node_count": len(nodes), "topology_digest": digest}


def describe(path: Path) -> dict:
    model = onnx.load(str(path))
    metadata = {item.key: item.value for item in model.metadata_props}
    initializers = {
        tensor.name: {
            "sha256": _tensor_sha(tensor),
            "dims": list(tensor.dims),
            "dtype": int(tensor.data_type),
        }
        for tensor in model.graph.initializer
    }
    weights_digest = hashlib.sha256(
        json.dumps(initializers, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "path": str(path),
        "sha256": _file_sha(path),
        "size_bytes": path.stat().st_size,
        "ir_version": model.ir_version,
        "producer_name": model.producer_name,
        "producer_version": model.producer_version,
        "opset_imports": [f"{item.domain or 'ai.onnx'}:{item.version}" for item in model.opset_import],
        "metadata_props": metadata,
        "graph": _canonical_graph(model),
        "initializer_count": len(initializers),
        "initializer_digest": weights_digest,
        "initializers": initializers,
        "inputs": [
            {"name": value.name, "shape": [
                dimension.dim_value for dimension in value.type.tensor_type.shape.dim
            ]} for value in model.graph.input
        ],
        "outputs": [value.name for value in model.graph.output],
    }


def numeric_equivalence(left: Path, right: Path, dumps: Path, frozen: Path, limit: int) -> dict:
    import onnxruntime as ort

    left_session = ort.InferenceSession(str(left), providers=["CPUExecutionProvider"])
    right_session = ort.InferenceSession(str(right), providers=["CPUExecutionProvider"])
    inputs = [item.name for item in left_session.get_inputs()]
    assert inputs == [item.name for item in right_session.get_inputs()], "input name mismatch"
    outputs = [item.name for item in left_session.get_outputs()]
    assert outputs == [item.name for item in right_session.get_outputs()], "output name mismatch"

    index = json.loads((dumps / "dump_index.json").read_text(encoding="utf-8"))["dumps"]
    if limit:
        index = index[:limit]

    stats = {name: {"max_abs": 0.0, "argmax_agree": 0, "compared": 0} for name in outputs}
    cases = 0
    for entry in index:
        directory = Path(entry["directory"])
        feed = {name: np.load(directory / f"{name}.npy").astype(np.float32) for name in inputs}
        left_values = left_session.run(outputs, feed)
        right_values = right_session.run(outputs, feed)
        cases += 1
        for name, a, b in zip(outputs, left_values, right_values):
            row = stats[name]
            difference = float(np.max(np.abs(a.astype(np.float64) - b.astype(np.float64))))
            row["max_abs"] = max(row["max_abs"], difference)
            row["argmax_agree"] += int(
                np.argmax(np.asarray(a).reshape(-1)) == np.argmax(np.asarray(b).reshape(-1))
            )
            row["compared"] += 1
    return {
        "cases": cases,
        "per_output": {
            name: {
                "max_abs_diff": row["max_abs"],
                "argmax_agreement": f"{row['argmax_agree']}/{row['compared']}",
            }
            for name, row in stats.items()
        },
        "worst_max_abs_diff": max(row["max_abs"] for row in stats.values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--left", required=True)
    parser.add_argument("--right", required=True)
    parser.add_argument("--dumps")
    parser.add_argument("--frozen")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--out")
    args = parser.parse_args()

    left_path, right_path = Path(args.left), Path(args.right)
    left, right = describe(left_path), describe(right_path)
    byte_identical = left["sha256"] == right["sha256"]

    metadata_only = [key for key in set(left["metadata_props"]) | set(right["metadata_props"])
                     if left["metadata_props"].get(key) != right["metadata_props"].get(key)]
    initializer_diff = sorted(
        name for name in set(left["initializers"]) | set(right["initializers"])
        if left["initializers"].get(name) != right["initializers"].get(name)
    )
    report: dict = {
        "left": {key: value for key, value in left.items() if key != "initializers"},
        "right": {key: value for key, value in right.items() if key != "initializers"},
        "byte_identical": byte_identical,
        "metadata_props_changed": metadata_only,
        "graph_topology_identical": (
            left["graph"]["topology_digest"] == right["graph"]["topology_digest"]
        ),
        "initializer_digest_identical": left["initializer_digest"] == right["initializer_digest"],
        "initializers_changed": initializer_diff,
    }

    if args.dumps and args.frozen:
        report["numeric_equivalence"] = numeric_equivalence(
            left_path, right_path, Path(args.dumps), Path(args.frozen), args.limit,
        )
        worst = report["numeric_equivalence"]["worst_max_abs_diff"]
        if byte_identical:
            verdict = "BYTE_IDENTICAL"
        elif (not initializer_diff and report["graph_topology_identical"]
              and worst <= 1e-6):
            verdict = "METADATA_ONLY_DIFFERENCE_NUMERICALLY_IDENTICAL"
        else:
            verdict = "DIFFERS_BEYOND_METADATA"
    else:
        if byte_identical:
            verdict = "BYTE_IDENTICAL"
        elif not initializer_diff and report["graph_topology_identical"]:
            verdict = "METADATA_AND_TOPOLOGY_IDENTICAL_NUMERICS_NOT_RUN"
        else:
            verdict = "DIFFERS_BEYOND_METADATA"
    report["verdict"] = verdict
    report["reading"] = (
        "the repository exporter stamps provenance (source_git_sha, producer_version, ...) "
        "into metadata_props, so two exports of the same state_dict are not byte-reproducible; "
        "the release candidate therefore has to pin one artifact and prove the other "
        "equivalent on weights, topology and numerics"
    )

    print(json.dumps(report, indent=2, ensure_ascii=False))
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
