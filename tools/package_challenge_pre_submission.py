#!/usr/bin/env python3
"""Build the hash-locked challenge-track pre-submission evidence package."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

PACKAGE_FILES = (
    # Latest freeze and collection documents.
    "submission/challenge/README.md",
    "submission/challenge/RC_V3_FREEZE_20261008.json",
    "submission/challenge/V3_INDEPENDENT_DIAGNOSTIC_20261008.md",
    "submission/challenge/V3_FIELD_SEMANTIC_NORMALIZATION_20261008.md",
    "submission/challenge/V3_1_ADAPTER_INT8_POSTHOC_20261008.md",
    "submission/challenge/PRE_SUBMISSION_LEDGER_20261008.md",
    "submission/challenge/SUBMISSION_COLLECTION_CHECKLIST_20261008.md",
    # A1 formal structure/FLOPs handoff, excluding its random-init smoke ONNX
    # and duplicated source tree.
    "A1_正式模型与FLOPs交接_20261008/README.md",
    "A1_正式模型与FLOPs交接_20261008/manifest.json",
    "A1_正式模型与FLOPs交接_20261008/environment.json",
    "A1_正式模型与FLOPs交接_20261008/challenge/a1_interface_verified.json",
    "A1_正式模型与FLOPs交接_20261008/challenge/model_structure.json",
    "A1_正式模型与FLOPs交接_20261008/challenge/flops_report.json",
    "A1_正式模型与FLOPs交接_20261008/challenge/flops_options.json",
    "A1_正式模型与FLOPs交接_20261008/challenge/teacher_flops_report.json",
    "A1_正式模型与FLOPs交接_20261008/challenge/teacher_baseline_manifest.json",
    "A1_正式模型与FLOPs交接_20261008/challenge/teacher_pinned_manifest.json",
    "A1_正式模型与FLOPs交接_20261008/logs/artifact_validation.txt",
    "A1_正式模型与FLOPs交接_20261008/logs/interface.txt",
    "A1_正式模型与FLOPs交接_20261008/logs/regression.txt",
    "A1_正式模型与FLOPs交接_20261008/logs/reproduced_teacher_flops.json",
    "A1_正式模型与FLOPs交接_20261008/logs/teacher_analysis.txt",
    # B1 governance identities. The labelled cases.jsonl is intentionally not
    # copied into the team-facing evidence package.
    "challenge/dataset/governance/b1_closeout_v1/B1_CLOSEOUT_REPORT.json",
    "challenge/dataset/governance/b1_closeout_v1/B1_HANDOFF.md",
    "challenge/dataset/governance/b1_closeout_v1/SHA256SUMS",
    "challenge/dataset/governance/b1_closeout_v1/calibration_identity.json",
    "challenge/dataset/governance/b1_closeout_v1/governed_release_manifest.json",
    "challenge/dataset/governance/b1_closeout_v1/leakage_audit.json",
    "challenge/dataset/governance/b1_closeout_v1/teacher_provenance_registry.json",
    "challenge/dataset/governance/b1_closeout_v1/independent_validation_v1/README.md",
    "challenge/dataset/governance/b1_closeout_v1/independent_validation_v1/dataset_identity.json",
    "challenge/dataset/governance/b1_closeout_v1/independent_validation_v1/case_set_digest.json",
    "challenge/dataset/governance/b1_closeout_v1/independent_validation_v1/source_release_binding.json",
    "challenge/dataset/attestations/b1_legacy_template_identity_recovery_v1/recovery_attestation.json",
    "challenge/dataset/attestations/b1_legacy_template_identity_recovery_v1/provenance_manifest.json",
    # A3 candidate metadata, excluding the 92 MB .pt and labelled training rows.
    "challenge/distillation/releases/a3_b1_closeout_robust_fp32_candidate_v3/README.md",
    "challenge/distillation/releases/a3_b1_closeout_robust_fp32_candidate_v3/handoff_manifest.json",
    "challenge/distillation/releases/a3_b1_closeout_robust_fp32_candidate_v3/student_v0_fp32_candidate.json",
    "challenge/distillation/releases/a3_b1_closeout_robust_fp32_candidate_v3/dataset_preflight.json",
    "challenge/distillation/releases/a3_b1_closeout_robust_fp32_candidate_v3/training_config.yaml",
    "challenge/distillation/releases/a3_b1_closeout_robust_fp32_candidate_v3/training_report.md",
    "challenge/distillation/releases/a3_b1_closeout_robust_fp32_candidate_v3/training_summary.json",
    "challenge/distillation/releases/a3_b1_closeout_robust_fp32_candidate_v3/hard_cases/summary.json",
    # A2 reports and manifests, excluding large ONNX/NPY payloads.
    "challenge/quantization/A2_ROBUST_CANDIDATE_V3_RESULT_20261007.md",
    "artifacts/a2/a3_robust_fp32_candidate_v3_11823750/upstream_audit.json",
    "artifacts/a2/a3_robust_fp32_candidate_v3_11823750/export_consistency.json",
    "artifacts/a2/a3_robust_fp32_candidate_v3_11823750/model_structure.json",
    "artifacts/a2/a3_robust_fp32_candidate_v3_11823750/flops_report.json",
    "artifacts/a2/a3_robust_fp32_candidate_v3_11823750/ptq_int8/int8_manifest.json",
    "artifacts/a2/a3_robust_fp32_candidate_v3_11823750/ptq_int8/quant_error_report.json",
    "artifacts/a2/a3_robust_fp32_candidate_v3_11823750/ptq_int8/raw_output_drift.json",
    "artifacts/a2/a3_robust_fp32_candidate_v3_11823750/mixed_precision_top3/int8_manifest.json",
    "artifacts/a2/a3_robust_fp32_candidate_v3_11823750/mixed_precision_top3/quant_error_report.json",
    "artifacts/a2/a3_robust_fp32_candidate_v3_11823750/mixed_precision_top3/raw_output_drift.json",
    "artifacts/a2/a3_robust_fp32_candidate_v3_11823750/sensitivity_full/sensitive_layer_report.json",
    "artifacts/a2/a3_robust_fp32_candidate_v3_11823750/sensitivity_full/sensitive_layers.md",
    "artifacts/a2/a3_robust_fp32_candidate_v3_11823750/openexplorer_oe391/openexplorer_input_manifest.json",
    "artifacts/a2/a3_robust_fp32_candidate_v3_11823750/openexplorer_oe391/student_j6p_oe391.yaml",
    # B4 release rules.
    "docs/architecture/modules/B4_REPRODUCTION_RELEASE_AND_SUBMISSION.md",
)

PACKAGE_TREES = (
    "challenge/hil/evidence/deployment_estimate_and_decay_20261008",
    "challenge/hil/evidence/carla_student_loop_20261007",
    "challenge/hil/evidence/a3_v3_simulation_20261007",
    "challenge/hil/evidence/teacher_local_bringup_20261008",
    "artifacts/b2_role_exception_v3_20261008_final",
    "artifacts/b2_role_exception_v3_20261008_semantic_normalized",
    "artifacts/b2_role_exception_v3_1_adapter_20261008_final",
    "artifacts/b2_role_exception_v3_1_full_int8_20261008_final",
    "artifacts/b2_role_exception_v3_1_mixed_int8_20261008_final",
)

EXTERNAL_ARTIFACTS = (
    {
        "owner": "A2",
        "recipient": "A3",
        "path": "artifacts/a2/handoff_20261008_v31_a2354507/A2_to_A3_gate_feedback_a2354507.zip",
        "claim_scope": "DIAGNOSTIC_ONLY",
    },
    {
        "owner": "A2",
        "recipient": "B2",
        "path": "artifacts/a2/handoff_20261008_v31_a2354507/A2_to_B2_evaluation_a2354507.zip",
        "claim_scope": "DIAGNOSTIC_ONLY",
    },
    {
        "owner": "A2",
        "recipient": "A4",
        "path": "artifacts/a2/handoff_20261008_v31_a2354507/PRE_GATE_ONLY_A2_to_A4_openexplorer_a2354507.zip",
        "claim_scope": "PRE_GATE_ONLY",
    },
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def copy_file(repo: Path, package: Path, relative: str) -> dict[str, Any]:
    source = repo / relative
    if not source.is_file():
        raise FileNotFoundError(source)
    destination = package / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return {
        "path": relative,
        "size_bytes": destination.stat().st_size,
        "sha256": sha256_file(destination),
    }


def canonical_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def git_value(repo: Path, *arguments: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), *arguments],
        text=True,
        encoding="utf-8",
    ).strip()


def deterministic_zip(source: Path, destination: Path) -> None:
    with zipfile.ZipFile(
        destination,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=6,
        allowZip64=True,
    ) as archive:
        for path in sorted(item for item in source.rglob("*") if item.is_file()):
            relative = path.relative_to(source).as_posix()
            info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = (0o100644 & 0xFFFF) << 16
            with path.open("rb") as input_stream, archive.open(
                info, "w", force_zip64=True
            ) as output_stream:
                shutil.copyfileobj(input_stream, output_stream, length=1024 * 1024)


def verify_zip(package: Path, archive_path: Path) -> dict[str, Any]:
    expected = {
        path.relative_to(package).as_posix(): sha256_file(path)
        for path in package.rglob("*")
        if path.is_file()
    }
    with zipfile.ZipFile(archive_path) as archive:
        bad = archive.testzip()
        if bad is not None:
            raise RuntimeError(f"ZIP CRC failure: {bad}")
        actual_names = set(archive.namelist())
        if actual_names != set(expected):
            raise RuntimeError("ZIP file list does not match package directory")
        for name, expected_sha in expected.items():
            actual_sha = hashlib.sha256(archive.read(name)).hexdigest()
            if actual_sha != expected_sha:
                raise RuntimeError(f"ZIP member SHA256 mismatch: {name}")
    return {"files": len(expected), "crc": "PASS", "sha256": "PASS"}


def zip_crc(path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(path) as archive:
        bad = archive.testzip()
        if bad is not None:
            raise RuntimeError(f"external ZIP CRC failure: {path}: {bad}")
        return {"zip_members": len(archive.infolist()), "zip_crc": "PASS"}


def build(repo: Path, output_root: Path) -> dict[str, Any]:
    package_id = "challenge_rc_v3_1_adapter_evidence_20261008"
    package = output_root / package_id
    archive_path = output_root / "CHALLENGE_RC_V3_1_ADAPTER_EVIDENCE_20261008.zip"
    archive_sha_path = archive_path.with_suffix(archive_path.suffix + ".sha256")
    if package.exists() or archive_path.exists() or archive_sha_path.exists():
        raise FileExistsError("pre-submission package output already exists")

    staging = output_root / (package_id + ".tmp")
    if staging.exists():
        raise FileExistsError(staging)
    staging.mkdir(parents=True)

    try:
        copied: list[dict[str, Any]] = []
        for relative in PACKAGE_FILES:
            copied.append(copy_file(repo, staging, relative))
        for relative_tree in PACKAGE_TREES:
            tree = repo / relative_tree
            if not tree.is_dir():
                raise FileNotFoundError(tree)
            for source in sorted(item for item in tree.rglob("*") if item.is_file()):
                relative = source.relative_to(repo).as_posix()
                copied.append(copy_file(repo, staging, relative))

        externals: list[dict[str, Any]] = []
        for entry in EXTERNAL_ARTIFACTS:
            path = repo / str(entry["path"])
            if not path.is_file():
                raise FileNotFoundError(path)
            externals.append(
                {
                    **entry,
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                    **zip_crc(path),
                    "included_in_this_zip": False,
                }
            )

        manifest = {
            "schema_version": "1.0",
            "package_id": package_id,
            "status": "FROZEN_CANDIDATE_BLOCKED_NOT_FINAL",
            "formal_release": False,
            "source_git_sha": git_value(repo, "rev-parse", "HEAD"),
            "source_branch": git_value(repo, "branch", "--show-current"),
            "candidate": {
                "weights_sha256": "7f379c78c170228713e3d91b8e2eabd04172010ae0ed0b8cf71afe291fe6e805",
                "fp32_onnx_sha256": "681a5d4bf16ba61741ef0e559649c43c041de649eef3e8e6f0b6285beaab4286",
                "adapter_contract_id": "student-plan-adapter-v3.1-semantic-contract",
                "preferred_int8_sha256": "9a08a03c42a9ea59ead664d168254cd3685d73d176d5ab53507bd4a4467132d3",
                "selection_status": "V3_FROZEN_AS_SOLE_RELEASE_CANDIDATE",
                "original_v3_threshold_projection": "FAIL",
                "adapter_v3_1_post_hoc_projection": "PASS_NOT_FORMAL_GATE",
            },
            "included_files": sorted(copied, key=lambda item: str(item["path"])),
            "external_large_artifacts": externals,
            "excluded_by_design": [
                "Independent Validation labelled cases.jsonl",
                "A1 random-initialized smoke ONNX",
                "A3 .pt weights and A2 ONNX/NPY payloads already present in external A2 ZIPs",
                "unavailable .bc/.hbm, J6P measurements, Docker archive, report PDF, and demo video",
            ],
            "limitations": [
                "This is a pre-submission evidence package, not FINAL_SUBMISSION.",
                "The original V3 projection failed; Adapter V3.1 passes only a post-hoc replay on the already exposed benchmark.",
                "Neither the V3.1 FP32 nor INT8 projection is an independent formal Gate decision.",
                "The original strict, null/CURRENT normalization, and implemented V3.1 results are all retained for audit.",
                "BPU estimates are not J6P measurements.",
            ],
        }
        canonical_json(staging / "PACKAGE_MANIFEST.json", manifest)
        readme = """# Challenge-track RC V3 freeze evidence package

This archive freezes all currently available small reports, manifests, and raw
role-exception diagnostic predictions across A1-A4 and B1-B4. It is not a Final
submission. Adapter V3.1 and both INT8 candidates pass the old 240-case replay,
but that replay is post-hoc because the benchmark was already exposed. It does
not overwrite the original FAIL result or complete the formal Gate chain.

Start with `submission/challenge/PRE_SUBMISSION_LEDGER_20261008.md` and
`submission/challenge/RC_V3_FREEZE_20261008.json`. Large A2 model/NPY payloads
are listed by path, size, and SHA256 in `PACKAGE_MANIFEST.json` and remain in
their recipient-specific ZIPs.
"""
        (staging / "README.md").write_text(readme, encoding="utf-8", newline="\n")
        checksum_paths = sorted(
            path for path in staging.rglob("*") if path.is_file() and path.name != "SHA256SUMS"
        )
        checksum_lines = [
            f"{sha256_file(path)}  {path.relative_to(staging).as_posix()}"
            for path in checksum_paths
        ]
        (staging / "SHA256SUMS").write_text(
            "\n".join(checksum_lines) + "\n", encoding="utf-8", newline="\n"
        )
        staging.replace(package)
        deterministic_zip(package, archive_path)
        verification = verify_zip(package, archive_path)
        archive_sha = sha256_file(archive_path)
        archive_sha_path.write_text(
            f"{archive_sha}  {archive_path.name}\n", encoding="ascii", newline="\n"
        )
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        if package.exists():
            shutil.rmtree(package, ignore_errors=True)
        archive_path.unlink(missing_ok=True)
        archive_sha_path.unlink(missing_ok=True)
        raise

    return {
        "package": str(package),
        "archive": str(archive_path),
        "archive_size_bytes": archive_path.stat().st_size,
        "archive_sha256": archive_sha,
        "verification": verification,
        "external_large_artifacts": externals,
    }


def main() -> int:
    argument_parser = argparse.ArgumentParser(description=__doc__)
    argument_parser.add_argument("--repo", default=str(REPOSITORY_ROOT))
    argument_parser.add_argument("--output", default="artifacts/submission")
    arguments = argument_parser.parse_args()
    repo = Path(arguments.repo).resolve()
    output = Path(arguments.output)
    if not output.is_absolute():
        output = (repo / output).resolve()
    try:
        result = build(repo, output)
    except (FileExistsError, FileNotFoundError, OSError, RuntimeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
