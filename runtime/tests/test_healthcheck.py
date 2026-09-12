from __future__ import annotations

from typing import Any

import pytest

from integration.qwen_profiles import (
    PRODUCTION_QWEN_ARTIFACT_SHA256,
    PRODUCTION_QWEN_MODEL,
    PRODUCTION_QWEN_REVISION,
)
from runtime import healthcheck


@pytest.fixture
def isolated_healthcheck(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        healthcheck,
        "_interfaces",
        lambda: {"status": "PASS", "interfaces": []},
    )
    monkeypatch.setattr(
        healthcheck,
        "_dependencies",
        lambda: {"status": "PASS", "modules": {}},
    )
    monkeypatch.setattr(
        healthcheck,
        "_carla",
        lambda *_: {"status": "PASS", "map": "Town03_Opt"},
    )


def _run(monkeypatch: pytest.MonkeyPatch, qwen: dict[str, Any]) -> dict[str, Any]:
    monkeypatch.setattr(
        healthcheck,
        "_http_json",
        lambda *_: (True, dict(qwen), "HTTP_OK"),
    )
    return healthcheck.run_healthcheck(
        qwen_url="http://qwen.invalid",
        carla_host="127.0.0.1",
        carla_port=2000,
        timeout_s=0.1,
        require_qwen=True,
        require_carla=True,
    )


def test_strict_healthcheck_accepts_exact_production_contract(
    monkeypatch: pytest.MonkeyPatch,
    isolated_healthcheck: None,
) -> None:
    report = _run(monkeypatch, {
        "status": "READY",
        "production_ready": True,
        "model_id": PRODUCTION_QWEN_MODEL,
        "model_revision": PRODUCTION_QWEN_REVISION,
        "artifact_sha256": PRODUCTION_QWEN_ARTIFACT_SHA256,
        "qwen_mode": "planner_v2",
    })

    assert report["status"] == "PASS"
    assert report["failed_checks"] == []
    assert all(report["checks"]["qwen"]["contract"].values())
    assert report["required"]["qwen_contract"]["revision"] != "main"
    assert len(report["required"]["qwen_contract"]["artifact_sha256"]) == 64


@pytest.mark.parametrize(
    ("field", "value", "failure"),
    [
        ("status", "DEGRADED", "qwen_status_ready"),
        ("production_ready", False, "qwen_production_ready"),
        ("model_id", "Qwen/Qwen3.5-7B", "qwen_model_exact"),
        ("model_revision", "main", "qwen_revision_exact"),
        ("artifact_sha256", "wrong", "qwen_artifact_exact"),
        ("qwen_mode", "atomic_v1", "qwen_planner_mode"),
    ],
)
def test_strict_healthcheck_fails_each_qwen_contract_dimension(
    monkeypatch: pytest.MonkeyPatch,
    isolated_healthcheck: None,
    field: str,
    value: object,
    failure: str,
) -> None:
    payload: dict[str, Any] = {
        "status": "READY",
        "production_ready": True,
        "model_id": PRODUCTION_QWEN_MODEL,
        "model_revision": PRODUCTION_QWEN_REVISION,
        "artifact_sha256": PRODUCTION_QWEN_ARTIFACT_SHA256,
        "qwen_mode": "planner_v2",
    }
    payload[field] = value

    report = _run(monkeypatch, payload)

    assert report["status"] == "FAIL"
    assert failure in report["failed_checks"]
