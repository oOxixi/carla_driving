import json
from pathlib import Path

from challenge.benchmark.benchmark import (
    canonical_lf_sha256,
    load_benchmark_cases,
)


ROOT = Path(__file__).resolve().parents[3]
RELEASE_DIR = ROOT / "challenge" / "dataset" / "releases" / "d2_v1_1"
VAL_PATH = RELEASE_DIR / "val.jsonl"
MANIFEST_PATH = RELEASE_DIR / "release_manifest.json"


def test_signed_val_matches_b1_release_manifest() -> None:
    """B2 must evaluate exactly the B1-signed Validation artifact."""
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    signed_val = manifest["files"]["val.jsonl"]

    cases = load_benchmark_cases(VAL_PATH)

    assert len(cases) == signed_val["rows"] == 539
    assert canonical_lf_sha256(VAL_PATH) == signed_val["sha256"]


def test_benchmark_case_identity_is_traceable() -> None:
    """Every case must keep a unique ID and matching request/plan identity."""
    cases = load_benchmark_cases(VAL_PATH)

    sample_ids = [case["sample_id"] for case in cases]

    assert len(sample_ids) == len(set(sample_ids))

    for case in cases:
        request = case["model_request"]
        plan = case["teacher_plan"]

        assert request["request_id"] == plan["request_id"]
        assert request["command_id"] == plan["command_id"]
        assert plan["schema_version"] == "2.0"
        assert plan["steps"]


def test_canonical_hash_is_stable_across_line_endings(
    tmp_path: Path,
) -> None:
    """Windows CRLF checkout and repository LF bytes must hash identically."""
    lf_path = tmp_path / "lf.jsonl"
    crlf_path = tmp_path / "crlf.jsonl"

    lf_path.write_bytes(b'{"sample": 1}\n{"sample": 2}\n')
    crlf_path.write_bytes(b'{"sample": 1}\r\n{"sample": 2}\r\n')

    assert canonical_lf_sha256(lf_path) == canonical_lf_sha256(crlf_path)