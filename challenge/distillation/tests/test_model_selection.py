from __future__ import annotations

import pytest

pytest.importorskip("torch")

from challenge.distillation.train import _selection_key, _selection_tiebreakers  # noqa: E402


def test_saturated_primary_metric_uses_loss_then_speed_mae() -> None:
    tiebreakers = _selection_tiebreakers(None)
    early = _selection_key(
        {"plan_sequence_accuracy": 1.0, "loss": 0.50, "target_speed_mae": 1.15},
        selection_metric="plan_sequence_accuracy",
        tiebreakers=tiebreakers,
    )
    later = _selection_key(
        {"plan_sequence_accuracy": 1.0, "loss": 0.18, "target_speed_mae": 0.52},
        selection_metric="plan_sequence_accuracy",
        tiebreakers=tiebreakers,
    )
    assert later is not None and early is not None and later > early


def test_primary_metric_still_dominates_tiebreakers() -> None:
    tiebreakers = _selection_tiebreakers([{"metric": "loss", "mode": "min"}])
    lower_accuracy = _selection_key(
        {"plan_sequence_accuracy": 0.9, "loss": 0.01},
        selection_metric="plan_sequence_accuracy",
        tiebreakers=tiebreakers,
    )
    higher_accuracy = _selection_key(
        {"plan_sequence_accuracy": 1.0, "loss": 1.0},
        selection_metric="plan_sequence_accuracy",
        tiebreakers=tiebreakers,
    )
    assert higher_accuracy is not None and lower_accuracy is not None
    assert higher_accuracy > lower_accuracy


def test_selection_rejects_unknown_or_nonfinite_tiebreakers() -> None:
    with pytest.raises(ValueError, match="unknown selection tie-breaker"):
        _selection_key(
            {"plan_sequence_accuracy": 1.0},
            selection_metric="plan_sequence_accuracy",
            tiebreakers=[{"metric": "loss", "mode": "min"}],
        )
    assert _selection_key(
        {"plan_sequence_accuracy": 1.0, "loss": float("nan")},
        selection_metric="plan_sequence_accuracy",
        tiebreakers=[{"metric": "loss", "mode": "min"}],
    ) is None


def test_selection_tiebreaker_config_is_fail_closed() -> None:
    with pytest.raises(ValueError, match="must be a list"):
        _selection_tiebreakers("loss")
    with pytest.raises(ValueError, match="mode must be min or max"):
        _selection_tiebreakers([{"metric": "loss", "mode": "sideways"}])
