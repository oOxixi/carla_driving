"""Deterministic Conv/Linear parameter and FLOPs report for Student V0."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
from typing import Any

import torch
from torch import nn

from challenge.student.contract import StudentShapeContract
from challenge.student.model import StudentModelConfig, StudentPlannerV0


def analyze_model() -> dict[str, Any]:
    contract = StudentShapeContract()
    config = StudentModelConfig()
    model = StudentPlannerV0(contract, config).eval()
    macs_by_module: dict[str, int] = {}
    handles = []

    def register(name: str, module: nn.Module) -> None:
        def hook(layer: nn.Module, inputs: tuple[torch.Tensor, ...], output: torch.Tensor) -> None:
            if isinstance(layer, nn.Conv2d):
                batch, out_channels, out_height, out_width = output.shape
                kernel_ops = layer.kernel_size[0] * layer.kernel_size[1] * (layer.in_channels // layer.groups)
                macs_by_module[name] = int(batch * out_channels * out_height * out_width * kernel_ops)
            elif isinstance(layer, nn.Linear):
                rows = output.numel() // layer.out_features
                macs_by_module[name] = int(rows * layer.in_features * layer.out_features)
        handles.append(module.register_forward_hook(hook))

    for name, module in model.named_modules():
        if isinstance(module, (nn.Conv2d, nn.Linear)):
            register(name, module)
    inputs = tuple(torch.zeros(shape, dtype=torch.float32) for shape in contract.input_shapes.values())
    with torch.inference_mode():
        model(*inputs)
    for handle in handles:
        handle.remove()

    parameters = sum(parameter.numel() for parameter in model.parameters())
    trainable_parameters = sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)
    macs = sum(macs_by_module.values())
    # Conservative 2B-class lower bound retained for relative architecture
    # sizing. The Teacher artifact identity is pinned, but this analytical
    # lower bound has not been recomputed from that exact model config, so it
    # must not be presented as a model-revision-specific benchmark.
    # hidden=2048, intermediate=6144, 16 query heads, 8 KV heads, 28 layers.
    # It counts one text token only and excludes embeddings, vision, attention
    # score products and all other input/output tokens. The real comparable
    # Teacher workload is therefore strictly larger.
    teacher_active_parameters_lower_bound = (
        2048 * 2048
        + 2 * 2048 * (8 * 128)
        + 2048 * 2048
        + 3 * 2048 * 6144
    ) * 28
    teacher_flops_lower_bound = 2 * teacher_active_parameters_lower_bound
    flops = macs * 2
    return {
        "schema_version": "1.0",
        "model_id": model.model_id,
        "source_git_sha": subprocess.check_output(
            ("git", "rev-parse", "HEAD"), text=True, encoding="utf-8",
        ).strip(),
        "dataset_version": "NOT_APPLICABLE_RANDOM_INIT",
        "config_id": config.config_id,
        "precision": "fp32",
        "input_shapes": {name: list(shape) for name, shape in contract.input_shapes.items()},
        "parameters": parameters,
        "trainable_parameters": trainable_parameters,
        "parameter_size_bytes_fp32": parameters * 4,
        "macs_per_fixed_batch": macs,
        "flops_per_fixed_batch": flops,
        "teacher_model_id": "Qwen/Qwen3.5-2B",
        "teacher_model_revision": "15852e8c16360a2fea060d615a32b45270f8a8fc",
        "teacher_artifact_fingerprint_sha256": "4bbf183b7b7f1ab9fb9eb325f189f4449d65e9fe664cbfe4bcc58a33888657fa",
        "teacher_non_embedding_active_parameters_lower_bound": teacher_active_parameters_lower_bound,
        "teacher_flops_lower_bound_one_text_token": teacher_flops_lower_bound,
        "flops_ratio_student_over_teacher_lower_bound": flops / teacher_flops_lower_bound,
        "ratio_target": 0.5,
        "ratio_pass": flops / teacher_flops_lower_bound <= 0.5,
        "counting_convention": "Conv2D/Linear only; 1 MAC = 2 FLOPs",
        "teacher_bound_scope": "2B-class conservative one-token bound; Teacher identity is pinned but this is not an exact-model FLOPs calculation; excludes vision and sequence work; not latency or board evidence",
        "macs_by_module": macs_by_module,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="challenge/flops_report.json")
    args = parser.parse_args()
    report = analyze_model()
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in (
        "parameters", "flops_per_fixed_batch", "flops_ratio_student_over_teacher_lower_bound", "ratio_pass",
    )}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
