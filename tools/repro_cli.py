"""Container-side entry point for the independent reproduction package."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from integration.run_manifest import begin_run, finish_run
from tools.verify_qwen_kernel import verify_kernel_log


EVALUATION_STEPS = ["preflight", "warmup", "latency_gate", "accuracy", "scenarios"]
SCENARIO_SETS = {
    "smoke": ("scenarios/smoke/S01_set_speed_20.json",),
    "evaluate": (
        "scenarios/smoke/S01_set_speed_20.json",
        "scenarios/regression/REG_008_challenge_pedestrian.json",
        "scenarios/safety_D/D07_low_ttc_emergency_brake.json",
    ),
}
SMOKE_AUDIO_RUNTIME = "samples/audio/smoke_set_speed_20.wav"
CommandRunner = Callable[[list[str], Path | None], subprocess.CompletedProcess[str]]


@dataclass(frozen=True, slots=True)
class EvaluationDecision:
    status: str
    remaining_steps: list[str]

    @classmethod
    def from_latency_p95(cls, latency_p95_ms: float) -> "EvaluationDecision":
        if latency_p95_ms > 300.0:
            return cls("EARLY_STOP", [])
        return cls("CONTINUE", ["accuracy", "scenarios"])


def build_evaluation_steps() -> list[str]:
    return list(EVALUATION_STEPS)


def run_command(command: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp, path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _required_data(data_root: Path) -> dict[str, Path]:
    return {
        "asr_manifest": data_root / "datasets/frozen_validation/asr/manifest.json",
        "multimodal_cases": data_root / "datasets/frozen_validation/multimodal/cases.jsonl",
        "latency_manifest": data_root / "datasets/frozen_validation/full_chain_latency_v1.json",
        "smoke_audio": data_root / SMOKE_AUDIO_RUNTIME,
    }


def _run_checked(command: list[str], runner: CommandRunner, log_path: Path) -> None:
    result = runner(command, None)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        f"$ {' '.join(command)}\nexit_code={result.returncode}\n{result.stdout}{result.stderr}",
        encoding="utf-8",
    )
    if result.returncode:
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(command)}")


def _preflight(data_root: Path, run_root: Path, qwen_log: Path | None, carla_log: Path | None,
               runner: CommandRunner) -> dict[str, object]:
    required = _required_data(data_root)
    missing = [f"{label}: {path}" for label, path in required.items() if not path.is_file()]
    if missing:
        raise FileNotFoundError("missing frozen release data: " + "; ".join(missing))
    gpu = runner(
        ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"],
        None,
    )
    if gpu.returncode:
        raise RuntimeError("nvidia-smi failed: " + (gpu.stderr or gpu.stdout).strip())
    kernel: dict[str, str] | None = None
    if qwen_log is not None:
        if not qwen_log.is_file():
            raise FileNotFoundError(f"Qwen bootstrap log missing: {qwen_log}")
        kernel = verify_kernel_log(qwen_log)
        shutil.copy2(qwen_log, run_root / "logs/qwen-bootstrap.log")
    if carla_log is not None:
        if not carla_log.is_file():
            raise FileNotFoundError(f"CARLA bootstrap log missing: {carla_log}")
        shutil.copy2(carla_log, run_root / "logs/carla-bootstrap.log")
    environment = {
        "status": "PASS",
        "gpu": gpu.stdout.strip(),
        "cuda_userspace": "13.2",
        "profile": os.environ.get("QWEN_PROFILE", "qwen3vl-2b-int4"),
        "qwen_kernel": kernel,
        "dataset_hashes": {label: _sha256(path) for label, path in required.items()},
    }
    _write_json(run_root / "environment.json", environment)
    return environment


def _scenario_command(data_root: Path, scenario: str, run_root: Path) -> list[str]:
    return [
        "python3", "-m", "integration.carla_runner", "--qwen-remote",
        "--qwen-service-url", os.environ.get("QWEN_BASE_URL", "http://qwen:8001/v1"),
        "--scenario-file", str(data_root / scenario),
        "--sensor-profile", "low", "--perception-mode", "sensors",
        "--log-dir", str(run_root / "raw"),
    ]


def _run_mode(args: argparse.Namespace, runner: CommandRunner) -> int:
    context = begin_run(args.output_root, {
        "mode": args.mode,
        "profile": args.profile,
        "git_commit": os.environ.get("RELEASE_COMMIT", "unknown"),
    })
    latest = args.output_root / "latest_run_id.txt"
    latest.parent.mkdir(parents=True, exist_ok=True)
    latest.write_text(context.run_id + "\n", encoding="utf-8")
    try:
        _preflight(args.data_root, context.root, args.qwen_log, args.carla_log, runner)
        if args.mode == "preflight":
            finish_run(context, "COMPLETED", None)
            return 0
        if args.mode in {"smoke", "demo"}:
            command = _scenario_command(args.data_root, SCENARIO_SETS["smoke"][0], context.root)
            command += ["--audio", str(args.data_root / SMOKE_AUDIO_RUNTIME)]
            _run_checked(command, runner, context.logs_dir / f"{args.mode}.log")
            finish_run(context, "COMPLETED", None)
            return 0
        if args.mode == "evaluate":
            report_path = context.metrics_dir / "full_chain.json"
            data = _required_data(args.data_root)
            qwen_profile = os.environ.get("QWEN_PROFILE", "qwen3vl-2b-int4")
            command = [
                "python3", "-m", "tools.run_four_modal_full_chain",
                "--qwen-base-url", os.environ.get("QWEN_BASE_URL", "http://qwen:8001/v1"),
                "--profile", qwen_profile,
                "--asr-manifest", str(data["asr_manifest"]),
                "--multimodal-cases", str(data["multimodal_cases"]),
                "--latency-manifest", str(data["latency_manifest"]),
                "--warmup", "5", "--measured", "10",
                "--hardware-label", args.profile,
                "--output", str(report_path),
            ]
            result = runner(command, None)
            (context.logs_dir / "full-chain.log").write_text(result.stdout + result.stderr, encoding="utf-8")
            if not report_path.is_file():
                raise RuntimeError(f"full-chain evaluation produced no report (exit {result.returncode})")
            report = json.loads(report_path.read_text(encoding="utf-8"))
            p95 = float(report["latency"]["end_to_end_ms"]["p95"])
            decision = EvaluationDecision.from_latency_p95(p95)
            _write_json(context.metrics_dir / "evaluation_decision.json", {
                "end_to_end_p95_ms": p95,
                "threshold_ms": 300.0,
                "status": decision.status,
                "remaining_steps": decision.remaining_steps,
            })
            if decision.status == "EARLY_STOP":
                finish_run(context, "EARLY_STOP", "end_to_end_p95_over_300ms")
                return 2
            if result.returncode not in {0, 3}:
                raise RuntimeError(f"full-chain evaluation failed official gates (exit {result.returncode})")
            for scenario in SCENARIO_SETS["evaluate"]:
                name = Path(scenario).stem
                _run_checked(_scenario_command(args.data_root, scenario, context.root), runner,
                             context.logs_dir / f"scenario-{name}.log")
            finish_run(context, "COMPLETED", None)
            return 0
        if args.mode == "stability":
            evaluate_run = args.evaluate_run
            if evaluate_run is None:
                candidates = sorted(
                    (path for path in (args.output_root / "runs").iterdir()
                     if path != context.root and (path / "metrics/full_chain.json").is_file()),
                    reverse=True,
                )
                if not candidates:
                    raise ValueError("stability requires an existing evaluate run or --evaluate-run")
                evaluate_run = candidates[0]
            report = json.loads((evaluate_run / "metrics/full_chain.json").read_text(encoding="utf-8"))
            p95 = float(report["latency"]["end_to_end_ms"]["p95"])
            if p95 > 150.0:
                raise ValueError(f"stability requires prior end-to-end P95 <= 150 ms; got {p95:.3f}")
            image_dir = args.data_root / "datasets/frozen_validation/multimodal/images"
            image = sorted(image_dir.glob("*"))[0]
            command = [
                "python3", "-m", "tools.run_long_stability", "--duration-minutes", "30",
                "--qwen-model", "h2oai/Qwen3-VL-2B-Instruct-GPTQ-Int4",
                "--qwen-image-root", str(image_dir), "--qwen-image-ref", image.name,
                "--output", str(context.metrics_dir / "stability.json"),
            ]
            _run_checked(command, runner, context.logs_dir / "stability.log")
            finish_run(context, "COMPLETED", None)
            return 0
        raise AssertionError(args.mode)
    except Exception as error:
        finish_run(context, "FAILED", f"{type(error).__name__}: {error}")
        print(f"reproduction failed: {error}", flush=True)
        return 1


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("preflight", "smoke", "evaluate", "demo", "stability"))
    parser.add_argument("--profile", choices=("rtx5070", "a800-safe", "a800-optimized"), default="rtx5070")
    parser.add_argument("--data-root", type=Path, default=Path("/app/release_data"))
    parser.add_argument("--output-root", type=Path, default=Path("/output"))
    parser.add_argument("--qwen-log", type=Path)
    parser.add_argument("--carla-log", type=Path)
    parser.add_argument("--evaluate-run", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None, *, runner: CommandRunner = run_command) -> int:
    return _run_mode(parse_args(argv), runner)


if __name__ == "__main__":
    raise SystemExit(main())
