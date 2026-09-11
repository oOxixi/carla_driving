import pytest

torch = pytest.importorskip("torch")

from challenge.distillation.dataset import (  # noqa: E402
    DistillationDataset,
    build_mock_records,
    make_collate_fn,
)
from challenge.distillation.class_balance import compute_class_weights  # noqa: E402
from challenge.distillation.dummy_student import DummyStudent  # noqa: E402
from challenge.distillation.losses import MultiHeadDistillationLoss  # noqa: E402


def test_multi_head_loss_is_finite_backpropagates_and_ignores_padding() -> None:
    dataset = DistillationDataset(build_mock_records(8))
    batch = make_collate_fn()([dataset[index] for index in range(len(dataset))])
    model = DummyStudent()
    outputs = model(batch["model_inputs"])
    loss_fn = MultiHeadDistillationLoss()

    total, components = loss_fn(outputs, batch["labels"])
    total.backward()

    assert torch.isfinite(total)
    assert set(components) == {
        "behavior", "target_pointer", "target_lane", "target_speed",
        "completion", "on_failure", "confidence", "replan", "plan_length",
        "requires_confirmation",
    }
    assert any(parameter.grad is not None for parameter in model.parameters())

    changed = {key: value.clone() for key, value in batch["labels"].items()}
    padding = ~changed["step_mask"]
    changed["behavior"][padding] = 3
    changed["target_pointer"][padding] = 2
    changed["target_lane"][padding] = 4
    changed["completion_type"][padding] = 5
    changed["on_failure"][padding] = 2
    changed["target_speed_mps"][padding] = 999.0
    changed_total, _ = loss_fn(outputs, changed)
    assert changed_total.item() == pytest.approx(total.item())


def test_train_only_class_balance_produces_usable_bounded_weights() -> None:
    dataset = DistillationDataset(build_mock_records(20))
    weights, counts = compute_class_weights(
        (dataset[index] for index in range(len(dataset))),
        heads=("behavior", "plan_length"), max_steps=4, max_targets=8,
        smoothing=1.0, max_weight=5.0,
    )
    batch = make_collate_fn()([dataset[index] for index in range(8)])
    model = DummyStudent()
    total, _ = MultiHeadDistillationLoss(class_weights=weights)(
        model(batch["model_inputs"]), batch["labels"],
    )

    assert len(weights["behavior"]) == 14
    assert len(counts["plan_length"]) == 4
    assert all(value > 0.0 for value in weights["behavior"])
    assert torch.isfinite(total)
