from pathlib import Path

import pytest

torch = pytest.importorskip("torch")

from challenge.distillation.checkpoint import load_checkpoint, save_checkpoint  # noqa: E402
from challenge.distillation.train import run_training  # noqa: E402

yaml = pytest.importorskip("yaml")
DISTILLATION_ROOT = Path(__file__).resolve().parents[1]


def _use_fast_dummy(config: dict) -> None:
    config["model"] = {
        "model_id": "dummy-student-d1",
        "factory": "challenge.distillation.dummy_student:build_dummy_student",
        "options": {"feature_dim": 32, "hidden_dim": 48},
    }
    config.pop("input", None)
    config["training"]["max_updates"] = 0


def test_checkpoint_restores_model_optimizer_and_progress(tmp_path: Path) -> None:
    model = torch.nn.Linear(3, 2)
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.01)
    expected = {name: value.detach().clone() for name, value in model.state_dict().items()}
    path = save_checkpoint(
        tmp_path / "resume.pt",
        model=model,
        optimizer=optimizer,
        epoch=2,
        global_step=17,
        best_metric=0.75,
        metadata={"dataset_version": "mock-v1"},
    )
    with torch.no_grad():
        for parameter in model.parameters():
            parameter.zero_()

    restored = load_checkpoint(path, model=model, optimizer=optimizer)

    assert restored["epoch"] == 2
    assert restored["global_step"] == 17
    assert restored["best_metric"] == pytest.approx(0.75)
    for name, value in model.state_dict().items():
        assert torch.equal(value, expected[name])


def test_epoch_boundary_resume_matches_uninterrupted_training(tmp_path: Path) -> None:
    config = yaml.safe_load(
        (DISTILLATION_ROOT / "train_config.yaml").read_text(encoding="utf-8")
    )
    _use_fast_dummy(config)
    config["dataset"]["mock_samples"] = 40
    config["training"]["epochs"] = 2
    config["training"]["batch_size"] = 8
    full_dir, resumed_dir = tmp_path / "full", tmp_path / "resumed"

    run_training(config, smoke=True, output_dir_override=full_dir)
    first_stage = yaml.safe_load(yaml.safe_dump(config))
    first_stage["training"]["epochs"] = 1
    run_training(first_stage, smoke=True, output_dir_override=resumed_dir)
    run_training(
        config,
        smoke=True,
        output_dir_override=resumed_dir,
        resume_override=resumed_dir / "student_fp32_last.pt",
    )

    full = torch.load(full_dir / "student_fp32_last.pt", weights_only=False)
    resumed = torch.load(resumed_dir / "student_fp32_last.pt", weights_only=False)
    assert resumed["global_step"] == full["global_step"]
    for name, value in full["model_state"].items():
        assert torch.equal(value, resumed["model_state"][name]), name
