"""Per-head FP32 versus INT8 raw-output drift analysis."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

import numpy as np

from .calibration import CalibrationDataset, sha256_file


DISCRETE_HEADS = {
    "plan_length_logits",
    "behavior_logits",
    "target_pointer_logits",
    "target_lane_logits",
    "completion_type_logits",
    "on_failure_logits",
}


def analyze_drift(
    repo_root: str | Path,
    *,
    baseline_onnx: str | Path,
    candidate_onnx: str | Path,
    jsonl_path: str | Path,
    output_json: str | Path,
    limit: int | None = 100,
) -> dict[str, Any]:
    import onnxruntime as ort

    repo = Path(repo_root).resolve()
    baseline = (repo / baseline_onnx).resolve()
    candidate = (repo / candidate_onnx).resolve()
    dataset = CalibrationDataset.open(repo, jsonl_path)
    base_session = ort.InferenceSession(str(baseline), providers=["CPUExecutionProvider"])
    cand_session = ort.InferenceSession(str(candidate), providers=["CPUExecutionProvider"])
    base_names = [item.name for item in base_session.get_outputs()]
    cand_names = [item.name for item in cand_session.get_outputs()]
    if base_names != cand_names:
        raise ValueError(f"output order mismatch: {base_names} != {cand_names}")

    absolute: dict[str, list[np.ndarray]] = defaultdict(list)
    argmax_equal: CounterLike = defaultdict(int)
    argmax_total: CounterLike = defaultdict(int)
    sample_errors: list[dict[str, Any]] = []
    feeds = dataset.feeds()
    request_count = 0
    for index, feed in enumerate(feeds):
        if limit is not None and index >= limit:
            break
        base_values = base_session.run(None, feed)
        cand_values = cand_session.run(None, feed)
        request_count += 1
        worst = ("", 0.0)
        for name, left, right in zip(base_names, base_values, cand_values, strict=True):
            left_array = np.asarray(left, dtype=np.float32)
            right_array = np.asarray(right, dtype=np.float32)
            if left_array.shape != right_array.shape:
                raise ValueError(f"{name} shape mismatch: {left_array.shape} != {right_array.shape}")
            delta = np.abs(left_array - right_array)
            absolute[name].append(delta.reshape(-1))
            max_abs = float(delta.max()) if delta.size else 0.0
            if max_abs > worst[1]:
                worst = (name, max_abs)
            if name in DISCRETE_HEADS:
                left_argmax = np.argmax(left_array, axis=-1)
                right_argmax = np.argmax(right_array, axis=-1)
                argmax_equal[name] += int(np.equal(left_argmax, right_argmax).sum())
                argmax_total[name] += int(left_argmax.size)
        sample_errors.append({"index": index, "worst_head": worst[0], "max_abs_error": worst[1]})

    heads: dict[str, Any] = {}
    for name in base_names:
        values = np.concatenate(absolute[name]) if absolute[name] else np.asarray([], dtype=np.float32)
        item: dict[str, Any] = {
            "count": int(values.size),
            "mean_abs_error": float(values.mean()) if values.size else 0.0,
            "p95_abs_error": float(np.quantile(values, 0.95)) if values.size else 0.0,
            "p99_abs_error": float(np.quantile(values, 0.99)) if values.size else 0.0,
            "max_abs_error": float(values.max()) if values.size else 0.0,
        }
        if name in DISCRETE_HEADS:
            item["argmax_agreement"] = (
                argmax_equal[name] / argmax_total[name] if argmax_total[name] else None
            )
        heads[name] = item
    report = {
        "schema_version": "1.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "raw-output diagnostic; not B2 accuracy Gate",
        "baseline": {"path": str(baseline.relative_to(repo)), "sha256": sha256_file(baseline)},
        "candidate": {"path": str(candidate.relative_to(repo)), "sha256": sha256_file(candidate)},
        "dataset": {"path": str(Path(jsonl_path)), "request_count": request_count},
        "per_head": heads,
        "worst_samples": sorted(sample_errors, key=lambda item: item["max_abs_error"], reverse=True)[:20],
    }
    output = (repo / output_json).resolve() if not Path(output_json).is_absolute() else Path(output_json)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ranked = sorted(
        heads.items(), key=lambda item: item[1]["mean_abs_error"], reverse=True
    )
    markdown = [
        "# A2 PTQ 敏感输出初筛（开发诊断）",
        "",
        "> 当前结果基于随机初始化 Student 和开发 Calibration，只用于验证分析流程，不能作为正式敏感层或精度结论。",
        "",
        "| 排名 | 输出 Head | Mean abs error | P95 | Max | Argmax agreement |",
        "|---:|---|---:|---:|---:|---:|",
    ]
    for index, (name, item) in enumerate(ranked, 1):
        agreement = item.get("argmax_agreement")
        markdown.append(
            f"| {index} | `{name}` | {item['mean_abs_error']:.6f} | "
            f"{item['p95_abs_error']:.6f} | {item['max_abs_error']:.6f} | "
            f"{agreement:.4f} |" if agreement is not None else
            f"| {index} | `{name}` | {item['mean_abs_error']:.6f} | "
            f"{item['p95_abs_error']:.6f} | {item['max_abs_error']:.6f} | - |"
        )
    markdown.extend([
        "",
        "正式权重到位后，需按层/算子组逐个恢复高精度并重新跑同一评价集；本表不能直接决定混合精度层。",
        "",
    ])
    (output.parent / "sensitive_layers.md").write_text("\n".join(markdown), encoding="utf-8")
    return report


CounterLike = dict[str, int]

__all__ = ["analyze_drift"]
