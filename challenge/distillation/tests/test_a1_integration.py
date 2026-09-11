import pytest

torch = pytest.importorskip("torch")

from challenge.distillation.a1_student import (  # noqa: E402
    build_a1_input_packer,
    build_a1_student,
)
from challenge.distillation.dataset import (  # noqa: E402
    DistillationDataset,
    build_mock_records,
    make_collate_fn,
)
from challenge.distillation.label_encoder import DistillationLabelEncoder  # noqa: E402
from challenge.distillation.losses import MultiHeadDistillationLoss  # noqa: E402
from challenge.distillation.student_contract import (  # noqa: E402
    forward_student,
    validate_student_outputs,
)
from challenge.student.contract import (  # noqa: E402
    BEHAVIORS,
    TARGET_LANES,
)


def test_a3_labels_use_a1_frozen_indices() -> None:
    records = build_mock_records(5)
    target_record = records[2]
    targetless_record = records[0]
    encoder = DistillationLabelEncoder()

    grounded = encoder.encode(
        target_record["input"], target_record["teacher"]["maneuver_plan"],
    )
    targetless = encoder.encode(
        targetless_record["input"], targetless_record["teacher"]["maneuver_plan"],
    )

    assert grounded["target_pointer"][0] == 0
    assert targetless["target_pointer"][0] == 8
    assert targetless["target_lane"][0] == TARGET_LANES.index("CURRENT")
    assert targetless["behavior"][0] == BEHAVIORS.index("KEEP_LANE")
    assert targetless["target_pointer"][1:] == [8, 8, 8]


def test_real_a1_student_runs_a3_forward_loss_and_backward() -> None:
    dataset = DistillationDataset(build_mock_records(2))
    packer = build_a1_input_packer({"max_steps": 4, "max_targets": 8})
    batch = make_collate_fn(input_packer=packer)([dataset[0]])
    model = build_a1_student({"max_steps": 4, "max_targets": 8})

    outputs = forward_student(model, batch["model_inputs"])
    validate_student_outputs(outputs, batch["labels"], max_targets=8)
    loss, _ = MultiHeadDistillationLoss()(outputs, batch["labels"])
    loss.backward()

    assert torch.isfinite(loss)
    assert any(parameter.grad is not None for parameter in model.parameters())
