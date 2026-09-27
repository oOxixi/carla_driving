"""Cross-check: A3's intake auditor must keep accepting B3's published v3 evidence.

A3 added ``challenge/distillation/audit_b3_v3_diagnostic.py``, which reads B3's
evidence directory, binds it to A3's frozen candidate identity and fails closed
unless every number, digest and gate status matches. Running that consumer from
B3's own suite turns the coupling into a regression guard: if B3 ever reshapes
the evidence bundle, the downstream intake breaks and this test says so first.

The test is skipped when either side is missing (for example on a branch that
does not carry A3's auditor yet).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
AUDITOR = REPO_ROOT / "challenge" / "distillation" / "audit_b3_v3_diagnostic.py"
EVIDENCE = REPO_ROOT / "challenge" / "hil" / "evidence" / "a3_fp32_candidate_v3_20260926"


@pytest.mark.skipif(not AUDITOR.is_file(), reason="A3 intake auditor not present on this checkout")
@pytest.mark.skipif(not EVIDENCE.is_dir(), reason="B3 v3 evidence bundle not present")
def test_a3_intake_auditor_accepts_b3_evidence(tmp_path: Path) -> None:
    output = tmp_path / "a3_intake.json"
    proc = subprocess.run(
        [sys.executable, str(AUDITOR), "--evidence-dir", str(EVIDENCE), "--output", str(output)],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    assert proc.returncode == 0, f"auditor failed\n{proc.stdout}\n{proc.stderr}"
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["errors"] == [], report["errors"]
    assert report["eligible_for_promotion"] is False, "diagnostic evidence must never be promotable"
