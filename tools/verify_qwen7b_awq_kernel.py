"""Reject a Qwen2.5-VL 7B launch log unless vLLM selected AWQ-Marlin."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


MODEL = "Qwen/Qwen2.5-VL-7B-Instruct-AWQ"


def verify_awq_marlin_log(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    if MODEL not in text:
        raise ValueError(f"launch log does not identify {MODEL}")
    if "quantization=awq_marlin" not in text and "Using awq_marlin kernel" not in text:
        raise ValueError("launch log does not prove awq_marlin quantization")
    if "Using MarlinLinearKernel for AWQMarlinLinearMethod" not in text:
        raise ValueError("launch log does not prove AWQ MarlinLinearKernel")
    return {
        "model": MODEL,
        "quantization": "awq_marlin",
        "linear_kernel": "MarlinLinearKernel",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify_awq_marlin_log(args.log), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
