from __future__ import annotations

import json
from pathlib import Path

from integration.run_manifest import begin_run, finish_run


def test_failed_run_keeps_logs_and_atomic_final_status(tmp_path: Path) -> None:
    context = begin_run(
        tmp_path,
        {
            "git_commit": "05281a8",
            "profile": "qwen3vl-2b-int4",
            "dataset_sha256": "a" * 64,
            "seed": 20260804,
        },
    )
    (context.logs_dir / "qwen_server.log").write_text(
        "startup failed", encoding="utf-8"
    )

    finish_run(context, "FAILED", "qwen_not_ready")

    manifest = json.loads(context.manifest_path.read_text(encoding="utf-8"))
    assert manifest["status"] == "FAILED"
    assert manifest["failure_reason"] == "qwen_not_ready"
    assert (context.logs_dir / "qwen_server.log").exists()
    assert not context.manifest_path.with_suffix(".json.tmp").exists()
