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


def test_3b_is_explicit_and_never_the_default() -> None:
    profile = get_qwen_profile("qwen25vl-3b-bf16")

    assert profile.model == "Qwen/Qwen2.5-VL-3B-Instruct"
    assert profile.optional is True


def test_unknown_profile_fails_closed() -> None:
    with pytest.raises(ValueError, match="unsupported Qwen profile"):
        get_qwen_profile("fastest")


def test_all_revisions_are_immutable() -> None:
    for name in ("qwen3vl-2b-int4", "qwen3vl-2b-fp8", "qwen25vl-3b-bf16"):
        assert get_qwen_profile(name).revision not in {"main", "master", "latest"}
