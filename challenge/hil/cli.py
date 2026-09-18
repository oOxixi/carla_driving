"""Command line entry points for the B3 measurement toolkit."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
import platform
from pathlib import Path
import shlex
import sys
import time
from typing import Any, Sequence

from .columns import FILE_SCHEMAS
from .artifact import verify_onnx_artifact
from .consistency import (
    DEFAULT_ATOL,
    DEFAULT_RTOL,
    OnnxOutputSource,
    TorchOutputSource,
    compare_sources,
)
from .contract import check_runtime_contract
from .failure_cases import build_failure_cases, run_failure_cases
from .freeze import freeze_snapshot, load_frozen_snapshot
from .handoff import export_handoff
from .identity import UNRESOLVED, CandidateIdentity, git_head, sha256_file
from .provenance import teacher_baselines
from .replay import load_replay_cases
from .report import SEGMENT_ORDER, build_report, claim_scope, report_filename
from .rounds import run_rounds
from .run_io import RunDir, new_run_id, read_jsonl, write_csv, write_json, write_jsonl
from .runtime_adapter import (
    AdapterError,
    BoardCliRuntime,
    InProcessStudentRuntime,
    OnnxModelRuntime,
    PlannerRuntime,
)
from .samplers import (
    ProbeCommand,
    TelemetrySpec,
    cpu_calibration_ms,
    cpu_frequency_mhz,
    machine_load_percent,
    power_source,
)
from .stability import run_soak, write_soak_files
from .stages import (
    CLOCK_SOURCE,
    STAGES,
    LatencyCollector,
    StageOrderError,
    StageTrace,
    clock_resolution_ns,
    percentile,
)


BLOCKED_ON_DEFAULT: tuple[str, ...] = (
    "BLOCKED_ON_A3: real FP32 weights + weights_manifest.json",
    "BLOCKED_ON_A2: INT8 quantized artifact + calibration record",
    "BLOCKED_ON_A4: board runtime entry point + model .bin",
    "BLOCKED_ON_B1: frozen formal request set (D1/D2 delivery)",
    "BLOCKED_ON_B2: frozen benchmark cases + metric policy",
    "BLOCKED_ON_HARDWARE: J6P board and power probe",
)


def _build_hardware_env(
    args: argparse.Namespace,
    identity: CandidateIdentity,
    artifact: str | Path | None,
) -> dict[str, Any]:
    artifact_info: dict[str, Any]
    if artifact is not None and Path(artifact).is_file():
        path = Path(artifact).resolve()
        artifact_info = {
            "path": str(path),
            "sha256": sha256_file(path),
            "size_bytes": path.stat().st_size,
            "format": path.suffix.lstrip(".").lower(),
        }
    else:
        artifact_info = {
            "path": str(artifact) if artifact else None,
            "sha256": None,
            "size_bytes": None,
            "format": None,
        }
    power_measured = bool(args.power_probe_command)
    return {
        "device_class": args.device_class,
        "run_started_at_utc": datetime.now(timezone.utc).isoformat(),
        "host": {
            "hostname": platform.node(),
            "os": platform.platform(),
            "kernel": platform.version(),
            "cpu_model": platform.processor() or platform.machine(),
            "cpu_cores": os.cpu_count(),
            "cpu_max_mhz": None,
        },
        "memory_total_mib": None,
        # A latency measurement taken on a busy machine is not comparable with
        # one taken on an idle machine, so the load at measurement start is
        # recorded with the environment rather than kept as an afterthought.
        "background_load_cpu_percent": machine_load_percent(),
        "power_source": power_source(),
        "cpu_frequency": cpu_frequency_mhz(),
        "cpu_calibration_ms": cpu_calibration_ms(),
        "python": {"version": sys.version.split()[0], "executable": sys.executable},
        # Library versions are part of the measurement environment: the torch
        # version in particular decides weight initialisation, and therefore
        # whether this run is comparable with an earlier one.
        "runtime_libraries": runtime_libraries(),
        "clock": {
            "source": CLOCK_SOURCE,
            "resolution_ns": clock_resolution_ns(),
            # `time.monotonic` on Windows only ticks every ~15.6 ms, which is
            # why the harness does not use it for latency marks.
            "platform_monotonic_resolution_ns": float(
                time.get_clock_info("monotonic").resolution
            ) * 1e9,
        },
        "accelerator": {
            "kind": args.accelerator_kind,
            "name": args.accelerator_name,
            "driver": None,
            "runtime_version": version_of("onnxruntime"),
        },
        "bpu": (
            {
                "arch": args.bpu_arch,
                "core_count": None,
                "frequency_mhz": None,
                "toolchain_version": args.openexplorer_version,
            }
            if args.device_class == "J6P_BOARD"
            else None
        ),
        "openexplorer": (
            {"version": args.openexplorer_version}
            if args.openexplorer_version
            else None
        ),
        "model_artifact": artifact_info,
        "model_seed": getattr(args, "model_seed", None),
        "teacher_baselines": teacher_baselines(args.repo),
        "identity": identity.to_dict(),
        "power_measurement": {
            "method": args.power_method if power_measured else "NOT_MEASURED",
            "probe_point": args.power_probe_point,
            "sampling_hz": (1.0 / args.telemetry_interval_s) if args.telemetry_interval_s else None,
            "notes": args.power_notes,
        },
        "thermal": None,
        "cpu_governor": args.cpu_governor,
    }


def version_of(module_name: str) -> str | None:
    try:
        module = __import__(module_name)
    except ImportError:
        return None
    return getattr(module, "__version__", None)


def package_version(distribution: str) -> str | None:
    """Version of an installed distribution, without importing it."""
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version(distribution)
    except PackageNotFoundError:
        return None


def runtime_libraries() -> dict[str, str | None]:
    """Every library whose version can change a measurement."""
    return {
        "torch": package_version("torch"),
        "onnxruntime": package_version("onnxruntime"),
        "onnx": package_version("onnx"),
        "numpy": package_version("numpy"),
        "Pillow": package_version("pillow"),
        "jsonschema": package_version("jsonschema"),
        "psutil": package_version("psutil"),
    }


def _probe_from_args(
    command: str | None,
    fields: str | None,
    name: str,
) -> ProbeCommand | None:
    if not command:
        return None
    return ProbeCommand(
        name=name,
        command=tuple(shlex.split(command)),
        fields=tuple(part.strip() for part in (fields or "").split(",") if part.strip()),
    )


def _telemetry_spec(args: argparse.Namespace) -> TelemetrySpec:
    return TelemetrySpec(
        interval_s=args.telemetry_interval_s,
        power_probe=_probe_from_args(
            args.power_probe_command, args.power_probe_fields, "onboard_ina"
        ),
        power_scope=args.power_scope,
        power_probe_point=args.power_probe_point,
        utilization_probe=_probe_from_args(
            args.utilization_probe_command, args.utilization_probe_fields, "board_tool"
        ),
        utilization_scope=args.utilization_scope,
    )


def _build_runtime(args: argparse.Namespace) -> PlannerRuntime:
    if args.adapter in {"inprocess", "both"}:
        return InProcessStudentRuntime(
            args.repo,
            weights=args.weights,
            weights_manifest=args.weights_manifest,
            dataset_version=args.dataset_version,
            seed=args.model_seed,
        )
    if args.adapter == "onnx":
        return OnnxModelRuntime(args.repo, args.onnx or (Path(args.repo) / "challenge" / "student_v0_fp32.onnx"))
    if args.adapter == "board":
        if not args.board_command:
            raise AdapterError("--board-command is required for the board adapter")
        return BoardCliRuntime(
            args.board_command,
            artifact=args.board_artifact,
            model_id=args.model_id,
            config_id=args.config_id,
            dataset_version=args.dataset_version,
        )
    raise AdapterError(f"unsupported adapter: {args.adapter}")


def command_schema(args: argparse.Namespace) -> int:
    output = Path(args.out)
    output.mkdir(parents=True, exist_ok=True)
    payload = {
        name: {"columns": list(columns)}
        for name, columns in FILE_SCHEMAS.items()
    }
    write_json(output / "columns.json", payload)
    for name, columns in FILE_SCHEMAS.items():
        write_json(output / f"{name}.columns.json", {"columns": list(columns)})
    print(json.dumps({name: len(columns) for name, columns in FILE_SCHEMAS.items()}, indent=2))
    return 0


def command_selftest(_: argparse.Namespace) -> int:
    failures: list[str] = []

    trace = StageTrace(trace_id="selftest", case_id="c1", round_index=1)
    for index, stage in enumerate(STAGES):
        trace.mark(stage, timestamp_ns=1_000_000 * (index + 1))
    trace.finish("READY")
    durations = trace.durations_ms()
    # Eight marks at 1 ms spacing: T0=1 ms ... T7=8 ms.
    if abs(durations["planner_e2e_ms"] - 7.0) > 1e-9:
        failures.append(f"planner_e2e_ms expected 7.0 got {durations['planner_e2e_ms']}")
    if abs(durations["model_only_ms"] - 1.0) > 1e-9:
        failures.append("model_only_ms must be a single stage gap")
    if abs(durations["planner_overhead_ms"] - 6.0) > 1e-9:
        failures.append("planner_overhead_ms must be e2e minus model only")

    out_of_order = StageTrace(trace_id="order")
    out_of_order.mark("packing_end", timestamp_ns=10)
    try:
        out_of_order.mark("preprocess_end", timestamp_ns=20)
    except StageOrderError:
        pass
    else:
        failures.append("out-of-order stage mark was accepted")

    backwards = StageTrace(trace_id="backwards")
    backwards.mark("input_arrival", timestamp_ns=100)
    try:
        backwards.mark("preprocess_end", timestamp_ns=50)
    except StageOrderError:
        pass
    else:
        failures.append("non-monotonic timestamp was accepted")

    if abs((percentile([0.0, 10.0], 0.5) or -1) - 5.0) > 1e-9:
        failures.append("percentile interpolation drifted from the repo convention")

    identity = CandidateIdentity()
    if identity.complete:
        failures.append("empty identity must not report complete")

    collector = LatencyCollector()
    collector.add(trace)
    report = collector.report(run_id="selftest", identity=identity.to_dict())
    if report["measured_ready_count"] != 1:
        failures.append("collector did not count the ready measured trace")
    expected_columns = set(FILE_SCHEMAS["latency_raw"])
    if set(report["rows"][0]) != expected_columns:
        failures.append("latency CSV row does not match the frozen column set")

    scope = claim_scope(device_class="X86_WORKSTATION", power_measured=False, bpu_measured=False)
    if scope["j6p_status"] != "J6P_PENDING":
        failures.append("X86 runs must report J6P_PENDING")

    if failures:
        print(json.dumps({"status": "FAIL", "failures": failures}, indent=2, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "PASS", "stage_count": len(STAGES)}, indent=2))
    return 0


def _add_shared_args(parser: argparse.ArgumentParser, *, out_help: str) -> None:
    """Arguments every measurement subcommand needs, defined exactly once."""
    parser.add_argument("--repo", required=True, help="carla_driving checkout")
    parser.add_argument("--out", required=True, help=out_help)
    parser.add_argument("--delivery", help="B1 delivery root (request set + rgb manifest)")
    parser.add_argument("--requests", help="explicit request JSONL path")
    parser.add_argument("--frozen", help="frozen replay snapshot directory")
    parser.add_argument(
        "--adapter",
        default="inprocess",
        choices=["inprocess", "onnx", "board", "both"],
    )
    parser.add_argument("--onnx", help="ONNX artifact for the model-only chain")
    parser.add_argument("--weights", help="FP32 weights for the in-process chain")
    parser.add_argument("--weights-manifest", help="A3 weight manifest JSON")
    parser.add_argument("--board-command", help="A4 runtime command (stdin JSON, stdout JSON)")
    parser.add_argument("--board-artifact", help="board model artifact for identity hashing")
    parser.add_argument("--model-id", default=UNRESOLVED)
    parser.add_argument("--config-id", default=UNRESOLVED)
    parser.add_argument("--dataset-version", default=UNRESOLVED)
    parser.add_argument(
        "--model-seed",
        type=int,
        default=20260911,
        help="torch seed for the random-initialized structure (A1 freezes 20260911)",
    )
    parser.add_argument("--run-id", default=None)
    parser.add_argument(
        "--device-class",
        default="X86_WORKSTATION",
        choices=["X86_WORKSTATION", "J6P_BOARD"],
    )
    parser.add_argument("--accelerator-kind", default="cpu")
    parser.add_argument("--accelerator-name", default=platform.processor() or platform.machine())
    parser.add_argument("--bpu-arch", default=None)
    parser.add_argument("--openexplorer-version", default=None)
    parser.add_argument("--cpu-governor", default=None)
    parser.add_argument("--power-method", default="EXTERNAL_METER")
    parser.add_argument("--power-scope", default="board_total")
    parser.add_argument("--power-probe-point", default="NOT_MEASURED")
    parser.add_argument("--power-probe-command", default=None)
    parser.add_argument("--power-probe-fields", default="power_w,voltage_v,current_a")
    parser.add_argument("--power-notes", default="")
    parser.add_argument("--utilization-scope", default="board_total")
    parser.add_argument("--utilization-probe-command", default=None)
    parser.add_argument(
        "--utilization-probe-fields",
        default="bpu_percent,cpu_percent,ddr_bandwidth_gbps",
    )
    parser.add_argument("--telemetry-interval-s", type=float, default=1.0)
    parser.add_argument("--quiet", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="b3_hil", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    selftest = sub.add_parser("selftest", help="run dependency-free internal checks")
    selftest.set_defaults(func=command_selftest)

    schema = sub.add_parser("schema", help="export the frozen column definitions")
    schema.add_argument("--out", default="schemas")
    schema.set_defaults(func=command_schema)

    run = sub.add_parser("run", help="execute a measurement run")
    _add_shared_args(run, out_help="runs/ root directory")
    run.add_argument("--rounds", type=int, default=3)
    run.add_argument("--warmup", type=int, default=5)
    run.add_argument("--limit", type=int, default=None, help="cap the number of replayed cases")
    run.add_argument("--no-failures", action="store_true", help="skip the abnormal input suite")
    run.add_argument("--no-handoff", action="store_true", help="skip the A3 handoff export")
    run.add_argument(
        "--verify-consistency",
        action="store_true",
        help="compare raw torch and ONNX outputs on the first requests",
    )
    run.add_argument("--consistency-rtol", type=float, default=DEFAULT_RTOL)
    run.add_argument("--consistency-atol", type=float, default=DEFAULT_ATOL)
    run.add_argument(
        "--verify-backend-consistency",
        action="store_true",
        help="prove the instrumented stage path matches StudentBackend.infer",
    )
    run.set_defaults(func=command_run)

    soak = sub.add_parser("soak", help="long-duration stability run with recovery probe")
    _add_shared_args(soak, out_help="runs/ root directory")
    soak.add_argument("--limit", type=int, default=None, help="cap the number of cases")
    soak.add_argument("--duration-minutes", type=float, default=30.0)
    soak.add_argument("--recovery-probe-cases", type=int, default=10)
    soak.set_defaults(func=command_soak)

    contract = sub.add_parser(
        "contract", help="check a runtime against the A4 measurement contract"
    )
    _add_shared_args(contract, out_help="directory for contract_report.json")
    contract.add_argument("--limit", type=int, default=5)
    contract.add_argument("--latency-budget-ms", type=float, default=1000.0)
    contract.set_defaults(func=command_contract)

    artifact = sub.add_parser(
        "artifact", help="independently verify an ONNX artifact (FP32 or INT8)"
    )
    artifact.add_argument("--repo", required=True, help="carla_driving checkout")
    artifact.add_argument("--onnx", help="ONNX artifact (defaults to the A1 structure export)")
    artifact.add_argument("--reference-structure", help="producer model_structure.json")
    artifact.add_argument("--expected-opset", type=int, default=17)
    artifact.add_argument("--out", help="optional directory for artifact_report.json")
    artifact.set_defaults(func=command_artifact)

    freeze = sub.add_parser("freeze", help="freeze a request set into a replay snapshot")
    freeze.add_argument("--delivery", help="B1 delivery root")
    freeze.add_argument("--requests", help="explicit request JSONL path")
    freeze.add_argument("--repo", help="carla_driving checkout (for raw rgb_ref fallback)")
    freeze.add_argument("--out", required=True, help="snapshot root directory")
    freeze.add_argument("--name", required=True, help="snapshot name")
    freeze.add_argument("--limit", type=int, default=None)
    freeze.add_argument("--no-copy-rgb", action="store_true")
    freeze.set_defaults(func=command_freeze)

    consistency = sub.add_parser("consistency", help="raw output equivalence between two graphs")
    consistency.add_argument("--repo", required=True)
    consistency.add_argument("--onnx", help="candidate ONNX artifact")
    consistency.add_argument("--baseline-onnx", help="reference ONNX (e.g. FP32) for INT8 checks")
    consistency.add_argument("--weights", help="torch weights for the reference path")
    consistency.add_argument("--delivery", help="B1 delivery root for the request set")
    consistency.add_argument("--frozen", help="frozen snapshot directory")
    consistency.add_argument("--requests", help="explicit request JSONL path")
    consistency.add_argument("--limit", type=int, default=5)
    consistency.add_argument("--rtol", type=float, default=DEFAULT_RTOL)
    consistency.add_argument("--atol", type=float, default=DEFAULT_ATOL)
    consistency.add_argument("--model-seed", type=int, default=20260911)
    consistency.add_argument("--out", help="optional report path")
    consistency.set_defaults(func=command_consistency)

    handoff = sub.add_parser("handoff", help="export failures for A3 (hard cases + vectors)")
    handoff.add_argument("--run", required=True, help="finished run directory")
    handoff.add_argument("--out", help="output directory (defaults to <run>/handoff)")
    handoff.set_defaults(func=command_handoff)
    return parser


def _warn_if_busy(hardware_env: Mapping[str, Any], log: Any, threshold: float = 20.0) -> None:
    load = hardware_env.get("background_load_cpu_percent")
    if isinstance(load, (int, float)) and load > threshold:
        log(
            f"WARNING: machine load was {load:.0f}% at measurement start; "
            "latency numbers from this run are not comparable with an idle-machine run"
        )
    if hardware_env.get("power_source") == "BATTERY":
        frequency = hardware_env.get("cpu_frequency") or {}
        current = frequency.get("current_mhz")
        maximum = frequency.get("max_mhz")
        # psutil reports the nominal clock on Windows even while the CPU is
        # throttled, so only quote the frequency when it really is reduced.
        reduced = current and maximum and current < maximum * 0.9
        detail = f" (CPU {current:.0f}/{maximum:.0f} MHz)" if reduced else ""
        log(
            "WARNING: host is running on battery power"
            f"{detail}; the CPU is throttled and latency is several times higher "
            "than on AC. Re-run on AC before treating these numbers as the baseline."
        )


def _load_cases(args: argparse.Namespace) -> tuple[list[Any], dict[str, Any]]:
    if getattr(args, "frozen", None):
        cases, info = load_frozen_snapshot(args.frozen)
        limit = getattr(args, "limit", None)
        if limit is not None:
            cases = cases[:limit]
            info = {
                **info,
                "cases": len(cases),
                "rgb_resolved": sum(1 for case in cases if case.rgb_resolved),
                "limit": limit,
            }
        return cases, info
    return load_replay_cases(
        delivery_root=getattr(args, "delivery", None),
        requests_path=getattr(args, "requests", None),
        repo_root=getattr(args, "repo", None),
        limit=getattr(args, "limit", None),
    )


def command_freeze(args: argparse.Namespace) -> int:
    result = freeze_snapshot(
        delivery_root=args.delivery,
        requests_path=args.requests,
        repo_root=args.repo,
        out_root=args.out,
        name=args.name,
        limit=args.limit,
        copy_rgb=not args.no_copy_rgb,
    )
    manifest = result["manifest"]
    cases, info = load_frozen_snapshot(result["snapshot"])
    print(
        json.dumps(
            {
                "snapshot": result["snapshot"],
                "cases": manifest["counts"]["cases"],
                "rgb_copied": manifest["counts"]["rgb_copied"],
                "teacher_plans": manifest["counts"]["teacher_plans"],
                "case_set_digest_sha256": manifest["case_set_digest_sha256"],
                "reload_check": {
                    "cases": len(cases),
                    "rgb_resolved": info["rgb_resolved"],
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def command_consistency(args: argparse.Namespace) -> int:
    cases, info = _load_cases(args)
    requests = [case.request for case in cases[: max(1, args.limit)]]
    if args.baseline_onnx:
        if not args.onnx:
            raise AdapterError("--onnx is required together with --baseline-onnx")
        reference = OnnxOutputSource(args.baseline_onnx, args.repo)
        candidate = OnnxOutputSource(args.onnx, args.repo)
    else:
        reference = TorchOutputSource(args.repo, weights=args.weights, seed=args.model_seed)
        candidate = OnnxOutputSource(
            args.onnx or (Path(args.repo) / "challenge" / "student_v0_fp32.onnx"),
            args.repo,
        )
    report = compare_sources(
        reference, candidate, requests, rtol=args.rtol, atol=args.atol
    )
    report["request_source"] = info
    if args.out:
        write_json(args.out, report)
    print(
        json.dumps(
            {
                "reference": report["reference"]["name"],
                "candidate": report["candidate"]["name"],
                "requests": report["request_count"],
                "passed": report["passed"],
                "max_abs_diff_over_all_cases": report["max_abs_diff_over_all_cases"],
                "rtol": report["rtol"],
                "atol": report["atol"],
                "worst_case": sorted(
                    report["cases"], key=lambda item: item.get("max_abs_diff") or -1
                )[-1].get("worst_outputs") if report["cases"] else [],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if report["passed"] else 1


def command_handoff(args: argparse.Namespace) -> int:
    run_root = Path(args.run).resolve()
    replay_path = run_root / "hil_replay.jsonl"
    plans_path = run_root / "hil_replay_plans.jsonl"
    failure_path = run_root / "failure_cases" / "failure_summary.json"
    if not replay_path.is_file():
        raise AdapterError(f"missing {replay_path}")
    replay_rows = read_jsonl(replay_path)
    plan_rows = read_jsonl(plans_path) if plans_path.is_file() else []
    abnormal = (
        json.loads(failure_path.read_text(encoding="utf-8"))
        if failure_path.is_file()
        else None
    )
    summary = export_handoff(
        out_dir=Path(args.out) if args.out else run_root / "handoff",
        run_id=run_root.name,
        replay_rows=replay_rows,
        plan_rows=plan_rows,
        abnormal_summary=abnormal,
    )
    print(json.dumps(summary["counts"], ensure_ascii=False, indent=2))
    return 0


def command_artifact(args: argparse.Namespace) -> int:
    onnx_path = args.onnx or (Path(args.repo) / "challenge" / "student_v0_fp32.onnx")
    structure = args.reference_structure
    if structure is None:
        candidate = Path(args.repo) / "challenge" / "model_structure.json"
        structure = candidate if candidate.is_file() else None
    report = verify_onnx_artifact(
        onnx_path,
        repo_root=args.repo,
        reference_structure=structure,
        expected_opset=args.expected_opset,
    )
    if args.out:
        target = Path(args.out)
        target.mkdir(parents=True, exist_ok=True)
        report["report_path"] = str(write_json(target / "artifact_report.json", report))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


def command_contract(args: argparse.Namespace) -> int:
    runtime = _build_runtime(args)
    cases, info = _load_cases(args)
    limit = args.limit if args.limit is not None else 5
    requests = [case.request for case in cases[: max(1, limit)]]
    report = check_runtime_contract(
        runtime, requests, latency_budget_ms=args.latency_budget_ms
    )
    report["request_source"] = info
    report["adapter"] = args.adapter
    target = Path(args.out)
    target.mkdir(parents=True, exist_ok=True)
    report_path = write_json(target / "contract_report.json", report)
    report["report_path"] = str(report_path)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


def command_soak(args: argparse.Namespace) -> int:
    root = Path(args.out).resolve()
    run_id = args.run_id or new_run_id("b3-soak")
    run_dir = RunDir(root, run_id)

    def log(message: str) -> None:
        if not args.quiet:
            print(f"[{run_id}] {message}", flush=True)

    runtime = _build_runtime(args)
    artifact = args.weights or args.board_artifact or args.onnx
    hardware_env = _build_hardware_env(args, runtime.identity, artifact)
    run_dir.write_hardware_env(hardware_env)
    cases, info = _load_cases(args)
    log(f"soak over {len(cases)} cases for {args.duration_minutes} minutes")
    _warn_if_busy(hardware_env, log)
    result = run_soak(
        runtime,
        cases,
        run_id=run_id,
        duration_s=args.duration_minutes * 60.0,
        telemetry=_telemetry_spec(args),
        recovery_probe_cases=args.recovery_probe_cases,
        progress=lambda message: log(message),
    )
    stability_summary = write_soak_files(run_dir, result)
    scope = claim_scope(
        device_class=args.device_class,
        power_measured=bool(args.power_probe_command),
        bpu_measured=bool(args.utilization_probe_command),
    )
    report_text = build_report(
        run_id=run_id,
        identity=runtime.identity,
        capabilities=runtime.capabilities.to_dict(),
        hardware_env=hardware_env,
        latency_report={
            "measured_ready_count": result["summary"]["iterations"],
            "trace_count": result["summary"]["iterations"],
            "outcome_counts": result["summary"]["outcomes"],
            "metrics_ms": {},
            "rounds": {},
        },
        replay_summary=None,
        telemetry=result["summary"]["telemetry"],
        failure_summary=None,
        run_summary={
            "rounds": 1,
            "measured_traces": result["summary"]["iterations"],
            "warmup_traces": 0,
            "replay_rows": 0,
            "duration_s": result["summary"]["observed_duration_s"],
        },
        blocked_on=BLOCKED_ON_DEFAULT if not runtime.identity.complete else (),
        stability_summary=stability_summary,
    )
    run_dir.path(report_filename(args.device_class)).write_text(report_text, encoding="utf-8")
    manifest = run_dir.build_manifest(
        identity=runtime.identity,
        claim_scope=scope["scope"],
        extra={
            "j6p_status": scope["j6p_status"],
            "capabilities": runtime.capabilities.to_dict(),
            "stability": stability_summary,
            "request_source": info,
            "teacher_baselines": hardware_env.get("teacher_baselines"),
        },
    )
    log(
        f"soak success={stability_summary['success']} "
        f"iterations={stability_summary['iterations']} "
        f"rss_drift_kib={stability_summary['memory_drift_kib']}"
    )
    print(json.dumps({"run_id": run_id, "run_dir": str(run_dir.root)}, ensure_ascii=False))
    return 0 if stability_summary["success"] else 1


def command_run(args: argparse.Namespace) -> int:
    root = Path(args.out).resolve()
    run_id = args.run_id or new_run_id()
    run_dir = RunDir(root, run_id)

    def log(message: str) -> None:
        if not args.quiet:
            print(f"[{run_id}] {message}", flush=True)

    if args.adapter in {"inprocess", "both"} and args.weights is None:
        log("no --weights given: running the random-initialized structure (toolchain validation only)")
    runtime = _build_runtime(args)
    artifact = args.weights or args.board_artifact or args.onnx
    if artifact is None and args.adapter in {"onnx", "both"}:
        artifact = Path(args.repo) / "challenge" / "student_v0_fp32.onnx"

    hardware_env = _build_hardware_env(args, runtime.identity, artifact)
    run_dir.write_hardware_env(hardware_env)
    write_json(
        run_dir.path("schema", "columns.json"),
        {name: {"columns": list(columns)} for name, columns in FILE_SCHEMAS.items()},
    )
    _warn_if_busy(hardware_env, log)

    if args.frozen:
        cases, case_info = _load_cases(args)
        log(
            f"loaded {len(cases)} frozen cases from {case_info['snapshot']} "
            f"(set digest {case_info['case_set_digest_sha256'][:12]})"
        )
    else:
        cases, case_info = _load_cases(args)
        log(f"loaded {len(cases)} replay cases from {case_info['requests_path']}")
    unresolved_rgb = len(cases) - int(case_info.get("rgb_resolved", 0))
    if unresolved_rgb:
        log(f"warning: {unresolved_rgb} cases have no resolvable RGB frame")

    result = run_rounds(
        runtime,
        cases,
        run_id=run_id,
        rounds=args.rounds,
        warmup=args.warmup,
        telemetry=_telemetry_spec(args),
        progress=lambda message: log(message),
    )

    latency_report = result.collector.report(run_id=run_id, identity=runtime.identity.to_dict())
    write_csv(run_dir.path("latency_raw.csv"), FILE_SCHEMAS["latency_raw"], latency_report["rows"])
    write_json(run_dir.path("latency_summary.json"), {k: v for k, v in latency_report.items() if k != "rows"})
    write_csv(run_dir.path("memory_raw.csv"), FILE_SCHEMAS["memory_raw"], result.memory_rows)
    write_csv(run_dir.path("power_raw.csv"), FILE_SCHEMAS["power_raw"], result.power_rows)
    write_csv(
        run_dir.path("utilization_raw.csv"),
        FILE_SCHEMAS["utilization_raw"],
        result.utilization_rows,
    )
    write_jsonl(run_dir.path("hil_replay.jsonl"), result.replay_rows)
    if result.plan_rows:
        write_jsonl(run_dir.path("hil_replay_plans.jsonl"), result.plan_rows)

    replay_summary: dict[str, Any] | None = None
    if result.replay_rows:
        total = len(result.replay_rows)
        ready = sum(1 for row in result.replay_rows if row["outcome"] == "READY")
        rgb_ok = sum(1 for row in result.replay_rows if row["rgb_resolved"])
        structural = sum(1 for row in result.replay_rows if not row["structural_failures"])
        replay_summary = {
            "case_count": total,
            "ready": ready,
            "rgb_resolved": rgb_ok,
            "structural_pass": structural,
            "ready_rate": ready / total,
            "rgb_resolution_rate": rgb_ok / total,
            "structural_pass_rate": structural / total,
            "teacher_comparison": "DIAGNOSTIC_ONLY",
            "teacher_comparison_reason": (
                "Student weights are not A3-gated in this run; behaviour match is recorded "
                "for toolchain validation and must not be read as accuracy."
            ),
            "requests": case_info,
        }
        write_json(run_dir.path("hil_replay_summary.json"), replay_summary)

    extra_notes: list[str] = []
    if args.adapter == "both":
        onnx_path = args.onnx or (Path(args.repo) / "challenge" / "student_v0_fp32.onnx")
        model_runtime = OnnxModelRuntime(args.repo, onnx_path)
        bench_traces = model_runtime.bench_model_only(
            cases[0].request, iterations=max(10, args.limit or 10), warmup=args.warmup, case_id="model-only"
        )
        collector = LatencyCollector()
        for trace in bench_traces:
            collector.add(trace)
        bench_report = collector.report(run_id=run_id, identity=model_runtime.identity.to_dict())
        write_csv(
            run_dir.path("latency_model_only_raw.csv"),
            FILE_SCHEMAS["latency_raw"],
            bench_report["rows"],
        )
        write_json(
            run_dir.path("latency_model_only_summary.json"),
            {k: v for k, v in bench_report.items() if k != "rows"},
        )
        stats = bench_report["metrics_ms"].get("model_only_ms") or {}
        extra_notes.append(
            "独立模型压测（ONNX Runtime，CPU EP，batch=1，warmup=5）："
            f"P50={stats.get('p50')} ms，P95={stats.get('p95')} ms，max={stats.get('max')} ms，"
            f"n={stats.get('count')}；详见 latency_model_only_raw.csv。"
        )

    failure_summary = None
    if not args.no_failures:
        failure_cases = build_failure_cases(cases[0].request)
        failure_summary = run_failure_cases(
            runtime,
            failure_cases,
            run_id=run_id,
            output_dir=run_dir.path("failure_cases"),
        )
        log(f"abnormal input suite: {failure_summary['verdicts']}")

    consistency_report = None
    if args.verify_consistency:
        onnx_path = args.onnx or (Path(args.repo) / "challenge" / "student_v0_fp32.onnx")
        reference = TorchOutputSource(args.repo, weights=args.weights, seed=args.model_seed)
        candidate = OnnxOutputSource(onnx_path, args.repo)
        consistency_report = compare_sources(
            reference,
            candidate,
            [case.request for case in cases[: max(1, min(5, len(cases)))]],
            rtol=args.consistency_rtol,
            atol=args.consistency_atol,
        )
        write_json(run_dir.path("consistency_report.json"), consistency_report)
        log(
            "torch vs onnx: "
            f"passed={consistency_report['passed']} "
            f"max_abs_diff={consistency_report['max_abs_diff_over_all_cases']:.3e}"
        )
        extra_notes.append(
            "torch↔ONNX 逐输出等价性："
            f"{'通过' if consistency_report['passed'] else '未通过'}，"
            f"全输出最大绝对差 {consistency_report['max_abs_diff_over_all_cases']:.3e}"
            f"（rtol={args.consistency_rtol}, atol={args.consistency_atol}）"
        )

    handoff_summary = None
    if not args.no_handoff and (result.replay_rows or failure_summary):
        handoff_summary = export_handoff(
            out_dir=run_dir.path("handoff"),
            run_id=run_id,
            replay_rows=result.replay_rows,
            plan_rows=result.plan_rows,
            abnormal_summary=failure_summary,
            source_snapshot={"frozen_snapshot": args.frozen} if args.frozen else None,
        )
        log(
            "handoff: "
            f"trainable={handoff_summary['counts']['trainable']} "
            f"robustness={handoff_summary['counts']['robustness_vectors']}"
        )

    backend_consistency = None
    if args.verify_backend_consistency:
        verifier = getattr(runtime, "verify_consistency", None)
        if verifier is None:
            backend_consistency = {
                "status": "NOT_APPLICABLE",
                "reason": f"adapter {runtime.name} has no in-process backend to compare against",
            }
        else:
            backend_consistency = verifier(cases[0].request)
        write_json(run_dir.path("backend_consistency.json"), backend_consistency)
        log(f"backend consistency: {backend_consistency['status']}")
        extra_notes.append(
            "打点路径 vs 生产入口（StudentBackend.infer）输出一致性："
            f"{backend_consistency['status']}"
            + (
                f"（{backend_consistency.get('reason')}）"
                if backend_consistency.get("reason")
                else ""
            )
        )

    scope = claim_scope(
        device_class=args.device_class,
        power_measured=bool(args.power_probe_command),
        bpu_measured=bool(args.utilization_probe_command),
    )
    report_text = build_report(
        run_id=run_id,
        identity=runtime.identity,
        capabilities=runtime.capabilities.to_dict(),
        hardware_env=hardware_env,
        latency_report={k: v for k, v in latency_report.items() if k != "rows"},
        replay_summary=replay_summary,
        telemetry={
            "memory": (result.rounds[-1].telemetry if result.rounds else {}).get("memory", {}),
            "power": (result.rounds[-1].telemetry if result.rounds else {}).get("power", {}),
            "utilization": (result.rounds[-1].telemetry if result.rounds else {}).get("utilization", {}),
        },
        failure_summary=failure_summary,
        run_summary=result.summary(),
        blocked_on=BLOCKED_ON_DEFAULT if not runtime.identity.complete else (),
        extra_notes=extra_notes,
    )
    run_dir.path(report_filename(args.device_class)).write_text(report_text, encoding="utf-8")

    manifest = run_dir.build_manifest(
        identity=runtime.identity,
        claim_scope=scope["scope"],
        extra={
            "j6p_status": scope["j6p_status"],
            "capabilities": runtime.capabilities.to_dict(),
            "replay_requests": case_info,
            "teacher_baselines": hardware_env.get("teacher_baselines"),
            "consistency": (
                None
                if consistency_report is None
                else {
                    "passed": consistency_report["passed"],
                    "max_abs_diff_over_all_cases": consistency_report[
                        "max_abs_diff_over_all_cases"
                    ],
                    "rtol": consistency_report["rtol"],
                    "atol": consistency_report["atol"],
                }
            ),
            "handoff": (
                None if handoff_summary is None else handoff_summary["counts"]
            ),
            "backend_consistency": backend_consistency,
        },
    )
    log(f"claim_scope={scope['scope']} files={manifest['file_count']}")
    print(json.dumps({"run_id": run_id, "run_dir": str(run_dir.root)}, ensure_ascii=False))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except AdapterError as error:
        print(f"adapter error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
