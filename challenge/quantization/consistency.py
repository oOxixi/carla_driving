"""Verify that a weight-backed PyTorch Student matches its exported ONNX."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

import numpy as np
import torch

from challenge.export.export_onnx import _load_verified_weights
from challenge.student.contract import OUTPUT_NAMES
from challenge.student.model import StudentPlannerV0

from .calibration import CalibrationDataset, sha256_file


def verify_export_consistency(
    repo_root: str | Path,
    *,
    weights: str | Path,
    weights_manifest: str | Path,
    onnx_model: str | Path,
    jsonl_path: str | Path,
    output_json: str | Path,
    limit: int = 20,
    atol: float = 1e-4,
    rtol: float = 1e-4,
    allow_pending_candidate: bool = False,
) -> dict[str, Any]:
    """Compare all ten raw heads on real preprocessed samples."""
    import onnxruntime as ort

    repo = Path(repo_root).absolute()
    def rooted(value: str | Path) -> Path:
        path = Path(value)
        return path if path.is_absolute() else (repo / path).absolute()

    weights_path = rooted(weights)
    manifest_path = rooted(weights_manifest)
    onnx_path = rooted(onnx_model)
    model = StudentPlannerV0().eval()
    identity = _load_verified_weights(
        model,
        weights=weights_path,
        weights_manifest=manifest_path,
        allow_pending_candidate=allow_pending_candidate,
    )
    session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    output_names = [item.name for item in session.get_outputs()]
    if output_names != list(OUTPUT_NAMES):
        raise ValueError(f"ONNX output order mismatch: {output_names}")
    metadata = dict(session.get_modelmeta().custom_metadata_map)
    if metadata.get("source_weights_sha256") != identity["source_weights_sha256"]:
        raise ValueError("ONNX source weight SHA256 does not match the supplied weights")

    dataset = CalibrationDataset.open(repo, jsonl_path)
    absolute: dict[str, list[np.ndarray]] = defaultdict(list)
    all_close = True
    request_count = 0
    with torch.no_grad():
        for index, feed in enumerate(dataset.feeds()):
            if index >= limit:
                break
            torch_feed = {name: torch.from_numpy(value) for name, value in feed.items()}
            expected = model(**torch_feed)
            actual = session.run(None, feed)
            request_count += 1
            for name, value in zip(output_names, actual, strict=True):
                left = expected[name].detach().cpu().numpy().astype(np.float32, copy=False)
                right = np.asarray(value, dtype=np.float32)
                if left.shape != right.shape:
                    raise ValueError(f"{name} shape mismatch: {left.shape} != {right.shape}")
                absolute[name].append(np.abs(left - right).reshape(-1))
                all_close = all_close and bool(np.allclose(left, right, atol=atol, rtol=rtol))
    if request_count == 0:
        raise ValueError("at least one consistency sample is required")

    per_head: dict[str, Any] = {}
    for name in output_names:
        values = np.concatenate(absolute[name])
        per_head[name] = {
            "mean_abs_error": float(values.mean()),
            "max_abs_error": float(values.max()),
        }
    report = {
        "schema_version": "1.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if all_close else "FAIL",
        "scope": "PyTorch state_dict versus exported FP32 ONNX raw outputs",
        "weights_status": identity["weights_status"],
        "weights_sha256": identity["source_weights_sha256"],
        "onnx_sha256": sha256_file(onnx_path),
        "dataset": {"path": str(jsonl_path), "request_count": request_count},
        "tolerance": {"atol": atol, "rtol": rtol},
        "per_head": per_head,
        "global_max_abs_error": max(item["max_abs_error"] for item in per_head.values()),
    }
    output = rooted(output_json)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not all_close:
        raise RuntimeError(f"PyTorch/ONNX consistency failed; see {output}")
    return report


__all__ = ["verify_export_consistency"]
