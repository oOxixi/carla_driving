from __future__ import annotations

import pytest

from integration.qwen_profiles import get_qwen_profile, resolve_qwen_profile


def test_default_profile_is_2b_int4(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QWEN_PROFILE", raising=False)

    profile = resolve_qwen_profile(None)

    assert profile.name == "qwen3vl-2b-int4"
    assert profile.quantization == "gptq"
    assert profile.required_linear_kernel == "MarlinLinearKernel"
    assert profile.image_max_side == 256
    assert profile.visual_tokens == 64
    assert profile.port == 8001


def test_only_2b_profiles_are_supported() -> None:
    assert get_qwen_profile("qwen3vl-2b-fp8").optional is True
    with pytest.raises(ValueError, match="unsupported Qwen profile"):
        get_qwen_profile("qwen25vl-3b-bf16")
    with pytest.raises(ValueError, match="unsupported Qwen profile"):
        get_qwen_profile("qwen25vl-7b-awq")


def test_unknown_profile_fails_closed() -> None:
    with pytest.raises(ValueError, match="unsupported Qwen profile"):
        get_qwen_profile("fastest")


def test_all_revisions_are_immutable() -> None:
    for name in (
        "qwen3vl-2b-int4",
        "qwen3vl-2b-fp8",
    ):
        assert get_qwen_profile(name).revision not in {"main", "master", "latest"}
