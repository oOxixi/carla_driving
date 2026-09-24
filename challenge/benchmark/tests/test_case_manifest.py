from pathlib import Path
import pytest

from challenge.benchmark.benchmark import load_benchmark_cases
from challenge.benchmark.case_manifest import (
    CaseManifestError,
    compute_case_set_digest,
    extract_case_identities,
    validate_independent_case_set,
)

ROOT = Path(__file__).resolve().parents[3]
RESERVED_PATH = (
    ROOT
    / "challenge"
    / "dataset"
    / "releases"
    / "d2_v1_1"
    / "reserved_test_candidates.jsonl"
)

def _case(
    sample_id: str,
    scenario_id: str,
    template_id: str | None = None,
) -> dict:
    metadata = {"scenario_id": scenario_id}

    if template_id is not None:
        metadata["template_id"] = template_id

    return {
        "sample_id": sample_id,
        "metadata": metadata,
    }


def test_case_set_digest_is_order_independent() -> None:
    identities = [
        {
            "sample_id": "sample-b",
            "scenario_id": "scenario-b",
            "template_id": "template-b",
        },
        {
            "sample_id": "sample-a",
            "scenario_id": "scenario-a",
            "template_id": "template-a",
        },
    ]

    assert compute_case_set_digest(
        identities
    ) == compute_case_set_digest(reversed(identities))


def test_missing_template_identity_fails_closed() -> None:
    cases = [_case("candidate-1", "scenario-c")]

    with pytest.raises(
        CaseManifestError,
        match="missing template identity",
    ):
        extract_case_identities(cases)


@pytest.mark.parametrize(
    ("candidate", "training", "development", "expected_field"),
    [
        (
            _case("same-sample", "scenario-c", "template-c"),
            _case("same-sample", "scenario-a", "template-a"),
            _case("dev-1", "scenario-b", "template-b"),
            "sample_id",
        ),
        (
            _case("candidate-1", "same-scenario", "template-c"),
            _case("train-1", "same-scenario", "template-a"),
            _case("dev-1", "scenario-b", "template-b"),
            "scenario_id",
        ),
        (
            _case("candidate-1", "scenario-c", "same-template"),
            _case("train-1", "scenario-a", "same-template"),
            _case("dev-1", "scenario-b", "template-b"),
            "template_id",
        ),
    ],
)
def test_independence_overlap_is_rejected(
    candidate: dict,
    training: dict,
    development: dict,
    expected_field: str,
) -> None:
    with pytest.raises(
        CaseManifestError,
        match=expected_field,
    ):
        validate_independent_case_set(
            [candidate],
            [training],
            [development],
        )


def test_external_template_mapping_can_supply_b1_evidence() -> None:
    candidate = [_case("candidate-1", "scenario-c")]
    training = [_case("train-1", "scenario-a")]
    development = [_case("dev-1", "scenario-b")]

    template_ids = {
        "candidate-1": "template-c",
        "train-1": "template-a",
        "dev-1": "template-b",
    }

    result = validate_independent_case_set(
        candidate,
        training,
        development,
        template_ids=template_ids,
    )

    assert result["sample_count"] == 1
    assert len(result["case_set_digest"]) == 64
    assert result["independence"] == {
        "sample_id_overlap_count": 0,
        "scenario_id_overlap_count": 0,
        "template_id_overlap_count": 0,
    }

def test_d2_reserved_candidates_are_not_independence_evidence() -> None:
    """
    Reserved D2 cases are readable, but lack template identity evidence.

    B2 must not silently promote them to independent Validation.
    """
    cases = load_benchmark_cases(RESERVED_PATH)

    assert len(cases) == 540

    with pytest.raises(
        CaseManifestError,
        match="missing template identity",
    ):
        extract_case_identities(cases)