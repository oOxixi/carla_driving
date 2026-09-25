"""Transport-only adaptation for replaying frozen benchmark requests."""

from __future__ import annotations

import copy
import time
from collections.abc import Callable, Mapping
from typing import Any


class ReplayTransportError(ValueError):
    """Raised when a frozen request cannot be replayed safely."""


def _required_timestamp(value: Any, label: str) -> int:
    if type(value) is not int:
        raise ReplayTransportError(f"{label} must be an integer")
    if value < 0:
        raise ReplayTransportError(f"{label} must be non-negative")
    return value


def refresh_replay_deadline(
    request: Mapping[str, Any],
    *,
    clock_ns: Callable[[], int] = time.monotonic_ns,
) -> dict[str, Any]:
    """
    Refresh only replay transport timestamps.

    The frozen request's original TTL is preserved exactly. All semantic
    fields and stable request/command identities remain unchanged.
    """
    if not isinstance(request, Mapping):
        raise ReplayTransportError("model_request must be an object")

    created_at_ns = _required_timestamp(
        request.get("created_at_ns"),
        "model_request.created_at_ns",
    )
    deadline_ns = _required_timestamp(
        request.get("deadline_ns"),
        "model_request.deadline_ns",
    )

    ttl_ns = deadline_ns - created_at_ns
    if ttl_ns <= 0:
        raise ReplayTransportError(
            "model_request.deadline_ns must follow created_at_ns"
        )

    now_ns = _required_timestamp(
        clock_ns(),
        "replay clock",
    )

    transformed = copy.deepcopy(dict(request))
    transformed["created_at_ns"] = now_ns
    transformed["deadline_ns"] = now_ns + ttl_ns
    return transformed


__all__ = [
    "ReplayTransportError",
    "refresh_replay_deadline",
]