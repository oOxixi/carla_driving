"""Optional Train-only class weighting for imbalanced structured labels."""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable, Mapping, Sequence

from .label_encoder import (
    BEHAVIORS,
    COMPLETION_TYPES,
    FAILURE_ACTIONS,
    TARGET_LANES,
)


CLASS_COUNTS = {
    "behavior": len(BEHAVIORS),
    "target_pointer": None,
    "target_lane": len(TARGET_LANES),
    "completion": len(COMPLETION_TYPES),
    "on_failure": len(FAILURE_ACTIONS),
    "plan_length": None,
}


def compute_class_weights(
    samples: Iterable[Mapping[str, Any]],
    *,
    heads: Sequence[str],
    max_steps: int,
    max_targets: int,
    smoothing: float = 1.0,
    max_weight: float = 5.0,
) -> tuple[dict[str, list[float]], dict[str, list[int]]]:
    """Compute bounded inverse-frequency weights from Train labels only."""
    if smoothing <= 0.0 or max_weight < 1.0:
        raise ValueError("smoothing must be positive and max_weight must be >= 1")
    unknown = set(heads).difference(CLASS_COUNTS)
    if unknown:
        raise ValueError("unsupported class-balance head(s): " + ", ".join(sorted(unknown)))
    sizes = {
        **CLASS_COUNTS,
        "target_pointer": max_targets + 1,
        "plan_length": max_steps,
    }
    counters = {head: Counter() for head in heads}
    for sample in samples:
        labels = sample["labels"]
        active = labels["step_mask"]
        for head in heads:
            source = "completion_type" if head == "completion" else head
            if head == "plan_length":
                counters[head][int(labels[source])] += 1
                continue
            for value, enabled in zip(labels[source], active, strict=True):
                if enabled:
                    counters[head][int(value)] += 1
    result: dict[str, list[float]] = {}
    counts: dict[str, list[int]] = {}
    for head in heads:
        raw_counts = [int(counters[head][index]) for index in range(int(sizes[head]))]
        adjusted = [value + smoothing for value in raw_counts]
        mean_count = sum(adjusted) / len(adjusted)
        weights = [min(max_weight, mean_count / value) for value in adjusted]
        # Keep the common class near one so this does not change the global loss scale.
        present = [weight for weight, count in zip(weights, raw_counts, strict=True) if count]
        normalizer = sum(present) / len(present) if present else 1.0
        result[head] = [
            float(min(max_weight, max(1.0 / max_weight, weight / normalizer)))
            for weight in weights
        ]
        counts[head] = raw_counts
    return result, counts


__all__ = ["compute_class_weights"]
