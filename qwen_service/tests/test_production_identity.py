from __future__ import annotations

from argparse import Namespace

import pytest

from integration.qwen_profiles import (
    PRODUCTION_QWEN_ARTIFACT_SHA256,
    PRODUCTION_QWEN_MODEL,
    PRODUCTION_QWEN_REVISION,
)
from qwen_service import server


class _Backend:
    production_ready = True

    def __init__(self, **kwargs: object) -> None:
        self.model_id = str(kwargs["model"])

    def health(self) -> tuple[bool, str]:
        return True, "ready"

    def infer(self, _request: object) -> dict[str, object]:
        raise AssertionError("not used")


def _args(**changes: object) -> Namespace:
    values: dict[str, object] = {
        "deterministic_test_backend": False,
        "vllm_base_url": "http://127.0.0.1:8000/v1",
        "vllm_model": PRODUCTION_QWEN_MODEL,
        "model_path": None,
        "image_root": None,
        "max_new_tokens": 256,
        "image_max_side": 224,
        "jpeg_quality": 75,
        "min_pixels": 64 * 28 * 28,
        "max_pixels": 256 * 28 * 28,
        "timeout_ms": 300.0,
        "max_concurrency": 1,
        "max_request_bytes": 262_144,
        "qwen_mode": "planner_v2",
        "model_revision": None,
        "model_artifact_sha256": None,
    }
    values.update(changes)
    return Namespace(**values)


def test_production_service_rejects_unverified_model_artifact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(server, "VllmQwenPlannerBackend", _Backend)

    with pytest.raises(ValueError, match="model-revision"):
        server.build_service(_args())
    with pytest.raises(ValueError, match="model-artifact-sha256"):
        server.build_service(_args(model_revision=PRODUCTION_QWEN_REVISION))


def test_production_service_exposes_verified_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(server, "VllmQwenPlannerBackend", _Backend)
    service = server.build_service(_args(
        model_revision=PRODUCTION_QWEN_REVISION,
        model_artifact_sha256=PRODUCTION_QWEN_ARTIFACT_SHA256,
    ))
    try:
        health = service.health()
    finally:
        service.close()

    assert health["model_id"] == PRODUCTION_QWEN_MODEL
    assert health["model_revision"] == PRODUCTION_QWEN_REVISION
    assert health["artifact_sha256"] == PRODUCTION_QWEN_ARTIFACT_SHA256
    assert health["qwen_mode"] == "planner_v2"
