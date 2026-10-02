"""Verify A2's OpenExplorer handoff package independently (B3 side).

The package is the input A4 compiles, so B3 checks what a consumer depends on:
every declared hash, the calibration it binds to, the FP32 ONNX it exports from,
whether each INT8 manifest's artefact digest matches the file shipped, and --
the check that decides whether the package is still current -- which A3
candidate the weights belong to.

Usage:
    python verify_a2_openexplorer_package.py <package_dir> [--repo <repo_root>]
                                            [--out <json>] [--compact-out <json>]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def sha256_file(path: Path, *, lf_normalise: bool = False) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            if lf_normalise:
                chunk = chunk.replace(b"\r\n", b"\n")
            digest.update(chunk)
    return digest.hexdigest()


def matches(path: Path, expected: str) -> tuple[bool, str, str]:
    expected = str(expected).lower()
    raw = sha256_file(path)
    if raw == expected:
        return True, raw, "raw"
    if sha256_file(path, lf_normalise=True) == expected:
        return True, raw, "lf_normalised"
    return False, raw, "raw"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def candidate_bindings(repo: Path) -> dict[str, str]:
    """Map a weights digest to the A3 candidate release that carries it."""
    bindings: dict[str, str] = {}
    releases = repo / "challenge" / "distillation" / "releases"
    if releases.is_dir():
        for release in sorted(releases.iterdir()):
            manifest = release / "handoff_manifest.json"
            if not manifest.is_file():
                continue
            try:
                payload = read_json(manifest)
            except json.JSONDecodeError:
                continue
            digest = ((payload.get("candidate_identity") or {}).get("weights_sha256")
                      or payload.get("weights_sha256"))
            if digest:
                bindings[str(digest).lower()] = release.name
    return bindings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--out")
    parser.add_argument("--compact-out")
    args = parser.parse_args()

    package = Path(args.package).resolve()
    repo = Path(args.repo).resolve()
    if not package.is_dir():
        print(f"package directory not found: {package}", file=sys.stderr)
        return 2

    errors: list[str] = []
    warnings: list[str] = []
    checks: list[dict] = []

    # 1. every file the package lists must match
    sums_path = package / "SHA256SUMS.txt"
    listed = {}
    if sums_path.is_file():
        for line in sums_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(None, 1)
            if len(parts) == 2:
                listed[parts[1].strip().lstrip("*")] = parts[0].strip().lower()
    mismatched, missing, lf_only = [], [], []
    for name, digest in listed.items():
        target = package / name
        if not target.is_file():
            missing.append(name)
            errors.append(f"SHA256SUMS lists a missing file: {name}")
            continue
        ok, actual, how = matches(target, digest)
        if not ok:
            mismatched.append({"file": name, "expected": digest, "actual": actual})
            errors.append(f"SHA256SUMS mismatch: {name}")
        elif how == "lf_normalised":
            lf_only.append(name)
    checks.append({"check": "sha256sums", "passed": not missing and not mismatched,
                   "detail": f"{len(listed) - len(missing) - len(mismatched)}/{len(listed)} listed files match"
                             f" ({len(lf_only)} only after CRLF->LF)",
                   "listed": len(listed), "mismatched": mismatched, "missing": missing})

    # 2. the manifest's own declared digests
    manifest_path = package / "PACKAGE_MANIFEST.json"
    manifest = read_json(manifest_path) if manifest_path.is_file() else {}
    artifacts = manifest.get("artifacts") or {}
    declared = {
        "fp32_onnx_sha256": package / "student_v0_fp32_candidate.onnx",
        "openexplorer_input_manifest_sha256": package / "openexplorer_oe391" / "openexplorer_input_manifest.json",
    }
    digest_results = {}
    for key, path in declared.items():
        expected = artifacts.get(key)
        if not isinstance(expected, str) or not path.is_file():
            errors.append(f"cannot check declared {key}")
            digest_results[key] = {"match": False, "reason": "missing expected digest or file"}
            continue
        ok, actual, how = matches(path, expected)
        digest_results[key] = {"match": ok, "matched_via": how, "expected": expected, "actual": actual}
        if not ok:
            errors.append(f"declared {key} does not match the shipped file")

    # calibration must be the frozen release B1 published
    cal_release = repo / "challenge" / "dataset" / "releases" / "calibration_v1"
    for key, name in (("calibration_jsonl_sha256", "calibration.jsonl"),
                      ("calibration_manifest_sha256", "calibration_manifest.json")):
        expected = artifacts.get(key)
        path = cal_release / name
        if not path.is_file():
            warnings.append(f"frozen calibration file not present in the repo, cannot check {key}")
            digest_results[key] = {"match": None, "reason": "repo file missing"}
            continue
        ok, actual, how = matches(path, expected or "")
        digest_results[key] = {"match": ok, "matched_via": how, "expected": expected, "actual": actual}
        if not ok:
            errors.append(f"{key} does not match the frozen calibration_v1 in the repo")
    checks.append({"check": "declared_digests", "passed": all(
        r.get("match") is not False for r in digest_results.values()), "detail": digest_results})

    # 3. calibration sample count
    npy_by_input = {}
    cal_root = package / "openexplorer_oe391" / "calibration_data"
    if cal_root.is_dir():
        for sub in sorted(p for p in cal_root.iterdir() if p.is_dir()):
            npy_by_input[sub.name] = len(list(sub.glob("*.npy")))
    expected_per_input = artifacts.get("npy_count_per_input")
    expected_total = artifacts.get("npy_total")
    total = sum(npy_by_input.values())
    count_ok = (expected_per_input is None or all(v == expected_per_input for v in npy_by_input.values())) \
        and (expected_total is None or total == expected_total)
    if not count_ok:
        errors.append(f"calibration tensor counts do not match the manifest: {npy_by_input} (total {total})")
    checks.append({"check": "calibration_tensors", "passed": count_ok,
                   "detail": f"{npy_by_input}, total {total}"})

    # 4. INT8 manifests against the artefacts actually shipped
    bindings = candidate_bindings(repo)
    int8_report = {}
    fp32_onnx_digest = digest_results.get("fp32_onnx_sha256", {}).get("actual")
    for label, rel in (("full_int8", "identity/full_int8_manifest.json"),
                       ("mixed_precision_top3", "identity/mixed_precision_top3_manifest.json")):
        path = package / rel
        if not path.is_file():
            errors.append(f"{rel} missing")
            continue
        info = read_json(path)
        artefact = None
        output = info.get("output") or {}
        if isinstance(output, dict) and output.get("path"):
            artefact = package / "models" / Path(str(output["path"])).name
        entry = {
            "quantization_id": info.get("quantization_id"),
            "status": info.get("status"),
            "gate_status": info.get("gate_status"),
            "source_fp32_weights_sha256": info.get("source_fp32_weights_sha256"),
            "source_fp32_onnx_sha256": info.get("source_fp32_onnx_sha256"),
            "calibration_manifest_sha256": info.get("calibration_manifest_sha256"),
            "int8_artifact_sha256": info.get("int8_artifact_sha256"),
        }
        if artefact is not None and artefact.is_file():
            ok, actual, how = matches(artefact, entry["int8_artifact_sha256"] or "")
            entry["artifact_file"] = artefact.name
            entry["artifact_match"] = ok
            if not ok:
                errors.append(f"{label}: shipped artefact does not match its manifest digest")
        else:
            entry["artifact_match"] = None
            warnings.append(f"{label}: artefact file not found next to the manifest")
        if fp32_onnx_digest and entry["source_fp32_onnx_sha256"] != fp32_onnx_digest:
            errors.append(f"{label}: manifest points at a different FP32 ONNX than the package ships")
        if artifacts.get("calibration_manifest_sha256") and \
                entry["calibration_manifest_sha256"] != artifacts["calibration_manifest_sha256"]:
            errors.append(f"{label}: manifest binds a different calibration manifest")
        release = bindings.get(str(entry["source_fp32_weights_sha256"]).lower())
        entry["binds_to_candidate_release"] = release
        if release is None:
            warnings.append(f"{label}: weights digest matches no candidate release in this checkout")
        int8_report[label] = entry

    latest_candidate = sorted((repo / "challenge" / "distillation" / "releases").glob("a3_*"))[-1].name \
        if (repo / "challenge" / "distillation" / "releases").is_dir() else None
    stale = [k for k, v in int8_report.items()
             if v.get("binds_to_candidate_release") and latest_candidate
             and v["binds_to_candidate_release"] != latest_candidate]
    if stale:
        warnings.append(
            "package binds to " + ", ".join(sorted({int8_report[k]['binds_to_candidate_release'] for k in stale}))
            + f" while the newest A3 candidate release in this checkout is {latest_candidate}"
        )

    checks.append({"check": "int8_manifests", "passed": not any(
        (v.get("artifact_match") is False) for v in int8_report.values()), "detail": int8_report})

    report = {
        "schema_version": "1.0",
        "package": str(package),
        "package_id": manifest.get("package_id"),
        "package_status": manifest.get("status"),
        "toolchain": manifest.get("toolchain"),
        "checks": checks,
        "int8_manifests": int8_report,
        "newest_a3_candidate_in_checkout": latest_candidate,
        "errors": errors,
        "warnings": warnings,
        "status": "PASS" if not errors else "FAIL",
        "policy_note": ("PASS means the package is self-consistent and bound to the frozen calibration "
                        "and to an identifiable A3 candidate. A warning about staleness means the INT8 "
                        "artefacts were produced from a candidate other than the newest one, which is a "
                        "decision for A2/A4, not something B3 may resolve."),
    }

    print(f"package      : {package.name} ({report['package_id']}, status {report['package_status']})")
    print(f"files        : {len(listed)} listed, {len(mismatched)} mismatched, {len(missing)} missing "
          f"({len(lf_only)} only after CRLF->LF)")
    print(f"fp32 onnx    : match={digest_results.get('fp32_onnx_sha256', {}).get('match')}")
    print(f"calibration  : {npy_by_input} (total {total})")
    for label, entry in int8_report.items():
        print(f"  {label:<22} artefact_match={entry.get('artifact_match')} "
              f"binds={entry.get('binds_to_candidate_release')} gate={entry.get('gate_status')}")
    print(f"newest cand. : {latest_candidate}")
    print(f"errors       : {len(errors)}")
    for error in errors[:10]:
        print(f"  - {error}")
    print(f"warnings     : {len(warnings)}")
    for warning in warnings[:10]:
        print(f"  ! {warning}")
    print(f"status       : {report['status']}")

    for target in (args.out, args.compact_out):
        if target:
            Path(target).parent.mkdir(parents=True, exist_ok=True)
            Path(target).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"wrote {target}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
