from __future__ import annotations

from .command_adapter import build_command
from .day22_cases import CASES
from .day22_context import Day22Context
from .qwen_day22_adapter import (
    ALLOWED_ACTIONS,
    FORBIDDEN_FIELDS,
    Day22QwenAdapter,
)


def main() -> None:
    adapter = Day22QwenAdapter()
    passed = 0

    for case in CASES:
        context = Day22Context(
            voice_command=case["voice"],
            safety_state=case["safety_state"],
            perception={},
            scene_state={},
        )

        decision = adapter.infer(context)

        assert decision["action"] == case["expected"], (
            case["case"],
            case["expected"],
            decision,
        )

        assert decision["action"] in ALLOWED_ACTIONS
        assert not FORBIDDEN_FIELDS.intersection(decision.keys())
        assert 0.0 <= decision["confidence"] <= 1.0
        assert isinstance(decision["requires_confirmation"], bool)
        assert len(decision["reason_zh"]) <= 20

        assert (
            decision["requires_confirmation"]
            == case["expected_confirmation"]
        )

        command = build_command(decision, case["voice"])

        assert command["intent"] == decision["action"]
        assert command["confirm_required"] == (
            decision["requires_confirmation"]
        )
        assert command["schema_version"] == "1.0"

        passed += 1

    print(f"DAY22 SMOKE PASS {passed}")


if __name__ == "__main__":
    main()
