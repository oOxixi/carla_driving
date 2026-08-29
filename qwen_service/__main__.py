"""Start the local bounded Qwen service."""

from __future__ import annotations

import argparse
from pathlib import Path

from integration.qwen_vl_adapter import StrictQwenVLAdapter

from .runtime import QwenServiceRuntime
from .server import create_server


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--model-name")
    parser.add_argument("--image-root", type=Path)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18000)
    parser.add_argument("--max-concurrency", type=int, default=1)
    parser.add_argument("--timeout-s", type=float, default=5.0)
    parser.add_argument("--max-new-tokens", type=int, default=48)
    parser.add_argument(
        "--awq-backend",
        choices=("auto", "torch_awq", "gemm", "gemm_triton"),
        default="auto",
        help="AWQ kernel override; torch_awq is the portable fallback",
    )
    parser.add_argument("--min-pixels", type=int, default=64 * 28 * 28)
    parser.add_argument("--max-pixels", type=int, default=64 * 28 * 28)
    args = parser.parse_args()

    model_path = args.model_path.expanduser().resolve()
    adapter = StrictQwenVLAdapter.from_local_checkpoint(
        model_path,
        image_root=args.image_root,
        max_new_tokens=args.max_new_tokens,
        awq_backend=args.awq_backend,
        min_pixels=args.min_pixels,
        max_pixels=args.max_pixels,
    )
    runtime = QwenServiceRuntime(
        adapter,
        model_name=args.model_name or model_path.name,
        max_concurrency=args.max_concurrency,
        timeout_s=args.timeout_s,
    )
    server = create_server(runtime, host=args.host, port=args.port)
    try:
        print(
            f"Qwen service ready at http://{args.host}:{server.server_port} "
            f"model={runtime.health()['model']}",
            flush=True,
        )
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        runtime.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
