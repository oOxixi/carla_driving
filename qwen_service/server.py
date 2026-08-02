"""Dependency-light HTTP server exposing /health, /infer and /metrics."""

from __future__ import annotations

import argparse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from typing import Any

from .service import (
    DeterministicTestBackend,
    LocalQwenBackend,
    QwenDecisionService,
    QwenServiceConfig,
    ServiceFailure,
    UnavailableBackend,
)


class QwenHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], service: QwenDecisionService) -> None:
        super().__init__(address, QwenRequestHandler)
        self.service = service


class QwenRequestHandler(BaseHTTPRequestHandler):
    server: QwenHTTPServer
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        if self.path == "/health":
            payload = self.server.service.health()
            self._send(HTTPStatus.OK if payload["status"] == "READY" else HTTPStatus.SERVICE_UNAVAILABLE, payload)
            return
        if self.path == "/metrics":
            self._send(HTTPStatus.OK, self.server.service.metrics())
            return
        self._send(HTTPStatus.NOT_FOUND, {"status": "ERROR", "error_code": "NOT_FOUND"})

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
        if self.path != "/infer":
            self._send(HTTPStatus.NOT_FOUND, {"status": "ERROR", "error_code": "NOT_FOUND"})
            return
        content_type = self.headers.get_content_type()
        if content_type != "application/json":
            self._send(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {"status": "ERROR", "error_code": "JSON_REQUIRED"})
            return
        length_text = self.headers.get("Content-Length")
        try:
            length = int(length_text or "0")
        except ValueError:
            length = -1
        maximum = self.server.service.config.max_request_bytes
        if length < 1 or length > maximum:
            self._send(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"status": "ERROR", "error_code": "REQUEST_SIZE_INVALID"})
            return
        try:
            payload = json.loads(self.rfile.read(length))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            self._send(HTTPStatus.BAD_REQUEST, {"status": "ERROR", "error_code": "INVALID_JSON", "message": str(error)})
            return
        try:
            result = self.server.service.infer(payload)
        except ServiceFailure as error:
            self._send(error.status_code, error.to_dict())
            return
        self._send(HTTPStatus.OK, result)

    def log_message(self, format: str, *args: Any) -> None:
        # Structured operational logs; no prompt/image content is printed.
        print(json.dumps({
            "client": self.client_address[0],
            "request": format % args,
        }, ensure_ascii=False), flush=True)

    def _send(self, status: int | HTTPStatus, payload: Any) -> None:
        body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        self.send_response(int(status))
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def build_service(args: argparse.Namespace) -> QwenDecisionService:
    if args.deterministic_test_backend:
        backend = DeterministicTestBackend()
    elif args.model_path is not None:
        backend = LocalQwenBackend(
            args.model_path,
            image_root=args.image_root,
            max_new_tokens=args.max_new_tokens,
            min_pixels=args.min_pixels,
            max_pixels=args.max_pixels,
        )
    else:
        backend = UnavailableBackend()
    return QwenDecisionService(
        backend,
        config=QwenServiceConfig(
            timeout_ms=args.timeout_ms,
            max_concurrency=args.max_concurrency,
            max_request_bytes=args.max_request_bytes,
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--model-path", type=Path)
    parser.add_argument("--image-root", type=Path)
    parser.add_argument("--deterministic-test-backend", action="store_true",
                        help="contract tests only; never production evidence")
    parser.add_argument("--timeout-ms", type=float, default=300.0)
    parser.add_argument("--max-concurrency", type=int, default=1)
    parser.add_argument("--max-request-bytes", type=int, default=262_144)
    parser.add_argument("--max-new-tokens", type=int, default=48)
    parser.add_argument("--min-pixels", type=int, default=64 * 28 * 28)
    parser.add_argument("--max-pixels", type=int, default=256 * 28 * 28)
    args = parser.parse_args()
    service = build_service(args)
    server = QwenHTTPServer((args.host, args.port), service)
    print(json.dumps({
        "record_type": "qwen_service_start",
        "listen": f"http://{args.host}:{args.port}",
        "health": service.health(),
    }, ensure_ascii=False), flush=True)
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        service.close(wait=False)


if __name__ == "__main__":
    main()
