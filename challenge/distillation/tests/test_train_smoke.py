from pathlib import Path
from copy import deepcopy
import json

import pytest

pytest.importorskip("torch")
yaml = pytest.importorskip("yaml")

from challenge.distillation.train import run_training  # noqa: E402
from challenge.distillation.dataset import build_mock_records  # noqa: E402


DISTILLATION_ROOT = Path(__file__).resolve().parents[1]


def _use_fast_dummy(config: dict) -> None:
    config["model"] = {
        "model_id": "dummy-student-d1",
        "factory": "challenge.distillation.dummy_student:build_dummy_student",
        "options": {"feature_dim": 32, "hidden_dim": 48},
    }
    config.pop("input", None)
    config["training"]["max_updates"] = 0


def test_mock_training_saves_reproducible_checkpoint_and_metrics(tmp_path: Path) -> None:
    config = yaml.safe_load(
        (DISTILLATION_ROOT / "train_config.yaml").read_text(encoding="utf-8")
    )
    _use_fast_dummy(config)
    config["dataset"]["mock_samples"] = 64
    config["training"]["epochs"] = 2
    config["training"]["batch_size"] = 16

    summary = run_training(config, smoke=True, output_dir_override=tmp_path)

    assert summary["smoke_only"] is True
    assert summary["train_samples"] + summary["validation_samples"] == 64
    assert summary["epochs_completed"] == 2
    assert summary["global_step"] > 0
    assert len(summary["best_checkpoint_sha256"]) == 64
    assert (tmp_path / "student_fp32_best.pt").is_file()
    assert (tmp_path / "training.jsonl").is_file()
    assert (tmp_path / "training_summary.json").is_file()
    assert (tmp_path / "training_report.md").is_file()
    assert (tmp_path / "hard_cases" / "validation_errors.jsonl").is_file()
    assert (tmp_path / "hard_cases" / "summary.json").is_file()


def test_real_data_integration_gate_preflights_and_limits_training(tmp_path: Path) -> None:
    config = yaml.safe_load(
        (DISTILLATION_ROOT / "train_config.yaml").read_text(encoding="utf-8")
    )
    _use_fast_dummy(config)
    records = build_mock_records(32)
    train_path, val_path = tmp_path / "train.jsonl", tmp_path / "validation.jsonl"

    def write(path: Path, rows: list[dict], split: str) -> None:
        encoded = []
        for row in rows:
            copied = deepcopy(row)
            copied["metadata"]["split"] = split
            copied["metadata"]["dataset_version"] = "b1-v1"
            encoded.append(json.dumps(copied))
        path.write_text("\n".join(encoded) + "\n", encoding="utf-8")

    write(train_path, records[:24], "train")
    write(val_path, records[24:], "validation")
    config["dataset"].update({
        "version": "b1-v1", "train_path": str(train_path), "val_path": str(val_path),
    })
    config["training"]["batch_size"] = 8

    summary = run_training(
        config, integration_smoke=True, output_dir_override=tmp_path / "gate",
    )

    assert summary["smoke_only"] is False
    assert summary["integration_smoke_only"] is True
    assert summary["global_step"] <= 2
    assert (tmp_path / "gate" / "dataset_preflight.json").is_file()
