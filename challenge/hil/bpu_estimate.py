"""Verify A4's BPU performance estimate instead of trusting it (B3 side).

The unified plan asks B3 to check the toolchain estimate rather than publish it:
operator mapping, CPU fallback, the estimate's basis, and the model identity it
was computed from.  This module defines the intake contract B3 will verify when
A4 delivers ``artifacts/a4/<runtime_id>/`` and produces
``bpu_estimate_verification.json``.

Expected package (B3 intake contract):

``runtime_manifest.json``, ``source_int8_manifest.json``, ``conversion_config.yaml``,
``compile_command.txt``, ``compile.log``, ``operator_mapping.json``,
``fallback_report.json``, ``bpu_performance_estimate.json``,
``estimation_method.md``, ``runtime_command.txt``, ``contract_report.json``,
``SHA256SUMS`` -- plus the optional ``openexplorer_env.json``,
``consistency_report.json``, ``runtime_profile_x86.json``.

Estimate schema B3 verifies::

    {"tool", "tool_version", "openexplorer_version", "model_sha256",
     "input_shapes", "batch", "quantisation", "assumptions": [...],
     "method" | "estimation_method", "estimated_latency_ms": {...},
     "scope": "BPU_ESTIMATED"}

The verdict is fail-closed: a missing tool version, an estimate that carries no
method, a fallback list that disagrees with the operator mapping, or an estimate
labelled as a board measurement all fail.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .claim_scope import SCOPE_BPU_ESTIMATED, validate_claims

REQUIRED_FILES: tuple[str, ...] = (
    "runtime_manifest.json",
    "source_int8_manifest.json",
    "conversion_config.yaml",
    "compile_command.txt",
    "compile.log",
    "operator_mapping.json",
    "fallback_report.json",
    "bpu_performance_estimate.json",
    "estimation_method.md",
    "runtime_command.txt",
    "contract_report.json",
    "SHA256SUMS",
)

OPTIONAL_FILES: tuple[str, ...] = (
    "openexplorer_env.json",
    "consistency_report.json",
    "runtime_profile_x86.json",
)

#: Estimate metadata that must be present for the number to be attributable.
ESTIMATE_METADATA: tuple[str, ...] = (
    "tool",
    "tool_version",
    "openexplorer_version",
    "model_sha256",
    "input_shapes",
    "batch",
    "quantisation",
)

METHOD_KEYS: tuple[str, ...] = ("method", "estimation_method")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _check(name: str, passed: bool, detail: str, **extra: Any) -> dict[str, Any]:
    entry = {"check": name, "passed": bool(passed), "detail": detail}
    entry.update(extra)
    return entry


def verify_sha256sums(package: Path) -> tuple[dict[str, Any], list[str]]:
    listing = package / "SHA256SUMS"
    errors: list[str] = []
    if not listing.is_file():
        return _check("sha256sums", False, "SHA256SUMS missing"), ["SHA256SUMS missing"]

    entries: dict[str, str] = {}
    for line in listing.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            errors.append(f"SHA256SUMS: unparsable line {line!r}")
            continue
        entries[parts[1].strip().lstrip("*")] = parts[0].strip().lower()

    matches, mismatches, missing = {}, [], []
    for name, expected in entries.items():
        path = package / name
        if not path.is_file():
            missing.append(name)
            errors.append(f"SHA256SUMS lists {name} but the file is missing")
            continue
        actual = sha256_file(path)
        if actual == expected:
            matches[name] = actual
        else:
            mismatches.append({"file": name, "expected": expected, "actual": actual})
            errors.append(f"SHA256SUMS mismatch for {name}")

    present = {p.name for p in package.iterdir() if p.is_file()}
    listed = {Path(name).name for name in entries}
    unlisted = sorted(present - listed - {listing.name})

    detail = (f"{len(matches)}/{len(entries)} listed files match"
              + (f"; {len(unlisted)} file(s) not covered by SHA256SUMS" if unlisted else ""))
    return _check("sha256sums", not errors, detail,
                  matched=len(matches), mismatches=mismatches, missing=missing,
                  unlisted=unlisted), errors


def verify_mapping_and_fallback(package: Path) -> tuple[list[dict[str, Any]], list[str]]:
    """Check the operator mapping against the fallback report."""
    checks: list[dict[str, Any]] = []
    errors: list[str] = []
    mapping_path = package / "operator_mapping.json"
    fallback_path = package / "fallback_report.json"
    if not mapping_path.is_file() or not fallback_path.is_file():
        return [_check("operator_mapping", False, "operator_mapping.json or fallback_report.json missing")], [
            "operator mapping or fallback report missing"
        ]

    mapping = _read_json(mapping_path)
    fallback = _read_json(fallback_path)
    nodes = mapping.get("nodes") if isinstance(mapping, Mapping) else None
    fallback_nodes = fallback.get("fallback_nodes") if isinstance(fallback, Mapping) else None
    if not isinstance(nodes, Sequence) or isinstance(nodes, (str, bytes)) or not nodes:
        errors.append("operator_mapping.json has no 'nodes' list")
        return [_check("operator_mapping", False, "no nodes list")], errors
    if not isinstance(fallback_nodes, Sequence) or isinstance(fallback_nodes, (str, bytes)):
        errors.append("fallback_report.json has no 'fallback_nodes' list")
        return [_check("fallback_report", False, "no fallback_nodes list")], errors

    placements: dict[str, int] = {}
    non_bpu: set[str] = set()
    for node in nodes:
        if not isinstance(node, Mapping):
            errors.append("operator_mapping.json: node is not an object")
            continue
        placement = str(node.get("placement") or "UNKNOWN").upper()
        placements[placement] = placements.get(placement, 0) + 1
        name = str(node.get("name") or "")
        if placement != "BPU" and name:
            non_bpu.add(name)

    total = sum(placements.values())
    bpu = placements.get("BPU", 0)
    share = round(bpu / total, 6) if total else 0.0
    checks.append(_check("operator_mapping", True,
                         f"{total} nodes, BPU {bpu} ({share:.4f}), placements={placements}",
                         placements=placements, bpu_share=share, node_count=total))

    declared = []
    for node in fallback_nodes:
        if isinstance(node, Mapping):
            declared.append(str(node.get("name") or ""))
        elif isinstance(node, str):
            declared.append(node)
    declared_set = {name for name in declared if name}
    undeclared = sorted(non_bpu - declared_set)
    phantom = sorted(declared_set - non_bpu)
    detail = f"{len(declared_set)} fallback node(s) declared, {len(non_bpu)} non-BPU node(s) in the mapping"
    ok = not phantom
    if phantom:
        errors.append(f"fallback_report.json lists nodes that the mapping does not place off-BPU: {phantom[:5]}")
    checks.append(_check("fallback_report", ok, detail,
                         declared=sorted(declared_set), undeclared=undeclared, phantom=phantom))
    return checks, errors


def verify_estimate(package: Path) -> tuple[list[dict[str, Any]], list[str], dict[str, Any] | None]:
    """Check the estimate metadata, its scope label and its identity binding."""
    checks: list[dict[str, Any]] = []
    errors: list[str] = []
    path = package / "bpu_performance_estimate.json"
    if not path.is_file():
        return [_check("estimate", False, "bpu_performance_estimate.json missing")], [
            "estimate file missing"
        ], None
    try:
        estimate = _read_json(path)
    except json.JSONDecodeError as error:
        return [_check("estimate", False, f"unparsable estimate: {error}")], [
            "estimate is not valid JSON"
        ], None
    if not isinstance(estimate, Mapping):
        return [_check("estimate", False, "estimate is not an object")], [
            "estimate is not an object"
        ], None

    missing = [key for key in ESTIMATE_METADATA if not estimate.get(key)]
    if missing:
        errors.append(f"estimate is missing metadata: {missing}")
    method = next((estimate.get(key) for key in METHOD_KEYS if estimate.get(key)), None)
    if not isinstance(method, str) or len(method.strip()) < 8:
        errors.append("estimate carries no usable method description")
    assumptions = estimate.get("assumptions")
    if not isinstance(assumptions, Sequence) or isinstance(assumptions, (str, bytes)) or not assumptions:
        errors.append("estimate carries no assumptions list")
    checks.append(_check("estimate_metadata", not missing and isinstance(method, str),
                         f"missing={missing or 'none'}; method={'yes' if isinstance(method, str) else 'no'}"))

    declared_scope = str(estimate.get("scope") or "").upper()
    scope_ok = declared_scope in ("", SCOPE_BPU_ESTIMATED)
    if not scope_ok:
        errors.append(f"estimate declares scope {declared_scope!r}; an estimate must be {SCOPE_BPU_ESTIMATED}")
    checks.append(_check("estimate_scope", scope_ok,
                         f"declared scope={declared_scope or '(none)'}"))

    # Identity binding: the estimate must be about the INT8 artefact we were given.
    identity_errors: list[str] = []
    model_sha = str(estimate.get("model_sha256") or "").lower()
    int8_manifest_path = package / "source_int8_manifest.json"
    if int8_manifest_path.is_file():
        manifest = _read_json(int8_manifest_path)
        candidates = []
        if isinstance(manifest, Mapping):
            for key in ("int8_sha256", "artifact_sha256", "sha256", "model_sha256"):
                value = manifest.get(key)
                if isinstance(value, str) and value:
                    candidates.append(value.lower())
            for nested in ("candidate_identity", "identity", "artifact"):
                inner = manifest.get(nested)
                if isinstance(inner, Mapping):
                    for key in ("int8_sha256", "artifact_sha256", "sha256", "weights_sha256"):
                        value = inner.get(key)
                        if isinstance(value, str) and value:
                            candidates.append(value.lower())
        if candidates and model_sha not in candidates:
            identity_errors.append(
                f"estimate model_sha256 {model_sha[:16]}... is not among the INT8 manifest digests"
            )
    else:
        identity_errors.append("source_int8_manifest.json missing, cannot bind the estimate to an artefact")
    errors.extend(identity_errors)
    checks.append(_check("estimate_identity", not identity_errors,
                         "; ".join(identity_errors) or "estimate digest matches the INT8 manifest"))
    return checks, errors, dict(estimate)


def verify_method_document(package: Path, estimate: Mapping[str, Any] | None) -> tuple[dict[str, Any], list[str]]:
    """The method document must at least name the tool and version the estimate used."""
    path = package / "estimation_method.md"
    if not path.is_file():
        return _check("estimation_method", False, "estimation_method.md missing"), [
            "estimation_method.md missing"
        ]
    text = path.read_text(encoding="utf-8", errors="ignore")
    errors: list[str] = []
    if len(text.strip()) < 200:
        errors.append("estimation_method.md is too short to explain tool, input, assumptions and scope")
    if isinstance(estimate, Mapping):
        for key in ("tool", "tool_version", "openexplorer_version"):
            value = estimate.get(key)
            if isinstance(value, str) and value and value not in text:
                errors.append(f"estimation_method.md does not mention the estimate's {key}={value!r}")
    checked: dict[str, bool] = {}
    if isinstance(estimate, Mapping):
        for key in ("tool", "tool_version"):
            value = estimate.get(key)
            checked[key] = bool(isinstance(value, str) and value and value in text)
    return _check("estimation_method", not errors,
                  "; ".join(errors) or f"{len(text)} chars, names the declared tool and version",
                  mentioned=checked), errors


def verify_bpu_estimate(package: str | Path) -> dict[str, Any]:
    """Verify an A4 package and return the ``bpu_estimate_verification`` report."""
    root = Path(package)
    errors: list[str] = []
    checks: list[dict[str, Any]] = []

    if not root.is_dir():
        return {
            "schema_version": "1.0", "package": str(package), "status": "FAIL",
            "checks": [], "errors": [f"package directory not found: {package}"],
        }

    present = {p.name for p in root.iterdir() if p.is_file()}
    missing_required = [name for name in REQUIRED_FILES if name not in present]
    missing_optional = [name for name in OPTIONAL_FILES if name not in present]
    errors.extend(f"required file missing: {name}" for name in missing_required)
    checks.append(_check("required_files", not missing_required,
                         f"missing required={missing_required or 'none'}; "
                         f"missing optional={missing_optional or 'none'}"))

    sums_check, sums_errors = verify_sha256sums(root)
    checks.append(sums_check)
    errors.extend(sums_errors)

    mapping_checks, mapping_errors = verify_mapping_and_fallback(root)
    checks.extend(mapping_checks)
    errors.extend(mapping_errors)

    estimate_checks, estimate_errors, estimate = verify_estimate(root)
    checks.extend(estimate_checks)
    errors.extend(estimate_errors)

    method_check, method_errors = verify_method_document(root, estimate)
    checks.append(method_check)
    errors.extend(method_errors)

    # Every number the estimate publishes must be labelled as an estimate.
    published: list[dict[str, Any]] = []
    if isinstance(estimate, Mapping):
        for key in ("estimated_latency_ms", "estimated_operator_placement",
                    "estimated_cpu_bpu_split", "estimated_memory"):
            if estimate.get(key):
                published.append({"name": key, "scope": SCOPE_BPU_ESTIMATED, "estimated": True,
                                  "tool": estimate.get("tool"),
                                  "tool_version": estimate.get("tool_version"),
                                  "method": estimate.get("method") or estimate.get("estimation_method"),
                                  "model_sha256": estimate.get("model_sha256")})
    scope_report = validate_claims(published)
    errors.extend(scope_report["errors"])
    checks.append(_check("claim_scope", scope_report["status"] == "PASS",
                         f"{len(published)} estimated number(s) labelled {SCOPE_BPU_ESTIMATED}"))

    report = {
        "schema_version": "1.0",
        "package": str(root),
        "status": "PASS" if not errors else "FAIL",
        "checks": checks,
        "errors": errors,
        "claim_scope": scope_report,
        "estimate": estimate,
        "policy_note": (
            "A PASS means the estimate is attributable and internally consistent: the tool, version, "
            "method and model digest are present, the mapping agrees with the fallback report, and every "
            "number stays labelled BPU_ESTIMATED. It is still an estimate -- never a J6P measurement."
        ),
    }
    return report


__all__ = [
    "REQUIRED_FILES",
    "OPTIONAL_FILES",
    "ESTIMATE_METADATA",
    "verify_bpu_estimate",
]
