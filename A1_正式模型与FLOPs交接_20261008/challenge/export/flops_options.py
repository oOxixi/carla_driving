"""Candidate denominators and scope choices; no competition decision is made.

Expanded Teacher counts are analytical, reference-algorithm counts (NOT vLLM
kernel FLOPs). Present direct counts only; no lower-bound-based ratios.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import torch
from torch import nn
from challenge.student.model import StudentPlannerV0
from challenge.student.contract import StudentShapeContract
from challenge.export.compute_flops import analyze_model


def student_arithmetic() -> dict:
    """Forward-shape count with a fully declared abstract arithmetic convention."""
    torch.set_num_threads(1)
    model = StudentPlannerV0().eval()
    contract = StudentShapeContract()
    rows, handles = [], []
    supported = (nn.Conv2d, nn.Linear, nn.ReLU, nn.AvgPool2d)
    for name, module in model.named_modules():
        if not list(module.children()) and not isinstance(module, supported):
            raise ValueError(f"Uncounted leaf module: {name}: {type(module).__name__}")
        if not isinstance(module, supported):
            continue
        def hook(layer, inputs, output, name=name):
            size = output.numel()
            extra, comparisons = 0, 0
            if isinstance(layer, (nn.Conv2d, nn.Linear)):
                extra = size if layer.bias is not None else 0
            elif isinstance(layer, nn.ReLU):
                comparisons = size
            else:
                k = layer.kernel_size
                area = k*k if isinstance(k, int) else k[0]*k[1]
                extra = size*area  # area-1 summation additions + one division
            rows.append({"module": name, "type": type(layer).__name__,
                         "output_shape": list(output.shape),
                         "bias_or_pool_arithmetic_ops": extra,
                         "relu_comparison_ops": comparisons})
        handles.append(module.register_forward_hook(hook))
    with torch.inference_mode():
        output = model(*(torch.zeros(s) for s in contract.input_shapes.values()))
    for h in handles:
        h.remove()
    core = analyze_model()["flops_per_fixed_batch"]
    sigmoid_elements = output["target_speed_mps"].numel()+output["confidence"].numel()
    functional = {"sigmoid_neg_exp_add_div": 4*sigmoid_elements,
                  "target_speed_scale_multiply": output["target_speed_mps"].numel()}
    extra = sum(r["bias_or_pool_arithmetic_ops"] for r in rows)+sum(functional.values())
    comparisons = sum(r["relu_comparison_ops"] for r in rows)
    return {"conv_linear_flops": core, "bias_pool_activation_extra_ops": extra,
            "arithmetic_total": core+extra, "relu_comparisons": comparisons,
            "arithmetic_plus_comparisons_total": core+extra+comparisons,
            "convention": "MAC=2; float add/mul/div/neg=1; abstract exp=1; sigmoid=4; "
                          "ReLU comparisons separately counted; reshape/cat/data movement=0; "
                          "initialization and preprocessing excluded",
            "status": "shape-derived abstract operation count, NOT measured kernel instructions",
            "functional_ops": functional, "modules": rows}


def build_options(root: Path) -> dict:
    teacher = json.loads((root/"challenge/teacher_flops_report.json").read_text(encoding="utf-8"))
    config = json.loads((root/"challenge/export/teacher_config_pinned.json").read_text(encoding="utf-8"))
    student = student_arithmetic()
    t, v = config["text_config"], config["vision_config"]
    seq = teacher["workload"]["total_prefill_tokens"]
    # Vision sequences do not attend across different temporal frames/images.
    vision_score_pairs = sum(frames*(height*width)**2
                             for frames,height,width in teacher["workload"]["image_grid_thw"])
    nfull = t["layer_types"].count("full_attention")
    nlinear = t["layer_types"].count("linear_attention")
    attention_vision = 4*v["depth"]*vision_score_pairs*v["hidden_size"]
    attention_text = 4*nfull*seq**2*t["num_attention_heads"]*t["head_dim"]
    # Reference serial delta update: decay state (KV), memory read (2K-1)V,
    # delta (2V), rank-one state update (2KV), output read (2K-1)V => 7KV.
    recurrence = 7*nlinear*seq*t["linear_num_value_heads"]*t["linear_key_head_dim"]*t["linear_value_head_dim"]
    expanded = teacher["core_flops"]+attention_vision+attention_text+recurrence
    # Frozen evidence for candidates, not an assertion of actual submission.
    evidence = root/"baselines/initial_prepared_package"
    release = json.loads((evidence/"release_manifest.json").read_text(encoding="utf-8"))
    # Text-equivalence tolerates Windows CRLF vs LF in the handoff copy.
    same_model = (evidence/"student/model.py").read_text(encoding="utf-8") == (root/"challenge/student/model.py").read_text(encoding="utf-8")
    same_contract = (evidence/"student/contract.py").read_text(encoding="utf-8") == (root/"challenge/student/contract.py").read_text(encoding="utf-8")
    if not same_model or not same_contract:
        raise ValueError("Initial Student snapshot changed; recompute that candidate independently")
    if release["model"] != teacher["teacher_model_id"] or release["model_revision"] != teacher["teacher_model_revision"]:
        raise ValueError("Initial prepared package is not the same Teacher identity")
    candidates = [
        {"id": "fixed_teacher_conv_linear", "baseline": "Pinned Teacher Qwen3.5-2B",
         "scope": "Conv/Linear only, declared 267-token/64-visual-token fixture",
         "numerator": student["conv_linear_flops"], "denominator": teacher["core_flops"],
         "ratio": student["conv_linear_flops"]/teacher["core_flops"], "ratio_kind": "exact within dense-layer analytical scope"},
        {"id": "fixed_teacher_expanded_dominant_ops", "baseline": "Pinned Teacher Qwen3.5-2B",
         "scope": "Conv/Linear + dense attention QK/AV + serial gated-delta core updates",
         "numerator": student["conv_linear_flops"], "denominator": expanded,
         "ratio": student["conv_linear_flops"]/expanded, "ratio_kind": "analytical partial-operator comparison; NOT whole network"},
        {"id": "initial_student_fp32_conv_linear", "baseline": "Initial prepared package's same-structure FP32 Student (conditional choice)",
         "scope": "Conv/Linear, identical model.py + contract.py, identical fixed shapes",
         "numerator": student["conv_linear_flops"], "denominator": student["conv_linear_flops"],
         "ratio": 1.0, "ratio_kind": "same architecture; FP32->INT8 alone does not reduce MAC count"},
        {"id": "initial_student_fp32_whole_forward", "baseline": "Initial prepared package's same-structure FP32 Student (conditional choice)",
         "scope": "Abstract whole-forward floating arithmetic, ReLU comparisons separately reported, identical architecture",
         "numerator": student["arithmetic_total"],
         "denominator": student["arithmetic_total"], "ratio": 1.0,
         "ratio_kind": "same-structure arithmetic-count equality; not measured FP32 vs INT8 kernel instructions"},
    ]
    for choice in candidates:
        ratio = choice["ratio"]
        choice["numeric_le_0p5_under_declared_scope"] = ratio <= 0.5
        choice["conditional_tier_points_if_baseline_and_scope_accepted"] = (
            15 if ratio <= 0.5 else 10 if ratio <= 0.7 else 5 if ratio <= 0.9 else 0
        )
        choice["formal_ratio_pass"] = None
        choice["baseline_selection"] = "REPORT_TEAM_CHOICE_NOT_SELECTED"
    return {
        "schema_version": "1.0", "student": student,
        "teacher_identity": {k: teacher[k] for k in ["teacher_model_id", "teacher_model_revision", "config_file_sha256"]},
        "teacher_counts": {"conv_linear_flops": teacher["core_flops"],
                           "vision_attention_qk_av": attention_vision,
                           "text_attention_qk_av": attention_text,
                           "serial_delta_core_updates": recurrence,
                           "expanded_dominant_flops": expanded,
                           "exact_whole_network_flops": None},
        "teacher_expanded_scope_note": "Reference dense attention and serial delta algorithm; production vLLM prefill may use chunk/fused kernels with different counts. "
                                       "Expanded sum still excludes norm/gates/softmax/rotary/nonlinear/residual/bias and does NOT claim total FLOPs.",
        "initial_prepared_package_evidence": {"status": release["status"], "model": release["model"],
                                            "revision": release["model_revision"],
                                            "same_as_fixed_teacher": True, "same_student_model_and_contract": True,
                                            "actual_competition_submission_identity": "NOT_PROVEN_BY_STAGED_PREPARATION_DIRECTORY"},
        "candidates": candidates,
        "caveat": "Direct model counts only; no bound-based ratios. Baseline and scope choices are supplied, not approved or selected. Exact Teacher whole-network FLOPs are not measured. "
                  "No scoring claim. A2/A4 graph changes require a fresh numerator. ASR/NLU/planning adapters/controllers are outside both model scopes.",
    }


if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=Path("."))
    p.add_argument("--output", type=Path, default=Path("challenge/flops_options.json"))
    a=p.parse_args()
    report=build_options(a.root.resolve())
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"student": {k: report["student"][k] for k in ["arithmetic_total", "arithmetic_plus_comparisons_total"]},
                      "teacher": report["teacher_counts"], "options": len(report["candidates"])}, ensure_ascii=False))
