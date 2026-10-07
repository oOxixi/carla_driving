"""Pinned Teacher dense Conv/Linear inventory, NOT a total-operator profiler.

No inference, downloads or GPU required. Meta construction inspects the actual
Transformers module dimensions; the local processor supplies real token counts.
Teacher selection as the competition denominator remains a team decision.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
from pathlib import Path

TEACHER_ID = "Qwen/Qwen3.5-2B"
REVISION = "15852e8c16360a2fea060d615a32b45270f8a8fc"
FINGERPRINT = "4bbf183b7b7f1ab9fb9eb325f189f4449d65e9fe664cbfe4bcc58a33888657fa"


def mlp_lower_bound(config: dict) -> int:
    """One text token, text gated MLP only, 1 MAC = 2 FLOPs."""
    t = config["text_config"]
    return 2 * t["num_hidden_layers"] * 3 * t["hidden_size"] * t["intermediate_size"]


def comparison(student_flops: int, teacher_flops: int) -> dict:
    if min(student_flops, teacher_flops) <= 0:
        raise ValueError("Both model counts must be positive")
    return {
        "core_flops_ratio": student_flops / teacher_flops,
        "scope": "Dense Conv/Linear model-only arithmetic; not complete network FLOPs",
        "ratio_target": 0.5,
        "formal_ratio_pass": None,
        "team_denominator_approval": "PENDING",
    }


def analyze_teacher(model_dir: Path, request_path: Path) -> dict:
    import torch
    import transformers
    from PIL import Image
    from transformers import AutoConfig, AutoModelForImageTextToText, AutoProcessor
    from qwen_service.service import VllmQwenPlannerBackend
    from challenge.export.compute_flops import analyze_model, source_revision

    pinned = Path(__file__).with_name("teacher_config_pinned.json")
    config_dict = json.loads(pinned.read_text(encoding="utf-8"))
    raw_config = (model_dir / "config.json").read_bytes()
    if json.loads(raw_config) != config_dict:
        raise ValueError("Local Teacher config differs from the pinned configuration")
    request = json.loads(request_path.read_text(encoding="utf-8"))
    backend = VllmQwenPlannerBackend.__new__(VllmQwenPlannerBackend)
    prompt = backend._choice_prompt(request, choice_codes=backend._choice_codes(request))
    # Pixels are an explicit synthetic fixture, not driving/quality evidence.
    image = Image.new("RGB", (224, 224), color=(0, 0, 0))
    processor = AutoProcessor.from_pretrained(model_dir, local_files_only=True)
    processed = processor.apply_chat_template(
        [{"role": "user", "content": [{"type": "image", "image": image},
                                        {"type": "text", "text": prompt}]}],
        tokenize=True, add_generation_prompt=True, enable_thinking=False,
        return_dict=True, return_tensors="pt",
    )
    grid = processed["image_grid_thw"].tolist()
    patch_tokens = sum(t * h * w for t, h, w in grid)
    merge = config_dict["vision_config"]["spatial_merge_size"] ** 2
    if patch_tokens % merge:
        raise ValueError("Vision patches are not divisible by the merger size")
    visual_tokens = patch_tokens // merge
    sequence_tokens = int(processed["input_ids"].shape[-1])
    # Single constrained output token: prefill's last hidden state is projected
    # to logits once. No additional autoregressive decode pass is necessary.
    config = AutoConfig.from_pretrained(model_dir, local_files_only=True)
    with torch.device("meta"):
        model = AutoModelForImageTextToText.from_config(
            config, attn_implementation="eager", dtype=torch.bfloat16,
        )
    inventory = []
    for name, module in model.named_modules():
        if not isinstance(module, (torch.nn.Linear, torch.nn.Conv1d,
                                   torch.nn.Conv2d, torch.nn.Conv3d)):
            continue
        if name == "lm_head":
            rows, group = 1, "output_projection"
        elif name.startswith("model.visual.merger."):
            rows, group = visual_tokens, "vision_merger"
        elif name.startswith("model.visual."):
            rows, group = patch_tokens, "vision_encoder"
        elif name.startswith("model.language_model.layers."):
            rows, group = sequence_tokens, "text_prefill"
        else:
            raise ValueError(f"Unclassified executed dense module: {name}")
        # For Conv, weight includes per-output kernel elements and groups.
        # Depthwise causal Conv1d retains S positions after right-padding trim;
        # count direct dense convolution, not a backend-specific FFT algorithm.
        macs = rows * module.weight.numel()
        inventory.append({"module": name, "type": type(module).__name__,
                          "weight_shape": list(module.weight.shape),
                          "rows_or_output_positions": rows, "group": group,
                          "macs": macs, "flops": 2 * macs})
    groups = {}
    for row in inventory:
        groups[row["group"]] = groups.get(row["group"], 0) + row["flops"]
    teacher_flops = sum(groups.values())
    return {
        "schema_version": "1.0", "teacher_model_id": TEACHER_ID,
        "teacher_model_revision": REVISION,
        "expected_weight_artifact_fingerprint_sha256": FINGERPRINT,
        "weight_execution": "NOT_RUN: shape inventory from pinned config, not quality evidence",
        "config_file_sha256": hashlib.sha256(raw_config).hexdigest(),
        "source_git_sha": source_revision(),
        "method": "Analytical dense Conv/Linear module inventory, not runtime operator profiling",
        "workload": {"batch": 1, "rgb_fixture": "synthetic black 224x224 RGB",
                     "request": request, "request_sha256": hashlib.sha256(request_path.read_bytes()).hexdigest(),
                     "prompt": prompt, "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                     "image_grid_thw": grid, "patch_tokens": patch_tokens,
                     "processed_pixel_values_shape": list(processed["pixel_values"].shape),
                     "processed_pixel_values_dtype": str(processed["pixel_values"].dtype),
                     "llm_visual_tokens": visual_tokens, "total_prefill_tokens": sequence_tokens,
                     "generated_tokens": 1, "logits_positions": 1,
                     "input_ids": processed["input_ids"].tolist()},
        "counting_convention": "1 MAC = 2 FLOPs; dense direct Conv/Linear; batch=1",
        "core_flops": teacher_flops, "core_flops_by_group": groups,
        "one_text_token_mlp_only_lower_bound_flops": mlp_lower_bound(config_dict),
        "excluded_operators": ["attention QK/AV matmul", "gated delta recurrence/chunk updates",
                               "embedding lookups", "bias/norm/activation/elementwise/position ops",
                               "ASR/NLU/preprocessing/tokenization/safety/controller",
                               "inactive MTP branch"],
        "comparison": comparison(analyze_model()["flops_per_fixed_batch"], teacher_flops),
        "runtime": {"python": platform.python_version(), "torch": torch.__version__,
                    "transformers": transformers.__version__, "device": "CPU/meta (no inference)"},
        "modules": inventory,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--request", type=Path, default=Path("interfaces/examples/model_request.json"))
    parser.add_argument("--output", type=Path, default=Path("challenge/teacher_flops_report.json"))
    args = parser.parse_args()
    report = analyze_teacher(args.model_dir, args.request)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("core_flops", "core_flops_by_group", "comparison")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
