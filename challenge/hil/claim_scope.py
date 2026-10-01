"""Three-way claim scope: X86 measured / BPU estimated / J6P measured, fail closed.

The unified execution plan (2026-09-30) splits every deployment-side number B3
publishes into exactly one of three classes and forbids presenting an estimate
as a measurement:

``X86_MEASURED``
    produced by running the chain on the workstation (latency, memory, CPU,
    stability).  Requires raw artefacts behind it.
``BPU_ESTIMATED``
    produced by the Horizon toolchain's analysis, **not** by a board.  Requires
    the tool name, tool version, estimation method and the model digest it was
    computed from, so the estimate can be reproduced and attributed.
``J6P_MEASURED``
    produced by running on a J6P board.  Requires board evidence: a device
    identity and a raw board log.  Without it the claim stays unverifiable and
    must not be published.

`validate_claims` is deliberately fail-closed: an unknown source, a missing
requirement, or an explicitly ``estimated`` number declared as ``J6P_MEASURED``
all produce errors rather than warnings.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

SCOPE_X86_MEASURED = "X86_MEASURED"
SCOPE_BPU_ESTIMATED = "BPU_ESTIMATED"
SCOPE_J6P_MEASURED = "J6P_MEASURED"

SCOPES: tuple[str, ...] = (SCOPE_X86_MEASURED, SCOPE_BPU_ESTIMATED, SCOPE_J6P_MEASURED)

#: Where a number came from -> which class it belongs to.
SOURCE_SCOPES: dict[str, str] = {
    # Workstation measurements.
    "x86_inprocess": SCOPE_X86_MEASURED,
    "x86_onnx": SCOPE_X86_MEASURED,
    "x86_cpu": SCOPE_X86_MEASURED,
    "x86_soak": SCOPE_X86_MEASURED,
    "workstation": SCOPE_X86_MEASURED,
    # Toolchain analysis on the workstation, not a board.
    "bpu_estimate": SCOPE_BPU_ESTIMATED,
    "horizon_toolchain": SCOPE_BPU_ESTIMATED,
    "hb_compile_analysis": SCOPE_BPU_ESTIMATED,
    "openexplorer_analysis": SCOPE_BPU_ESTIMATED,
    # Board measurements.
    "j6p_board": SCOPE_J6P_MEASURED,
    "cloud_board": SCOPE_J6P_MEASURED,
    "hil_board": SCOPE_J6P_MEASURED,
}

#: Fields a BPU estimate must carry to be attributable and reproducible.
ESTIMATE_REQUIREMENTS: tuple[str, ...] = ("tool", "tool_version", "method", "model_sha256")

#: Evidence a board claim must carry.
BOARD_REQUIREMENTS: tuple[str, ...] = ("device", "raw_log")

#: Evidence an X86 measurement must carry (at least one raw artefact reference).
MEASURED_EVIDENCE_KEYS: tuple[str, ...] = ("raw_artifacts", "raw_csv", "raw_log")


def classify_source(source: str | None) -> str | None:
    """Map a source label onto one of the three classes, or ``None`` if unknown."""
    if not source:
        return None
    return SOURCE_SCOPES.get(str(source).strip().lower())


def _has_any(claim: Mapping[str, Any], keys: Sequence[str]) -> bool:
    for key in keys:
        value = claim.get(key)
        if isinstance(value, str) and value.strip():
            return True
        if isinstance(value, (list, tuple, dict)) and len(value) > 0:
            return True
    return False


def _missing(claim: Mapping[str, Any], keys: Sequence[str]) -> list[str]:
    return [key for key in keys if not (isinstance(claim.get(key), str) and claim.get(key).strip())]


def validate_claims(claims: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Check a table of published numbers against the three-way rule.

    Each claim is ``{"name": str, "scope" | "source": str, ...}`` plus the
    evidence its class requires.  Returns a machine-readable report; ``status``
    is ``PASS`` only when there are no errors.
    """
    results: list[dict[str, Any]] = []
    errors: list[str] = []
    counts = {scope: 0 for scope in SCOPES}

    for index, claim in enumerate(claims):
        if not isinstance(claim, Mapping):
            errors.append(f"claim {index}: not an object")
            continue
        name = str(claim.get("name") or f"claim_{index:02d}")
        scope = claim.get("scope")
        scope = str(scope) if isinstance(scope, str) and scope else classify_source(claim.get("source"))
        entry_errors: list[str] = []

        if scope not in SCOPES:
            entry_errors.append(
                f"{name}: unknown scope (declare scope={'|'.join(SCOPES)} or a known source label)"
            )
            results.append({"name": name, "scope": scope, "errors": entry_errors})
            errors.extend(entry_errors)
            continue

        counts[scope] += 1

        # A number that says it is an estimate can never be a board measurement.
        if scope == SCOPE_J6P_MEASURED and claim.get("estimated") is True:
            entry_errors.append(
                f"{name}: declared J6P_MEASURED while flagged estimated=true "
                "(an estimate must be published as BPU_ESTIMATED)"
            )

        if scope == SCOPE_J6P_MEASURED:
            missing = _missing(claim, BOARD_REQUIREMENTS)
            if missing:
                entry_errors.append(
                    f"{name}: J6P claim without board evidence, missing {missing}"
                )
        elif scope == SCOPE_BPU_ESTIMATED:
            missing = _missing(claim, ESTIMATE_REQUIREMENTS)
            if missing:
                entry_errors.append(
                    f"{name}: BPU estimate without {missing} (tool, version, method and model digest are required)"
                )
        else:  # X86_MEASURED
            if not _has_any(claim, MEASURED_EVIDENCE_KEYS):
                entry_errors.append(
                    f"{name}: X86 measurement without a raw artefact reference "
                    f"(one of {list(MEASURED_EVIDENCE_KEYS)})"
                )

        results.append({"name": name, "scope": scope, "errors": entry_errors})
        errors.extend(entry_errors)

    return {
        "schema_version": "1.0",
        "claims": results,
        "summary": counts,
        "errors": errors,
        "status": "PASS" if not errors else "FAIL",
        "legend": {
            SCOPE_X86_MEASURED: "workstation measurement; carries raw artefacts",
            SCOPE_BPU_ESTIMATED: "Horizon toolchain estimate; carries tool, version, method, model digest",
            SCOPE_J6P_MEASURED: "board measurement; carries device identity and raw board log",
        },
        "policy_note": (
            "X86 measured != BPU estimated != J6P measured. An estimate is never reported as a "
            "measurement, and a board claim without device identity and raw log is rejected."
        ),
    }


__all__ = [
    "SCOPE_X86_MEASURED",
    "SCOPE_BPU_ESTIMATED",
    "SCOPE_J6P_MEASURED",
    "SCOPES",
    "SOURCE_SCOPES",
    "ESTIMATE_REQUIREMENTS",
    "BOARD_REQUIREMENTS",
    "classify_source",
    "validate_claims",
]
