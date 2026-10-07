"""Assemble an isolated, verifiable A1 handoff without modifying other worktrees."""
from __future__ import annotations
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from challenge.export.compute_flops import analyze_model, source_revision


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_manifest(destination: Path, source_base: str) -> dict:
    manifest = {"schema_version": "1.0", "analysis_base_git_sha": source_base,
                "weight_status": "A1 random smoke only; trained A3 weights NOT included",
                "files": [{"path": p.relative_to(destination).as_posix(), "size_bytes": p.stat().st_size,
                           "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                          for p in sorted(destination.rglob("*")) if p.is_file()
                          and p != destination/"manifest.json"
                          and "__pycache__" not in p.parts and ".pytest_cache" not in p.parts]}
    write_json(destination/"manifest.json", manifest)
    return manifest


def build(destination: Path, teacher_dir: Path, *, resume: bool = False, teacher_image: str | None = None) -> None:
    root = Path(__file__).resolve().parents[2]
    destination = destination.resolve()
    if destination.exists():
        if not resume or (destination/"README.md").read_bytes() != (root/"challenge/export/A1_HANDOFF_README.md").read_bytes():
            raise FileExistsError(f"Refusing to overwrite an existing handoff: {destination}")
    destination.mkdir(parents=True, exist_ok=True)
    # Source-only dependency closure; no datasets, secrets, deployment weights
    # or unrelated scenario recordings are copied.
    folders = ["challenge/student", "challenge/planner", "challenge/export",
               "challenge/quantization", "qwen_service", "runtime", "integration",
               "car_control_A", "car_control_B", "car_control_C", "car_control_D", "config"]
    files = set()
    for folder in folders:
        files.update(p for p in (root/folder).rglob("*.py") if "tests" not in p.parts)
    files.update([root/"compat.py", root/"challenge/__init__.py", root/"challenge/hil/__init__.py",
                  root/"challenge/hil/identity.py", root/"challenge/hil/stages.py", root/"challenge/hil/columns.py"])
    files.update([root/"config/strategy_config.yaml", root/"config/driving_policy.json"])
    baseline = root/"baselines/initial_prepared_package"
    files.update(p for p in baseline.rglob("*") if p.is_file())
    files.update(p for p in (root/"interfaces").rglob("*") if p.is_file() and p.suffix in {".json", ".py"})
    for name in ["A1_MODEL_INTERFACE.md", "student_config.json", "model_structure.json",
                 "student_v0_fp32.onnx", "teacher_flops_report.json", "a1_interface_verified.json",
                 "teacher_baseline_manifest.json", "teacher_pinned_manifest.json", "requirements.txt",
                 "tests/test_a1_student.py", "tests/test_flops_denominator.py",
                 "export/teacher_config_pinned.json", "export/A1_HANDOFF_README.md",
                 "flops_options.json", "tests/test_flops_options.py"]:
        files.add(root/"challenge"/name)
    for src in sorted(files):
        target = destination/src.relative_to(root)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
    shutil.copy2(root/"challenge/export/A1_HANDOFF_README.md", destination/"README.md")
    # Processor/tokenizer and config only. No real weight execution is claimed.
    metadata = destination/"teacher_metadata"
    metadata.mkdir(exist_ok=True)
    for name in ["config.json", "chat_template.jinja", "tokenizer.json", "tokenizer_config.json",
                 "preprocessor_config.json", "video_preprocessor_config.json", "vocab.json", "merges.txt", "LICENSE"]:
        shutil.copy2(teacher_dir/name, metadata/name)
    original = json.loads((root/"challenge/model_structure.json").read_text(encoding="utf-8"))
    report = analyze_model()
    report["analysis_source_git_sha"] = source_revision()
    report["source_git_sha"] = original["source_git_sha"]
    report["source_identity_note"] = "Original ONNX provenance retained; revised analysis source hashes are in manifest.json"
    write_json(destination/"challenge/flops_report.json", report)
    environment = {"python": platform.python_version(), "platform": platform.platform(),
                   "student_packages": {k: importlib.metadata.version(k) for k in
                                        ["torch", "numpy", "Pillow", "onnx", "onnxruntime", "pytest"]},
                   "teacher_analysis": json.loads((root/"challenge/teacher_flops_report.json").read_text(encoding="utf-8"))["runtime"]}
    write_json(destination/"environment.json", environment)
    verifier = root/"challenge/export/verify_a1_manifest.py"
    shutil.copy2(verifier, destination/"verify_manifest.py")
    logs = destination/"logs"
    logs.mkdir(exist_ok=True)
    commands = [
        ("interface.txt", [sys.executable, "-m", "challenge.export.verify_a1"]),
        ("regression.txt", [sys.executable, "-m", "pytest", "-q", "challenge/tests/test_a1_student.py", "challenge/tests/test_flops_denominator.py", "--disable-warnings", "--maxfail=1"]),
        ("artifact_validation.txt", [sys.executable, "-m", "challenge.export.validate_artifacts", "--root", "."]),
        ("flops_options_validation.txt", [sys.executable, "-m", "pytest", "-q", "challenge/tests/test_flops_options.py", "--disable-warnings"]),
    ]
    if teacher_image:
        commands.append(("teacher_analysis.txt", ["docker", "run", "--rm", "--entrypoint", "python3",
                         "-e", "PYTHONPATH=/work:/tmp/qwen-site:/opt/controller-site",
                         "-e", "A1_SOURCE_GIT_SHA="+source_revision(),
                         "-v", destination.as_posix()+":/work", "-w", "/work", teacher_image,
                         "-m", "challenge.export.teacher_flops", "--model-dir", "teacher_metadata",
                         "--output", "logs/reproduced_teacher_flops.json"]))
    for name, command in commands:
        result = subprocess.run(command, cwd=destination, text=True, encoding="utf-8", errors="replace",
                                env={**os.environ, "PYTHONUTF8": "1"}, capture_output=True)
        (logs/name).write_text("COMMAND: "+" ".join(command)+"\nEXIT: "+str(result.returncode)+"\n"+result.stdout+result.stderr, encoding="utf-8")
        if result.returncode:
            raise RuntimeError(f"Handoff self-check failed; see {logs/name}")
    manifest = write_manifest(destination, source_revision())
    print(json.dumps({"status": "PASS", "directory": str(destination), "manifest_files": len(manifest["files"])}, ensure_ascii=False))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--teacher-dir", type=Path, required=True)
    p.add_argument("--resume", action="store_true", help="Resume only an identical generated README/directory")
    p.add_argument("--teacher-image", help="Optional existing Python 3.12 image for offline meta self-check")
    a = p.parse_args()
    build(a.output_dir, a.teacher_dir, resume=a.resume, teacher_image=a.teacher_image)
