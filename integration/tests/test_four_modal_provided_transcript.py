from __future__ import annotations

from tools.run_four_modal_full_chain import _provided_transcript_command


def test_provided_transcript_runs_real_nlu_without_asr() -> None:
    command = _provided_transcript_command("立即停车", "case-1")

    assert command["source_text"] == "立即停车"
    assert command["intent"] == "EMERGENCY_STOP"
    assert command["status"] == "valid"
    assert command["confirm_required"] is False
