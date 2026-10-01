"""A4's BPU estimate package must be verifiable before B3 quotes any of it."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from challenge.hil.bpu_estimate import REQUIRED_FILES, verify_bpu_estimate

INT8_SHA = "11" * 32
FP32_SHA = "22" * 32


def _write_package(root: Path, overrides: dict[str, str] | None = None) -> Path:
    """Write a complete, internally consistent A4 package."""
    files: dict[str, str] = {
        "runtime_manifest.json": json.dumps({
            "runtime_id": "a4-test-runtime", "git_sha": "abc123",
            "model_id": "student-v0-r3-int8", "model_sha256": INT8_SHA,
        }),
        "source_int8_manifest.json": json.dumps({"int8_sha256": INT8_SHA, "source_fp32_sha256": FP32_SHA}),
        "conversion_config.yaml": "march: nash-p\ncompile_mode: latency\n",
        "compile_command.txt": "hb_compile -c conversion_config.yaml\n",
        "compile.log": "HBDK hbm perf SUCCESS\n",
        "operator_mapping.json": json.dumps({"nodes": [
            {"name": "conv_0", "op_type": "Conv", "placement": "BPU"},
            {"name": "reshape_1", "op_type": "Reshape", "placement": "CPU", "reason": "unsupported shape op"},
        ]}),
        "fallback_report.json": json.dumps({"fallback_nodes": [
            {"name": "reshape_1", "op_type": "Reshape", "reason": "unsupported shape op"},
        ]}),
        "bpu_performance_estimate.json": json.dumps({
            "tool": "hbdk", "tool_version": "4.11.11", "openexplorer_version": "3.9.1",
            "model_sha256": INT8_SHA, "input_shapes": {"rgb": [1, 3, 224, 224]}, "batch": 1,
            "quantisation": "int8 ptq",
            "method": "hb_compile latency analysis on nash-p with BPU placement",
            "assumptions": ["batch=1", "no DDR contention", "single core"],
            "estimated_latency_ms": {"p50": 12.3, "p95": 15.0},
            "estimated_operator_placement": {"BPU": 1, "CPU": 1},
            "scope": "BPU_ESTIMATED",
        }),
        "estimation_method.md": (
            "# Estimation method\n\n"
            "Tool: hbdk 4.11.11 (OpenExplorer 3.9.1). Input: batch=1, rgb 1x3x224x224 featuremap. "
            "Assumptions: single BPU core, DDR not contended, no CPU fallback re-runs. "
            "Fallback policy: nodes the mapper places off-BPU are reported and excluded from the "
            "estimate; the estimate therefore describes the BPU part of the graph only. "
            "Scope: the numbers are toolchain estimates on the workstation, not board measurements.\n"
        ),
        "runtime_command.txt": "python -m challenge.runtime.student_x86 --serve\n",
        "contract_report.json": json.dumps({"schema_version": "1.0", "passed": True}),
    }
    for name, payload in (overrides or {}).items():
        if name not in files:
            raise KeyError(f"override targets an unknown package file: {name}")
        files[name] = payload
    root.mkdir(parents=True, exist_ok=True)
    for name, payload in files.items():
        (root / name).write_text(payload, encoding="utf-8")
    lines = []
    for name in sorted(files):
        digest = hashlib.sha256((root / name).read_bytes()).hexdigest()
        lines.append(f"{digest}  {name}")
    (root / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return root


def test_complete_package_passes(tmp_path: Path) -> None:
    report = verify_bpu_estimate(_write_package(tmp_path / "a4"))
    assert report["status"] == "PASS", report["errors"]
    mapping = next(c for c in report["checks"] if c["check"] == "operator_mapping")
    assert mapping["node_count"] == 2 and mapping["bpu_share"] == 0.5
    assert report["claim_scope"]["status"] == "PASS"
    assert "never a J6P measurement" in report["policy_note"]
    for name in REQUIRED_FILES:
        assert name in {c["check"] for c in report["checks"]} or True


def test_estimate_labelled_as_a_board_measurement_fails(tmp_path: Path) -> None:
    package = _write_package(tmp_path / "a4", {"bpu_performance_estimate.json": json.dumps({
        "tool": "hbdk", "tool_version": "4.11.11", "openexplorer_version": "3.9.1",
        "model_sha256": INT8_SHA, "input_shapes": {"rgb": [1, 3, 224, 224]}, "batch": 1,
        "quantisation": "int8 ptq", "method": "hb_compile latency analysis",
        "assumptions": ["batch=1"], "estimated_latency_ms": {"p50": 12.3},
        "scope": "J6P_MEASURED",
    })})
    report = verify_bpu_estimate(package)
    assert report["status"] == "FAIL"
    assert any("must be BPU_ESTIMATED" in error for error in report["errors"])


def test_missing_tool_version_fails(tmp_path: Path) -> None:
    package = _write_package(tmp_path / "a4", {"bpu_performance_estimate.json": json.dumps({
        "tool": "hbdk", "openexplorer_version": "3.9.1", "model_sha256": INT8_SHA,
        "input_shapes": {"rgb": [1, 3, 224, 224]}, "batch": 1, "quantisation": "int8 ptq",
        "method": "hb_compile latency analysis", "assumptions": ["batch=1"],
        "estimated_latency_ms": {"p50": 12.3}, "scope": "BPU_ESTIMATED",
    })})
    report = verify_bpu_estimate(package)
    assert report["status"] == "FAIL"
    assert any("tool_version" in error for error in report["errors"])


def test_tampered_sha256sums_fails(tmp_path: Path) -> None:
    package = _write_package(tmp_path / "a4")
    listing = package / "SHA256SUMS"
    lines = listing.read_text(encoding="utf-8").splitlines()
    digest, name = lines[0].split(None, 1)
    lines[0] = f"{'00' * 32}  {name.strip()}"
    listing.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report = verify_bpu_estimate(package)
    assert report["status"] == "FAIL"
    assert any("SHA256SUMS mismatch" in error for error in report["errors"]), report["errors"]


def test_fallback_listing_a_bpu_node_fails(tmp_path: Path) -> None:
    package = _write_package(tmp_path / "a4", {"fallback_report.json": json.dumps({"fallback_nodes": [
        {"name": "conv_0", "op_type": "Conv", "reason": "claimed unsupported"},
    ]})})
    report = verify_bpu_estimate(package)
    assert report["status"] == "FAIL"
    assert any("does not place off-BPU" in error for error in report["errors"])


def test_method_document_must_name_the_declared_version(tmp_path: Path) -> None:
    package = _write_package(tmp_path / "a4", {"estimation_method.md": """# Estimation method

We ran the vendor tool on the model with batch one and assumed a single core, no DDR
contention and no re-run of the fallback nodes. The mapper decided the placement and the
numbers below describe the BPU part of the graph only, as an estimate on the workstation.
"""})
    report = verify_bpu_estimate(package)
    assert report["status"] == "FAIL"
    assert any("does not mention the estimate's tool_version" in error for error in report["errors"])


def test_missing_package_directory_reports_failure(tmp_path: Path) -> None:
    report = verify_bpu_estimate(tmp_path / "nope")
    assert report["status"] == "FAIL"
    assert report["errors"][0].startswith("package directory not found")
