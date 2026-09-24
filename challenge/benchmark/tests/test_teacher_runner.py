from __future__ import annotations

from typing import Any

import pytest

from challenge.benchmark.raw_predictions import (
    canonical_prediction_jsonl,
    prediction_records_sha256,
    write_prediction_records,
)

from challenge.benchmark.replay_transport import (
    refresh_replay_deadline,
)
from challenge.benchmark.teacher_runner import (
    TeacherRunnerError,
    build_teacher_client,
    run_teacher_cases,
)


def _request(index: int) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "request_id": f"request-{index}",
        "command_id": f"command-{index}",
        "created_at_ns": 1_000_000_000,
        "deadline_ns": 6_000_000_000,
        "source_text": "keep lane",
        "scene_summary": {
            "frame_id": index,
            "sim_time_s": float(index),
            "traffic_light": "GREEN",
            "risk_level": "LOW",
        },
        "targets": [],
        "constraints": {
            "speed_limit_mps": 10.0,
            "allowed_behaviors": [
                "KEEP_LANE",
                "STOP",
            ],
            "must_stop": False,
            "max_target_speed_mps": 10.0,
        },
    }


def _case(index: int) -> dict[str, Any]:
    return {
        "sample_id": f"sample-{index}",
        "model_request": _request(index),
    }


def _plan(
    request: dict[str, Any],
    *,
    request_id: str | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "2.0",
        "request_id": request_id or request["request_id"],
        "command_id": request["command_id"],
        "plan_id": f"plan-{request['request_id']}",
        "plan_type": "MANEUVER_SEQUENCE",
        "steps": [
            {
                "step_id": "step-1",
                "behavior": "HOLD",
                "target": {},
                "preconditions": [],
                "completion": {
                    "type": "HOLD_FRAMES",
                    "hold_frames": 3,
                },
                "timeout_s": 1.0,
                "on_failure": "SAFE_STOP",
            }
        ],
        "replan_conditions": [],
        "confidence": 1.0,
        "requires_confirmation": False,
        "created_at_ns": request["created_at_ns"],
        "valid_until_ns": request["deadline_ns"],
        "reason_code": "TEST_PLAN",
        "model_id": "Qwen/Qwen3.5-2B",
    }


class EchoClient:
    def __init__(self) -> None:
        self.calls = 0

    def infer(
        self,
        request: dict[str, Any],
    ) -> dict[str, Any]:
        self.calls += 1
        return _plan(request)


def test_real_client_uses_frozen_replay_transport_policy() -> None:
    client = build_teacher_client(
        "http://127.0.0.1:9999",
    )

    assert client.request_transform is refresh_replay_deadline


def test_success_emits_exactly_one_record_per_case() -> None:
    client = EchoClient()

    records = run_teacher_cases(
        [_case(1), _case(2)],
        client=client,
    )

    assert client.calls == 2
    assert len(records) == 2
    assert [record["sample_id"] for record in records] == [
        "sample-1",
        "sample-2",
    ]
    assert [record["status"] for record in records] == [
        "SUCCESS",
        "SUCCESS",
    ]

    canonical_prediction_jsonl(records)


def test_inference_failure_is_retained_as_raw_record() -> None:
    class MixedClient:
        def infer(
            self,
            request: dict[str, Any],
        ) -> dict[str, Any]:
            if request["request_id"] == "request-2":
                raise RuntimeError("service unavailable")
            return _plan(request)

    records = run_teacher_cases(
        [_case(1), _case(2)],
        client=MixedClient(),
    )

    assert len(records) == 2
    assert records[0]["status"] == "SUCCESS"

    failure = records[1]
    assert failure["status"] == "INFERENCE_ERROR"
    assert failure["prediction"] is None
    assert failure["error"]["code"] == "QWEN_CLIENT_ERROR"
    assert failure["error"]["type"] == "RuntimeError"

    canonical_prediction_jsonl(records)


def test_invalid_plan_is_retained_and_classified() -> None:
    class InvalidPlanClient:
        def infer(
            self,
            request: dict[str, Any],
        ) -> dict[str, Any]:
            return {
                "schema_version": "2.0",
            }

    records = run_teacher_cases(
        [_case(1)],
        client=InvalidPlanClient(),
    )

    assert len(records) == 1

    failure = records[0]
    assert failure["status"] == "INVALID_OUTPUT"
    assert failure["error"]["code"] == "INVALID_PLAN_SCHEMA"

    canonical_prediction_jsonl(records)


def test_prediction_identity_mismatch_is_not_success() -> None:
    class WrongIdentityClient:
        def infer(
            self,
            request: dict[str, Any],
        ) -> dict[str, Any]:
            return _plan(
                request,
                request_id="wrong-request",
            )

    records = run_teacher_cases(
        [_case(1)],
        client=WrongIdentityClient(),
    )

    assert records[0]["status"] == "INVALID_OUTPUT"
    assert records[0]["error"]["code"] == "REQUEST_ID_MISMATCH"


def test_invalid_benchmark_input_fails_before_inference() -> None:
    client = EchoClient()

    invalid = _case(1)
    del invalid["model_request"]["constraints"]

    with pytest.raises(
        TeacherRunnerError,
        match="invalid model_request",
    ):
        run_teacher_cases(
            [invalid],
            client=client,
        )

    assert client.calls == 0

def test_failure_record_is_written_into_hashed_evidence(
    tmp_path,
) -> None:
    class MixedClient:
        def infer(
            self,
            request: dict[str, Any],
        ) -> dict[str, Any]:
            if request["request_id"] == "request-2":
                raise RuntimeError("service unavailable")
            return _plan(request)

    records = run_teacher_cases(
        [_case(1), _case(2)],
        client=MixedClient(),
    )

    path = tmp_path / "teacher_predictions.jsonl"

    digest = write_prediction_records(
        path,
        records,
    )

    written_lines = path.read_text(
        encoding="utf-8",
    ).splitlines()

    assert len(written_lines) == 2
    assert '"sample_id":"sample-2"' in written_lines[1]
    assert '"status":"INFERENCE_ERROR"' in written_lines[1]

    assert digest == prediction_records_sha256(
        records
    )

    # Removing the failed case must change the evidence identity.
    assert digest != prediction_records_sha256(
        [records[0]]
    )