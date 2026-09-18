"""Independent verification of a model artifact (FP32 or INT8 ONNX).

A1 already validates its own structure export; that check is written by the
producer.  This one is B3's own, and it is written so the same code applies to
whatever A2 later delivers: opset, forbidden operators, input/output contract,
embedded metadata, and the file digest.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from .identity import sha256_file
from .runtime_adapter import AdapterError, _RepoModules


# Operators that introduce dynamic shapes/control flow or are known to be
# awkward on a fixed-shape board compiler.  Presence is a failure, not a note.
FORBIDDEN_OPS: frozenset[str] = frozenset(
    {"Shape", "NonZero", "Scatter", "ScatterND", "Loop", "If", "TopK", "NonMaxSuppression"}
)


def _shape_of(value: Any) -> list[int]:
    return [int(dimension.dim_value) for dimension in value.type.tensor_type.shape.dim]


def verify_onnx_artifact(
    onnx_path: str | Path,
    *,
    repo_root: str | Path | None = None,
    reference_structure: str | Path | None = None,
    expected_opset: int | None = 17,
) -> dict[str, Any]:
    path = Path(onnx_path).resolve()
    if not path.is_file():
        raise AdapterError(f"artifact not found: {path}")
    try:
        import onnx
    except ImportError as error:  # pragma: no cover - dependency guard
        raise AdapterError("onnx is required for artifact verification") from error

    checks: list[dict[str, str]] = []

    def check(name: str, passed: bool, detail: str, *, fatal: bool = True) -> None:
        status = "PASS" if passed else ("FAIL" if fatal else "WARN")
        checks.append({"check": name, "status": status, "detail": detail})

    graph = onnx.load(str(path))
    digest = sha256_file(path)
    try:
        onnx.checker.check_model(graph)
        check("onnx_checker", True, "model passes the ONNX checker")
    except Exception as error:
        check("onnx_checker", False, f"{type(error).__name__}: {error}")

    opsets = {item.domain or "ai.onnx": int(item.version) for item in graph.opset_import}
    default_opset = opsets.get("ai.onnx")
    if expected_opset is None:
        check("opset", True, f"opset={default_opset} (not pinned)")
    else:
        check(
            "opset",
            default_opset == expected_opset,
            f"opset={default_opset}, expected {expected_opset}",
        )
    check("ir_version", True, f"ir_version={graph.ir_version}", fatal=False)

    inputs = {value.name: _shape_of(value) for value in graph.graph.input}
    outputs = [value.name for value in graph.graph.output]
    operators = sorted({node.op_type for node in graph.graph.node})
    forbidden = sorted(FORBIDDEN_OPS.intersection(operators))
    check(
        "no_board_hostile_operators",
        not forbidden,
        f"forbidden={forbidden}" if forbidden else "no dynamic-shape/control-flow operators",
    )
    check(
        "single_batch_fixed_shape",
        all(
            shape[:1] == [1] and all(dimension > 0 for dimension in shape)
            for shape in inputs.values()
        ),
        f"inputs={inputs}",
    )

    metadata = {item.key: item.value for item in graph.metadata_props}
    if repo_root is not None:
        modules = _RepoModules(repo_root)
        contract = modules.get("challenge.student.contract.StudentShapeContract")()
        output_names = list(modules.get("challenge.student.contract.OUTPUT_NAMES"))
        expected_inputs = {
            name: list(shape) for name, shape in contract.input_shapes.items()
        }
        check(
            "input_contract",
            inputs == expected_inputs,
            f"{inputs} vs expected {expected_inputs}",
        )
        check(
            "output_order",
            outputs == output_names,
            "output order matches OUTPUT_NAMES"
            if outputs == output_names
            else f"{outputs} vs expected {output_names}",
        )
    check(
        "metadata_present",
        all(key in metadata for key in ("model_id", "config_id")),
        f"metadata keys={sorted(metadata)}",
        fatal=False,
    )

    reference = None
    if reference_structure is not None:
        reference = json.loads(
            Path(reference_structure).read_text(encoding="utf-8")
        )
        check(
            "structure_sha256_matches",
            reference.get("artifact_sha256") == digest,
            f"{digest} vs {reference.get('artifact_sha256')}",
        )
        check(
            "structure_operator_set_matches",
            reference.get("onnx_operators") == operators,
            "operator set matches the producer report"
            if reference.get("onnx_operators") == operators
            else f"{operators} vs {reference.get('onnx_operators')}",
        )

    initializers = list(graph.graph.initializer)
    initializer_bytes = sum(len(item.raw_data) for item in initializers)
    failures = [item for item in checks if item["status"] == "FAIL"]
    warnings = [item for item in checks if item["status"] == "WARN"]
    return {
        "schema_version": "1.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "path": str(path),
        "sha256": digest,
        "size_bytes": path.stat().st_size,
        "ir_version": graph.ir_version,
        "opset": opsets,
        "producer": graph.producer_name,
        "inputs": inputs,
        "outputs": outputs,
        "operators": operators,
        "forbidden_operators": forbidden,
        "metadata": metadata,
        "reference_structure": (
            str(reference_structure) if reference_structure else None
        ),
        "initializer_count": len(initializers),
        "initializer_bytes": initializer_bytes,
        "checks": checks,
        "failed": [item["check"] for item in failures],
        "warned": [item["check"] for item in warnings],
        "passed": not failures,
        "scope_note": (
            "Structural and contract verification only. A pass says nothing about "
            "accuracy, latency, or board deployability; it only rules out the "
            "cheap, silent failure modes."
        ),
    }


__all__ = ["verify_onnx_artifact", "FORBIDDEN_OPS"]
