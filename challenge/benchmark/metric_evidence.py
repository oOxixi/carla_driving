"""Metric evidence accounting for the B2 benchmark."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from typing import Any

import torch
from torch.nn import functional as F

from challenge.distillation.artifacts import (
    CORE_METRICS,
    SAFETY_METRICS,
)
from challenge.distillation.dataset import (
    DistillationDataset,
    make_collate_fn,
)
from challenge.distillation.label_encoder import (
    BEHAVIORS,
    COMPLETION_TYPES,
    FAILURE_ACTIONS,
    REPLAN_CONDITIONS,
    TARGET_LANES,
    DistillationLabelEncoder,
)
from challenge.distillation.metrics import (
    compute_batch_metrics,
    metric_denominators,
)

from challenge.benchmark.evaluation_summary import (
    EvaluationSummaryError,
    summarize_prediction_coverage,
)


GATE_METRICS = (
    *CORE_METRICS,
    *SAFETY_METRICS,
)


class MetricEvidenceError(ValueError):
    """Raised when B2 metric evidence cannot be derived safely."""


def reference_gate_denominators(
    cases: Iterable[Mapping[str, Any]],
) -> dict[str, int]:
    """
    Derive Gate denominators from the frozen reference labels.

    This intentionally reuses the existing distillation label encoder and
    metric_denominators implementation instead of defining B2-specific metric
    eligibility rules.
    """
    materialized = list(cases)

    if not materialized:
        raise MetricEvidenceError(
            "benchmark cases must not be empty"
        )

    try:
        batch = _reference_batch(materialized)
        denominators = metric_denominators(
            batch["labels"],
            batch["sample_classes"],
        )
    except (KeyError, TypeError, ValueError) as error:
        raise MetricEvidenceError(
            f"cannot derive reference metric denominators: {error}"
        ) from error

    return {
        name: _integer_denominator(
            denominators[name],
            name,
        )
        for name in GATE_METRICS
    }


def score_success_gate_metrics(
    case: Mapping[str, Any],
    prediction: Mapping[str, Any],
) -> dict[str, dict[str, int | float | None]]:
    """
    Score one successful ManeuverPlan against one frozen reference case.

    The prediction is encoded through the same DistillationLabelEncoder and
    scored through the same compute_batch_metrics implementation used by the
    Student validation path.
    """
    if not isinstance(case, Mapping):
        raise MetricEvidenceError(
            "benchmark case must be an object"
        )

    if not isinstance(prediction, Mapping):
        raise MetricEvidenceError(
            "successful prediction must be an object"
        )

    try:
        batch = _reference_batch([case])

        encoder = DistillationLabelEncoder()
        prediction_labels = encoder.encode(
            batch["requests"][0],
            prediction,
        )

        outputs = _encoded_plan_outputs(
            prediction_labels,
            max_targets=encoder.max_targets,
        )

        metrics = compute_batch_metrics(
            outputs,
            batch["labels"],
            batch["sample_classes"],
        )

        denominators = metric_denominators(
            batch["labels"],
            batch["sample_classes"],
        )
    except (KeyError, TypeError, ValueError) as error:
        raise MetricEvidenceError(
            f"cannot score successful prediction: {error}"
        ) from error

    evidence: dict[
        str,
        dict[str, int | float | None],
    ] = {}

    for name in GATE_METRICS:
        denominator = _integer_denominator(
            denominators[name],
            name,
        )
        raw_value = float(metrics[name])

        if denominator == 0:
            if not math.isnan(raw_value):
                raise MetricEvidenceError(
                    f"metric {name!r} must be undefined "
                    "when denominator is zero"
                )

            evidence[name] = {
                "numerator": 0,
                "denominator": 0,
                "value": None,
            }
            continue

        if not math.isfinite(raw_value) or not 0.0 <= raw_value <= 1.0:
            raise MetricEvidenceError(
                f"metric {name!r} must be finite and in [0, 1]"
            )

        raw_numerator = raw_value * denominator
        numerator = int(round(raw_numerator))

        if not math.isclose(
            raw_numerator,
            numerator,
            abs_tol=1e-6,
        ):
            raise MetricEvidenceError(
                f"metric {name!r} does not map to an integer numerator"
            )

        evidence[name] = {
            "numerator": numerator,
            "denominator": denominator,
            "value": numerator / denominator,
        }

    return evidence


def score_failed_gate_metrics(
    case: Mapping[str, Any],
    *,
    status: str,
) -> dict[str, dict[str, int | float | None]]:
    """
    Apply the frozen B2 zero-credit policy to a failed inference.

    Failed cases retain every reference-eligible Gate opportunity in the
    denominator while receiving zero numerator credit.
    """
    if status not in {
        "INFERENCE_ERROR",
        "INVALID_OUTPUT",
    }:
        raise MetricEvidenceError(
            f"unsupported failure status: {status!r}"
        )

    denominators = reference_gate_denominators(
        [case]
    )

    evidence: dict[
        str,
        dict[str, int | float | None],
    ] = {}

    for name in GATE_METRICS:
        denominator = denominators[name]

        evidence[name] = {
            "numerator": 0,
            "denominator": denominator,
            "value": (
                None
                if denominator == 0
                else 0.0
            ),
        }

    return evidence

def aggregate_gate_metric_evidence(
    cases: Iterable[Mapping[str, Any]],
    records: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """
    Aggregate B2 Gate metric evidence over the complete frozen case set.

    Prediction coverage is validated first. SUCCESS records are scored through
    the shared distillation metric implementation. Failed records receive zero
    numerator credit while retaining every reference-eligible denominator.
    """
    case_rows = list(cases)
    record_rows = list(records)

    try:
        coverage = summarize_prediction_coverage(
            case_rows,
            record_rows,
        )
    except EvaluationSummaryError as error:
        raise MetricEvidenceError(
            f"invalid prediction coverage: {error}"
        ) from error

    totals = {
        name: {
            "numerator": 0,
            "denominator": 0,
        }
        for name in GATE_METRICS
    }

    for case, record in zip(
        case_rows,
        record_rows,
        strict=True,
    ):
        status = record["status"]

        if status == "SUCCESS":
            evidence = score_success_gate_metrics(
                case,
                record.get("prediction"),
            )
        else:
            evidence = score_failed_gate_metrics(
                case,
                status=status,
            )

        for name in GATE_METRICS:
            totals[name]["numerator"] += int(
                evidence[name]["numerator"]
            )
            totals[name]["denominator"] += int(
                evidence[name]["denominator"]
            )

    metrics: dict[
        str,
        dict[str, int | float | None],
    ] = {}

    for name in GATE_METRICS:
        numerator = totals[name]["numerator"]
        denominator = totals[name]["denominator"]

        if numerator < 0 or numerator > denominator:
            raise MetricEvidenceError(
                f"invalid aggregate metric counts for {name!r}"
            )

        metrics[name] = {
            "numerator": numerator,
            "denominator": denominator,
            "value": (
                None
                if denominator == 0
                else numerator / denominator
            ),
        }

    return {
        "coverage": coverage,
        "metrics": metrics,
    }

def _reference_batch(
    cases: list[Mapping[str, Any]],
) -> dict[str, Any]:
    dataset = DistillationDataset(
        cases,
        require_rgb=False,
    )

    collate = make_collate_fn(
        input_packer=lambda requests: {},
    )

    return collate(
        [
            dataset[index]
            for index in range(len(dataset))
        ]
    )


def _encoded_plan_outputs(
    labels: Mapping[str, Any],
    *,
    max_targets: int,
) -> dict[str, torch.Tensor]:
    """
    Represent an encoded ManeuverPlan as deterministic Student-head outputs.

    These tensors exist only to reuse compute_batch_metrics; they are not
    model inference outputs.
    """
    max_steps = len(labels["behavior"])

    return {
        "plan_length_logits": F.one_hot(
            torch.tensor(
                [int(labels["plan_length"])],
                dtype=torch.long,
            ),
            num_classes=max_steps,
        ).to(torch.float32),
        "behavior_logits": _categorical_logits(
            labels["behavior"],
            len(BEHAVIORS),
        ),
        "target_pointer_logits": _categorical_logits(
            labels["target_pointer"],
            max_targets + 1,
        ),
        "target_lane_logits": _categorical_logits(
            labels["target_lane"],
            len(TARGET_LANES),
        ),
        "target_speed_mps": torch.tensor(
            [labels["target_speed_mps"]],
            dtype=torch.float32,
        ),
        "completion_type_logits": _categorical_logits(
            labels["completion_type"],
            len(COMPLETION_TYPES),
        ),
        "on_failure_logits": _categorical_logits(
            labels["on_failure"],
            len(FAILURE_ACTIONS),
        ),
        "confidence": torch.tensor(
            [[float(labels["confidence"])]],
            dtype=torch.float32,
        ),
        "requires_confirmation_logits": torch.tensor(
            [[
                1.0
                if bool(labels["requires_confirmation"])
                else -1.0
            ]],
            dtype=torch.float32,
        ),
        "replan_condition_logits": torch.tensor(
            [[
                1.0 if bool(value) else -1.0
                for value in labels["replan_conditions"]
            ]],
            dtype=torch.float32,
        ),
    }


def _categorical_logits(
    values: Any,
    num_classes: int,
) -> torch.Tensor:
    indices = torch.tensor(
        [list(values)],
        dtype=torch.long,
    )

    return F.one_hot(
        indices,
        num_classes=num_classes,
    ).to(torch.float32)


def _integer_denominator(
    value: Any,
    name: str,
) -> int:
    numeric = float(value)

    if (
        not math.isfinite(numeric)
        or numeric < 0
        or not numeric.is_integer()
    ):
        raise MetricEvidenceError(
            f"metric denominator {name!r} "
            "must be a non-negative integer"
        )

    return int(numeric)


__all__ = [
    "GATE_METRICS",
    "MetricEvidenceError",
    "aggregate_gate_metric_evidence",
    "reference_gate_denominators",
    "score_failed_gate_metrics",
    "score_success_gate_metrics",
]