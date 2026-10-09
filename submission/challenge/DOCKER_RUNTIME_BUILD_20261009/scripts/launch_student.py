#!/usr/bin/env python3
"""Launch the packaged Student with an explicit trained-model selection."""
from __future__ import annotations
import argparse, json, os, subprocess, sys, time
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[2]
SOURCE = PACKAGE / "02_源码与部署" / "source"
MODELS = {
    "full_int8": "03_训练与模型/A2模型与量化/models/full_int8/student_int8.onnx",
    "fp32": "03_训练与模型/A2模型与量化/models/student_v0_fp32_candidate.onnx",
    "mixed_top3": "03_训练与模型/A2模型与量化/models/mixed_precision_top3/student_int8_mixed_top3.onnx",
}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=MODELS, default="full_int8")
    parser.add_argument("--mode", choices=["http", "serve", "describe"], default="http")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8100)
    parser.add_argument("--input", help="JSONL ModelRequest input for --mode serve")
    parser.add_argument("--image-root", help="same RGB staging folder used by CARLA runner")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    model = PACKAGE / MODELS[args.variant]
    logs = PACKAGE / "runs" / args.variant
    command = [sys.executable]
    if args.mode == "http":
        command += ["-m", "challenge.hil.carla.student_action_service", "--onnx", str(model),
                    "--host", args.host, "--port", str(args.port), "--infer-response", "plan",
                    "--log-dir", str(logs), "--image-dir", str(logs / "images")]
        if args.image_root:
            command += ["--image-root", str(Path(args.image_root).resolve())]
    else:
        command += ["-m", "challenge.runtime.student_x86", "--model", str(model),
                    "--precision", "fp32" if args.variant == "fp32" else "int8",
                    "--" + args.mode]
    if args.dry_run:
        print(json.dumps({"cwd": str(SOURCE), "model": str(model), "command": command}, ensure_ascii=False, indent=2))
        return 0
    if not model.is_file():
        parser.error("packaged model not found: " + str(model))
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SOURCE) + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONIOENCODING"] = "utf-8"
    if args.mode == "serve" and args.input:
        records = []
        for line in Path(args.input).read_text(encoding="utf-8-sig").splitlines():
            if not line.strip():
                continue
            request = json.loads(line)
            request = dict(request.get("model_request", request))
            if request.get("rgb_ref"):
                image = Path(request["rgb_ref"])
                if not image.is_absolute():
                    image = SOURCE / image
                if not image.is_file():
                    raise FileNotFoundError("RGB file missing: " + str(image))
                request["rgb_ref"] = str(image.resolve())
            now = time.monotonic_ns()
            request["created_at_ns"] = now
            request["deadline_ns"] = now + 5_000_000_000
            records.append(json.dumps(request, ensure_ascii=False))
        return subprocess.run(command, cwd=SOURCE, env=env,
                              input="\n".join(records) + "\n", text=True, encoding="utf-8").returncode
    return subprocess.run(command, cwd=SOURCE, env=env).returncode

if __name__ == "__main__":
    raise SystemExit(main())
