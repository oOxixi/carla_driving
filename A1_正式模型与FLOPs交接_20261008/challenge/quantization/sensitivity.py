"""Controlled mixed-precision sensitivity experiments for A2.

Each experiment starts from the same FP32 ONNX, Calibration and quantization
configuration.  It restores exactly one named node to FP32 by excluding that
node from ORT QDQ quantization, then compares all ten raw Student heads against
the FP32 baseline.  The report is diagnostic until B2 evaluates the resulting
candidate on its frozen benchmark.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Sequence

from .config import DEFAULT_QUANT_CONFIG, load_quant_config
from .drift import analyze_drift
from .ptq import quantize_qdq


def discover_candidate_nodes(
    source_onnx: str | Path,
    *,
    op_types: Sequence[str],
) -> list[dict[str, str]]:
    import onnx

    graph = onnx.load(str(source_onnx), load_external_data=False)
    accepted = set(op_types)
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, node in enumerate(graph.graph.node):
        if node.op_type not in accepted or not node.name or node.name in seen:
            continue
        seen.add(node.name)
        rows.append({"name": node.name, "op_type": node.op_type, "index": str(index)})
    return rows


def _safe_name(value: str) -> str:
    result = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._")
    return result[:100] or "unnamed"


def _score_variant(
    baseline: dict[str, Any],
    variant: dict[str, Any],
    focus_heads: Sequence[str],
) -> tuple[float, dict[str, Any]]:
    details: dict[str, Any] = {}
    reductions: list[float] = []
    for head in focus_heads:
        if head not in baseline or head not in variant:
            continue
        base = float(baseline[head]["mean_abs_error"])
        value = float(variant[head]["mean_abs_error"])
        reduction = (base - value) / max(abs(base), 1e-12)
        reductions.append(reduction)
        item: dict[str, Any] = {
            "baseline_mean_abs_error": base,
            "variant_mean_abs_error": value,
            "relative_error_reduction": reduction,
        }
        if "argmax_agreement" in baseline[head] and "argmax_agreement" in variant[head]:
            item["argmax_agreement_delta"] = (
                float(variant[head]["argmax_agreement"])
                - float(baseline[head]["argmax_agreement"])
            )
        details[head] = item
    score = sum(reductions) / len(reductions) if reductions else 0.0
    return score, details


def analyze_sensitive_nodes(
    repo_root: str | Path,
    *,
    source_onnx: str | Path,
    calibration_jsonl: str | Path,
    calibration_manifest: str | Path,
    output_directory: str | Path,
    quant_config: str | Path = DEFAULT_QUANT_CONFIG,
    limit: int | None = None,
    max_groups: int | None = None,
    allow_smoke: bool = False,
    allow_candidate: bool = False,
) -> dict[str, Any]:
    """Run full-INT8 plus one-node-restored controlled experiments."""
    repo = Path(repo_root).absolute()
    source = (repo / source_onnx).absolute() if not Path(source_onnx).is_absolute() else Path(source_onnx)
    output = (repo / output_directory).absolute() if not Path(output_directory).is_absolute() else Path(output_directory)
    config_path = (repo / quant_config).absolute() if not Path(quant_config).is_absolute() else Path(quant_config)
    config = load_quant_config(config_path)
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"sensitivity output directory must be empty: {output}")
    output.resolve().mkdir(parents=True, exist_ok=True)

    candidates = discover_candidate_nodes(
        source, op_types=config["sensitivity"]["candidate_op_types"],
    )
    if max_groups is not None:
        if max_groups < 1:
            raise ValueError("max_groups must be positive")
        candidates = candidates[:max_groups]
    if not candidates:
        raise ValueError("no named sensitivity candidate nodes were found")

    baseline_dir = output / "full_int8_baseline"
    baseline_onnx = baseline_dir / "student_int8.onnx"
    baseline_manifest = quantize_qdq(
        repo,
        source_onnx=source,
        calibration_jsonl=calibration_jsonl,
        calibration_manifest=calibration_manifest,
        output_onnx=baseline_onnx,
        quant_config=config_path,
        allow_smoke=allow_smoke,
        allow_candidate=allow_candidate,
    )
    baseline_drift = analyze_drift(
        repo,
        baseline_onnx=source,
        candidate_onnx=baseline_onnx,
        jsonl_path=calibration_jsonl,
        output_json=baseline_dir / "raw_output_drift.json",
        limit=limit,
    )

    experiments: list[dict[str, Any]] = []
    focus_heads = config["sensitivity"]["focus_heads"]
    for index, candidate in enumerate(candidates, 1):
        variant_dir = output / "variants" / f"{index:03d}_{_safe_name(candidate['name'])}"
        variant_onnx = variant_dir / "student_int8.onnx"
        manifest = quantize_qdq(
            repo,
            source_onnx=source,
            calibration_jsonl=calibration_jsonl,
            calibration_manifest=calibration_manifest,
            output_onnx=variant_onnx,
            quant_config=config_path,
            excluded_nodes=[candidate["name"]],
            allow_smoke=allow_smoke,
            allow_candidate=allow_candidate,
        )
        drift = analyze_drift(
            repo,
            baseline_onnx=source,
            candidate_onnx=variant_onnx,
            jsonl_path=calibration_jsonl,
            output_json=variant_dir / "raw_output_drift.json",
            limit=limit,
        )
        score, focus = _score_variant(
            baseline_drift["per_head"], drift["per_head"], focus_heads,
        )
        experiments.append({
            "node": candidate,
            "excluded_nodes": [candidate["name"]],
            "quantization_id": manifest["quantization_id"],
            "int8_artifact_sha256": manifest["int8_artifact_sha256"],
            "artifact_size_bytes": manifest["output"]["size_bytes"],
            "diagnostic_score": score,
            "focus_head_changes": focus,
            "per_head": drift["per_head"],
            "report": str((variant_dir / "raw_output_drift.json").relative_to(output)),
        })

    ranked = sorted(experiments, key=lambda item: item["diagnostic_score"], reverse=True)
    report = {
        "schema_version": "1.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "DIAGNOSTIC_PENDING_B2_INT8_GATE",
        "scope": (
            "One-node FP32 restoration sensitivity analysis. Raw-head drift is diagnostic "
            "and cannot replace B2 frozen-benchmark accuracy or A4 OpenExplorer fallback evidence."
        ),
        "source_fp32_onnx": str(source),
        "baseline_quantization_id": baseline_manifest["quantization_id"],
        "baseline_int8_artifact_sha256": baseline_manifest["int8_artifact_sha256"],
        "baseline_per_head": baseline_drift["per_head"],
        "focus_heads": focus_heads,
        "candidate_op_types": config["sensitivity"]["candidate_op_types"],
        "experiment_count": len(experiments),
        "ranking": ranked,
    }
    json_path = output / "sensitive_layer_report.json"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    markdown = [
        "# A2 敏感层受控实验",
        "",
        "> 每次只将一个命名节点恢复为 FP32。排名是原始 Head 漂移诊断，不是 B2 精度 Gate。",
        "",
        "| 排名 | 节点 | 算子 | 诊断改善分 | INT8 SHA256 |",
        "|---:|---|---|---:|---|",
    ]
    for rank, item in enumerate(ranked, 1):
        markdown.append(
            f"| {rank} | `{item['node']['name']}` | `{item['node']['op_type']}` | "
            f"{item['diagnostic_score']:.6f} | `{item['int8_artifact_sha256']}` |"
        )
    markdown.extend([
        "",
        "只有同时改善关键 Head、通过 B2 Frozen Benchmark，并经 A4 证明部署代价可接受的节点，",
        "才允许进入最终 Mixed Precision 白名单。",
        "",
    ])
    (output / "sensitive_layers.md").write_text("\n".join(markdown), encoding="utf-8")
    return report


__all__ = ["analyze_sensitive_nodes", "discover_candidate_nodes"]
