"""Strict stdlib client suitable for runtime.PipelineOrchestrator."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class QwenServiceClient:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8765",
        *,
        timeout_s: float = 0.35,
        request_transform: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_s = float(timeout_s)
        self.request_transform = request_transform
        if self.timeout_s <= 0:
            raise ValueError("timeout_s must be positive")
        if request_transform is not None and not callable(request_transform):
            raise TypeError("request_transform must be callable or None")

    def infer(self, request: Mapping[str, Any]) -> dict[str, Any]:
        payload = request if self.request_transform is None else self.request_transform(request)
        body = json.dumps(dict(payload), ensure_ascii=False, allow_nan=False).encode("utf-8")
        http_request = Request(
            self.base_url + "/infer",
            data=body,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urlopen(http_request, timeout=self.timeout_s) as response:
                return json.loads(response.read())
        except HTTPError as error:
            try:
                payload = json.loads(error.read())
            except Exception:
                payload = {"error_code": "HTTP_ERROR", "message": str(error)}
            raise RuntimeError(f"Qwen service {error.code}: {payload}") from error
        except URLError as error:
            raise RuntimeError(f"Qwen service unavailable: {error.reason}") from error

    def health(self) -> dict[str, Any]:
        with urlopen(self.base_url + "/health", timeout=self.timeout_s) as response:
            return json.loads(response.read())

    def metrics(self) -> dict[str, Any]:
        with urlopen(self.base_url + "/metrics", timeout=self.timeout_s) as response:
            return json.loads(response.read())

    def __call__(self, request: Mapping[str, Any]) -> dict[str, Any]:
        return self.infer(request)


__all__ = ["QwenServiceClient"]
