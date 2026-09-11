import pytest

torch = pytest.importorskip("torch")

from challenge.distillation.dataset import (  # noqa: E402
    DistillationDataset,
    build_mock_records,
    make_collate_fn,
)
from challenge.distillation.dummy_student import DummyStudent  # noqa: E402
from challenge.distillation.student_contract import validate_student_outputs  # noqa: E402


def test_student_contract_accepts_expected_heads_and_rejects_bad_shape() -> None:
    dataset = DistillationDataset(build_mock_records(4))
    batch = make_collate_fn()([dataset[index] for index in range(4)])
    outputs = DummyStudent()(batch["model_inputs"])

    validate_student_outputs(outputs, batch["labels"], max_targets=8)
    outputs["behavior_logits"] = outputs["behavior_logits"][:, :3]
    with pytest.raises(ValueError, match="behavior_logits.*shape"):
        validate_student_outputs(outputs, batch["labels"], max_targets=8)


def test_student_contract_rejects_non_finite_head() -> None:
    dataset = DistillationDataset(build_mock_records(2))
    batch = make_collate_fn()([dataset[index] for index in range(2)])
    outputs = DummyStudent()(batch["model_inputs"])
    outputs["target_speed_mps"][0, 0] = float("nan")

    with pytest.raises(ValueError, match="NaN or infinity"):
        validate_student_outputs(outputs, batch["labels"], max_targets=8)
