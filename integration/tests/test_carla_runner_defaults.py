from __future__ import annotations

from integration.carla_runner import DEFAULT_QWEN_MODEL


def test_default_qwen_model_is_the_competition_2b_model() -> None:
    assert DEFAULT_QWEN_MODEL == "Qwen/Qwen3.5-2B"
