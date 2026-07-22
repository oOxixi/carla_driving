from __future__ import annotations

import json
from pathlib import Path

from .command_adapter import build_command
from .day22_cases import CASES
from .day22_context import Day22Context
from .qwen_day22_adapter import Day22QwenAdapter


OUTPUT_PATH = Path("integration/day22/day22_results.json")


def main() -> None:
    adapter = Day22QwenAdapter()
    outputs = []

    for case in CASES:
        context = Day22Context(
            voice_command=case["voice"],
            safety_state=case["safety_state"],
            perception={},
            scene_state={},
        )

        decision = adapter.infer(context)
        command = build_command(decision, context.voice_command)

        outputs.append({
            "case": case["case"],
            "expected": case["expected"],
            "expected_confirmation": case[
                "expected_confirmation"
            ],
            "input": context.to_dict(),
            "decision": decision,
            "command": command,
        })

    OUTPUT_PATH.write_text(
        json.dumps(
            outputs,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(f"saved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
