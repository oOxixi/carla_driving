"""Immutable Qwen model profiles shared by remote serving and evaluation."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class QwenModelProfile:
    name: str
    model: str
    revision: str
    quantization: str
    required_linear_kernel: str | None
    image_max_side: int
    visual_tokens: int
    port: int
    prompt_style: str
    optional: bool


_PROFILES = {
    "qwen3vl-2b-int4": QwenModelProfile(
        name="qwen3vl-2b-int4",
        model="h2oai/Qwen3-VL-2B-Instruct-GPTQ-Int4",
        revision="f91db2369bd00e7ec20bf09b6a0080cdb26aefa5",
        quantization="gptq",
        required_linear_kernel="MarlinLinearKernel",
        image_max_side=256,
        visual_tokens=64,
        port=8001,
        prompt_style="compact-v2",
        optional=False,
    ),
    "qwen3vl-2b-fp8": QwenModelProfile(
        name="qwen3vl-2b-fp8",
        model="Qwen/Qwen3-VL-2B-Instruct-FP8",
        revision="46485250d8854c0a9be4f1adbc67ca47e5bb6fa5",
        quantization="fp8",
        required_linear_kernel=None,
        image_max_side=256,
        visual_tokens=64,
        port=8001,
        prompt_style="compact-v2",
        optional=True,
    ),
    "qwen25vl-3b-bf16": QwenModelProfile(
        name="qwen25vl-3b-bf16",
        model="Qwen/Qwen2.5-VL-3B-Instruct",
        revision="66285546d2b821cf421d4f5eb2576359d3770cd3",
        quantization="bf16",
        required_linear_kernel=None,
        image_max_side=224,
        visual_tokens=256,
        port=8002,
        prompt_style="compact-v2",
        optional=True,
    ),
    "qwen25vl-7b-awq": QwenModelProfile(
        name="qwen25vl-7b-awq",
        model="Qwen/Qwen2.5-VL-7B-Instruct-AWQ",
        revision="536a35794df8831aa814970ee8f89eff577e7718",
        quantization="awq_marlin",
        required_linear_kernel="MarlinLinearKernel",
        image_max_side=224,
        visual_tokens=64,
        port=8001,
        prompt_style="compact-v2",
        optional=True,
    ),
}


def get_qwen_profile(name: str) -> QwenModelProfile:
    try:
        return _PROFILES[name]
    except KeyError as exc:
        raise ValueError(f"unsupported Qwen profile: {name}") from exc


def resolve_qwen_profile(name: str | None) -> QwenModelProfile:
    return get_qwen_profile(name or os.getenv("QWEN_PROFILE", "qwen3vl-2b-int4"))


__all__ = ["QwenModelProfile", "get_qwen_profile", "resolve_qwen_profile"]
