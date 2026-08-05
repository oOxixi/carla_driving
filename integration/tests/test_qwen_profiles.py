from __future__ import annotations

import pytest

from integration.qwen_profiles import get_qwen_profile, resolve_qwen_profile
from tools.verify_qwen7b_awq_kernel import verify_awq_marlin_log


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


def test_7b_awq_is_a800_migration_profile() -> None:
    profile = get_qwen_profile("qwen25vl-7b-awq")

    assert profile.model == "Qwen/Qwen2.5-VL-7B-Instruct-AWQ"
    assert profile.revision == "536a35794df8831aa814970ee8f89eff577e7718"
    assert profile.quantization == "awq_marlin"
    assert profile.required_linear_kernel == "MarlinLinearKernel"
    assert profile.visual_tokens == 64
    assert profile.optional is True


def test_unknown_profile_fails_closed() -> None:
    with pytest.raises(ValueError, match="unsupported Qwen profile"):
        get_qwen_profile("fastest")


def test_all_revisions_are_immutable() -> None:
    for name in (
        "qwen3vl-2b-int4",
        "qwen3vl-2b-fp8",
        "qwen25vl-3b-bf16",
        "qwen25vl-7b-awq",
    ):
        assert get_qwen_profile(name).revision not in {"main", "master", "latest"}


def test_7b_kernel_log_must_prove_awq_marlin(tmp_path) -> None:
    log = tmp_path / "vllm.log"
    log.write_text(
        "model=Qwen/Qwen2.5-VL-7B-Instruct-AWQ quantization=awq_marlin\n"
        "Using MarlinLinearKernel for AWQMarlinLinearMethod\n",
        encoding="utf-8",
    )
    assert verify_awq_marlin_log(log)["quantization"] == "awq_marlin"

    log.write_text(
        "model=Qwen/Qwen2.5-VL-7B-Instruct-AWQ quantization=awq\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="awq_marlin"):
        verify_awq_marlin_log(log)
