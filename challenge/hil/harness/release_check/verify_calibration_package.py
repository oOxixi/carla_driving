"""Verify B1's frozen calibration package independently (B3 side).

The frozen calibration is the input A2 must quantise with, so B3 checks the
things a consumer depends on: every declared hash, the declared sample counts,
and -- most importantly -- that no calibration sample also appears in a
validation split.  The last check is the one that decides whether a quantisation
result may be quoted at all.

Usage:
    python verify_calibration_package.py <calibration_dir> [--val <jsonl> ...]
                                          [--out <json>] [--compact-out <json>]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def verify_hashes(package: Path) -> tuple[list[dict], list[str]]:
    listing = package / "hashes.sha256"
    if not listing.is_file():
        return [], ["hashes.sha256 missing"]
    results, errors = [], []
    for line in listing.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            errors.append(f"unparsable hash line: {line!r}")
            continue
        expected, name = parts[0].lower(), parts[1].strip().lstrip("*")
        path = package / name
        if not path.is_file():
            errors.append(f"hashes.sha256 lists {name} but the file is missing")
            continue
        actual = sha256_file(path)
        if actual != expected:
            # Text files published from LF content differ on a Windows checkout (F12).
            normalised = sha256_file_text_lf(path)
            if normalised != expected:
                errors.append(f"hash mismatch for {name}")
                results.append({"file": name, "match": False, "expected": expected, "actual": actual})
                continue
            results.append({"file": name, "match": True, "matched_via": "lf_normalised"})
            continue
        results.append({"file": name, "match": True, "matched_via": "raw"})
    return results, errors


def sha256_file_text_lf(path: Path) -> str:
    raw = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(raw).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package")
    parser.add_argument("--val", action="append", default=[],
                        help="validation JSONL that the calibration must not overlap (repeatable)")
    parser.add_argument("--out")
    parser.add_argument("--compact-out")
    args = parser.parse_args()

    package = Path(args.package)
    if not package.is_dir():
        print(f"calibration package not found: {package}", file=sys.stderr)
        return 2

    errors: list[str] = []
    hash_results, hash_errors = verify_hashes(package)
    errors.extend(hash_errors)

    calibration_path = package / "calibration.jsonl"
    rows = read_jsonl(calibration_path) if calibration_path.is_file() else []
    if not rows:
        errors.append("calibration.jsonl missing or empty")

    manifest_path = package / "calibration_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else None
    if manifest is None:
        errors.append("calibration_manifest.json missing")

    declared = None
    if isinstance(manifest, dict):
        for key in ("samples", "sample_count", "count", "num_samples"):
            value = manifest.get(key)
            if isinstance(value, int):
                declared = value
                break
    count_ok = declared is None or declared == len(rows)
    if not count_ok:
        errors.append(f"calibration_manifest declares {declared} samples but calibration.jsonl has {len(rows)}")

    cal_ids = {str(r.get("sample_id")) for r in rows if r.get("sample_id")}
    overlaps: dict[str, dict] = {}
    for val_path in args.val:
        path = Path(val_path)
        if not path.is_file():
            errors.append(f"validation file not found: {val_path}")
            continue
        val_rows = read_jsonl(path)
        val_ids = {str(r.get("sample_id")) for r in val_rows if r.get("sample_id")}
        if not val_ids and isinstance(manifest, dict):
            # Tolerate other id fields rather than silently passing.
            errors.append(f"{path.name}: no sample_id field found, overlap not verifiable")
        shared = sorted(cal_ids & val_ids)
        label = f"{path.parent.name}/{path.name}"
        overlaps[label] = {"validation_samples": len(val_ids), "shared": len(shared),
                           "shared_sample_ids": shared[:10]}
        if shared:
            errors.append(f"calibration overlaps {label} on {len(shared)} sample(s)")

    report = {
        "schema_version": "1.0",
        "package": str(package),
        "calibration_samples": len(rows),
        "declared_samples": declared,
        "hashes": hash_results,
        "overlap_with_validation": overlaps,
        "errors": errors,
        "status": "PASS" if not errors else "FAIL",
    }

    print(f"package      : {package.name}")
    print(f"samples      : {len(rows)} (manifest declares {declared})")
    print(f"hashes       : {sum(1 for h in hash_results if h['match'])}/{len(hash_results)} match"
          f" ({sum(1 for h in hash_results if h.get('matched_via') == 'lf_normalised')} only after CRLF->LF)")
    for name, info in overlaps.items():
        print(f"overlap      : {name}: {info['shared']} shared of {info['validation_samples']} val samples")
    print(f"failures     : {len(errors)}")
    for error in errors[:10]:
        print(f"  - {error}")
    print(f"status       : {report['status']}")

    for target in (args.out, args.compact_out):
        if target:
            Path(target).parent.mkdir(parents=True, exist_ok=True)
            Path(target).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"wrote {target}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
