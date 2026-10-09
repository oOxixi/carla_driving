#!/usr/bin/env python3

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import onnxruntime as ort
import torch

from challenge.planner.student_adapter import StudentPlanAdapter
from challenge.student.preprocess import StudentPreprocessor
from challenge.hil.tensors import load_tensor_dump, output_checksums


DEFAULT_MODEL_ID = "student-v0-r3-fp32"
DEFAULT_CONFIG_ID = "student-v0-r3-structure-20260911"
DEFAULT_DATASET_VERSION = "NOT_APPLICABLE_CURRENT_ONNX"
DEFAULT_OPENEXPLORER_VERSION = "N/A_FOR_X86"
TRACE_STAGES = (
    "input_arrival",
    "preprocess_end",
    "packing_end",
    "inference_start",
    "inference_end",
    "postprocess_end",
    "adapter_end",
    "plan_ready",
)

INPUT_SHAPES = {
    "rgb": [1, 3, 224, 224],
    "text_tokens": [1, 32],
    "targets": [1, 8, 14],
    "state": [1, 64],
}

OUTPUT_SHAPES = {
    "plan_length_logits": [1, 4],
    "behavior_logits": [1, 4, 14],
    "target_pointer_logits": [1, 4, 9],
    "target_lane_logits": [1, 4, 6],
    "target_speed_mps": [1, 4],
    "completion_type_logits": [1, 4, 8],
    "on_failure_logits": [1, 4, 4],
    "confidence": [1, 1],
    "requires_confirmation_logits": [1, 1],
    "replan_condition_logits": [1, 7],
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


def normalize_shape(shape):
    result = []

    for value in shape:
        if isinstance(value, (int, np.integer)):
            result.append(int(value))
        else:
            result.append(str(value))

    return result


class OnnxModel:
    def __init__(self, model_path: str):
        self.model_path = Path(model_path).resolve()

        if not self.model_path.is_file():
            raise FileNotFoundError(
                f"ONNX model does not exist: {self.model_path}"
            )

        self.model_sha256 = sha256_file(self.model_path)

        self.session = ort.InferenceSession(
            str(self.model_path),
            providers=["CPUExecutionProvider"],
        )

        self.providers = self.session.get_providers()
        self.inputs = self.session.get_inputs()
        self.outputs = self.session.get_outputs()
        self.metadata = dict(self.session.get_modelmeta().custom_metadata_map)

        self._validate_contract()

    def _validate_contract(self):
        actual_input_names = [item.name for item in self.inputs]
        expected_input_names = list(INPUT_SHAPES.keys())

        if set(actual_input_names) != set(expected_input_names):
            raise RuntimeError(
                "ONNX input names do not match contract.\n"
                f"Expected: {expected_input_names}\n"
                f"Actual: {actual_input_names}"
            )

        for item in self.inputs:
            expected_shape = INPUT_SHAPES[item.name]
            actual_shape = normalize_shape(item.shape)

            if actual_shape != expected_shape:
                raise RuntimeError(
                    f"Input shape mismatch for {item.name}: "
                    f"expected {expected_shape}, got {actual_shape}"
                )

            if item.type != "tensor(float)":
                raise RuntimeError(
                    f"Input dtype mismatch for {item.name}: "
                    f"expected tensor(float), got {item.type}"
                )

        actual_output_names = [item.name for item in self.outputs]
        expected_output_names = list(OUTPUT_SHAPES.keys())

        if actual_output_names != expected_output_names:
            raise RuntimeError(
                "ONNX output names or order do not match contract.\n"
                f"Expected: {expected_output_names}\n"
                f"Actual: {actual_output_names}"
            )

        for item in self.outputs:
            expected_shape = OUTPUT_SHAPES[item.name]
            actual_shape = normalize_shape(item.shape)

            if actual_shape != expected_shape:
                raise RuntimeError(
                    f"Output shape mismatch for {item.name}: "
                    f"expected {expected_shape}, got {actual_shape}"
                )

            if item.type != "tensor(float)":
                raise RuntimeError(
                    f"Output dtype mismatch for {item.name}: "
                    f"expected tensor(float), got {item.type}"
                )

    def run(self, inputs):
        expected_names = set(INPUT_SHAPES.keys())
        actual_names = set(inputs.keys())

        if actual_names != expected_names:
            raise RuntimeError(
                "Runtime input names do not match contract.\n"
                f"Expected: {sorted(expected_names)}\n"
                f"Actual: {sorted(actual_names)}"
            )

        for name, expected_shape in INPUT_SHAPES.items():
            array = np.asarray(inputs[name])

            if array.dtype != np.float32:
                raise RuntimeError(
                    f"Input dtype mismatch for {name}: "
                    f"expected float32, got {array.dtype}"
                )

            if list(array.shape) != expected_shape:
                raise RuntimeError(
                    f"Input shape mismatch for {name}: "
                    f"expected {expected_shape}, got {list(array.shape)}"
                )

        return self.session.run(None, inputs)


def current_git_sha() -> str:
    repo_root = Path(__file__).resolve().parents[2]
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
            timeout=20,
        )
    except (OSError, subprocess.SubprocessError):
        return "UNRESOLVED"
    value = result.stdout.strip()
    return value if len(value) == 40 else "UNRESOLVED"


class TraceClock:
    def __init__(self, enabled: bool):
        self.enabled = enabled
        self.last_ns = 0
        self.values = {}

    def mark(self, stage: str) -> None:
        if not self.enabled:
            return
        value = time.perf_counter_ns()
        if value <= self.last_ns:
            value = self.last_ns + 1
        self.values[stage] = value
        self.last_ns = value


def describe(args, runtime: OnnxModel) -> dict:
    metadata = runtime.metadata
    return {
        "git_sha": current_git_sha(),
        "model_id": str(metadata.get("model_id", args.model_id)),
        "model_sha256": runtime.model_sha256,
        "dataset_version": str(
            metadata.get("dataset_version", args.dataset_version)
        ),
        "config_id": str(metadata.get("config_id", args.config_id)),
        "precision": str(metadata.get("precision", args.precision)),
        "batch": int(metadata.get("batch", 1)),
        "input_shapes": {
            item.name: normalize_shape(item.shape)
            for item in runtime.inputs
        },
        "output_names": [item.name for item in runtime.outputs],
        "execution_provider": runtime.providers[0],
        "openexplorer_version": str(
            metadata.get("openexplorer_version", args.openexplorer_version)
        ),
        "model_only": True,
        "resident": True,
    }


def serve(args):
    runtime = OnnxModel(args.model)

    preprocessor = StudentPreprocessor()
    adapter = StudentPlanAdapter(
        model_id="student-v0-r3-fp32"
    )

    input_names = [
        item.name for item in runtime.inputs
    ]

    for line_number, line in enumerate(sys.stdin, start=1):
        if not line.strip():
            continue

        try:
            request = json.loads(line)
            clock = TraceClock(args.trace)
            clock.mark("input_arrival")

            tensorized = preprocessor(request)
            clock.mark("preprocess_end")
            tensors = tensorized.as_tuple()

            inputs = {
                name: tensor.numpy()
                for name, tensor in zip(input_names, tensors)
            }
            clock.mark("packing_end")

            clock.mark("inference_start")
            raw_outputs = runtime.run(inputs)
            clock.mark("inference_end")

            outputs = {
                item.name: torch.from_numpy(value)
                for item, value in zip(runtime.outputs, raw_outputs)
            }
            clock.mark("postprocess_end")

            plan = adapter.decode(
                request,
                outputs,
            )
            clock.mark("adapter_end")
            clock.mark("plan_ready")

            if args.trace:
                plan = dict(plan)
                plan["trace"] = clock.values

            print(
                json.dumps(
                    plan,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                flush=True,
            )

        except Exception as exc:
            print(
                f"request line {line_number} failed: {exc}",
                file=sys.stderr,
            )
            return 1

    return 0


def build_zero_inputs():
    return {
        "rgb": np.zeros(INPUT_SHAPES["rgb"], dtype=np.float32),
        "text_tokens": np.zeros(
            INPUT_SHAPES["text_tokens"],
            dtype=np.float32,
        ),
        "targets": np.zeros(
            INPUT_SHAPES["targets"],
            dtype=np.float32,
        ),
        "state": np.zeros(
            INPUT_SHAPES["state"],
            dtype=np.float32,
        ),
    }


def model_only(args):
    runtime = OnnxModel(args.model)
    arrays, manifest = load_tensor_dump(args.input)
    inputs = {
        name: arrays[name]
        for name in INPUT_SHAPES
    }
    raw_outputs = runtime.run(inputs)
    outputs = {
        item.name: value
        for item, value in zip(runtime.outputs, raw_outputs)
    }
    payload = {
        "status": "OK",
        "mode": "onnx",
        "iterations": 1,
        "model_sha256": runtime.model_sha256,
        "dump_case_id": manifest.get("case_id"),
        "dump_request_sha256": manifest.get("request_sha256"),
        "outputs": output_checksums(outputs),
    }
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="X86 ONNX Runtime smoke benchmark"
    )

    parser.add_argument(
        "--model",
        default="challenge/student_v0_fp32.onnx",
    )

    parser.add_argument(
        "--warmup",
        type=int,
        default=5,
    )

    parser.add_argument(
        "--runs",
        type=int,
        default=20,
    )

    parser.add_argument(
        "--profile-output",
        default="challenge/runtime/runtime_profile_x86.json",
    )

    parser.add_argument(
        "--serve",
        action="store_true",
        help="read ModelRequest JSON lines from stdin",
    )
    parser.add_argument(
        "--describe",
        action="store_true",
        help="print runtime identity without inference",
    )
    parser.add_argument(
        "--model-only",
        action="store_true",
        help="run only ONNX forward on a tensor dump",
    )
    parser.add_argument(
        "--trace",
        action="store_true",
        help="include monotonic nanosecond stage marks in serve output",
    )
    parser.add_argument(
        "--input",
        help="tensor dump directory for --model-only",
    )
    parser.add_argument(
        "--model-id",
        default=DEFAULT_MODEL_ID,
    )
    parser.add_argument(
        "--config-id",
        default=DEFAULT_CONFIG_ID,
    )
    parser.add_argument(
        "--dataset-version",
        default=DEFAULT_DATASET_VERSION,
    )
    parser.add_argument(
        "--precision",
        default="fp32",
    )
    parser.add_argument(
        "--openexplorer-version",
        default=DEFAULT_OPENEXPLORER_VERSION,
    )

    args = parser.parse_args()
    if args.describe and args.model_only:
        parser.error("--describe and --model-only cannot be combined")
    if args.trace and not args.serve:
        parser.error("--trace requires --serve")
    if args.model_only and not args.input:
        parser.error("--model-only requires --input <tensor-dump-dir>")
    if args.describe:
        runtime = OnnxModel(args.model)
        print(
            json.dumps(
                describe(args, runtime),
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
        return
    if args.model_only:
        raise SystemExit(model_only(args))
    if args.serve:
        raise SystemExit(serve(args))

    if args.warmup < 0:
        raise ValueError("--warmup must be >= 0")

    if args.runs <= 0:
        raise ValueError("--runs must be > 0")

    runtime = OnnxModel(args.model)
    inputs = build_zero_inputs()

    print("=== Model ===")
    print(runtime.model_path)

    print("\n=== Model SHA256 ===")
    print(runtime.model_sha256)

    print("\n=== Providers ===")
    print(runtime.providers)

    print("\n=== Inputs ===")
    for item in runtime.inputs:
        print(item.name, item.shape, item.type)

    print("\n=== Outputs ===")
    for item in runtime.outputs:
        print(item.name, item.shape, item.type)

    print("\n=== Warmup ===")
    for _ in range(args.warmup):
        runtime.run(inputs)

    print("Warmup complete.")

    durations_ms = []

    print("\n=== Benchmark ===")
    for _ in range(args.runs):
        start_ns = time.perf_counter_ns()
        outputs = runtime.run(inputs)
        end_ns = time.perf_counter_ns()
        durations_ms.append((end_ns - start_ns) / 1_000_000.0)

    print(f"runs: {args.runs}")
    print(f"avg_ms: {sum(durations_ms) / len(durations_ms):.3f}")
    print(f"min_ms: {min(durations_ms):.3f}")
    print(f"max_ms: {max(durations_ms):.3f}")

    print("\n=== Output Shapes ===")
    output_shapes = {}

    for item, output in zip(runtime.outputs, outputs):
        shape = list(np.asarray(output).shape)
        output_shapes[item.name] = shape
        print(f"{item.name}: {shape}")

    profile = {
        "runtime_mode": "x86_benchmark",
        "backend": "onnxruntime",
        "execution_provider": runtime.providers[0],
        "model": str(runtime.model_path),
        "model_sha256": runtime.model_sha256,
        "git_sha": current_git_sha(),
        "model_id": str(runtime.metadata.get("model_id", args.model_id)),
        "config_id": str(runtime.metadata.get("config_id", args.config_id)),
        "dataset_version": str(
            runtime.metadata.get("dataset_version", args.dataset_version)
        ),
        "precision": str(runtime.metadata.get("precision", args.precision)),
        "warmup_runs": args.warmup,
        "benchmark_runs": args.runs,
        "avg_ms": sum(durations_ms) / len(durations_ms),
        "min_ms": min(durations_ms),
        "max_ms": max(durations_ms),
        "input_shapes": INPUT_SHAPES,
        "output_shapes": output_shapes,
    }

    profile_path = Path(args.profile_output)
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile_path.write_text(
        json.dumps(profile, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"\nProfile written to: {profile_path}")


if __name__ == "__main__":
    main()
