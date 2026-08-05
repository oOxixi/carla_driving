"""Strict parser for one Qwen GPTQ/Marlin launch evidence block.

Launchers must emit the following exact, line-oriented contract.  ``launch_id``
is any non-empty token without whitespace and must agree at BEGIN and END.

    QWEN_LAUNCH_BEGIN launch_id=<id> profile=qwen3vl-2b-int4 model=h2oai/Qwen3-VL-2B-Instruct-GPTQ-Int4
    quantization=auto_gptq
    Using MarlinLinearKernel for AutoGPTQLinearMethod
    batch1_path=gemv                 # optional; only this field proves GEMV
    QWEN_LAUNCH_END launch_id=<id>
"""

from __future__ import annotations

import re
from pathlib import Path


DEFAULT_PROFILE = "qwen3vl-2b-int4"
DEFAULT_MODEL = "h2oai/Qwen3-VL-2B-Instruct-GPTQ-Int4"
LAUNCH_BEGIN = "QWEN_LAUNCH_BEGIN"
LAUNCH_END = "QWEN_LAUNCH_END"
BEGIN_PATTERN = re.compile(
    rf"^{LAUNCH_BEGIN} launch_id=(?P<launch_id>\S+) "
    rf"profile={re.escape(DEFAULT_PROFILE)} model={re.escape(DEFAULT_MODEL)}$"
)
END_PATTERN = re.compile(rf"^{LAUNCH_END} launch_id=(?P<launch_id>\S+)$")
QUANTIZATION_PATTERN = re.compile(r"^quantization=auto_gptq$")
MARLIN_PATTERN = re.compile(r"^Using MarlinLinearKernel(?: .*)?$")
GEMV_PATTERN = re.compile(r"^batch1_path=gemv$")


def _complete_blocks(lines: list[str]) -> list[list[str]]:
    blocks: list[list[str]] = []
    active_id: str | None = None
    active_lines: list[str] = []
    for line in lines:
        if line.startswith(LAUNCH_BEGIN):
            match = BEGIN_PATTERN.fullmatch(line)
            if match is None:
                raise ValueError("invalid Qwen launch BEGIN evidence marker")
            if active_id is not None:
                raise ValueError("nested Qwen launch evidence blocks are not allowed")
            active_id = match["launch_id"]
            active_lines = []
            continue
        if line.startswith(LAUNCH_END):
            match = END_PATTERN.fullmatch(line)
            if match is None or active_id is None:
                raise ValueError("invalid Qwen launch END evidence marker")
            if match["launch_id"] != active_id:
                raise ValueError("Qwen launch END launch_id does not match BEGIN")
            blocks.append(active_lines)
            active_id = None
            active_lines = []
            continue
        if active_id is not None:
            active_lines.append(line)
    if active_id is not None:
        raise ValueError("unterminated Qwen launch evidence block")
    return blocks


def verify_kernel_log(path: Path) -> dict[str, str]:
    """Return runtime evidence only for the unique complete ready launch block."""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    ready = [
        block
        for block in _complete_blocks(lines)
        if any(QUANTIZATION_PATTERN.fullmatch(line) for line in block)
        and any(MARLIN_PATTERN.fullmatch(line) for line in block)
    ]
    if not ready:
        raise ValueError("no complete Qwen launch block proves auto_gptq and Marlin")
    if len(ready) != 1:
        raise ValueError("expected exactly one complete ready Qwen launch block")
    mode = "gemv" if any(GEMV_PATTERN.fullmatch(line) for line in ready[0]) else "marlin_batch1"
    return {
        "quantization": "auto_gptq",
        "linear_kernel": "MarlinLinearKernel",
        "batch1_path": mode,
    }
