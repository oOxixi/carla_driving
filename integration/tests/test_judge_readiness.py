from __future__ import annotations

from tools.validate_judge_readiness import (
    _qwen_contract_check,
    render_markdown,
)


def test_judge_readiness_qwen_contract_is_self_consistent() -> None:
    check = _qwen_contract_check()

    assert check["status"] == "PASS"
    assert check["model"] == "Qwen/Qwen3.5-2B"
    assert check["revision"] == (
        "15852e8c16360a2fea060d615a32b45270f8a8fc"
    )
    assert all(check["dimensions"].values())


def test_judge_markdown_distinguishes_static_from_live_evidence() -> None:
    report = {
        "status": "PASS",
        "scope": "static",
        "created_at_utc": "2026-09-12T00:00:00+00:00",
        "failed_checks": [],
        "checks": [
            {
                "name": "repository_baseline",
                "status": "PASS",
                "branch": "main_optimization",
                "head": "abc",
                "based_on_origin_main": True,
                "clean": True,
            },
            {
                **_qwen_contract_check(),
                "duration_s": 0.0,
            },
        ],
    }

    markdown = render_markdown(report)

    assert "Overall: **PASS**" in markdown
    assert "Qwen/Qwen3.5-2B" in markdown
    assert "Static PASS proves repository contracts and tests only" in markdown
    assert "--require-live" in markdown
