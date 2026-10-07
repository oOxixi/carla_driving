"""Deterministic Conv/Linear parameter and FLOPs report for Student V0."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
from typing import Any

import torch
from torch import nn

from challenge.student.contract import StudentShapeContract
from challenge.student.model import StudentModelConfig, StudentPlannerV0


def source_revision() -> str:
    """Bundles and minimal runtime images do not necessarily contain Git."""
    if os.environ.get("A1_SOURCE_GIT_SHA"):
        return os.environ["A1_SOURCE_GIT_SHA"]
    try:
        return subprocess.check_output(
            ("git", "rev-parse", "HEAD"), text=True, encoding="utf-8",
            stderr=subprocess.DEVNULL,
        ).strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return "NOT_AVAILABLE_SEE_MANIFEST"


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
    # Retire the incompatible 28-layer denominator. A separate report counts
    # the pinned Teacher and a declared request; team approval is still needed.
    flops = macs * 2
    return {
        "schema_version": "1.0",
        "model_id": model.model_id,
        "source_git_sha": source_revision(),
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
        "teacher_non_embedding_active_parameters_lower_bound": None,
        "teacher_flops_lower_bound_one_text_token": None,
        "flops_ratio_student_over_teacher_lower_bound": None,
        "ratio_target": 0.5,
        "ratio_pass": None,
        "counting_convention": "Conv2D/Linear only; 1 MAC = 2 FLOPs",
        "teacher_bound_scope": "Legacy 28-layer estimate retired: use teacher_flops_report.json; formal denominator approval pending",
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
