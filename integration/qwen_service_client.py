"""Client for the repository-owned bounded Qwen inference service."""

from __future__ import annotations

from collections.abc import Mapping
from http.client import HTTPResponse
import json
import math
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from .qwen_boundary import QwenInputContext, validate_qwen_response


class QwenServiceClient:
    def __init__(self, base_url: str, *, timeout_s: float = 5.0) -> None:
        if type(base_url) is not str or not base_url.strip():
            raise ValueError("base_url must be a non-empty string")
        parsed = urlsplit(base_url.strip())
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("base_url must be an absolute HTTP(S) URL")
        if parsed.query or parsed.fragment:
            raise ValueError("base_url must not contain a query or fragment")
        if (
            type(timeout_s) not in (int, float)
            or isinstance(timeout_s, bool)
            or not math.isfinite(float(timeout_s))
            or float(timeout_s) <= 0.0
        ):
            raise ValueError("timeout_s must be finite and positive")
        self._base_url = base_url.rstrip("/")
        self._timeout_s = float(timeout_s)

    def infer(self, context: QwenInputContext) -> dict[str, Any]:
        if not isinstance(context, QwenInputContext):
            raise TypeError("context must be QwenInputContext")
        body = json.dumps(
            context.to_payload(),
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
        request = Request(
            f"{self._base_url}/infer",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        response = self._open(request)
        payload = _response_json(response)
        if payload.get("status") != "READY":
            raise RuntimeError("Qwen service returned a non-ready response")
        if payload.get("request_id") != context.request_id:
            raise RuntimeError("Qwen service response request_id mismatch")
        decision = payload.get("decision")
        if not isinstance(decision, Mapping):
            raise RuntimeError("Qwen service response has no decision object")
        return validate_qwen_response(decision)

    def health(self) -> dict[str, Any]:
        return self._get("health")

    def metrics(self) -> dict[str, Any]:
        return self._get("metrics")

    def _get(self, route: str) -> dict[str, Any]:
        request = Request(f"{self._base_url}/{route}", method="GET")
        return _response_json(self._open(request))

    def _open(self, request: Request) -> HTTPResponse:
        try:
            return urlopen(request, timeout=self._timeout_s)
        except HTTPError as error:
            try:
                payload = json.loads(error.read().decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                payload = {}
            code = payload.get("error_code", f"HTTP_{error.code}")
            message = payload.get("message", error.reason)
            raise RuntimeError(f"Qwen service {code}: {message}") from error
        except URLError as error:
            raise RuntimeError(f"Qwen service unavailable: {error.reason}") from error


def _response_json(response: HTTPResponse) -> dict[str, Any]:
    try:
        payload = json.loads(response.read().decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError("Qwen service returned invalid JSON") from error
    finally:
        response.close()
    if not isinstance(payload, dict):
        raise RuntimeError("Qwen service response must be a JSON object")
    return payload


__all__ = ["QwenServiceClient"]
