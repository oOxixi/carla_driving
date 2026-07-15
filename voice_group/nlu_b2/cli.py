"""Command line entry for the B2 parser."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .parser import CommandParser


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse B1 NLU result into B2 vehicle command JSON.")
    parser.add_argument("--input", help="B1 result as a JSON string. If omitted, stdin is used.")
    parser.add_argument("--input-file", help="UTF-8 JSON file containing a B1 result.")
    parser.add_argument("--request-id", help="B1 request_id, used with --intent for quick tests.")
    parser.add_argument("--intent", help="Intent name, used with --text for quick tests.")
    parser.add_argument("--text", help="Normalized text, used with --intent for quick tests.")
    parser.add_argument("--intent-confidence", type=float, help="B1 intent confidence.")
    args = parser.parse_args()

    payload = _load_payload(args)
    result = CommandParser().parse(payload)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _load_payload(args: argparse.Namespace) -> dict[str, Any]:
    if args.input_file:
        return json.loads(Path(args.input_file).read_text(encoding="utf-8"))
    if args.input:
        return json.loads(args.input)
    if args.intent and args.text:
        payload: dict[str, Any] = {
            "intent": args.intent,
            "normalized_text": args.text,
            "status": "valid",
            "route": "fast",
        }
        if args.request_id:
            payload["request_id"] = args.request_id
        if args.intent_confidence is not None:
            payload["intent_confidence"] = args.intent_confidence
        return payload
    raw = sys.stdin.read().strip()
    if not raw:
        raise SystemExit("请通过 --input、--intent/--text 或 stdin 提供输入")
    return json.loads(raw)


if __name__ == "__main__":
    raise SystemExit(main())
