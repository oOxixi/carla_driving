"""Independent verification of an A3 FP32 candidate handoff package (B3 side).

B3 never promotes a candidate on the strength of its own manifest. This checks
the package the way a consumer must: every listed file hash and size, the
weights digest against the declared identity, and the gate/package status, so a
fail-closed gate can be told apart from a broken package.

Usage:
    python verify_a3_handoff.py <package_dir> [--out <json>] [--compact-out <json>]
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


def digest_matches(path: Path, expected: str) -> tuple[bool, str, str]:
    """Return (match, actual, how); retry after CRLF->LF for text files."""
    raw = sha256_file(path)
    if raw == expected:
        return True, raw, "raw"
    normalised = sha256_file(path, lf_normalise=True)
    if normalised == expected:
        return True, raw, "lf_normalised"
    return False, raw, "raw"


def lf_normalised_size(path: Path) -> int:
    """Byte count after collapsing CRLF to LF (finding F12).

    A manifest published from LF content declares LF sizes; a Windows checkout
    with core.autocrlf rewrites every newline and adds one byte per line, so the
    recorded size can only be compared after the same normalisation that the
    digest already uses.
    """
    raw = path.read_bytes()
    return len(raw) - raw.count(b"\r\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package")
    parser.add_argument("--out")
    parser.add_argument("--compact-out")
    args = parser.parse_args()

    package = Path(args.package).resolve()
    manifest_path = package / "handoff_manifest.json"
    if not manifest_path.is_file():
        print(f"no handoff_manifest.json under {package}", file=sys.stderr)
        return 2
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    identity = manifest.get("candidate_identity") or {}
    files = manifest.get("files") or {}

    results, failures, normalised = {}, [], []
    for name, entry in sorted(files.items()):
        expected = entry.get("sha256")
        expected_size = entry.get("size_bytes")
        path = package / name
        if not path.is_file():
            failures.append({"file": name, "reason": "missing"})
            continue
        match, actual, how = digest_matches(path, str(expected))
        raw_size = path.stat().st_size
        # Text files that only match after CRLF->LF normalisation must have their
        # declared size compared the same way, otherwise every line looks like a
        # size mismatch on a Windows checkout (finding F12).
        if how == "lf_normalised":
            measured_size = lf_normalised_size(path)
            size_via = "lf_normalised"
        else:
            measured_size = raw_size
            size_via = "raw"
        size_ok = expected_size is None or int(expected_size) == measured_size
        results[name] = {"match": match, "matched_via": how, "actual": actual,
                         "expected": expected, "size_ok": size_ok,
                         "size_bytes": raw_size, "size_measured": measured_size,
                         "size_via": size_via, "size_expected": expected_size}
        if how == "lf_normalised":
            normalised.append(name)
        if not match:
            failures.append({"file": name, "reason": "sha256_mismatch",
                             "expected": expected, "actual": actual})
        elif not size_ok:
            failures.append({"file": name, "reason": "size_mismatch",
                             "expected": expected_size, "actual": measured_size,
                             "size_via": size_via})

    weights_name = None
    weights_digest = identity.get("weights_sha256")
    for name, entry in files.items():
        if entry.get("sha256") == weights_digest and name.endswith(".pt"):
            weights_name = name
            break

    report = {
        "package_dir": str(package),
        "schema_version": manifest.get("schema_version"),
        "gate_status": manifest.get("gate_status"),
        "package_status": manifest.get("package_status"),
        "limitations": manifest.get("limitations"),
        "identity": identity,
        "weights_file": weights_name,
        "training_evidence": manifest.get("training_evidence"),
        "files_checked": len(results),
        "normalised_text_files": sorted(normalised),
        "results": results,
        "failures": failures,
        "failure_count": len(failures),
        "status": "PASS" if not failures else "FAIL",
    }
    report["gate_is_passed"] = str(report["gate_status"]).upper().endswith("GATE_PASSED")

    print(f"package      : {package.name}")
    print(f"gate_status  : {report['gate_status']}  (passed={report['gate_is_passed']})")
    print(f"package_status: {report['package_status']}")
    print(f"model/config : {identity.get('model_id')} / {identity.get('config_id')}")
    print(f"dataset      : {identity.get('dataset_version')}")
    print(f"weights      : {weights_name} sha256={str(weights_digest)[:16]}…")
    print(f"files        : {len(results)} checked, "
          f"{len(report['normalised_text_files'])} matched only after CRLF->LF normalisation")
    print(f"failures     : {report['failure_count']}")
    for item in failures[:10]:
        print(f"  - {item}")
    print(f"status       : {report['status']}")
    if not report["gate_is_passed"]:
        print("note         : gate not passed -> any B3 replay stays DIAGNOSTIC_ONLY by design")

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"wrote {args.out}")
    if args.compact_out:
        compact = {k: v for k, v in report.items() if k != "results"}
        compact["file_matches"] = {k: {"match": v["match"], "matched_via": v["matched_via"],
                                       "size_ok": v["size_ok"]} for k, v in results.items()}
        Path(args.compact_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.compact_out).write_text(json.dumps(compact, indent=2, ensure_ascii=False),
                                          encoding="utf-8")
        print(f"wrote {args.compact_out}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
