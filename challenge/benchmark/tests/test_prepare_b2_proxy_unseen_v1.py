from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from challenge.benchmark.policy_manifest import (
    build_policy_manifest,
    canonical_policy_manifest_json,
    load_benchmark_policy_config,
    policy_manifest_sha256,
)
from tools.prepare_b2_proxy_unseen_v1 import (
    FreezeError,
    _build_exposure,
    _canonical_json_line,
    _derive_seed,
    _materialize_scenario,
    _read_json,
    _validate_base_membership,
)


ROOT = Path(__file__).resolve().parents[3]
BENCHMARK_ROOT = ROOT / "challenge" / "benchmark" / "b2_proxy_unseen_v1"


def test_tracked_policy_manifest_is_canonical_and_matches_config() -> None:
    config = load_benchmark_policy_config(BENCHMARK_ROOT / "benchmark_config.yaml")
    generated = build_policy_manifest(config)
    tracked_path = BENCHMARK_ROOT / "policy_manifest.json"
    tracked = json.loads(tracked_path.read_text(encoding="utf-8"))
    payload = tracked_path.read_bytes()

    assert tracked == generated
    assert payload == canonical_policy_manifest_json(generated)
    assert policy_manifest_sha256(generated) == hashlib.sha256(payload).hexdigest()


def test_seed_derivation_is_deterministic_unique_and_rejects_exposure() -> None:
    forbidden = {123, 456}
    first_allocated: set[int] = set()
    second_allocated: set[int] = set()

    first = _derive_seed("freeze", "seen", "000", forbidden, first_allocated)
    repeated = _derive_seed("freeze", "seen", "000", forbidden, second_allocated)
    next_seed = _derive_seed("freeze", "seen", "001", forbidden, first_allocated)

    assert first == repeated
    assert first not in forbidden
    assert next_seed not in forbidden
    assert first != next_seed


@pytest.mark.parametrize(
    ("cohort", "base_id", "exposed", "expected"),
    [
        ("seen", "KNOWN", {"KNOWN"}, True),
        ("variant", "KNOWN", {"KNOWN"}, True),
        ("unseen", "NEW", {"KNOWN"}, False),
    ],
)
def test_base_membership_accepts_only_declared_cohort_semantics(
    cohort: str,
    base_id: str,
    exposed: set[str | int],
    expected: bool,
) -> None:
    assert _validate_base_membership(
        cohort=cohort,
        base_id=base_id,
        exposed_scenario_ids=exposed,
    ) is expected


@pytest.mark.parametrize(
    ("cohort", "base_id", "exposed"),
    [
        ("seen", "NEW", {"KNOWN"}),
        ("variant", "NEW", {"KNOWN"}),
        ("unseen", "KNOWN", {"KNOWN"}),
        ("other", "NEW", {"KNOWN"}),
    ],
)
def test_base_membership_fails_closed_on_overlap_or_bad_cohort(
    cohort: str,
    base_id: str,
    exposed: set[str | int],
) -> None:
    with pytest.raises(FreezeError):
        _validate_base_membership(
            cohort=cohort,
            base_id=base_id,
            exposed_scenario_ids=exposed,
        )


def test_design_cohorts_obey_exposure_boundary_and_slot_counts() -> None:
    design = _read_json(BENCHMARK_ROOT / "acquisition_design.json")
    _, exposed = _build_exposure(ROOT, design)
    cohorts = design["cohorts"]
    samples_per_base = design["samples_per_base"]
    expected = design["expected_slots"]

    for cohort in ("seen", "variant", "unseen"):
        assert len(cohorts[cohort]) * samples_per_base == expected[cohort]
        for relative_path in cohorts[cohort]:
            scenario = _read_json(ROOT / relative_path)
            _validate_base_membership(
                cohort=cohort,
                base_id=scenario["scenario_id"],
                exposed_scenario_ids=exposed["scenario_id"],
            )

    assert sum(expected[name] for name in ("seen", "variant", "unseen")) == expected["total"]


def test_materialized_scenario_uses_design_freeze_id_and_jsonl_is_one_line() -> None:
    raw = _read_json(ROOT / "scenarios" / "acceptance_suite" / "basic" / "ACC_B02_set_speed_20.json")
    design = _read_json(BENCHMARK_ROOT / "acquisition_design.json")
    scenario = _materialize_scenario(
        raw,
        freeze_id=design["freeze_id"],
        cohort="seen",
        slot_id="000",
        seed=987654321,
        repeat_index=0,
        axes=design["variant_axes"],
        base_path="scenarios/acceptance_suite/basic/ACC_B02_set_speed_20.json",
    )
    payload = _canonical_json_line({"slot": scenario["scenario_id"]})

    assert scenario["extensions"]["b2_benchmark_case"]["freeze_id"] == design["freeze_id"]
    assert payload.endswith(b"\n")
    assert payload.count(b"\n") == 1
    assert json.loads(payload) == {"slot": scenario["scenario_id"]}
