from __future__ import annotations

import pytest

torch = pytest.importorskip("torch")

from challenge.distillation.ablation_eval import masked_batches  # noqa: E402


def test_masked_batches_changes_only_requested_modality() -> None:
    batch = {"model_inputs": {"rgb": torch.ones(1, 3), "state": torch.ones(1, 2)}}
    result = list(masked_batches([batch], "rgb"))[0]
    assert result["model_inputs"]["rgb"].sum().item() == 0
    assert result["model_inputs"]["state"].sum().item() == 2
    assert batch["model_inputs"]["rgb"].sum().item() == 3
    with pytest.raises(ValueError, match="unknown modality"):
        list(masked_batches([batch], "label"))
