"""Rebuild and compare the A3 recovery cumulative view read-only."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile
from typing import Any

from challenge.dataset.build_a3_recovery_cumulative_view import (
    DEFAULT_D2_RELEASE,
    DEFAULT_D3_RELEASE,
    DEFAULT_D3_WAVE2_RELEASE,
    DEFAULT_OUTPUT,
    DEFAULT_TARGETED_GAP_RELEASE,
    DEFAULT_TURN_GAP_RELEASE,
    RECOVERY_VIEW_VERSION,
    build_recovery_cumulative_view,
)
from challenge.dataset.validate_d2_release import canonical_text_sha256


def audit_recovery_cumulative_view(
    d2: Path,
    wave1: Path,
    wave2: Path,
    targeted: Path,
    turn: Path,
    view: Path,
    *,
    check_images: bool = True,
) -> dict[str, Any]:
    view = view.resolve()
    with tempfile.TemporaryDirectory(prefix="a3-recovery-audit-") as temporary:
        expected_dir = Path(temporary)
        expected = build_recovery_cumulative_view(
            d2, wave1, wave2, targeted, turn, expected_dir,
            check_images=check_images,
        )
        actual_manifest_path = view / "a3_cumulative_view_manifest.json"
        actual = json.loads(actual_manifest_path.read_text(encoding="utf-8"))
        if actual != expected:
            raise ValueError("recovery view manifest does not reproduce from immutable inputs")
        for name, details in expected["files"].items():
            path = view / name
            if canonical_text_sha256(path) != details["sha256"]:
                raise ValueError(f"recovery view file changed: {name}")
            if len(path.read_bytes().replace(b"\r\n", b"\n")) != details["bytes"]:
                raise ValueError(f"recovery view file size changed: {name}")
    return {
        "status": "PASS",
        "view_version": RECOVERY_VIEW_VERSION,
        "view_manifest_sha256": canonical_text_sha256(actual_manifest_path),
        "source_evidence_sha256": actual["source_evidence_sha256"],
        "counts": actual["counts"],
        "image_check_enabled": check_images,
        "current_v3_candidate_identity_unchanged": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--d2-release-dir", type=Path, default=Path(DEFAULT_D2_RELEASE))
    parser.add_argument("--d3-wave1-release-dir", type=Path, default=Path(DEFAULT_D3_RELEASE))
    parser.add_argument("--d3-wave2-release-dir", type=Path, default=Path(DEFAULT_D3_WAVE2_RELEASE))
    parser.add_argument("--targeted-gap-release-dir", type=Path, default=Path(DEFAULT_TARGETED_GAP_RELEASE))
    parser.add_argument("--turn-gap-release-dir", type=Path, default=Path(DEFAULT_TURN_GAP_RELEASE))
    parser.add_argument("--view-dir", type=Path, default=Path(DEFAULT_OUTPUT))
    parser.add_argument("--skip-images", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit_recovery_cumulative_view(
        args.d2_release_dir,
        args.d3_wave1_release_dir,
        args.d3_wave2_release_dir,
        args.targeted_gap_release_dir,
        args.turn_gap_release_dir,
        args.view_dir,
        check_images=not args.skip_images,
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
