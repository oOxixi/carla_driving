"""Frozen, reviewable configuration for the A2 PTQ workflow.

The checked-in ``.yaml`` file deliberately uses JSON syntax.  JSON is a strict
subset of YAML, which keeps the configuration consumable by OpenExplorer users
without adding a YAML parser to the reproducible Python environment.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .calibration import sha256_file


DEFAULT_QUANT_CONFIG = Path(__file__).with_name("config") / "ptq_int8_v1.yaml"
SUPPORTED_SCHEMA_VERSION = "1.0"


def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"quant config field {field} must be an object")
    return value


def load_quant_config(path: str | Path = DEFAULT_QUANT_CONFIG) -> dict[str, Any]:
    """Load and fail-closed validate the frozen PTQ configuration."""
    config_path = Path(path)
    try:
        value = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(
            "quant config must use JSON-compatible YAML syntax"
        ) from error
    if not isinstance(value, dict):
        raise ValueError("quant config must contain an object")
    if value.get("schema_version") != SUPPORTED_SCHEMA_VERSION:
        raise ValueError("unsupported quant config schema_version")
    config_id = value.get("config_id")
    if not isinstance(config_id, str) or not config_id.strip():
        raise ValueError("quant config config_id must be a non-empty string")

    backend = _mapping(value.get("backend"), "backend")
    if backend.get("framework") != "onnxruntime":
        raise ValueError("only the reviewed onnxruntime PTQ backend is supported")
    if backend.get("quant_format") != "QDQ":
        raise ValueError("only QDQ quant_format is supported")

    activations = _mapping(value.get("activations"), "activations")
    weights = _mapping(value.get("weights"), "weights")
    calibration = _mapping(value.get("calibration"), "calibration")
    for name, section in (("activations", activations), ("weights", weights)):
        if section.get("dtype") != "QInt8" or section.get("bits") != 8:
            raise ValueError(f"{name} must use signed QInt8/8-bit")
    if weights.get("granularity") not in {"per_channel", "per_tensor"}:
        raise ValueError("weights.granularity must be per_channel or per_tensor")
    if activations.get("granularity") != "per_tensor":
        raise ValueError("activations.granularity must be per_tensor")
    if calibration.get("method") not in {"MinMax", "Entropy", "Percentile"}:
        raise ValueError("unsupported calibration.method")

    options = _mapping(value.get("options"), "options")
    excluded = options.get("excluded_nodes", [])
    if not isinstance(excluded, list) or not all(isinstance(item, str) for item in excluded):
        raise ValueError("options.excluded_nodes must be a list of node names")
    sensitivity = _mapping(value.get("sensitivity"), "sensitivity")
    op_types = sensitivity.get("candidate_op_types")
    if not isinstance(op_types, list) or not op_types or not all(
        isinstance(item, str) and item for item in op_types
    ):
        raise ValueError("sensitivity.candidate_op_types must be a non-empty list")
    return value


def quant_config_identity(path: str | Path = DEFAULT_QUANT_CONFIG) -> dict[str, Any]:
    config_path = Path(path)
    config = load_quant_config(config_path)
    return {
        "path": str(config_path),
        "sha256": sha256_file(config_path),
        "config_id": config["config_id"],
        "schema_version": config["schema_version"],
    }


__all__ = [
    "DEFAULT_QUANT_CONFIG",
    "load_quant_config",
    "quant_config_identity",
]
