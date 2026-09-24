from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from challenge.benchmark.benchmark import load_benchmark_cases
from challenge.benchmark.case_manifest import (
    IDENTITY_FIELDS,
    CaseManifestError,
    compute_case_set_digest,
    extract_case_identities,
    normalized_request_sha256,
    source_text_sha256,
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


def _sample_id(
    run_id: str,
    command_id: str,
    request_id: str,
    frame_id: int,
) -> str:
    """Reproduce the B1 supervision-event sample identity contract."""
    identity = {
        "run_id": run_id,
        "command_id": command_id,
        "request_id": request_id,
        "frame_id": frame_id,
    }

    canonical = json.dumps(
        identity,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return "td_" + hashlib.sha256(canonical).hexdigest()[:24]


def _semantic_speed(key: str) -> float:
    value = int(
        hashlib.sha256(key.encode("utf-8")).hexdigest()[:8],
        16,
    )
    ratio = value / 0xFFFFFFFF
    return round(2.0 + ratio * 5.0, 6)


def _case(
    key: str,
    *,
    scenario_id: str | None = None,
    template_id: str | None = None,
    group_key: str | None = None,
    rgb_seed: str | None = None,
    source_text: str | None = None,
    request_semantics: str | None = None,
    event_key: str | None = None,
) -> dict:
    """
    Build a synthetic B1-shaped case with a valid supervision identity.

    key controls ordinary per-case identity.
    event_key may be shared deliberately to test event leakage.
    request_semantics may be shared deliberately to test normalized
    request leakage while transport identities remain different.
    """
    event_key = event_key or key
    semantic_key = request_semantics or key

    run_id = f"run-{event_key}"
    command_id = f"command-{event_key}"
    request_id = f"request-{event_key}"

    frame_id = int(
        hashlib.sha256(
            event_key.encode("utf-8")
        ).hexdigest()[:8],
        16,
    )

    sample_id = _sample_id(
        run_id,
        command_id,
        request_id,
        frame_id,
    )

    if group_key is None:
        group_key = hashlib.sha256(
            f"group-{key}".encode("utf-8")
        ).hexdigest()[:20]

    metadata = {
        "scenario_id": scenario_id or f"scenario-{key}",
        "group_key": group_key,
        "run_id": run_id,
        "command_id": command_id,
        "request_id": request_id,
        "frame_id": frame_id,
    }

    if template_id is not None:
        metadata["template_id"] = template_id

    return {
        "sample_id": sample_id,
        "metadata": metadata,
        "model_request": {
            "schema_version": "1.0",
            "request_id": request_id,
            "command_id": command_id,
            "created_at_ns": frame_id * 1000,
            "deadline_ns": frame_id * 1000 + 500,
            "rgb_ref": f"images/{key}.jpg",
            "source_text": source_text or f"instruction {key}",
            "command_hint": {
                "intent": "KEEP_LANE",
                "target_speed_mps": _semantic_speed(
                    semantic_key
                ),
            },
            "scene_summary": {
                "frame_id": frame_id,
                "sim_time_s": float(frame_id),
                "risk_level": "LOW",
            },
            "targets": [
                {
                    "target_id": f"target-{key}",
                    "class": "obstacle",
                    "distance_m": 10.0,
                }
            ],
            "constraints": {
                "speed_limit_mps": 8.333333333333334,
            },
        },
        "visual_input": {
            "rgb_sha256": hashlib.sha256(
                f"rgb-{rgb_seed or key}".encode("utf-8")
            ).hexdigest(),
        },
    }


def test_case_set_digest_is_order_independent() -> None:
    identities = extract_case_identities(
        [
            _case(
                "b",
                template_id="template-b",
            ),
            _case(
                "a",
                template_id="template-a",
            ),
        ]
    )

    assert compute_case_set_digest(
        identities
    ) == compute_case_set_digest(
        reversed(identities)
    )


def test_missing_template_identity_fails_closed() -> None:
    cases = [_case("candidate")]

    with pytest.raises(
        CaseManifestError,
        match="missing template identity",
    ):
        extract_case_identities(cases)


@pytest.mark.parametrize(
    (
        "candidate",
        "training",
        "expected_field",
    ),
    [
        (
            _case(
                "candidate-scenario",
                scenario_id="same-scenario",
                template_id="template-c1",
            ),
            _case(
                "training-scenario",
                scenario_id="same-scenario",
                template_id="template-t1",
            ),
            "scenario_id",
        ),
        (
            _case(
                "candidate-template",
                template_id="same-template",
            ),
            _case(
                "training-template",
                template_id="same-template",
            ),
            "template_id",
        ),
        (
            _case(
                "candidate-group",
                group_key="a" * 20,
                template_id="template-c3",
            ),
            _case(
                "training-group",
                group_key="a" * 20,
                template_id="template-t3",
            ),
            "group_key",
        ),
        (
            _case(
                "candidate-rgb",
                rgb_seed="same-rgb",
                template_id="template-c4",
            ),
            _case(
                "training-rgb",
                rgb_seed="same-rgb",
                template_id="template-t4",
            ),
            "rgb_sha256",
        ),
        (
            _case(
                "candidate-text",
                source_text=" ＴＵＲＮ   LEFT ",
                template_id="template-c5",
            ),
            _case(
                "training-text",
                source_text="turn left",
                template_id="template-t5",
            ),
            "source_text_sha256",
        ),
        (
            _case(
                "candidate-request",
                request_semantics="shared-request",
                template_id="template-c6",
            ),
            _case(
                "training-request",
                request_semantics="shared-request",
                template_id="template-t6",
            ),
            "normalized_request_sha256",
        ),
    ],
)
def test_independence_overlap_is_rejected(
    candidate: dict,
    training: dict,
    expected_field: str,
) -> None:
    development = _case(
        "development",
        template_id="template-development",
    )

    with pytest.raises(
        CaseManifestError,
        match=expected_field,
    ):
        validate_independent_case_set(
            [candidate],
            [training],
            [development],
        )


def test_same_supervision_event_is_rejected() -> None:
    candidate = _case(
        "candidate-event",
        event_key="same-event",
        template_id="template-c",
    )
    training = _case(
        "training-event",
        event_key="same-event",
        template_id="template-t",
    )
    development = _case(
        "development-event",
        template_id="template-d",
    )

    with pytest.raises(
        CaseManifestError,
    ) as error:
        validate_independent_case_set(
            [candidate],
            [training],
            [development],
        )

    message = str(error.value)

    assert "sample_id" in message
    assert "supervision_event_key" in message


def test_changed_sample_id_copy_fails_closed() -> None:
    case = _case(
        "tampered",
        template_id="template-tampered",
    )

    case["sample_id"] = "td_" + ("0" * 24)

    with pytest.raises(
        CaseManifestError,
        match="sample_id does not match",
    ):
        extract_case_identities([case])


def test_source_text_normalization_is_stable() -> None:
    assert source_text_sha256(
        " ＴＵＲＮ   LEFT "
    ) == source_text_sha256(
        "turn left"
    )


def test_normalized_request_ignores_transport_identity() -> None:
    candidate = _case(
        "candidate-normalized",
        template_id="template-c",
        request_semantics="shared-semantics",
    )
    training = _case(
        "training-normalized",
        template_id="template-t",
        request_semantics="shared-semantics",
    )

    assert (
        candidate["model_request"]["request_id"]
        != training["model_request"]["request_id"]
    )
    assert (
        candidate["model_request"]["command_id"]
        != training["model_request"]["command_id"]
    )
    assert (
        candidate["model_request"]["targets"][0]["target_id"]
        != training["model_request"]["targets"][0]["target_id"]
    )

    assert normalized_request_sha256(
        candidate
    ) == normalized_request_sha256(
        training
    )


def test_normalized_request_preserves_semantic_changes() -> None:
    first = _case(
        "semantic-a",
        template_id="template-a",
        request_semantics="semantic-a",
    )
    second = _case(
        "semantic-b",
        template_id="template-b",
        request_semantics="semantic-b",
    )

    assert normalized_request_sha256(
        first
    ) != normalized_request_sha256(
        second
    )


def test_external_template_mapping_can_supply_b1_evidence() -> None:
    candidate = [_case("candidate")]
    training = [_case("training")]
    development = [_case("development")]

    template_ids = {
        candidate[0]["sample_id"]: "template-c",
        training[0]["sample_id"]: "template-t",
        development[0]["sample_id"]: "template-d",
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
        f"{field}_overlap_count": 0
        for field in IDENTITY_FIELDS
    }


def test_d2_reserved_candidates_match_b1_event_identity() -> None:
    """
    Audit the B1 event identity independently of missing template evidence.

    Synthetic audit template IDs only allow identity extraction to proceed;
    they are not formal B2 template evidence.
    """
    cases = load_benchmark_cases(RESERVED_PATH)

    template_ids = {
        record["sample_id"]: (
            "audit-" + record["sample_id"]
        )
        for record in cases
    }

    identities = extract_case_identities(
        cases,
        template_ids=template_ids,
    )

    assert len(identities) == 540

    for identity in identities:
        assert identity["sample_id"] == (
            "td_"
            + identity["supervision_event_key"][:24]
        )


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