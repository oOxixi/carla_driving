"""Evidence-derived gate and scope decisions, fail closed.

`docs/architecture/modules/B3_HIL_J6P_INDEPENDENT_VALIDATION.md` §3/§15/§16 requires the
credibility of a conclusion to be decided by verified evidence rather than by a
directory name, a manifest self-report or a command line switch.  Two hard-coded
conclusions used to violate that rule:

* `hil_replay_summary.json` always claimed the Student was not A3-gated, even
  when a real Gate-passed weight manifest was passed in;
* `claim_scope` promoted a run to board evidence as soon as
  `--device-class J6P_BOARD` appeared on the command line.

Both decisions are derived here from the material that actually landed in the
run directory.  Every check fails closed: a missing, unresolved or unverified
input can only lower the claim, never raise it, and no check consults a flag the
caller could set on its own.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .identity import UNRESOLVED, VERIFICATION_METHOD_MANIFEST


#: Gate statuses that mean "a real gate has been passed for these weights".
#: A3 owns the FP32 gate, A2 owns the INT8 gate; anything else, including an
#: empty or unknown string, keeps a run diagnostic.
GATE_PASSED_STATUSES: frozenset[str] = frozenset(
    {"A3_FP32_GATE_PASSED", "A2_INT8_GATE_PASSED"}
)

IDENTITY_FIELDS: tuple[str, ...] = (
    "git_sha",
    "model_id",
    "model_sha256",
    "dataset_version",
    "config_id",
)

LEVEL_E0 = "E0_TOOL_SELFTEST"
LEVEL_E1 = "E1_STRUCTURE_PREVALIDATION"
LEVEL_E2 = "E2_CANDIDATE_X86"
LEVEL_E3 = "E3_J6P_BRINGUP"
LEVEL_E4 = "E4_J6P_INDEPENDENT_MEASURED"
#: A board-classified run whose board evidence chain is incomplete.  It is not
#: E3/E4 (no board chain to read) and it is not E1 either (the device class is
#: not an X86 host), so it gets its own label instead of a misleading tier.
LEVEL_UNVERIFIED = "UNVERIFIED_J6P_CLAIM"

SCOPE_X86_PRE_VALIDATED = "X86_PRE_VALIDATED"
SCOPE_X86_CANDIDATE_PREVALIDATED = "X86_CANDIDATE_PREVALIDATED"
SCOPE_J6P_BRINGUP = "J6P_BRINGUP"
SCOPE_J6P_ON_DEVICE = "J6P_ON_DEVICE"
SCOPE_J6P_UNVERIFIED = "J6P_CLAIM_UNVERIFIED"

J6P_MEASURED_SCOPES: frozenset[str] = frozenset({SCOPE_J6P_ON_DEVICE})

_HEX_DIGITS = frozenset("0123456789abcdef")


def _field(source: Any, name: str) -> Any:
    """Read one field from a dataclass-like object or a plain mapping."""
    if source is None:
        return None
    if isinstance(source, Mapping):
        return source.get(name)
    return getattr(source, name, None)


def sha256_hex(value: Any) -> str | None:
    """Return the lower-case digest when ``value`` is a full SHA256 hex string."""
    if not isinstance(value, str):
        return None
    text = value.strip().lower()
    if len(text) != 64 or any(char not in _HEX_DIGITS for char in text):
        return None
    return text


def _check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def passed_names(checks: Sequence[Mapping[str, Any]]) -> set[str]:
    return {str(item["name"]) for item in checks if item.get("passed")}


def failed_names(checks: Sequence[Mapping[str, Any]]) -> list[str]:
    return [str(item["name"]) for item in checks if not item.get("passed")]


# --------------------------------------------------------------------------
# Candidate identity: is this really a gate-passed candidate?


def gate_checks(identity: Any) -> list[dict[str, Any]]:
    """Check the five identifiers, the gate status and the manifest digest.

    The digest is only trusted when it was produced by
    `identity.identity_from_weight_manifest`, which recomputes the SHA256 from
    the file on disk.  A hand-written identity that merely *says*
    `A3_FP32_GATE_PASSED` therefore stays diagnostic: it has no verification
    record, so it cannot be promoted by editing a JSON field.
    """
    if identity is None:
        reason = "no candidate identity was recorded for this run"
        return [
            _check("identity_present", False, reason),
            _check("identity_complete", False, reason),
            _check("gate_status_passed", False, reason),
            _check("weights_manifest_verified", False, reason),
            _check("digest_matches_identity", False, reason),
        ]

    missing = [
        name
        for name in IDENTITY_FIELDS
        if _field(identity, name) in (None, "", UNRESOLVED)
    ]
    gate_status = str(_field(identity, "gate_status") or "")
    verification = _field(identity, "verification")
    verification_map = verification if isinstance(verification, Mapping) else {}
    manifest_digest = sha256_hex(verification_map.get("artifact_sha256"))
    identity_digest = sha256_hex(_field(identity, "model_sha256"))
    verification_ok = bool(
        verification_map.get("verified")
        and verification_map.get("method") == VERIFICATION_METHOD_MANIFEST
        and manifest_digest
    )
    return [
        _check("identity_present", True, "candidate identity recorded"),
        _check(
            "identity_complete",
            not missing,
            f"missing identifiers: {missing}" if missing else "all five identifiers resolved",
        ),
        _check(
            "gate_status_passed",
            gate_status in GATE_PASSED_STATUSES,
            f"gate_status={gate_status or 'MISSING'}",
        ),
        _check(
            "weights_manifest_verified",
            verification_ok,
            (
                "weights SHA256 recomputed from disk and matched the manifest"
                if verification_ok
                else "no machine-verified weights manifest record on this identity"
            ),
        ),
        _check(
            "digest_matches_identity",
            bool(identity_digest and manifest_digest == identity_digest),
            (
                "verified digest equals model_sha256"
                if identity_digest and manifest_digest == identity_digest
                else "verified manifest digest does not equal model_sha256"
            ),
        ),
    ]


def gate_verified(identity: Any) -> bool:
    checks = gate_checks(identity)
    return bool(checks) and all(item["passed"] for item in checks)


def replay_conclusion(identity: Any) -> dict[str, Any]:
    """Decide how the Teacher comparison of a replay may be read.

    Returns the fields written into `hil_replay_summary.json`, so the conclusion
    lives with the evidence that justifies it instead of being typed into the
    writer.
    """
    checks = gate_checks(identity)
    failed = failed_names(checks)
    if not failed:
        return {
            "teacher_comparison": "GATE_ELIGIBLE",
            "teacher_comparison_reason": (
                "Student weights are gate-passed and the artifact digest was "
                "recomputed from disk against the weight manifest, so this "
                "behaviour/target comparison is a gate-eligible input for B2. "
                "The accuracy verdict itself is still B2's to sign."
            ),
            "diagnostic_only": False,
            "gate_verified": True,
            "gate_checks": checks,
            "gate_failed_checks": [],
        }
    return {
        "teacher_comparison": "DIAGNOSTIC_ONLY",
        "teacher_comparison_reason": (
            "Student weights are not A3-gated in this run "
            f"(failed checks: {', '.join(failed)}); the behaviour and target "
            "match is recorded for toolchain validation and must not be read as "
            "accuracy."
        ),
        "diagnostic_only": True,
        "gate_verified": False,
        "gate_checks": checks,
        "gate_failed_checks": failed,
    }


# --------------------------------------------------------------------------
# Claim scope: how far may this run's numbers be quoted?


def scope_checks(
    *,
    device_class: str,
    identity: Any = None,
    artifact: Mapping[str, Any] | None = None,
    capabilities: Mapping[str, Any] | None = None,
    hardware_env: Mapping[str, Any] | None = None,
    telemetry: Mapping[str, Any] | None = None,
    board_runtime: Mapping[str, Any] | None = None,
    rounds_measured: int | None = None,
    stability: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """All evidence a scope decision may look at.

    Device class alone never appears as a passing check on its own: it is only
    the switch that decides *which* evidence is required.
    """
    env = hardware_env if isinstance(hardware_env, Mapping) else {}
    capabilities = capabilities if isinstance(capabilities, Mapping) else {}
    artifact = artifact if isinstance(artifact, Mapping) else {}
    telemetry = telemetry if isinstance(telemetry, Mapping) else {}
    board_runtime = board_runtime if isinstance(board_runtime, Mapping) else {}

    identity_digest = sha256_hex(_field(identity, "model_sha256"))
    artifact_digest = sha256_hex(artifact.get("sha256"))
    board_log_path = board_runtime.get("log_path")
    board_trace = bool(board_runtime.get("trace_emitted"))
    board_log_lines = board_runtime.get("log_lines") or 0
    board_command = str(board_runtime.get("command") or "").strip()

    power = telemetry.get("power")
    power = power if isinstance(power, Mapping) else {}
    utilization = telemetry.get("utilization")
    utilization = utilization if isinstance(utilization, Mapping) else {}
    power_source = str(power.get("source") or "").strip()
    power_probe_point = str(power.get("probe_point") or "").strip()
    utilization_source = str(utilization.get("source") or "").strip()
    power_samples = power.get("sample_count") or 0
    utilization_samples = utilization.get("sample_count") or 0

    host = env.get("host")
    host = host if isinstance(host, Mapping) else {}
    clock = env.get("clock")
    clock = clock if isinstance(clock, Mapping) else {}
    fingerprint_ok = all(
        (
            str(env.get("device_class") or "").strip(),
            str(host.get("hostname") or "").strip(),
            clock.get("resolution_ns") is not None,
            env.get("background_load_cpu_percent") is not None,
        )
    )

    checks = [
        _check(
            "device_class_declared",
            bool(str(device_class or "").strip()),
            f"device_class={device_class or 'MISSING'}",
        ),
        _check(
            "artifact_digest_recorded",
            artifact_digest is not None,
            (
                "loaded artifact SHA256 recomputed on this host"
                if artifact_digest
                else "no SHA256 recorded for the loaded artifact"
            ),
        ),
        _check(
            "artifact_matches_identity",
            bool(artifact_digest and identity_digest and artifact_digest == identity_digest),
            (
                "artifact digest equals the candidate identity digest"
                if artifact_digest and identity_digest == artifact_digest
                else "artifact digest and candidate identity digest differ"
            ),
        ),
        _check(
            "runtime_stage_source_instrumented",
            capabilities.get("stage_source") == "INSTRUMENTED",
            f"stage_source={capabilities.get('stage_source') or 'MISSING'}",
        ),
        _check(
            "runtime_full_chain",
            bool(capabilities.get("full_chain")),
            f"full_chain={capabilities.get('full_chain')}",
        ),
        _check(
            "board_runtime_log_recorded",
            bool(
                board_runtime.get("adapter") == "board"
                and board_command
                and (bool(board_log_lines) or board_trace)
            ),
            (
                "board runtime command and its log/trace are recorded"
                if board_log_lines or board_trace
                else (
                    f"no board runtime log or trace record "
                    f"(log_path={board_log_path or 'MISSING'}, lines={board_log_lines})"
                )
            ),
        ),
        _check(
            "hardware_env_fingerprint_recorded",
            fingerprint_ok,
            (
                "device, host, clock resolution and background load recorded"
                if fingerprint_ok
                else "hardware environment fingerprint is incomplete"
            ),
        ),
        _check(
            "power_probe_verified",
            bool(
                power.get("measured")
                and power_source
                and power_source != "NOT_APPLICABLE"
                and power_probe_point
                and power_probe_point != "NOT_MEASURED"
                and power_samples
            ),
            (
                f"source={power_source or 'MISSING'} "
                f"probe_point={power_probe_point or 'MISSING'} samples={power_samples}"
            ),
        ),
        _check(
            "bpu_probe_verified",
            bool(
                utilization.get("bpu_measured")
                and utilization_source
                and utilization_source != "NOT_APPLICABLE"
                and utilization_samples
            ),
            (
                f"source={utilization_source or 'MISSING'} "
                f"samples={utilization_samples}"
            ),
        ),
        _check(
            "repeated_measurement_verified",
            bool(
                (rounds_measured is not None and rounds_measured >= 3)
                or (
                    isinstance(stability, Mapping)
                    and bool(stability.get("duration_met"))
                    and bool(stability.get("success"))
                )
            ),
            (
                f"rounds={rounds_measured if rounds_measured is not None else 'MISSING'}; "
                "stability duration met="
                f"{bool(isinstance(stability, Mapping) and stability.get('duration_met'))}"
            ),
        ),
    ]
    checks.extend(gate_checks(identity))
    return checks


@dataclass(frozen=True, slots=True)
class ScopeDecision:
    evidence_level: str
    scope: str
    j6p_status: str


#: Checks a J6P run must satisfy before any board claim is allowed at all.
J6P_CORE_CHECKS: tuple[str, ...] = (
    "device_class_declared",
    "artifact_digest_recorded",
    "artifact_matches_identity",
    "runtime_stage_source_instrumented",
    "runtime_full_chain",
    "board_runtime_log_recorded",
    "hardware_env_fingerprint_recorded",
)

#: Additional checks required before board numbers may be quoted as measured.
J6P_MEASURED_CHECKS: tuple[str, ...] = (
    "gate_status_passed",
    "weights_manifest_verified",
    "digest_matches_identity",
    "power_probe_verified",
    "bpu_probe_verified",
    "repeated_measurement_verified",
)

X86_CANDIDATE_CHECKS: tuple[str, ...] = (
    "gate_status_passed",
    "weights_manifest_verified",
    "digest_matches_identity",
    "artifact_matches_identity",
    "runtime_stage_source_instrumented",
    "runtime_full_chain",
)


def scope_decision(
    *,
    device_class: str,
    checks: Sequence[Mapping[str, Any]],
) -> ScopeDecision:
    passed = passed_names(checks)
    if str(device_class or "").strip() != "J6P_BOARD":
        if set(X86_CANDIDATE_CHECKS) <= passed:
            return ScopeDecision(LEVEL_E2, SCOPE_X86_CANDIDATE_PREVALIDATED, "J6P_PENDING")
        return ScopeDecision(LEVEL_E1, SCOPE_X86_PRE_VALIDATED, "J6P_PENDING")
    if not set(J6P_CORE_CHECKS) <= passed:
        return ScopeDecision(LEVEL_UNVERIFIED, SCOPE_J6P_UNVERIFIED, "J6P_NOT_VERIFIABLE")
    if set(J6P_MEASURED_CHECKS) <= passed:
        return ScopeDecision(LEVEL_E4, SCOPE_J6P_ON_DEVICE, "J6P_MEASURED")
    return ScopeDecision(LEVEL_E3, SCOPE_J6P_BRINGUP, "J6P_BRINGUP_ONLY")


__all__ = [
    "GATE_PASSED_STATUSES",
    "IDENTITY_FIELDS",
    "LEVEL_E0",
    "LEVEL_E1",
    "LEVEL_E2",
    "LEVEL_E3",
    "LEVEL_E4",
    "LEVEL_UNVERIFIED",
    "SCOPE_X86_PRE_VALIDATED",
    "SCOPE_X86_CANDIDATE_PREVALIDATED",
    "SCOPE_J6P_BRINGUP",
    "SCOPE_J6P_ON_DEVICE",
    "SCOPE_J6P_UNVERIFIED",
    "J6P_MEASURED_SCOPES",
    "ScopeDecision",
    "failed_names",
    "gate_checks",
    "gate_verified",
    "passed_names",
    "replay_conclusion",
    "scope_checks",
    "scope_decision",
    "sha256_hex",
]
