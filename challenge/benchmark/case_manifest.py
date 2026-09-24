"""B2 independent-validation case-set identity and isolation checks."""

from __future__ import annotations

import copy
import hashlib
import json
import unicodedata
from collections.abc import Iterable, Mapping
from typing import Any


class CaseManifestError(ValueError):
    """Raised when B2 cannot prove that a case set is independent."""


IDENTITY_FIELDS = (
    "sample_id",
    "scenario_id",
    "template_id",
    "group_key",
    "rgb_sha256",
    "source_text_sha256",
    "normalized_request_sha256",
    "supervision_event_key",
)


def _required_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CaseManifestError(f"{label} must be a non-empty string")
    return value.strip()


def _required_sha256(value: Any, label: str) -> str:
    digest = _required_text(value, label).lower()

    if len(digest) != 64:
        raise CaseManifestError(f"{label} must be a SHA256 hex digest")

    try:
        int(digest, 16)
    except ValueError as error:
        raise CaseManifestError(
            f"{label} must be a SHA256 hex digest"
        ) from error

    return digest


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def normalize_source_text(value: Any) -> str:
    """
    Canonicalize source text only for leakage detection.

    This does not change the text presented to Teacher or Student.
    """
    text = _required_text(value, "model_request.source_text")
    normalized = unicodedata.normalize("NFKC", text)
    normalized = " ".join(normalized.split())
    return normalized.casefold()


def source_text_sha256(value: Any) -> str:
    return _sha256_bytes(
        normalize_source_text(value).encode("utf-8")
    )


def normalize_model_request(
    record: Mapping[str, Any],
) -> dict[str, Any]:
    """
    Remove transport/run identity while retaining request semantics.

    source_text is deliberately excluded because B2 audits it separately.
    """
    request = record.get("model_request")

    if not isinstance(request, Mapping):
        raise CaseManifestError(
            "model_request must be an object"
        )

    normalized = copy.deepcopy(dict(request))

    for field in (
        "request_id",
        "command_id",
        "created_at_ns",
        "deadline_ns",
        "rgb_ref",
        "source_text",
    ):
        normalized.pop(field, None)

    scene_summary = normalized.get("scene_summary")

    if isinstance(scene_summary, dict):
        scene_summary.pop("frame_id", None)
        scene_summary.pop("sim_time_s", None)

    targets = normalized.get("targets")

    if isinstance(targets, list):
        normalized_targets = []

        for index, target in enumerate(targets):
            if not isinstance(target, Mapping):
                raise CaseManifestError(
                    f"model_request.targets[{index}] must be an object"
                )

            normalized_target = copy.deepcopy(dict(target))
            normalized_target.pop("target_id", None)
            normalized_targets.append(normalized_target)

        normalized["targets"] = normalized_targets

    return normalized


def normalized_request_sha256(
    record: Mapping[str, Any],
) -> str:
    payload = json.dumps(
        normalize_model_request(record),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")

    return _sha256_bytes(payload)


def extract_case_identities(
    cases: Iterable[dict[str, Any]],
    *,
    template_ids: Mapping[str, str] | None = None,
) -> list[dict[str, str]]:
    """
    Extract identities required to prove B2 case-set independence.

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

        if not isinstance(metadata, Mapping):
            raise CaseManifestError(
                f"{sample_id}: metadata must be an object"
            )

        scenario_id = _required_text(
            metadata.get("scenario_id"),
            f"{sample_id}: scenario_id",
        )
        group_key = _required_text(
            metadata.get("group_key"),
            f"{sample_id}: group_key",
        )
        run_id = _required_text(
            metadata.get("run_id"),
            f"{sample_id}: run_id",
        )
        command_id = _required_text(
            metadata.get("command_id"),
            f"{sample_id}: command_id",
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

        visual = record.get("visual_input")

        if not isinstance(visual, Mapping):
            raise CaseManifestError(
                f"{sample_id}: visual_input must be an object"
            )

        rgb_sha256 = _required_sha256(
            visual.get("rgb_sha256"),
            f"{sample_id}: rgb_sha256",
        )

        request = record.get("model_request")

        if not isinstance(request, Mapping):
            raise CaseManifestError(
                f"{sample_id}: model_request must be an object"
            )

        text_digest = source_text_sha256(
            request.get("source_text")
        )
        request_digest = normalized_request_sha256(record)

        request_id = _required_text(
            request.get("request_id"),
            f"{sample_id}: model_request.request_id",
        )
        request_command_id = _required_text(
            request.get("command_id"),
            f"{sample_id}: model_request.command_id",
        )

        scene_summary = request.get("scene_summary")

        if not isinstance(scene_summary, Mapping):
            raise CaseManifestError(
                f"{sample_id}: model_request.scene_summary must be an object"
            )

        frame_id = scene_summary.get("frame_id")

        if frame_id is None:
            raise CaseManifestError(
                f"{sample_id}: model_request.scene_summary.frame_id is required"
            )

        metadata_request_id = _required_text(
            metadata.get("request_id"),
            f"{sample_id}: metadata.request_id",
        )
        metadata_frame_id = metadata.get("frame_id")

        if metadata_frame_id is None:
            raise CaseManifestError(
                f"{sample_id}: metadata.frame_id is required"
            )

        if metadata_request_id != request_id:
            raise CaseManifestError(
                f"{sample_id}: metadata/model_request request_id mismatch"
            )

        if command_id != request_command_id:
            raise CaseManifestError(
                f"{sample_id}: metadata/model_request command_id mismatch"
            )

        if metadata_frame_id != frame_id:
            raise CaseManifestError(
                f"{sample_id}: metadata/model_request frame_id mismatch"
            )

        sample_identity = {
            "run_id": run_id,
            "command_id": command_id,
            "request_id": request_id,
            "frame_id": frame_id,
        }

        canonical_identity = json.dumps(
            sample_identity,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

        supervision_event_key = _sha256_bytes(
            canonical_identity
        )

        expected_sample_id = (
            "td_" + supervision_event_key[:24]
        )

        if sample_id != expected_sample_id:
            raise CaseManifestError(
                f"{sample_id}: sample_id does not match "
                "B1 supervision-event identity"
            )

        identities.append(
            {
                "sample_id": sample_id,
                "scenario_id": scenario_id,
                "template_id": template_id,
                "group_key": group_key,
                "rgb_sha256": rgb_sha256,
                "source_text_sha256": text_digest,
                "normalized_request_sha256": request_digest,
                "supervision_event_key": supervision_event_key,
            }
        )

    if not identities:
        raise CaseManifestError("case set must not be empty")

    return identities


def compute_case_set_digest(
    identities: Iterable[dict[str, str]],
) -> str:
    """Return an order-independent digest for the exact B2 case set."""
    canonical = sorted(
        (
            {
                field: item[field]
                for field in IDENTITY_FIELDS
            }
            for item in identities
        ),
        key=lambda item: tuple(
            item[field] for field in IDENTITY_FIELDS
        ),
    )

    payload = json.dumps(
        canonical,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")

    return _sha256_bytes(payload)


def validate_independent_case_set(
    candidate_cases: Iterable[dict[str, Any]],
    training_cases: Iterable[dict[str, Any]],
    development_cases: Iterable[dict[str, Any]],
    *,
    template_ids: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """
    Prove that candidate Validation is isolated from Train + Dev Val.

    Formal B2 independent Validation requires zero overlap for every
    identity dimension in IDENTITY_FIELDS.
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

    for field in IDENTITY_FIELDS:
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

    independence = {
        f"{field}_overlap_count": 0
        for field in IDENTITY_FIELDS
    }

    return {
        "sample_count": len(candidate),
        "case_set_digest": compute_case_set_digest(candidate),
        "independence": independence,
    }


__all__ = [
    "CaseManifestError",
    "IDENTITY_FIELDS",
    "compute_case_set_digest",
    "extract_case_identities",
    "normalize_model_request",
    "normalize_source_text",
    "normalized_request_sha256",
    "source_text_sha256",
    "validate_independent_case_set",
]