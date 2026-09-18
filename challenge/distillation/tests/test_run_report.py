from __future__ import annotations

from pathlib import Path

from challenge.distillation.run_report import write_training_report


def test_report_distinguishes_selected_checkpoint_from_last_epoch(tmp_path: Path) -> None:
    path = tmp_path / "report.md"
    write_training_report(
        path,
        {"best_validation": {"target_speed_mae": 0.97}, "smoke_only": False},
        [{"validation": {"target_speed_mae": 0.98}}],
    )
    text = path.read_text(encoding="utf-8")
    assert "Selected best-checkpoint validation" in text
    assert "target_speed_mae: `0.970000`" in text
    assert "target_speed_mae: `0.980000`" in text
    assert "not an independent unseen-scenario" in text
