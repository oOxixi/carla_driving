"""Small dependency-free HTTP surface for the bounded Qwen runtime."""

from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from typing import Any
from urllib.parse import urlsplit

from .runtime import (
    InferenceTimeoutError,
    ModelInferenceError,
    QwenServiceRuntime,
    ServiceBusyError,
)


_MAX_REQUEST_BYTES = 1_048_576


def create_server(
    runtime: QwenServiceRuntime,
    *,
    host: str = "127.0.0.1",
    port: int = 18000,
) -> ThreadingHTTPServer:
    if not isinstance(runtime, QwenServiceRuntime):
        raise TypeError("runtime must be QwenServiceRuntime")

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            path = urlsplit(self.path).path
            if path == "/health":
                self._send(HTTPStatus.OK, runtime.health())
            elif path == "/metrics":
                self._send(HTTPStatus.OK, runtime.metrics())
            else:
                self._error(HTTPStatus.NOT_FOUND, "NOT_FOUND", "unknown route")

        def do_POST(self) -> None:
            if urlsplit(self.path).path != "/infer":
                self._error(HTTPStatus.NOT_FOUND, "NOT_FOUND", "unknown route")
                return
            request_id: str | None = None
            try:
                payload = self._read_json()
                value = payload.get("request_id")
                if isinstance(value, str):
                    request_id = value
                response = runtime.infer(payload)
            except (TypeError, ValueError, json.JSONDecodeError) as error:
                self._error(
                    HTTPStatus.BAD_REQUEST,
                    "INVALID_REQUEST",
                    str(error),
                    request_id=request_id,
                )
                return
            except ServiceBusyError as error:
                self._error(
                    HTTPStatus.TOO_MANY_REQUESTS,
                    "BUSY",
                    str(error),
                    request_id=request_id,
                )
                return
            except InferenceTimeoutError as error:
                self._error(
                    HTTPStatus.GATEWAY_TIMEOUT,
                    "TIMEOUT",
                    str(error),
                    request_id=request_id,
                )
                return
            except ModelInferenceError as error:
                self._error(
                    HTTPStatus.BAD_GATEWAY,
                    "MODEL_ERROR",
                    str(error),
                    request_id=request_id,
                )
                return
            self._send(HTTPStatus.OK, response)

        def _read_json(self) -> dict[str, Any]:
            raw_length = self.headers.get("Content-Length")
            if raw_length is None:
                raise ValueError("Content-Length is required")
            try:
                length = int(raw_length)
            except ValueError as error:
                raise ValueError("Content-Length must be an integer") from error
            if length < 1 or length > _MAX_REQUEST_BYTES:
                raise ValueError(
                    f"request body must be between 1 and {_MAX_REQUEST_BYTES} bytes"
                )
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(payload, dict):
                raise TypeError("request body must be a JSON object")
            return payload

        def _error(
            self,
            status: HTTPStatus,
            code: str,
            message: str,
            *,
            request_id: str | None = None,
        ) -> None:
            body: dict[str, object] = {
                "schema_version": "1.0",
                "status": "ERROR",
                "error_code": code,
                "message": message,
            }
            if request_id is not None:
                body["request_id"] = request_id
            self._send(status, body)

        def _send(self, status: HTTPStatus, body: object) -> None:
            encoded = json.dumps(
                body,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            ).encode("utf-8")
            self.send_response(int(status))
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def log_message(self, _format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer((host, port), Handler)
    server.daemon_threads = True
    return server


__all__ = ["create_server"]
