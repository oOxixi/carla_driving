"""Read-only inventory and CPU token-mask smoke; never load model weights."""
from __future__ import annotations

from importlib import metadata
import hashlib
import json
import os
from pathlib import Path
import re

from .data import PLAN, SFT_SYSTEM


def assistant_token_mask(tokenizer, messages: list[dict], *, max_length: int = 4096) -> dict:
    if not messages or messages[-1].get("role") != "assistant" or not messages[-1].get("content"):
        raise ValueError("last message must be a non-empty assistant completion")
    if any(m.get("role") == "assistant" for m in messages[:-1]):
        raise ValueError("this preparation contract is single-turn, not a multi-assistant dataset")
    prefix = tokenizer.apply_chat_template(messages[:-1], tokenize=False,
        add_generation_prompt=True, enable_thinking=False)
    full = tokenizer.apply_chat_template(messages, tokenize=False,
        add_generation_prompt=False, enable_thinking=False)
    if not full.startswith(prefix):
        raise ValueError("chat template prefix mismatch; cannot guess assistant loss boundary")
    prefix_ids = tokenizer(prefix, add_special_tokens=False)["input_ids"]
    full_ids = tokenizer(full, add_special_tokens=False)["input_ids"]
    if not prefix_ids or full_ids[:len(prefix_ids)] != prefix_ids:
        raise ValueError("tokenizer prefix mismatch; cannot guess assistant loss boundary")
    if len(full_ids) > max_length:
        raise ValueError("example exceeds token budget; no silent truncation")
    if len(prefix_ids) >= len(full_ids):
        raise ValueError("no assistant tokens remain")
    labels = [-100] * len(prefix_ids) + full_ids[len(prefix_ids):]
    eos = getattr(tokenizer, "eos_token_id", None)
    if eos is not None and eos not in labels[len(prefix_ids):]:
        raise ValueError("assistant end-of-turn token is not trained")
    return {"input_ids": full_ids, "labels": labels, "prompt_tokens": len(prefix_ids),
            "assistant_tokens": len(full_ids) - len(prefix_ids)}


def compare_module_layout(modules: list[dict], expected_names: list[str], *, rank: int) -> dict:
    """Check instantiated meta modules; parameter counts are estimates, not PEFT weights."""
    if type(rank) is not int or rank < 1:
        raise ValueError("LoRA rank must be a positive integer")
    errors = []
    names = [module["name"] for module in modules]
    if not names:
        errors.append("NO_TARGET_MODULES")
    if len(set(names)) != len(names):
        errors.append("DUPLICATE_MODULE_NAMES")
    if set(names) != set(expected_names):
        errors.append("INDEX_INSTANTIATED_MODULE_MISMATCH")
    total = 0
    for module in modules:
        name = module["name"]
        if not re.fullmatch(r"model\.language_model\.layers\.[0-9]+\.self_attn\.(q_proj|v_proj)", name):
            errors.append("TARGET_OUTSIDE_ALLOWED_LANGUAGE_QV:" + name)
        if module["module_type"] != "torch.nn.modules.linear.Linear":
            errors.append("TARGET_NOT_LINEAR:" + name)
        if module["weight_device"] != "meta":
            errors.append("NON_META_TARGET:" + name)
        incoming, outgoing = module["in_features"], module["out_features"]
        if any(type(n) is not int or n < 1 for n in (incoming, outgoing)) or module["weight_shape"] != [outgoing, incoming]:
            errors.append("LINEAR_SHAPE_MISMATCH:" + name)
        else:
            total += rank * (incoming + outgoing)
    return {"status": "FAIL" if errors else "PASS", "errors": errors, "modules": modules,
            "module_count": len(modules), "rank": rank,
            "candidate_lora_parameters_estimate": total,
            "candidate_adapter_fp32_bytes_estimate": total * 4,
            "estimate_note": "A/B matrices only, bias=none; not allocated or injected PEFT parameters.",
            "peft_injection_verified": False, "ready_for_training": False}


def meta_module_audit(model_path: Path, expected_names: list[str]) -> dict:
    # Scope this diagnostic to its own process; never contact or reconfigure the running service.
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    import torch
    from transformers import AutoConfig, AutoModelForImageTextToText

    if torch.cuda.is_initialized():
        raise ValueError("meta audit must run before any CUDA context is initialized")
    config = AutoConfig.from_pretrained(str(model_path), local_files_only=True, trust_remote_code=False)
    if config.model_type != "qwen3_5" or config.architectures != ["Qwen3_5ForConditionalGeneration"]:
        raise ValueError("meta audit only supports the pinned Qwen3.5-2B architecture")
    with torch.device("meta"):
        model = AutoModelForImageTextToText.from_config(config, dtype=torch.float32, attn_implementation="eager")
    if not all(t.device.type == "meta" for t in (*model.parameters(), *model.buffers())):
        raise ValueError("architecture created non-meta tensors; refuse to certify this diagnostic")
    pattern = re.compile(PLAN["candidate_lora"]["target_modules_regex"])
    modules = [{"name": name, "module_type": type(module).__module__ + "." + type(module).__qualname__,
                "in_features": getattr(module, "in_features", None), "out_features": getattr(module, "out_features", None),
                "weight_shape": list(module.weight.shape) if hasattr(module, "weight") else None,
                "weight_device": module.weight.device.type if hasattr(module, "weight") else None}
               for name, module in model.named_modules() if pattern.fullmatch(name)]
    report = compare_module_layout(modules, expected_names, rank=PLAN["candidate_lora"]["r"])
    report.update(scope="META_ARCHITECTURE_ONLY_NOT_TRAINING_OR_INFERENCE",
        architecture=type(model).__name__, base_parameters=sum(p.numel() for p in model.parameters()),
        all_parameters_and_buffers_meta=True, cuda_initialized=torch.cuda.is_initialized(),
        model_weights_loaded=False, adapter_weights_created=False, base_fingerprint_verified=False)
    if report["cuda_initialized"]:
        raise ValueError("meta audit unexpectedly initialized CUDA")
    return report


def inventory(model_path: Path | None = None, *, tokenizer_smoke: bool = False, module_audit: bool = False) -> dict:
    packages = {}
    for name in ("torch", "transformers", "tokenizers", "jsonschema", "peft", "datasets", "accelerate", "trl", "bitsandbytes"):
        try:
            packages[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            packages[name] = None
    report = {"scope": "READ_ONLY_PREPARATION_NOT_TRAINING", "packages": packages,
              "model_weights_loaded": False, "gpu_allocated_by_this_tool": False,
              "artifact_fingerprint_verified_by_this_tool": False, "ready_for_training": False}
    if model_path is not None:
        model_path = model_path.resolve(strict=True)
        config = json.loads((model_path / "config.json").read_text(encoding="utf-8"))
        report["architectures"] = config.get("architectures", [])
        report["model_config_sha256"] = hashlib.sha256((model_path / "config.json").read_bytes()).hexdigest()
        index = model_path / "model.safetensors.index.json"
        if index.is_file():
            report["model_index_sha256"] = hashlib.sha256(index.read_bytes()).hexdigest()
            keys = json.loads(index.read_text(encoding="utf-8"))["weight_map"]
            pattern = re.compile(PLAN["candidate_lora"]["target_modules_regex"])
            selected = sorted({k.removesuffix(".weight") for k in keys
                               if k.endswith(".weight") and pattern.fullmatch(k.removesuffix(".weight"))})
            report["candidate_index_modules"] = selected
            report["candidate_index_module_count"] = len(selected)
            report["instantiated_module_compatibility_verified"] = False
        if module_audit:
            if not index.is_file():
                raise ValueError("module audit requires the local model index for comparison")
            report["meta_module_audit"] = meta_module_audit(model_path, report["candidate_index_modules"])
            report["instantiated_module_compatibility_verified"] = report["meta_module_audit"]["status"] == "PASS"
        if tokenizer_smoke:
            from transformers import AutoTokenizer
            tokenizer = AutoTokenizer.from_pretrained(str(model_path), local_files_only=True, trust_remote_code=False)
            if not getattr(tokenizer, "chat_template", None):
                tokenizer.chat_template = (model_path / "chat_template.jinja").read_text(encoding="utf-8")
            # Protected prompt example is a UNIT TEST, never exported as training data.
            messages = [{"role": "system", "content": SFT_SYSTEM},
                        {"role": "user", "content": "停车"},
                        {"role": "assistant", "content": '{"action":"STOP"}'}]
            try:
                result = assistant_token_mask(tokenizer, messages)
                report["tokenizer_smoke"] = {"status": "PASS", "scope": "UNIT_TEST_ONLY_NOT_TRAINING_SAMPLE",
                    "prompt_tokens": result["prompt_tokens"], "assistant_tokens": result["assistant_tokens"],
                    "prompt_loss_masked": all(v == -100 for v in result["labels"][:result["prompt_tokens"]])}
            except ValueError as error:
                report["tokenizer_smoke"] = {"status": "FAIL", "reason": str(error)}
    elif tokenizer_smoke or module_audit:
        raise ValueError("tokenizer/module audit requires a local model path")
    return report
