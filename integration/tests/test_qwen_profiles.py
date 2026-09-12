from __future__ import annotations

import pytest

from integration.qwen_profiles import (
    PRODUCTION_QWEN_ARTIFACT_SHA256,
    PRODUCTION_QWEN_MODEL,
    PRODUCTION_QWEN_REVISION,
    get_qwen_profile,
    get_qwen_profile_by_model,
    resolve_qwen_profile,
)


def test_default_profile_is_pinned_production_2b(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("QWEN_PROFILE", raising=False)

    profile = resolve_qwen_profile(None)

    assert profile.name == "qwen3.5-2b"
    assert profile.model == PRODUCTION_QWEN_MODEL
    assert profile.revision == PRODUCTION_QWEN_REVISION
    assert profile.quantization == "bfloat16"
    assert profile.required_linear_kernel is None
    assert profile.image_max_side == 224
    assert profile.visual_tokens == 64
    assert profile.port == 8000
    assert profile.optional is False
    assert len(PRODUCTION_QWEN_ARTIFACT_SHA256) == 64


def test_production_model_id_resolves_to_pinned_profile() -> None:
    profile = get_qwen_profile_by_model(PRODUCTION_QWEN_MODEL)

    assert profile.name == "qwen3.5-2b"
    assert profile.revision == PRODUCTION_QWEN_REVISION


def test_only_2b_profiles_are_supported() -> None:
    assert get_qwen_profile("qwen3vl-2b-int4").optional is True
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
        "qwen3.5-2b",
        "qwen3vl-2b-int4",
        "qwen3vl-2b-fp8",
    ):
        assert get_qwen_profile(name).revision not in {"main", "master", "latest"}
