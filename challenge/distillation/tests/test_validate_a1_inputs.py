from __future__ import annotations

import pytest

torch = pytest.importorskip("torch")

from challenge.distillation.a1_student import build_a1_input_packer  # noqa: E402
from challenge.distillation.dataset import (  # noqa: E402
    DistillationDataset, build_mock_records, make_collate_fn,
)
from challenge.distillation.validate_a1_inputs import check_packed_batch  # noqa: E402


def test_a1_input_shape_gate_accepts_real_packer_and_rejects_nonfinite() -> None:
    dataset = DistillationDataset(build_mock_records(2))
    collate = make_collate_fn(input_packer=build_a1_input_packer())
    batch = collate([dataset[0], dataset[1]])
    check_packed_batch(batch, 2)
    batch["model_inputs"]["state"][0, 0] = float("nan")
    with pytest.raises(ValueError, match="non-finite"):
        check_packed_batch(batch, 2)
