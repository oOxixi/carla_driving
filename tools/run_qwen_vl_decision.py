"""Run one strict high-level decision with a local Qwen2.5-VL checkpoint."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from integration.qwen_boundary import QwenInputContext
from integration.qwen_vl_adapter import StrictQwenVLAdapter


def load_context(path: Path) -> QwenInputContext:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise TypeError("context file must contain one JSON object")
    return QwenInputContext(
        request_id=payload["request_id"],
        frame=payload["frame"],
        sim_time_s=payload["sim_time_s"],
        voice_command=payload["voice_command"],
        rgb_ref=payload.get("rgb_ref"),
        scene_state=_mapping(payload, "scene_state"),
        perception=_mapping(payload, "perception"),
        safety_state=_mapping(payload, "safety_state"),
    )


def _mapping(payload: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    value = payload.get(name)
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be an object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("context_json", type=Path)
    parser.add_argument("--model-path", required=True, type=Path)
    parser.add_argument("--image-root", type=Path)
    parser.add_argument("--max-new-tokens", type=int, default=192)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        context = load_context(args.context_json)
        adapter = StrictQwenVLAdapter.from_local_checkpoint(
            args.model_path,
            image_root=args.image_root,
            max_new_tokens=args.max_new_tokens,
        )
        decision = adapter(context)
        trace = adapter.last_trace
        assert trace is not None
        report = {
            "schema_version": "1.0",
            "request_id": context.request_id,
            "status": "READY",
            "decision": decision,
            "latency_ms": trace.latency_ms,
            "raw_model_output": trace.raw_output,
            "image_path": trace.image_path,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 0
    except Exception as error:
        print(json.dumps({
            "status": "ERROR",
            "error_type": type(error).__name__,
            "error": str(error),
        }, ensure_ascii=False, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
