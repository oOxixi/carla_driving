
from __future__ import annotations

import copy

from pathlib import Path

import pytest

import yaml

from challenge.benchmark.replay_transport import (
    ReplayTransportError,
    refresh_replay_deadline,
)


def _request() -> dict:
    return {
        "schema_version": "1.0",
        "request_id": "request-001",
        "command_id": "command-001",
        "created_at_ns": 1_000_000_000,
        "deadline_ns": 6_000_000_000,
        "source_text": "keep lane",
        "rgb_ref": "images/sample.jpg",
        "targets": [
            {
                "target_id": "target-001",
                "class": "obstacle",
            }
        ],
        "constraints": {
            "must_stop": False,
        },
    }


def test_refresh_preserves_frozen_ttl_and_semantics() -> None:
    request = _request()
    original = copy.deepcopy(request)

    transformed = refresh_replay_deadline(
        request,
        clock_ns=lambda: 20_000_000_000,
    )

    assert transformed["created_at_ns"] == 20_000_000_000
    assert transformed["deadline_ns"] == 25_000_000_000

    expected = copy.deepcopy(original)
    expected["created_at_ns"] = 20_000_000_000
    expected["deadline_ns"] = 25_000_000_000

    assert transformed == expected
    assert request == original


def test_refresh_returns_independent_nested_data() -> None:
    request = _request()

    transformed = refresh_replay_deadline(
        request,
        clock_ns=lambda: 20_000_000_000,
    )

    transformed["targets"][0]["class"] = "vehicle"

    assert request["targets"][0]["class"] == "obstacle"


@pytest.mark.parametrize(
    ("created_at_ns", "deadline_ns"),
    [
        (1_000, 1_000),
        (2_000, 1_000),
        ("1000", 2_000),
        (1_000, 2_000.0),
        (True, 2_000),
    ],
)
def test_invalid_frozen_deadline_fails_closed(
    created_at_ns: object,
    deadline_ns: object,
) -> None:
    request = _request()
    request["created_at_ns"] = created_at_ns
    request["deadline_ns"] = deadline_ns

    with pytest.raises(ReplayTransportError):
        refresh_replay_deadline(
            request,
            clock_ns=lambda: 20_000_000_000,
        )


def test_invalid_replay_clock_fails_closed() -> None:
    request = _request()

    with pytest.raises(
        ReplayTransportError,
        match="replay clock",
    ):
        refresh_replay_deadline(
            request,
            clock_ns=lambda: -1,
        )

def test_benchmark_config_freezes_replay_transport_policy() -> None:
    config_path = Path(__file__).parents[1] / "benchmark_config.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    policy = config["replay_transport"]

    assert policy["timestamp_policy"] == "preserve_original_ttl"
    assert policy["clock"] == "time.monotonic_ns"
    assert policy["mutable_fields"] == [
        "created_at_ns",
        "deadline_ns",
    ]
    assert policy["preserve_request_id"] is True
    assert policy["preserve_command_id"] is True
    assert policy["preserve_semantic_fields"] is True