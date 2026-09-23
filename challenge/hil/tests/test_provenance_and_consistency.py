from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from ..consistency import compare_outputs, compare_plans, compare_sources
from ..identity import CandidateIdentity
from ..provenance import teacher_baseline, teacher_baselines
from ..stages import StageTrace


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


class _PlanRuntime:
    """Minimal runtime whose infer path returns a fixed plan."""

    name = "plan-fake"
    identity = CandidateIdentity(
        git_sha="0" * 40,
        model_id="m",
        model_sha256="1" * 64,
        dataset_version="d",
        config_id="c",
    )

    def __init__(self, plan):
        self._plan = plan

    def infer(self, request, *, case_id, round_index, phase="measured"):
        trace = StageTrace(trace_id=str(case_id), case_id=case_id, round_index=round_index)
        trace.mark("input_arrival", timestamp_ns=1_000)
        trace.mark("plan_ready", timestamp_ns=2_000)
        trace.finish("READY")
        return json.loads(json.dumps(self._plan)), trace

    def close(self):
        return None


class _ZeroSource:
    name = "zero"
    identity = {"model_id": "m"}

    def outputs(self, request):
        return {"head": np.zeros((1, 2), dtype=np.float32)}

    def close(self):
        return None


def _case(request_id: str):
    from ..replay import ReplayCase

    return ReplayCase(
        case_id=request_id,
        sample_id=request_id,
        scenario_id="SCN",
        request={"request_id": request_id, "command_id": "c"},
        teacher_plan=None,
        rgb_path=None,
        rgb_sha256=None,
        rgb_resolved=False,
        rgb_source="test",
        source_file="test",
    )


def test_compare_plans_drives_the_runtime_under_test():
    """The audited gap: consistency must exercise the SUT's own infer path."""
    plan = {"schema_version": "2.0", "steps": [{"behavior": "FOLLOW"}]}
    runtime = _PlanRuntime(plan)
    calls: list[str] = []

    def decode(request, outputs):
        calls.append(request["request_id"])
        return {"schema_version": "2.0", "steps": [{"behavior": "FOLLOW"}]}

    report = compare_plans(
        runtime,
        [_case("r1"), _case("r2")],
        reference=_ZeroSource(),
        decode_reference=decode,
    )
    assert calls == ["r1", "r2"], "the SUT runtime must be driven per case"
    assert report["passed"] is True
    assert report["mode"] == "plan_vs_reference_graph"
    assert report["runtime"]["name"] == "plan-fake"


def test_compare_plans_fails_when_the_runtime_plan_differs():
    plan = {"schema_version": "2.0", "steps": [{"behavior": "STOP"}]}
    report = compare_plans(
        _PlanRuntime(plan),
        [_case("r1")],
        reference=_ZeroSource(),
        decode_reference=lambda request, outputs: {
            "schema_version": "2.0",
            "steps": [{"behavior": "FOLLOW"}],
        },
    )
    assert report["passed"] is False
    assert report["cases"][0]["same_plan"] is False


def test_compare_plans_tolerates_float_noise_but_not_semantic_change():
    """A 6e-8 difference in `confidence` is float32 noise, not a mismatch."""
    base = {
        "schema_version": "2.0",
        "confidence": 0.37850677967071533,
        "steps": [{"behavior": "FOLLOW", "target": {"target_id": "C-0001"}}],
    }
    noisy = json.loads(json.dumps(base))
    noisy["confidence"] = 0.37850672006607056  # Δ ≈ 6e-8, the real observed drift
    report = compare_plans(
        _PlanRuntime(noisy),
        [_case("r1")],
        reference=_ZeroSource(),
        decode_reference=lambda request, outputs: base,
    )
    assert report["passed"] is True, report["cases"][0]
    assert report["cases"][0]["numeric_max_abs_diff"] < 1e-6

    # A different behaviour is a semantic change and must fail.
    changed = json.loads(json.dumps(base))
    changed["steps"][0]["behavior"] = "STOP"
    report2 = compare_plans(
        _PlanRuntime(changed),
        [_case("r1")],
        reference=_ZeroSource(),
        decode_reference=lambda request, outputs: base,
    )
    assert report2["passed"] is False
    assert any("behavior" in item for item in report2["cases"][0]["structural_diffs"])


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
