"""B2 independent-validation case-set identity and isolation checks."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from typing import Any


class CaseManifestError(ValueError):
    """Raised when B2 cannot prove that a case set is independent."""


def _required_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CaseManifestError(f"{label} must be a non-empty string")
    return value.strip()


def extract_case_identities(
    cases: Iterable[dict[str, Any]],
    *,
    template_ids: Mapping[str, str] | None = None,
) -> list[dict[str, str]]:
    """
    Extract the minimum identity B2 needs to prove case-set independence.

    Template identity may come from future B1 record metadata or from a
    separately supplied B1 template-identity mapping. If neither exists,
    B2 fails closed instead of inferring a template from source_text.
    """
    template_ids = template_ids or {}
    identities: list[dict[str, str]] = []
    seen_sample_ids: set[str] = set()

    for index, record in enumerate(cases, start=1):
        if not isinstance(record, dict):
            raise CaseManifestError(
                f"case {index}: benchmark case must be an object"
            )

        sample_id = _required_text(
            record.get("sample_id"),
            f"case {index}: sample_id",
        )

        if sample_id in seen_sample_ids:
            raise CaseManifestError(
                f"duplicate sample_id in case set: {sample_id}"
            )
        seen_sample_ids.add(sample_id)

        metadata = record.get("metadata")
        if not isinstance(metadata, dict):
            raise CaseManifestError(
                f"{sample_id}: metadata must be an object"
            )

        scenario_id = _required_text(
            metadata.get("scenario_id"),
            f"{sample_id}: scenario_id",
        )

        template_id = metadata.get("template_id")

        if template_id is None:
            template_id = template_ids.get(sample_id)

        if template_id is None:
            raise CaseManifestError(
                f"{sample_id}: missing template identity; "
                "B2 cannot prove template-disjoint evaluation"
            )

        template_id = _required_text(
            template_id,
            f"{sample_id}: template_id",
        )

        identities.append(
            {
                "sample_id": sample_id,
                "scenario_id": scenario_id,
                "template_id": template_id,
            }
        )

    if not identities:
        raise CaseManifestError("case set must not be empty")

    return identities


def compute_case_set_digest(
    identities: Iterable[dict[str, str]],
) -> str:
    """Return an order-independent SHA256 for the exact B2 case identity set."""
    canonical = sorted(
        (
            {
                "sample_id": item["sample_id"],
                "scenario_id": item["scenario_id"],
                "template_id": item["template_id"],
            }
            for item in identities
        ),
        key=lambda item: (
            item["sample_id"],
            item["scenario_id"],
            item["template_id"],
        ),
    )

    payload = json.dumps(
        canonical,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(payload).hexdigest()


def validate_independent_case_set(
    candidate_cases: Iterable[dict[str, Any]],
    training_cases: Iterable[dict[str, Any]],
    development_cases: Iterable[dict[str, Any]],
    *,
    template_ids: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """
    Prove that candidate Validation cases are disjoint from Train + Dev Val.

    Formal B2 independent Validation requires zero overlap by:
    - sample_id
    - scenario_id
    - template_id
    """
    candidate = extract_case_identities(
        candidate_cases,
        template_ids=template_ids,
    )
    training = extract_case_identities(
        training_cases,
        template_ids=template_ids,
    )
    development = extract_case_identities(
        development_cases,
        template_ids=template_ids,
    )

    reference = training + development

    overlaps: dict[str, list[str]] = {}

    for field in ("sample_id", "scenario_id", "template_id"):
        candidate_values = {item[field] for item in candidate}
        reference_values = {item[field] for item in reference}
        overlap = sorted(candidate_values & reference_values)

        if overlap:
            overlaps[field] = overlap

    if overlaps:
        details = "; ".join(
            f"{field}={values[:5]}"
            for field, values in sorted(overlaps.items())
        )
        raise CaseManifestError(
            f"independent Validation overlap detected: {details}"
        )

    return {
        "sample_count": len(candidate),
        "case_set_digest": compute_case_set_digest(candidate),
        "independence": {
            "sample_id_overlap_count": 0,
            "scenario_id_overlap_count": 0,
            "template_id_overlap_count": 0,
        },
    }


__all__ = [
    "CaseManifestError",
    "compute_case_set_digest",
    "extract_case_identities",
    "validate_independent_case_set",
]