"""Read-only inventory and CPU token-mask smoke; never load model weights."""
from __future__ import annotations

from importlib import metadata
import json
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


def inventory(model_path: Path | None = None, *, tokenizer_smoke: bool = False) -> dict:
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
        index = model_path / "model.safetensors.index.json"
        if index.is_file():
            keys = json.loads(index.read_text(encoding="utf-8"))["weight_map"]
            pattern = re.compile(PLAN["candidate_lora"]["target_modules_regex"])
            selected = sorted({k.removesuffix(".weight") for k in keys
                               if k.endswith(".weight") and pattern.fullmatch(k.removesuffix(".weight"))})
            report["candidate_index_modules"] = selected
            report["candidate_index_module_count"] = len(selected)
            report["instantiated_module_compatibility_verified"] = False
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
    elif tokenizer_smoke:
        raise ValueError("tokenizer smoke requires a local model path")
    return report
