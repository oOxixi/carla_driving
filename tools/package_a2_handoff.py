"""Build hash-locked A2 diagnostic handoff packages for A3, B2, and A4."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import Any


TOP3_NODES = (
    "/model/target_pointer_head/Gemm",
    "/model/behavior_head/Gemm",
    "/model/target_lane_head/Gemm",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def require_file(path: Path) -> Path:
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def copy_file(source: Path, destination: Path) -> None:
    require_file(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def copy_tree(source: Path, destination: Path) -> None:
    if not source.is_dir():
        raise FileNotFoundError(source)
    shutil.copytree(source, destination)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def git_value(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), *args], text=True, encoding="utf-8"
    ).strip()


def write_sums(package: Path) -> tuple[int, str]:
    entries = []
    for path in sorted(package.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.txt":
            entries.append(f"{sha256_file(path)}  {path.relative_to(package).as_posix()}")
    sums = package / "SHA256SUMS.txt"
    sums.write_text("\n".join(entries) + "\n", encoding="utf-8", newline="\n")
    return len(entries), sha256_file(sums)


def zip_package(package: Path, destination: Path) -> None:
    """Write a byte-reproducible archive for a fixed package directory."""

    with zipfile.ZipFile(
        destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True
    ) as archive:
        for path in sorted(package.rglob("*")):
            if path.is_file():
                relative = path.relative_to(package).as_posix()
                info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 3
                info.external_attr = (0o100644 & 0xFFFF) << 16
                with path.open("rb") as source, archive.open(
                    info, "w", force_zip64=True
                ) as target:
                    shutil.copyfileobj(source, target, length=1 << 20)


def package_manifest(
    *,
    package_id: str,
    recipient: str,
    purpose: str,
    branch: str,
    commit: str,
    artifacts: dict[str, Any],
    toolchain: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "package_id": package_id,
        "recipient": recipient,
        "purpose": purpose,
        "status": "PENDING_A3_FP32_GATE",
        "formal_release": False,
        "source_branch": branch,
        "source_commit": commit[:8],
        "workflow_git_sha": commit,
        "artifacts": artifacts,
        "limitations": [
            "DIAGNOSTIC_ONLY; not A3_FP32_GATE_PASSED or A2_INT8_GATE_PASSED.",
            "B2 must decide the exact FP32 and INT8 bytes on its frozen benchmark.",
            "OpenExplorer and J6P claims require A4/B3 evidence.",
        ],
    }
    if toolchain:
        payload["toolchain"] = toolchain
    return payload


def copy_identity(release: Path, destination: Path, quant_config: Path) -> None:
    copy_file(release / "handoff_manifest.json", destination / "handoff_manifest.json")
    copy_file(
        release / "student_v0_fp32_candidate.json",
        destination / "student_v0_fp32_candidate.json",
    )
    copy_file(quant_config, destination / quant_config.name)


def build_packages(
    repo: Path,
    source: Path,
    release: Path,
    output: Path,
    workflow_git_sha: str,
    source_branch: str,
) -> dict[str, Any]:
    upstream = read_json(require_file(source / "upstream_audit.json"))
    consistency = read_json(require_file(source / "export_consistency.json"))
    full = read_json(require_file(source / "ptq_int8" / "int8_manifest.json"))
    mixed = read_json(require_file(source / "mixed_precision_top3" / "int8_manifest.json"))
    sensitivity = read_json(
        require_file(source / "sensitivity_full" / "sensitive_layer_report.json")
    )
    openexplorer = read_json(
        require_file(source / "openexplorer_oe391" / "openexplorer_input_manifest.json")
    )
    handoff = read_json(require_file(release / "handoff_manifest.json"))
    candidate = handoff.get("candidate_identity") or {}

    expected_weight_sha = str(candidate.get("weights_sha256") or "")
    weights = require_file(release / "student_v0_fp32_candidate.pt")
    if sha256_file(weights) != expected_weight_sha:
        raise ValueError("candidate weights do not match the A3 handoff")
    if upstream.get("blockers") != ["A3_FP32_GATE_NOT_PASSED:PENDING_A3_FP32_GATE"]:
        raise ValueError(f"unexpected upstream blockers: {upstream.get('blockers')}")
    consistency_samples = consistency.get("dataset", {}).get("request_count")
    if consistency.get("status") != "PASS" or consistency_samples != 300:
        raise ValueError("FP32 export consistency is not a 300-sample PASS")
    for label, manifest in (("full", full), ("mixed", mixed)):
        status = manifest.get("status")
        gate_status = manifest.get("gate_status")
        if status != "A3_CANDIDATE_PRE_PTQ" or gate_status != "NOT_FORMAL":
            raise ValueError(f"{label} candidate status is not diagnostic")
        if manifest.get("source_fp32_weights_sha256") != expected_weight_sha:
            raise ValueError(f"{label} candidate binds the wrong FP32 weights")
    ranking = sensitivity.get("ranking") or []
    selected = tuple(item.get("node", {}).get("name") for item in ranking[:3])
    if selected != TOP3_NODES:
        raise ValueError(f"unexpected Top-3 sensitivity ranking: {selected}")
    if openexplorer.get("status") != "A3_CANDIDATE_OPENEXPLORER_INPUT_READY":
        raise ValueError("OpenExplorer package is not a diagnostic-ready candidate")

    fp32 = require_file(source / "student_v0_fp32_candidate.onnx")
    full_model = require_file(source / "ptq_int8" / "student_int8.onnx")
    mixed_model = require_file(
        source / "mixed_precision_top3" / "student_int8_mixed_top3.onnx"
    )
    oe_manifest = source / "openexplorer_oe391" / "openexplorer_input_manifest.json"
    calibration = openexplorer.get("calibration") or {}
    common_artifacts = {
        "source_weights_sha256": expected_weight_sha,
        "fp32_onnx_sha256": sha256_file(fp32),
        "full_int8_sha256": sha256_file(full_model),
        "mixed_precision_top3_sha256": sha256_file(mixed_model),
        "openexplorer_input_manifest_sha256": sha256_file(oe_manifest),
        "calibration_jsonl_sha256": calibration.get("jsonl_sha256"),
        "calibration_manifest_sha256": calibration.get("manifest_sha256"),
        "npy_count_per_input": 300,
        "npy_total": 1200,
    }
    commit = git_value(repo, "rev-parse", f"{workflow_git_sha}^{{commit}}")
    quant_config = repo / "challenge" / "quantization" / "config" / "ptq_int8_v1.yaml"
    package_specs = {
        "A3_gate_feedback": (
            "A3",
            "candidate_identity_and_gate_feedback",
            "A2_to_A3_gate_feedback",
        ),
        "B2_evaluation": (
            "B2",
            "independent_fp32_and_int8_gate_evaluation",
            "A2_to_B2_evaluation",
        ),
        "A4_openexplorer": (
            "A4",
            "openexplorer_3_9_1_compile_and_deployment_handoff",
            "A2_to_A4_openexplorer",
        ),
    }
    output.mkdir(parents=True, exist_ok=False)

    built: dict[str, Any] = {}
    for directory, (recipient, purpose, zip_stem) in package_specs.items():
        package = output / directory
        package.mkdir()
        manifest = package_manifest(
            package_id=f"a2-to-{recipient.lower()}-closeout-v2-{commit[:8]}",
            recipient=recipient,
            purpose=purpose,
            branch=source_branch,
            commit=commit,
            artifacts=common_artifacts,
            toolchain={
                "version": "3.9.1",
                "container": "openexplorer/ai_toolchain_ubuntu_22_j6_cpu:v3.9.1",
                "march": "nash-p",
            }
            if recipient == "A4"
            else None,
        )
        write_json(package / "PACKAGE_MANIFEST.json", manifest)
        package.joinpath("README.md").write_text(
            "\n".join(
                (
                    f"# A2 → {recipient} B1 closeout candidate v2 交接包",
                    "",
                    f"用途：`{purpose}`。",
                    "",
                    "本包严格保持 `PENDING_A3_FP32_GATE` / `DIAGNOSTIC_ONLY`。",
                    "接收方须先核验 `SHA256SUMS.txt`，不得将候选结果表述为正式 Gate 或板端结论。",
                    "",
                )
            ),
            encoding="utf-8",
            newline="\n",
        )

        if recipient == "A3":
            copy_identity(release, package / "identity", quant_config)
            for source_file, name in (
                (source / "upstream_audit.json", "upstream_audit.json"),
                (source / "export_consistency.json", "export_consistency.json"),
                (source / "ptq_int8" / "int8_manifest.json", "full_int8_manifest.json"),
                (
                    source / "mixed_precision_top3" / "int8_manifest.json",
                    "mixed_precision_top3_manifest.json",
                ),
                (
                    source / "sensitivity_full" / "sensitive_layer_report.json",
                    "sensitive_layer_report.json",
                ),
            ):
                copy_file(source_file, package / "reports" / name)
        elif recipient == "B2":
            copy_identity(release, package / "identity", quant_config)
            copy_file(fp32, package / "models" / fp32.name)
            copy_file(weights, package / "models" / weights.name)
            copy_tree(source / "ptq_int8", package / "models" / "full_int8")
            copy_tree(source / "mixed_precision_top3", package / "models" / "mixed_precision_top3")
            for source_file in (
                source / "upstream_audit.json",
                source / "export_consistency.json",
                source / "flops_report.json",
                source / "model_structure.json",
                source / "sensitivity_full" / "sensitive_layer_report.json",
                source / "sensitivity_full" / "sensitive_layers.md",
            ):
                copy_file(source_file, package / "reports" / source_file.name)
        else:
            copy_file(fp32, package / fp32.name)
            for source_file in (
                source / "upstream_audit.json",
                source / "flops_report.json",
                source / "model_structure.json",
                source / "sensitivity_full" / "sensitive_layer_report.json",
                source / "sensitivity_full" / "sensitive_layers.md",
            ):
                copy_file(source_file, package / "analysis" / source_file.name)
            copy_identity(release, package / "identity", quant_config)
            copy_file(
                source / "ptq_int8" / "int8_manifest.json",
                package / "identity" / "full_int8_manifest.json",
            )
            copy_file(
                source / "mixed_precision_top3" / "int8_manifest.json",
                package / "identity" / "mixed_precision_top3_manifest.json",
            )
            copy_file(full_model, package / "models" / full_model.name)
            copy_file(mixed_model, package / "models" / mixed_model.name)
            copy_tree(source / "openexplorer_oe391", package / "openexplorer_oe391")

        file_count, sums_sha = write_sums(package)
        zip_path = output / f"{zip_stem}_{commit[:8]}.zip"
        zip_package(package, zip_path)
        built[recipient] = {
            "directory": str(package.relative_to(repo)),
            "file_count": file_count,
            "sha256sums_sha256": sums_sha,
            "zip": str(zip_path.relative_to(repo)),
            "zip_sha256": sha256_file(zip_path),
            "zip_bytes": zip_path.stat().st_size,
        }

    delivery = output / "DELIVERY_SHA256SUMS.txt"
    delivery.write_text(
        "\n".join(
            f"{item['zip_sha256']}  {Path(item['zip']).name}" for item in built.values()
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    summary = {
        "schema_version": "1.0",
        "status": "DIAGNOSTIC_ONLY",
        "source_commit": commit,
        "candidate_weights_sha256": expected_weight_sha,
        "packages": built,
        "delivery_sha256sums": str(delivery.relative_to(repo)),
    }
    write_json(output / "DELIVERY_MANIFEST.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument(
        "--source", default="artifacts/a2/a3_final_fp32_candidate_v2_20c80d7c"
    )
    parser.add_argument(
        "--candidate-release",
        default="challenge/distillation/releases/a3_final_fp32_candidate_v2",
    )
    parser.add_argument(
        "--output", default="artifacts/a2/handoff_20261003_20c80d7c"
    )
    parser.add_argument(
        "--workflow-git-sha",
        default="20c80d7cde2ca8ca651f383ca06b8bc06e0acaa3",
        help="Commit whose A3/B1 inputs were executed; embedded into every package.",
    )
    parser.add_argument(
        "--source-branch",
        default="challenge",
        help="Shared integration branch from which workflow-git-sha was resolved.",
    )
    args = parser.parse_args()
    repo = Path(args.repo).resolve()
    result = build_packages(
        repo,
        (repo / args.source).resolve(),
        (repo / args.candidate_release).resolve(),
        (repo / args.output).resolve(),
        args.workflow_git_sha,
        args.source_branch,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
