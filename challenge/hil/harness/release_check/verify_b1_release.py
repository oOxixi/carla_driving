"""Independent integrity check of a B1 dataset release (B3 side).

B3 measures other teams' artefacts; it does not take their signature on faith.
This checks the release the way a consumer would: every locked file hash, the
signed digests, the packaged image payload, and the per-row request/rgb pairing.

Usage:
    python verify_b1_release.py <release_dir> [--repo <repo_root>] [--out <json>]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
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


def sha256_matches(path: Path, expected: str, *, allow_lf_normalise: bool) -> tuple[bool, str, str]:
    """Return (match, actual_digest, how) where how explains a normalised match.

    B1 publishes digests over LF content. A Windows checkout with
    core.autocrlf=true rewrites text files to CRLF, so the byte-for-byte digest
    differs even though the content is intact. Report both so a mismatch is never
    silently accepted.
    """
    raw = sha256_file(path)
    if raw == expected:
        return True, raw, "raw"
    if allow_lf_normalise:
        normalised = sha256_file(path, lf_normalise=True)
        if normalised == expected:
            return True, raw, "lf_normalised"
    return False, raw, "raw"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _integrity_entries(release: Path) -> tuple[str | None, dict[str, str | None], list[str]]:
    """Return (source, {file: expected_sha256}, notes) for whatever B1 shipped.

    B1 has used two integrity carriers so far: a ``b1_release_lock.sha256`` listing,
    and (for the small supplements) a ``release_manifest.json`` whose ``files``
    map carries sha256 + size per file.  A release with neither is reported, not
    silently accepted.
    """
    notes: list[str] = []
    lock = release / "b1_release_lock.sha256"
    if lock.is_file():
        entries: dict[str, str | None] = {}
        for line in lock.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(None, 1)
            if len(parts) != 2:
                notes.append(f"unparsable lock line: {line!r}")
                continue
            entries[parts[1].strip().lstrip("*")] = parts[0].strip().lower()
        return "b1_release_lock.sha256", entries, notes

    manifest = release / "release_manifest.json"
    if manifest.is_file():
        payload = read_json(manifest)
        files = payload.get("files") if isinstance(payload, dict) else None
        if isinstance(files, dict) and files:
            entries = {}
            for name, entry in files.items():
                digest = entry.get("sha256") if isinstance(entry, dict) else None
                entries[str(name)] = str(digest).lower() if digest else None
            notes.append("no b1_release_lock.sha256; integrity taken from release_manifest.json:files")
            return "release_manifest.json:files", entries, notes
    return None, {}, ["no integrity listing found (no lock file, no release_manifest files map)"]


def check_lock(release: Path, *, allow_lf_normalise: bool) -> dict:
    source, entries, notes = _integrity_entries(release)
    results, failures = {}, [{"reason": note} for note in notes if "no integrity listing" in note]
    for name, digest in entries.items():
        target = release / name
        if not target.is_file():
            # The manifest may legitimately list itself; a missing self-entry is
            # still worth surfacing but only as a note, never as a silent pass.
            failures.append({"file": name, "reason": "missing"})
            continue
        if not digest:
            failures.append({"file": name, "reason": "no declared digest"})
            continue
        match, actual, how = sha256_matches(target, digest, allow_lf_normalise=allow_lf_normalise)
        results[name] = {"expected": digest, "actual": actual, "match": match, "matched_via": how}
        if not match:
            failures.append({"file": name, "reason": "sha256_mismatch",
                             "expected": digest, "actual": actual})
    normalised = sum(1 for r in results.values() if r["matched_via"] == "lf_normalised")
    return {"source": source, "files_checked": len(results),
            "matched_after_lf_normalisation": normalised,
            "notes": notes, "results": results, "failures": failures}


def check_signed_pass(release: Path, *, allow_lf_normalise: bool) -> dict:
    """Verify the digests the pass actually claims, for every pass schema B1 ships.

    Three shapes exist so far:

    1. ``B1_SIGNED_PASS.json`` (D3 Wave2) -- claims release_lock_sha256,
       release_manifest_sha256 and integrity_report_sha256, plus a teacher block.
    2. ``B1_SIGNED_PASS.json`` (targeted gap) -- claims release_manifest_sha256 only.
    3. ``B1_CONTENT_BOUND_PASS.json`` (turn gap) -- no cryptographic signature at
       all: ``signature_status = CONTENT_BOUND_UNSIGNED`` with a single
       ``binding.sha256`` over a canonical JSON payload. The digest is
       recomputable, so B3 verifies it and reports the lower assurance level
       instead of treating it as equivalent to a signed pass.
    """
    signed_path = release / "B1_SIGNED_PASS.json"
    content_path = release / "B1_CONTENT_BOUND_PASS.json"
    if signed_path.is_file():
        signed = read_json(signed_path)
        pass_schema = "B1_SIGNED_PASS"
        assurance = "signed"
    elif content_path.is_file():
        signed = read_json(content_path)
        pass_schema = "B1_CONTENT_BOUND_PASS"
        assurance = "content_bound_unsigned"
    else:
        return {"pass_schema": None, "assurance": None, "gate": None, "status": None,
                "dataset_version": None, "signed_at_utc": None, "teacher": None, "counts": {},
                "claimed_digests": [], "not_claimed_digests": [], "not_recomputable_digests": [],
                "content_binding": None, "results": {},
                "failures": [{"reason": "no_pass_file",
                              "expected": ["B1_SIGNED_PASS.json", "B1_CONTENT_BOUND_PASS.json"]}]}
    pairs = {
        "release_lock_sha256": "b1_release_lock.sha256",
        "release_manifest_sha256": "release_manifest.json",
        "integrity_report_sha256": "b1_release_integrity_report.json",
    }
    # Digests B1 may claim that this checker cannot recompute on its own.
    not_recomputable_keys = ("image_set_canonical_sha256",)
    results, failures, not_claimed, not_recomputable = {}, [], [], []
    for key, relative in pairs.items():
        expected = signed.get(key)
        if expected is None:
            not_claimed.append(key)
            continue
        path = release / relative
        if not path.is_file():
            results[key] = {"expected": expected, "actual": None, "match": False,
                            "matched_via": "missing_file", "file": relative}
            failures.append({"digest": key, "reason": "signed_file_missing",
                             "expected": expected, "actual": None, "file": relative})
            continue
        match, actual, how = sha256_matches(path, str(expected),
                                            allow_lf_normalise=allow_lf_normalise)
        results[key] = {"expected": expected, "actual": actual, "match": match,
                        "matched_via": how, "file": relative}
        if not match:
            failures.append({"digest": key, "reason": "sha256_mismatch",
                             "expected": expected, "actual": actual, "file": relative})
    for key in not_recomputable_keys:
        if signed.get(key):
            not_recomputable.append(key)
    for key in signed:
        if (key.endswith("_sha256") and key not in pairs
                and key not in not_recomputable_keys):
            not_recomputable.append(key)

    content_binding = None
    if pass_schema == "B1_CONTENT_BOUND_PASS":
        binding = signed.get("binding") if isinstance(signed.get("binding"), dict) else {}
        payload = binding.get("payload")
        declared = binding.get("sha256")
        if isinstance(payload, dict) and isinstance(declared, str):
            canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
            actual = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            match = actual == declared
            content_binding = {
                "variant": "payload_binding",
                "algorithm": binding.get("algorithm"),
                "canonicalisation": "json.dumps(payload, sort_keys=True, separators=(',', ':'))",
                "declared": declared,
                "actual": actual,
                "match": match,
                "payload": payload,
            }
            if not match:
                failures.append({"digest": "binding.sha256", "reason": "sha256_mismatch",
                                 "expected": declared, "actual": actual})
        else:
            # Flat attestation variant (e.g. d3_gap300): no payload binding at all,
            # the release only carries `attestation_type` plus the manifest digest,
            # and that digest is already checked through the claimed-digest path
            # above. Not having a binding lowers what can be proven, so it is
            # reported explicitly rather than treated as a failure.
            content_binding = {
                "variant": "flat_attestation",
                "attestation_type": signed.get("attestation_type") or signed.get("signature_status"),
                "match": None,
                "note": ("this release carries no payload binding; only the manifest digest is claimed, "
                         "so content integrity rests on the file listing"),
            }

    return {"pass_schema": pass_schema, "assurance": assurance,
            "signature_status": signed.get("signature_status"),
            "gate": signed.get("gate"), "status": signed.get("status"),
            "dataset_version": signed.get("dataset_version"),
            "signed_at_utc": signed.get("signed_at_utc"),
            "teacher": signed.get("teacher"),
            "counts": {k: signed[k] for k in ("strict_positive_runs", "strict_positive_samples")
                       if k in signed},
            "claimed_digests": sorted(results),
            "not_claimed_digests": not_claimed,
            "not_recomputable_digests": sorted(set(not_recomputable)),
            "content_binding": content_binding,
            "results": results, "failures": failures}


def check_images(release: Path, repo: Path) -> dict:
    mapping = read_json(release / "rgb_mapping.json")
    results, failures = {}, []
    for sample_id, entry in mapping.items():
        ref = entry.get("release_rgb_ref")
        digest = entry.get("sha256")
        size = entry.get("size_bytes")
        path = (repo / ref).resolve() if ref else None
        if path is None or not path.is_file():
            failures.append({"sample_id": sample_id, "reason": "image_missing", "ref": ref})
            continue
        actual = sha256_file(path)
        size_match = size is None or int(size) == path.stat().st_size
        results[sample_id] = {"sha256": actual, "match": actual == digest, "size_match": size_match}
        if actual != digest:
            failures.append({"sample_id": sample_id, "reason": "image_sha256_mismatch",
                             "expected": digest, "actual": actual})
        elif not size_match:
            failures.append({"sample_id": sample_id, "reason": "image_size_mismatch",
                             "expected": size, "actual": path.stat().st_size})
    return {"images_in_mapping": len(mapping), "results": results, "failures": failures}


def check_rows(release: Path, repo: Path) -> dict:
    summary, failures = {}, []
    for name in ("train_addition.jsonl", "val_addition.jsonl", "hard_negative_addition.jsonl"):
        path = release / name
        rows = read_jsonl(path) if path.is_file() else []
        missing_request = missing_plan = unresolved_rgb = mismatch_rgb = 0
        classes: dict[str, int] = {}
        scenarios: dict[str, int] = {}
        for index, row in enumerate(rows):
            if not isinstance(row.get("model_request"), dict):
                missing_request += 1
            if not isinstance(row.get("teacher_plan"), dict):
                missing_plan += 1
            metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
            scenario = str(metadata.get("scenario_id", "UNKNOWN"))
            scenarios[scenario] = scenarios.get(scenario, 0) + 1
            sample_class = row.get("sample_class")
            if isinstance(sample_class, dict):
                key = str(sample_class.get("primary", "UNKNOWN"))
                classes[key] = classes.get(key, 0) + 1
            request = row.get("model_request") if isinstance(row.get("model_request"), dict) else {}
            ref = request.get("rgb_ref")
            if isinstance(ref, str) and ref.strip():
                candidate = (repo / ref).resolve()
                if not candidate.is_file():
                    unresolved_rgb += 1
                    failures.append({"file": name, "row": index, "reason": "rgb_ref_missing", "ref": ref})
                visual = row.get("visual_input") if isinstance(row.get("visual_input"), dict) else {}
                expected = visual.get("rgb_sha256")
                if isinstance(expected, str) and expected:
                    if sha256_file(candidate) != expected:
                        mismatch_rgb += 1
                        failures.append({"file": name, "row": index, "reason": "rgb_sha256_mismatch"})
            else:
                unresolved_rgb += 1
        summary[name] = {
            "rows": len(rows),
            "missing_model_request": missing_request,
            "missing_teacher_plan": missing_plan,
            "rows_without_resolved_rgb": unresolved_rgb,
            "rgb_sha256_mismatch": mismatch_rgb,
            "sample_class": classes,
            "scenario_counts": dict(sorted(scenarios.items())),
        }
    return {"files": summary, "failures": failures}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--out")
    parser.add_argument("--compact-out", help="write a small summary without per-file/per-image rows")
    parser.add_argument("--eol", choices=("auto", "raw"), default="auto",
                        help="auto: accept CRLF->LF normalised digests for text files "
                             "(Windows checkout); raw: byte-for-byte only")
    args = parser.parse_args()

    release = Path(args.release).resolve()
    repo = Path(args.repo).resolve()
    if not release.is_dir():
        print(f"release directory not found: {release}", file=sys.stderr)
        return 2

    normalise = args.eol == "auto"
    report = {
        "release_dir": str(release),
        "repo_root": str(repo),
        "eol_mode": args.eol,
        "lock": check_lock(release, allow_lf_normalise=normalise),
        "signed_pass": check_signed_pass(release, allow_lf_normalise=normalise),
        "images": check_images(release, repo),
        "rows": check_rows(release, repo),
    }
    failures = (report["lock"]["failures"] + report["signed_pass"]["failures"]
                + report["images"]["failures"] + report["rows"]["failures"])
    report["failure_count"] = len(failures)
    report["status"] = "PASS" if not failures else "FAIL"

    pass_info = report["signed_pass"]
    print(f"release      : {release.name}")
    print(f"pass schema  : {pass_info.get('pass_schema')} "
          f"(assurance: {pass_info.get('assurance')}"
          + (f", signature_status: {pass_info['signature_status']}"
             if pass_info.get("signature_status") else "") + ")")
    gate = pass_info.get("gate") or "(not claimed)"
    print(f"signed gate  : {gate} / status {pass_info.get('status')} "
          f"at {pass_info.get('signed_at_utc') or '(not stamped)'}")
    teacher = pass_info.get("teacher")
    if isinstance(teacher, dict):
        print(f"teacher      : {teacher.get('model_id')} @ "
              f"{str(teacher.get('model_revision'))[:12]}")
    if pass_info.get("counts"):
        print(f"declared     : {pass_info['counts']}")
    print(f"digests      : claimed={pass_info['claimed_digests']} "
          f"not_claimed={pass_info['not_claimed_digests']} "
          f"not_recomputable={pass_info['not_recomputable_digests']}")
    binding = pass_info.get("content_binding")
    if isinstance(binding, dict):
        print(f"content bind : match={binding.get('match')} "
              f"declared={binding.get('declared')} canonical={binding.get('canonicalisation')}")
    print(f"integrity    : source={report['lock'].get('source')}")
    print(f"locked files : {report['lock']['files_checked']} checked; "
          f"{report['lock']['matched_after_lf_normalisation']} matched only after "
          f"CRLF->LF normalisation (eol mode: {report['eol_mode']})")
    print(f"images       : {report['images']['images_in_mapping']} checked")
    for name, stats in report["rows"]["files"].items():
        print(f"{name:<30} rows={stats['rows']:<4} "
              f"no_request={stats['missing_model_request']} "
              f"no_plan={stats['missing_teacher_plan']} "
              f"rgb_unresolved={stats['rows_without_resolved_rgb']} "
              f"rgb_mismatch={stats['rgb_sha256_mismatch']} {stats['sample_class']}")
    print(f"failures     : {report['failure_count']}")
    for item in failures[:10]:
        print(f"  - {item}")
    print(f"status       : {report['status']}")

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"wrote {args.out}")
    if args.compact_out:
        compact = {
            "release_dir": report["release_dir"],
            "eol_mode": report["eol_mode"],
            "status": report["status"],
            "failure_count": report["failure_count"],
            "failures": failures,
            "signed_pass": {k: v for k, v in report["signed_pass"].items() if k != "results"},
            "lock": {"files_checked": report["lock"]["files_checked"],
                     "matched_after_lf_normalisation":
                         report["lock"]["matched_after_lf_normalisation"],
                     "matched_via": {k: v["matched_via"] for k, v in report["lock"]["results"].items()}},
            "signed_digests": {k: {"match": v["match"], "matched_via": v["matched_via"]}
                               for k, v in report["signed_pass"]["results"].items()},
            "images": {"images_in_mapping": report["images"]["images_in_mapping"],
                       "failures": len(report["images"]["failures"])},
            "rows": report["rows"]["files"],
        }
        Path(args.compact_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.compact_out).write_text(json.dumps(compact, indent=2, ensure_ascii=False),
                                          encoding="utf-8")
        print(f"wrote {args.compact_out}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
