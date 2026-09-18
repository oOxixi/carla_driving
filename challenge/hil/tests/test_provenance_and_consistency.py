from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from ..consistency import compare_outputs, compare_sources
from ..provenance import teacher_baseline, teacher_baselines


def _outputs(**overrides):
    base = {
        "plan_length_logits": np.zeros((1, 4), dtype=np.float32),
        "behavior_logits": np.zeros((1, 4, 14), dtype=np.float32),
    }
    base.update(overrides)
    return base


def test_compare_outputs_passes_for_identical_tensors():
    result = compare_outputs(_outputs(), _outputs())
    assert result["passed"] is True
    assert result["max_abs_diff_over_all_outputs"] == 0.0


def test_compare_outputs_flags_drift_beyond_tolerance():
    candidate = _outputs(behavior_logits=np.full((1, 4, 14), 1.0, dtype=np.float32))
    result = compare_outputs(_outputs(), candidate, rtol=1e-4, atol=1e-5)
    assert result["passed"] is False
    assert result["per_output"]["behavior_logits"]["allclose"] is False
    assert result["per_output"]["behavior_logits"]["max_abs_diff"] == pytest.approx(1.0)


def test_compare_outputs_reports_key_and_shape_mismatch():
    result = compare_outputs(_outputs(), {"plan_length_logits": np.zeros((1, 3), dtype=np.float32)})
    assert result["passed"] is False
    assert result["missing_outputs"] == ["behavior_logits"]
    assert "shape_mismatch" in result["per_output"]["plan_length_logits"]


class _FakeSource:
    def __init__(self, name, outputs, identity=None):
        self.name = name
        self._outputs = outputs
        self.identity = identity or {"model_id": name}
        self.closed = False

    def outputs(self, request):
        value = self._outputs(request)
        if isinstance(value, Exception):
            raise value
        return value

    def close(self):
        self.closed = True


def test_compare_sources_aggregates_cases_and_survives_errors():
    good = _FakeSource("a", lambda request: _outputs())
    bad = _FakeSource(
        "b",
        lambda request: _outputs()
        if request["request_id"] == "ok"
        else RuntimeError("boom"),
    )
    report = compare_sources(
        good,
        bad,
        [{"request_id": "ok"}, {"request_id": "bad"}],
    )
    assert report["passed"] is False
    assert report["request_count"] == 2
    assert report["cases"][0]["passed"] is True
    assert "boom" in report["cases"][1]["error"]


def test_teacher_baseline_reads_the_pinned_manifest(tmp_path: Path):
    challenge = tmp_path / "challenge"
    challenge.mkdir()
    (challenge / "teacher_baseline_manifest.json").write_text(
        json.dumps(
            {
                "baseline_id": "teacher-baseline-v1",
                "git_sha": "a" * 40,
                "model_id": "Qwen/Qwen3.5-2B",
                "model_revision": "b" * 40,
                "artifact_fingerprint_sha256": "c" * 64,
            }
        ),
        encoding="utf-8",
    )
    baseline = teacher_baseline(tmp_path)
    assert baseline["status"] in {"PINNED", "TAG_MISMATCH"}
    assert baseline["baseline_id"] == "teacher-baseline-v1"
    assert baseline["git_sha"] == "a" * 40
    assert baseline["manifest_sha256"]
    # A repository without git history must not pretend the tag resolved.
    assert baseline["git_tag"]["tag"] == "teacher-baseline-v1"


def test_teacher_baseline_is_unresolved_without_the_manifest(tmp_path: Path):
    baseline = teacher_baseline(tmp_path)
    assert baseline["status"] == "UNRESOLVED"
    assert baseline["git_sha"] == "UNRESOLVED"


def _write_v1(tmp_path: Path, **overrides) -> None:
    payload = {
        "baseline_id": "teacher-baseline-v1",
        "git_sha": "a" * 40,
        "model_id": "Qwen/Qwen3.5-2B",
        "model_revision": "b" * 40,
        "artifact_fingerprint_sha256": "c" * 64,
    }
    payload.update(overrides)
    challenge = tmp_path / "challenge"
    challenge.mkdir(exist_ok=True)
    (challenge / "teacher_baseline_manifest.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )


def _write_v4(tmp_path: Path, **overrides) -> None:
    payload = {
        "teacher_profile": "b1-pinned-teacher-v4",
        "teacher_git_sha": "d" * 40,
        "model_id": "Qwen/Qwen3.5-2B",
        "model_revision": "b" * 40,
        "model_artifact_sha256": "c" * 64,
        "dtype": "bfloat16",
    }
    payload.update(overrides)
    challenge = tmp_path / "challenge"
    challenge.mkdir(exist_ok=True)
    (challenge / "teacher_pinned_manifest_v4.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )


def test_both_pins_are_recorded_and_v4_is_active(tmp_path: Path):
    _write_v1(tmp_path)
    _write_v4(tmp_path)
    baselines = teacher_baselines(tmp_path)
    assert baselines["active"] == "v4"
    assert baselines["v1"]["manifest_sha256"]
    assert baselines["v4"]["manifest_sha256"]
    assert baselines["v4"]["baseline_id"] == "b1-pinned-teacher-v4"
    assert baselines["v4"]["dtype"] == "bfloat16"
    # The same model, described by two governance versions.
    assert baselines["model_identity_consistent"] is True


def test_conflicting_pins_are_flagged_not_hidden(tmp_path: Path):
    _write_v1(tmp_path)
    _write_v4(tmp_path, model_revision="e" * 40)
    baselines = teacher_baselines(tmp_path)
    assert baselines["model_identity_consistent"] is False


def test_v4_alone_is_still_recorded(tmp_path: Path):
    _write_v4(tmp_path)
    baselines = teacher_baselines(tmp_path)
    assert baselines["active"] == "v4"
    assert baselines["v1"]["status"] == "UNRESOLVED"


def test_state_dict_fingerprint_is_stable_and_weights_sensitive():
    torch = pytest.importorskip("torch")
    from ..runtime_adapter import state_dict_fingerprint

    class Tiny(torch.nn.Module):
        def __init__(self, seed: int) -> None:
            super().__init__()
            torch.manual_seed(seed)
            self.linear = torch.nn.Linear(4, 2)

    first = state_dict_fingerprint(Tiny(1))
    again = state_dict_fingerprint(Tiny(1))
    different = state_dict_fingerprint(Tiny(2))
    assert len(first) == 64
    assert first == again
    assert first != different
