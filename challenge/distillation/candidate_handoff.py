"""Build a fail-closed A3 FP32 candidate package for independent B2 evaluation."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence


REQUIRED_SOURCE_FILES = (
    "student_v0_fp32_candidate.pt",
    "student_v0_fp32_candidate.json",
    "student_fp32_best.pt",
    "training_summary.json",
    "training_report.md",
    "training.jsonl",
    "dataset_preflight.json",
    "hard_cases/summary.json",
)
PACKAGE_FILES = tuple(
    relative for relative in REQUIRED_SOURCE_FILES if relative != "student_fp32_best.pt"
)


def build_candidate_handoff(
    source_directory: str | Path,
    output_directory: str | Path,
    *,
    config_snapshot: bytes,
    config_source: Mapping[str, str],
) -> dict[str, Any]:
    """Verify and copy one pending production candidate into an immutable package."""
    source = Path(source_directory).resolve()
    output = Path(output_directory).resolve()
    if output.exists():
        raise FileExistsError(f"handoff output already exists: {output}")
    for relative in REQUIRED_SOURCE_FILES:
        if not (source / relative).is_file():
            raise ValueError(f"candidate source is missing {relative}")

    candidate = _read_object(source / "student_v0_fp32_candidate.json")
    summary = _read_object(source / "training_summary.json")
    preflight = _read_object(source / "dataset_preflight.json")
    hard_cases = _read_object(source / "hard_cases" / "summary.json")
    _validate_candidate(candidate, summary, preflight, hard_cases, source)

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
    try:
        for relative in PACKAGE_FILES:
            destination = temporary / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / relative, destination)
        (temporary / "training_config.yaml").write_bytes(config_snapshot)

        manifest = {
            "schema_version": "1.0",
            "package_status": "PENDING_B2_INDEPENDENT_VALIDATION",
            "gate_status": "PENDING_A3_FP32_GATE",
            "candidate_identity": {
                "git_sha": candidate["git_sha"],
                "model_id": candidate["model_id"],
                "config_id": candidate["config_id"],
                "weights_sha256": candidate["weights_sha256"],
                "dataset_version": candidate["dataset_version"],
                "release_manifest_sha256": candidate["release_manifest_sha256"],
                "a3_view_manifest_sha256": candidate["a3_view_manifest_sha256"],
                "teacher_identity_policy": candidate["teacher_identity_policy"],
                **({
                    field: candidate[field]
                    for field in (
                        "d2_release_manifest_sha256", "b1_signature_sha256",
                        "source_evidence_sha256",
                    )
                    if candidate.get(field) is not None
                }),
            },
            "training_evidence": {
                "source_checkpoint_sha256": candidate["source_checkpoint_sha256"],
                "train_samples": summary["train_samples"],
                "validation_samples": summary["validation_samples"],
                "hard_case_count": summary["hard_case_count"],
                "development_validation_only": True,
            },
            "config_source": dict(config_source),
            "limitations": [
                "This package is not A3_FP32_GATE_PASSED.",
                "Development Validation is not independent generalization evidence.",
                "B2 must evaluate the exact weights on its frozen independent Validation package.",
            ],
        }
        (temporary / "README.md").write_text(_readme(manifest), encoding="utf-8")
        files: dict[str, dict[str, Any]] = {}
        for path in sorted(item for item in temporary.rglob("*") if item.is_file()):
            relative = path.relative_to(temporary).as_posix()
            files[relative] = {"sha256": _sha256(path), "size_bytes": path.stat().st_size}
        manifest["files"] = files
        _write_json(temporary / "handoff_manifest.json", manifest)
        temporary.replace(output)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return manifest


def _validate_candidate(
    candidate: Mapping[str, Any],
    summary: Mapping[str, Any],
    preflight: Mapping[str, Any],
    hard_cases: Mapping[str, Any],
    source: Path,
) -> None:
    if candidate.get("gate_status") != "PENDING_A3_FP32_GATE":
        raise ValueError("handoff requires a candidate pending the A3 FP32 gate")
    if candidate.get("source_worktree_dirty") is not False:
        raise ValueError("candidate must originate from a clean worktree")
    if candidate.get("teacher_identity_policy") not in {
        "signed_d2_release_formal", "signed_cumulative_release_formal",
    }:
        raise ValueError("handoff requires the formal signed-release identity policy")
    for field, length in (
        ("git_sha", 40),
        ("weights_sha256", 64),
        ("source_checkpoint_sha256", 64),
        ("release_manifest_sha256", 64),
        ("a3_view_manifest_sha256", 64),
    ):
        _require_hex(str(candidate.get(field, "")), length, field)
    if candidate.get("teacher_identity_policy") == "signed_cumulative_release_formal":
        for field in (
            "d2_release_manifest_sha256", "b1_signature_sha256",
            "source_evidence_sha256",
        ):
            _require_hex(str(candidate.get(field, "")), 64, field)
    for field in ("model_id", "config_id", "dataset_version"):
        if not str(candidate.get(field, "")).strip():
            raise ValueError(f"candidate requires {field}")
    if _sha256(source / "student_v0_fp32_candidate.pt") != candidate["weights_sha256"]:
        raise ValueError("candidate weight SHA256 does not match its manifest")
    if _sha256(source / "student_fp32_best.pt") != candidate["source_checkpoint_sha256"]:
        raise ValueError("best checkpoint SHA256 does not match the candidate manifest")

    pairs = (
        ("git_sha", "git_sha"),
        ("teacher_git_sha", "teacher_git_sha"),
        ("teacher_model_id", "teacher_model_id"),
        ("teacher_model_revision", "teacher_model_revision"),
        ("teacher_artifact_fingerprint_sha256", "teacher_artifact_fingerprint_sha256"),
        ("teacher_identity_policy", "teacher_identity_policy"),
        ("model_id", "model_id"),
        ("config_id", "model_config_id"),
        ("dataset_version", "dataset_version"),
        ("release_manifest_sha256", "release_manifest_sha256"),
        ("a3_view_manifest_sha256", "a3_view_manifest_sha256"),
        ("weights_sha256", "candidate_weights_sha256"),
        ("source_checkpoint_sha256", "best_checkpoint_sha256"),
        ("gate_status", "candidate_gate_status"),
    )
    for candidate_field, summary_field in pairs:
        if candidate.get(candidate_field) != summary.get(summary_field):
            raise ValueError(
                f"candidate {candidate_field} does not match training summary {summary_field}"
            )
    if candidate.get("teacher_identity_policy") == "signed_cumulative_release_formal":
        for field in (
            "d2_release_manifest_sha256", "b1_signature_sha256",
            "source_evidence_sha256",
        ):
            if candidate.get(field) != summary.get(field):
                raise ValueError(f"candidate {field} does not match training summary {field}")
    if summary.get("smoke_only") is not False or summary.get("integration_smoke_only") is not False:
        raise ValueError("Smoke or integration-only training cannot enter the B2 handoff")
    if preflight.get("valid") is not True or preflight.get("error_count") != 0:
        raise ValueError("dataset preflight must be valid with zero errors")
    if preflight.get("expected_dataset_version") != candidate.get("dataset_version"):
        raise ValueError("dataset preflight version does not match the candidate")
    if hard_cases.get("hard_case_count") != summary.get("hard_case_count"):
        raise ValueError("hard-case summary count does not match training summary")


def _config_from_git(repo_root: Path, revision: str, relative_path: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(repo_root), "show", f"{revision}:{relative_path}"],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        raise ValueError(
            f"cannot read training config at {revision}:{relative_path}: "
            f"{result.stderr.decode(errors='replace').strip()}"
        )
    return result.stdout


def _read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(dict(value), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_hex(value: str, length: int, field: str) -> None:
    if len(value) != length or any(char not in "0123456789abcdef" for char in value.lower()):
        raise ValueError(f"candidate requires a valid {field}")


def _readme(manifest: Mapping[str, Any]) -> str:
    identity = manifest["candidate_identity"]
    return (
        "# A3 FP32 Candidate Handoff\n\n"
        "This is a pending candidate package for B2 independent Validation. It is not a "
        "production approval or a Frozen Test result.\n\n"
        f"- Gate status: `{manifest['gate_status']}`\n"
        f"- Model: `{identity['model_id']}` / `{identity['config_id']}`\n"
        f"- Weights SHA256: `{identity['weights_sha256']}`\n"
        f"- Dataset: `{identity['dataset_version']}`\n"
        f"- Training Git SHA: `{identity['git_sha']}`\n\n"
        "B2 must use the exact packaged weights and return only the approved independent "
        "Validation evidence required by the promotion contract.\n"
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument(
        "--config-path",
        default="challenge/distillation/d2_v1_1_formal_config.yaml",
    )
    args = parser.parse_args(argv)
    source = Path(args.source)
    candidate = _read_object(source / "student_v0_fp32_candidate.json")
    config = _config_from_git(Path(args.repo_root).resolve(), candidate["git_sha"], args.config_path)
    manifest = build_candidate_handoff(
        source,
        args.output,
        config_snapshot=config,
        config_source={"git_sha": candidate["git_sha"], "path": args.config_path},
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
