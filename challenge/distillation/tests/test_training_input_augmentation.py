from __future__ import annotations

import pytest
import torch

from challenge.distillation.train import (
    _apply_training_input_augmentation,
    _validate_config,
)


def test_train_only_augmentation_masks_requested_modalities() -> None:
    torch.manual_seed(7)
    inputs = {
        "text_tokens": torch.ones((64, 32)),
        "rgb": torch.ones((64, 3, 8, 8)),
        "targets": torch.ones((64, 8, 14)),
        "state": torch.ones((64, 64)),
    }
    augmented = _apply_training_input_augmentation(
        inputs,
        {
            "enabled": True,
            "text_full_dropout_probability": 0.5,
            "text_token_dropout_probability": 0.2,
            "rgb_dropout_probability": 0.5,
        },
    )

    assert torch.count_nonzero(augmented["text_tokens"]) < torch.numel(inputs["text_tokens"])
    assert torch.count_nonzero(augmented["rgb"]) < torch.numel(inputs["rgb"])
    assert torch.equal(augmented["targets"], inputs["targets"])
    assert torch.equal(augmented["state"], inputs["state"])
    assert torch.equal(inputs["text_tokens"], torch.ones_like(inputs["text_tokens"]))
    assert torch.equal(inputs["rgb"], torch.ones_like(inputs["rgb"]))


def test_disabled_augmentation_preserves_inputs() -> None:
    inputs = {
        "text_tokens": torch.ones((2, 32)),
        "rgb": torch.ones((2, 3, 8, 8)),
    }
    augmented = _apply_training_input_augmentation(inputs, {"enabled": False})
    assert torch.equal(augmented["text_tokens"], inputs["text_tokens"])
    assert torch.equal(augmented["rgb"], inputs["rgb"])


@pytest.mark.parametrize("value", [-0.01, 1.0])
def test_augmentation_probability_is_validated(value: float) -> None:
    config = {
        "config_id": "test",
        "seed": 1,
        "teacher": {},
        "contract": {"max_steps": 4, "max_targets": 8},
        "dataset": {},
        "model": {},
        "training": {"batch_size": 1, "epochs": 1},
        "sampling": {},
        "loss_weights": {},
        "distillation": {},
        "output": {},
        "training_input_augmentation": {
            "text_full_dropout_probability": value,
        },
    }
    with pytest.raises(ValueError, match="must be in"):
        _validate_config(config)
