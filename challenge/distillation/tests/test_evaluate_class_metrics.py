from __future__ import annotations

import math

import pytest

torch = pytest.importorskip("torch")

from challenge.distillation.dataset import (  # noqa: E402
    DistillationDataset, build_mock_records, make_collate_fn,
)
from challenge.distillation.dummy_student import DummyStudent  # noqa: E402
from challenge.distillation.evaluate import evaluate  # noqa: E402
from challenge.distillation.losses import MultiHeadDistillationLoss  # noqa: E402


def test_validation_reports_each_class_across_single_class_batches() -> None:
    dataset = DistillationDataset(build_mock_records(5))
    collate = make_collate_fn()
    batches = [collate([dataset[index]]) for index in range(len(dataset))]
    metrics = evaluate(
        DummyStudent(), batches, MultiHeadDistillationLoss(),
        device=torch.device("cpu"), max_targets=8,
    )
    for sample_class in ("normal", "complex", "safety_critical"):
        assert math.isfinite(metrics[f"{sample_class}_behavior_accuracy"])
        assert math.isfinite(metrics[f"{sample_class}_plan_sequence_accuracy"])
    weighted = (
        2 * metrics["normal_behavior_accuracy"]
        + 2 * metrics["complex_behavior_accuracy"]
        + metrics["safety_critical_behavior_accuracy"]
    ) / 5
    assert metrics["behavior_accuracy"] == pytest.approx(weighted)
