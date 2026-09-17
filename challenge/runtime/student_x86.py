#!/usr/bin/env python3

import argparse
import json
import time
from pathlib import Path

import numpy as np
import onnxruntime as ort


INPUT_SHAPES = {
    "rgb": (1, 3, 224, 224),
    "text_tokens": (1, 32),
    "targets": (1, 8, 14),
    "state": (1, 64),
}


def build_inputs():
    return {
        "rgb": np.zeros(INPUT_SHAPES["rgb"], dtype=np.float32),
        "text_tokens": np.zeros(INPUT_SHAPES["text_tokens"], dtype=np.float32),
        "targets": np.zeros(INPUT_SHAPES["targets"], dtype=np.float32),
        "state": np.zeros(INPUT_SHAPES["state"], dtype=np.float32),
    }


def main():
    parser = argparse.ArgumentParser()
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
    args = parser.parse_args()

    model_path = Path(args.model)

    if not model_path.exists():
        raise FileNotFoundError(
            f"ONNX model not found: {model_path}"
        )

    session = ort.InferenceSession(
        str(model_path),
        providers=["CPUExecutionProvider"],
    )

    inputs = build_inputs()

    print("=== Model ===")
    print(model_path)

    print("\n=== Providers ===")
    print(session.get_providers())

    print("\n=== Inputs ===")
    for item in session.get_inputs():
        print(
            item.name,
            item.shape,
            item.type,
        )

    print("\n=== Outputs ===")
    for item in session.get_outputs():
        print(
            item.name,
            item.shape,
            item.type,
        )

    print("\n=== Warmup ===")

    for _ in range(args.warmup):
        session.run(None, inputs)

    print("Warmup complete.")

    print("\n=== Benchmark ===")

    latencies_ms = []

    for _ in range(args.runs):
        start = time.perf_counter()

        outputs = session.run(
            None,
            inputs,
        )

        elapsed_ms = (
            time.perf_counter() - start
        ) * 1000.0

        latencies_ms.append(elapsed_ms)

    latencies_ms = np.asarray(
        latencies_ms,
        dtype=np.float64,
    )

    print(
        f"runs: {args.runs}"
    )

    print(
        f"avg_ms: {latencies_ms.mean():.3f}"
    )

    print(
        f"min_ms: {latencies_ms.min():.3f}"
    )

    print(
        f"max_ms: {latencies_ms.max():.3f}"
    )

    print("\n=== Output Shapes ===")

    output_shapes = {}

    for meta, output in zip(
        session.get_outputs(),
        outputs,
    ):
        shape = list(output.shape)

        output_shapes[meta.name] = shape

        print(
            f"{meta.name}: {shape}"
        )

    profile = {
        "backend": "onnxruntime",
        "execution_provider": "CPUExecutionProvider",
        "model": str(model_path),
        "warmup_runs": args.warmup,
        "benchmark_runs": args.runs,
        "latency_ms": {
            "avg": float(latencies_ms.mean()),
            "min": float(latencies_ms.min()),
            "max": float(latencies_ms.max()),
        },
        "inputs": {
            name: list(shape)
            for name, shape in INPUT_SHAPES.items()
        },
        "outputs": output_shapes,
    }

    profile_path = Path(
        args.profile_output
    )

    profile_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    profile_path.write_text(
        json.dumps(
            profile,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        f"\nProfile written to: {profile_path}"
    )


if __name__ == "__main__":
    main()
