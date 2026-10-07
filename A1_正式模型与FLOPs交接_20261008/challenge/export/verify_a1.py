"""Small, CPU-only A1 interface/padding/FLOPs handoff check."""
from __future__ import annotations
import json
from pathlib import Path
import torch
from challenge.student.contract import (
    BEHAVIORS, TARGET_LANES, COMPLETION_TYPES, ON_FAILURE, REPLAN_CONDITIONS,
    OUTPUT_NAMES, StudentShapeContract,
)
from challenge.student.model import StudentPlannerV0, StudentModelConfig
from challenge.student.training_contract import build_step_mask, masked_step_mean
from challenge.export.compute_flops import analyze_model


def verify() -> dict:
    torch.set_num_threads(1)
    torch.manual_seed(20260911)
    contract = StudentShapeContract()
    model = StudentPlannerV0().eval()
    inputs = tuple(torch.zeros(shape, dtype=torch.float32) for shape in contract.input_shapes.values())
    with torch.inference_mode():
        outputs = model(*inputs)
    assert tuple(outputs) == OUTPUT_NAMES
    assert {k: tuple(v.shape) for k,v in outputs.items()} == contract.output_shapes
    assert all(v.dtype == torch.float32 and torch.isfinite(v).all() for v in outputs.values())
    lengths = torch.tensor([1, 2, 3, 4], dtype=torch.int64)
    mask = build_step_mask(lengths)
    assert mask.tolist() == [[True]*n + [False]*(4-n) for n in lengths.tolist()]
    losses = torch.where(mask, 1.0, 999.0)
    assert masked_step_mean(losses, mask).item() == 1.0
    flops = analyze_model()
    assert flops["parameters"] == 23006581
    assert flops["flops_per_fixed_batch"] == 498640896
    assert flops["ratio_pass"] is None
    return {
        "status": "PASS", "device": "CPU", "random_initialization": True,
        "checks": ["forward keys/shapes/float32/finiteness", "1..4 step mask",
                   "padding contributes zero step loss", "student Conv/Linear count",
                   "no unapproved denominator pass claim"],
        "input_fields": {k: {"shape": list(v), "dtype": "float32"} for k,v in contract.input_shapes.items()},
        "output_heads": {k: {"shape": list(v), "dtype": "float32"} for k,v in contract.output_shapes.items()},
        "class_mappings": {key: dict(enumerate(values)) for key,values in (
            ("behavior", BEHAVIORS), ("target_lane", TARGET_LANES),
            ("completion", COMPLETION_TYPES), ("on_failure", ON_FAILURE), ("replan", REPLAN_CONDITIONS))},
        "target_pointer": {"0..7": "request targets in order", "8": "NONE"},
        "plan_length_class": {str(i): i+1 for i in range(4)},
        "padding": {"mask": "bool[B,4], step_index < plan_length",
                    "behavior": 13, "target_pointer": 8, "target_lane": 5,
                    "completion": 7, "on_failure": 1, "target_speed_mps": 0,
                    "plan_level_heads": "not masked by step padding"},
        "model_config": StudentModelConfig().as_dict(),
        "boundary": "structural verification only; NOT accuracy, quantization or driving acceptance",
    }


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    result = verify()
    content = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content, encoding="utf-8")
    print(content)
