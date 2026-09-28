"""Accept B3's v3 evidence as diagnostic-only, never as an FP32 Gate.

This audit binds the newly published B3 evidence to A3's frozen v3 identity,
checks that every replay remains fail-closed, and extracts improvement signals.
It deliberately has no code path that promotes a candidate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


DEFAULT_EVIDENCE = "challenge/hil/evidence/a3_fp32_candidate_v3_20260926"
EXPECTED_IDENTITY = {
    "model_id": "student-v0-r3-fp32",
    "config_id": "student-v0-r3-structure-20260911",
    "dataset_version": "b1_d2_v1_1_plus_d3_wave1_a3_strict_positive_v1",
    "git_sha": "151efbbfa0c8920bfc78e29262d984bcfae1877f",
    "weights_sha256": "1afb8ebd11e401d4d7e6181d244ed39438421183c5303f1ce4a4391cee8cc68c",
}
EXPECTED_HANDOFF_SHA256 = (
    "966e16c78457e4022fb1a3eaab11eb6da9ee23d8231e50631437808f03bf7e92"
)
PENDING_GATE = "PENDING_A3_FP32_GATE"
PENDING_PACKAGE = "PENDING_B2_INDEPENDENT_VALIDATION"
EVIDENCE_FILES = (
    "01_handoff_integrity_compact.json",
    "02_real_weights_replay.json",
    "04_real_weights_d2_539.json",
    "05_export_and_consistency.json",
    "06_int8_real_weights_gap99.json",
    "08_soak_real_weights.json",
    "09_int8_real_weights_d3w2_56.json",
)


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _expect(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def _check_diagnostic_run(
    errors: list[str], name: str, run: dict[str, Any], *, require_identity: bool
) -> None:
    _expect(errors, run.get("teacher_comparison") == "DIAGNOSTIC_ONLY", f"{name}: not diagnostic-only")
    _expect(errors, run.get("gate_verified") is False, f"{name}: gate must remain unverified")
    _expect(
        errors,
        run.get("gate_failed_checks") == ["gate_status_passed"],
        f"{name}: unexpected gate failures",
    )
    _expect(errors, run.get("ready_rate") == 1.0, f"{name}: ready rate is not 1.0")
    _expect(errors, run.get("structural_pass_rate") == 1.0, f"{name}: structural pass rate is not 1.0")
    if require_identity:
        _expect(
            errors,
            run.get("identity_gate_status") == PENDING_GATE,
            f"{name}: identity gate status changed",
        )
        _expect(
            errors,
            run.get("identity_weights_sha256") == EXPECTED_IDENTITY["weights_sha256"],
            f"{name}: weights identity mismatch",
        )
        verification = run.get("identity_verification") or {}
        _expect(errors, verification.get("verified") is True, f"{name}: artifact digest was not verified")
        _expect(
            errors,
            verification.get("manifest_sha256") == EXPECTED_HANDOFF_SHA256,
            f"{name}: handoff manifest mismatch",
        )


def audit_b3_v3_diagnostic(evidence_dir: Path) -> dict[str, Any]:
    evidence_dir = evidence_dir.resolve()
    errors: list[str] = []
    missing = [name for name in EVIDENCE_FILES if not (evidence_dir / name).is_file()]
    if missing:
        return {
            "schema_version": "1.0",
            "status": "INVALID",
            "eligible_for_promotion": False,
            "errors": [f"missing evidence file: {name}" for name in missing],
        }

    data = {name: _load(evidence_dir / name) for name in EVIDENCE_FILES}
    integrity = data["01_handoff_integrity_compact.json"]
    identity = integrity.get("identity") or {}
    _expect(errors, integrity.get("status") == "PASS", "handoff integrity did not pass")
    _expect(errors, integrity.get("failure_count") == 0, "handoff integrity reports failures")
    _expect(errors, integrity.get("files_checked") == 9, "handoff did not verify nine payload files")
    _expect(errors, integrity.get("gate_status") == PENDING_GATE, "candidate Gate status changed")
    _expect(errors, integrity.get("gate_is_passed") is False, "diagnostic evidence claims Gate PASS")
    _expect(errors, integrity.get("package_status") == PENDING_PACKAGE, "package status changed")
    for key, expected in EXPECTED_IDENTITY.items():
        _expect(errors, identity.get(key) == expected, f"candidate identity mismatch: {key}")

    replay = data["02_real_weights_replay.json"]
    weights = replay.get("weights") or {}
    for key, expected in EXPECTED_IDENTITY.items():
        replay_key = "training_git_sha" if key == "git_sha" else ("sha256" if key == "weights_sha256" else key)
        _expect(errors, weights.get(replay_key) == expected, f"replay identity mismatch: {key}")
    _expect(errors, weights.get("manifest_gate_status") == PENDING_GATE, "replay Gate status changed")
    _expect(errors, weights.get("manifest_package_status") == PENDING_PACKAGE, "replay package status changed")
    runs = replay.get("runs") or {}
    for name in ("d3_wave2_val_56x3", "gap_val_99x3"):
        run = runs.get(name)
        if not isinstance(run, dict):
            errors.append(f"missing replay run: {name}")
        else:
            _check_diagnostic_run(errors, name, run, require_identity=True)

    d2 = data["04_real_weights_d2_539.json"]
    _check_diagnostic_run(errors, "d2_v1_1_val_539x3", d2, require_identity=False)

    export = data["05_export_and_consistency.json"]
    onnx = export.get("onnx") or {}
    consistency = export.get("torch_vs_onnx") or {}
    _expect(errors, consistency.get("passed") is True, "B3 scratch ONNX consistency failed")
    _expect(errors, consistency.get("requests") == 10, "unexpected ONNX consistency sample count")
    _expect(
        errors,
        onnx.get("sha256") == onnx.get("reported_in_consistency_report"),
        "B3 scratch ONNX digest is internally inconsistent",
    )

    gap_int8 = data["06_int8_real_weights_gap99.json"]
    wave2_int8 = data["09_int8_real_weights_d3w2_56.json"]
    _expect(errors, gap_int8.get("cases") == 99, "targeted-gap INT8 case count changed")
    _expect(errors, wave2_int8.get("cases") == 56, "D3 Wave2 INT8 case count changed")
    gap_speed = (gap_int8.get("head_stats") or {}).get("target_speed_mps") or {}
    wave2_speed = (wave2_int8.get("head_stats") or {}).get("target_speed_mps") or {}

    soak = data["08_soak_real_weights.json"]
    _expect(errors, soak.get("duration_met") is True, "30-minute soak duration not met")
    _expect(errors, soak.get("error_count") == 0, "30-minute soak reports errors")
    _expect(errors, soak.get("success_rate") == 1.0, "30-minute soak success rate is not 1.0")

    evidence_sha256 = {name: _sha256(evidence_dir / name) for name in EVIDENCE_FILES}
    accepted = not errors
    wave2_run = runs.get("d3_wave2_val_56x3") or {}
    gap_run = runs.get("gap_val_99x3") or {}
    return {
        "schema_version": "1.0",
        "status": "DIAGNOSTIC_EVIDENCE_ACCEPTED" if accepted else "INVALID",
        "eligible_for_promotion": False,
        "candidate_identity": EXPECTED_IDENTITY,
        "gate_status": PENDING_GATE,
        "package_status": PENDING_PACKAGE,
        "evidence_sha256": evidence_sha256,
        "checks": {
            "handoff_integrity": integrity.get("status"),
            "files_checked": integrity.get("files_checked"),
            "diagnostic_runs_fail_closed": accepted and all(
                (runs.get(name) or {}).get("gate_verified") is False
                for name in ("d3_wave2_val_56x3", "gap_val_99x3")
            ) and d2.get("gate_verified") is False,
            "torch_onnx_consistency": consistency.get("passed"),
            "soak_duration_met": soak.get("duration_met"),
            "soak_errors": soak.get("error_count"),
        },
        "diagnostic_metrics": {
            "d3_wave2": {
                "behavior_match": wave2_run.get("mean_behavior_match_ratio"),
                "target_match": wave2_run.get("mean_target_match_ratio"),
                "student_outputs": wave2_run.get("distinct_student_outputs"),
                "teacher_outputs": wave2_run.get("distinct_teacher_outputs"),
            },
            "d2_v1_1": {
                "behavior_match": d2.get("mean_behavior_match_ratio"),
                "target_match": d2.get("mean_target_match_ratio"),
                "student_outputs": d2.get("distinct_student_outputs"),
                "teacher_outputs": d2.get("distinct_teacher_outputs"),
            },
            "targeted_gap": {
                "behavior_match": gap_run.get("mean_behavior_match_ratio"),
                "target_match": gap_run.get("mean_target_match_ratio"),
                "student_outputs": gap_run.get("distinct_student_outputs"),
                "teacher_outputs": gap_run.get("distinct_teacher_outputs"),
            },
            "int8_target_speed": {
                "targeted_gap_min_cosine": gap_speed.get("min"),
                "d3_wave2_min_cosine": wave2_speed.get("min"),
                "d3_wave2_below_0_99": wave2_speed.get("below_0_99"),
            },
        },
        "formal_scope": {
            "b3_scratch_onnx_is_formal_artifact": False,
            "development_replays_are_generalization_evidence": False,
            "b3_diagnostic_can_open_a3_gate": False,
            "required_next_authority": "B2 frozen independent Validation Gate",
        },
        "improvement_signals": [
            "track the 6-versus-9 targeted-gap output coverage gap",
            "cover D2, D3 Wave2 and targeted-gap distributions in calibration",
            "treat target_speed_mps as a quantization-sensitive regression head",
        ],
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", type=Path, default=Path(DEFAULT_EVIDENCE))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit_b3_v3_diagnostic(args.evidence_dir)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "DIAGNOSTIC_EVIDENCE_ACCEPTED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
