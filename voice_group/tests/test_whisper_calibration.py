from __future__ import annotations

import numpy as np
import pytest

from tools.calibrate_whisper_confidence import calibrate, fit_platt


def test_platt_fit_ranks_high_raw_probability_as_more_correct() -> None:
    raw = [0.55, 0.60, 0.65, 0.88, 0.92, 0.97]
    labels = [False, False, False, True, True, True]
    intercept, slope = fit_platt(raw, labels, regularization=0.1)

    assert np.isfinite(intercept)
    assert slope > 0
    assert calibrate(0.95, intercept, slope) > calibrate(
        0.60,
        intercept,
        slope,
    )


def test_platt_output_is_a_probability() -> None:
    value = calibrate(0.8, intercept=-1.0, slope=0.5)
    assert value == pytest.approx(value)
    assert 0.0 < value < 1.0
