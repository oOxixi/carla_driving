#!/usr/bin/env python3
"""ModelRequest JSONL -> CPU preprocessor -> resident hbDNN/UCP -> CPU adapter.

This bridge deliberately imports the supplied production preprocessor/adapter.
No simulated logits, no CPU inference fallback.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

import numpy as np
import torch

SOURCE = Path(__file__).resolve().parent.parent / "source"
sys.path.insert(0, str(SOURCE))
from challenge.student.preprocess import StudentPreprocessor
from challenge.planner.student_adapter import StudentPlanAdapter

INPUTS = {"rgb": (1,3,224,224), "text_tokens": (1,32), "targets": (1,8,14), "state": (1,64)}
OUTPUTS = {
    "plan_length_logits": (1,4), "behavior_logits": (1,4,14),
    "target_pointer_logits": (1,4,9), "target_lane_logits": (1,4,6),
    "target_speed_mps": (1,4), "completion_type_logits": (1,4,8),
    "on_failure_logits": (1,4,4), "confidence": (1,1),
    "requires_confirmation_logits": (1,1), "replan_condition_logits": (1,7),
}

def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def prepare(request: dict, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    # Preserve training behavior: a missing rgb_ref produces a zero image.
    tensors = StudentPreprocessor()(request).as_tuple()
    for (name, shape), tensor in zip(INPUTS.items(), tensors):
        array = tensor.detach().cpu().numpy().astype("<f4", copy=False)
        if array.shape != shape or not np.isfinite(array).all():
            raise ValueError(f"Invalid preprocessed tensor: {name}")
        np.ascontiguousarray(array).tofile(destination / f"{name}.f32")
    (destination / "request.json").write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")

def load_outputs(source: Path) -> dict:
    outputs = {}
    for name, shape in OUTPUTS.items():
        array = np.fromfile(source / f"{name}.f32", dtype="<f4")
        if array.size != int(np.prod(shape)) or not np.isfinite(array).all():
            raise ValueError(f"Invalid SDK output: {name}")
        outputs[name] = torch.from_numpy(array.reshape(shape).copy())
    return outputs

def decode(request: dict, source: Path, model_id: str) -> dict:
    return StudentPlanAdapter(model_id=model_id).decode(request, load_outputs(source))

def command(args, mode: str) -> list[str]:
    result = [str(Path(args.worker).resolve()), str(Path(args.model).resolve()), mode]
    if args.model_name:
        result.append(args.model_name)
    return result

def read_record(proc, expected: str) -> str:
    # Some SDK versions emit diagnostics to stdout. Keep these diagnostics off
    # the public ManeuverPlan JSONL channel without interpreting them as results.
    for line in proc.stdout:
        value = line.strip()
        if value == expected or value.startswith(expected + "\t"):
            return value
        print(f"SDK: {value}", file=sys.stderr, flush=True)
    raise RuntimeError(f"SDK worker exited before {expected}; see stderr")

def serve(args) -> None:
    # One in-flight request per worker. CPU tensors and SDK allocations are not
    # concurrently reused. The model and UCP buffers stay resident until EOF.
    with tempfile.TemporaryDirectory(prefix="student-hbdnn-", dir=args.work_dir) as temp:
        root = Path(temp).resolve()
        if any(c in str(root) for c in "\t\r\n"):
            raise ValueError("Worker directories cannot contain tabs/newlines")
        proc = subprocess.Popen(command(args, "--worker"), stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, text=True, bufsize=1)
        try:
            if read_record(proc, "READY") != "READY":
                raise RuntimeError("SDK worker failed to initialize; see stderr")
            for line in sys.stdin:
                if not line.strip():
                    continue
                request = json.loads(line)
                marks = {"input_arrival": time.perf_counter_ns()}
                prepare(request, root / "input")
                marks["preprocess_end"] = time.perf_counter_ns()
                marks["packing_end"] = marks["preprocess_end"]
                # Worker returns the actual InferV2 -> WaitTaskDone interval.
                # Cross-process steady-clock epochs need not match Python's;
                # never splice the C++ absolute timestamps into Python trace.
                marks["inference_start"] = time.perf_counter_ns()
                proc.stdin.write(f"RUN\t{root / 'input'}\t{root / 'output'}\n")
                proc.stdin.flush()
                status = read_record(proc, "OK").split("\t")
                marks["inference_end"] = time.perf_counter_ns()
                if len(status) != 3 or status[0] != "OK":
                    raise RuntimeError(f"SDK inference failed: {status}; see stderr")
                start_ns, end_ns = map(int, status[1:])
                outputs = load_outputs(root / "output")
                marks["postprocess_end"] = time.perf_counter_ns()
                plan = StudentPlanAdapter(model_id=args.model_id).decode(request, outputs)
                marks["adapter_end"] = time.perf_counter_ns()
                marks["plan_ready"] = time.perf_counter_ns()
                if args.trace:
                    plan["trace"] = marks
                if args.metrics:
                    print(json.dumps({"request_id": request["request_id"],
                        "backend": "hbDNNInferV2/UCP", "model_only_ms": (end_ns-start_ns)/1e6,
                        "planner_e2e_ms": (marks["plan_ready"]-marks["input_arrival"])/1e6,
                        "includes_file_transport_in_e2e": True}), file=sys.stderr, flush=True)
                print(json.dumps(plan, ensure_ascii=False, separators=(",", ":")), flush=True)
        finally:
            if proc.poll() is None:
                try:
                    proc.stdin.write("QUIT\n"); proc.stdin.flush()
                    proc.wait(timeout=5)
                except (BrokenPipeError, subprocess.TimeoutExpired):
                    proc.kill(); proc.wait()

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", default=str(Path(__file__).parent / "build_arm" / "student_hbdnn"))
    parser.add_argument("--model")
    parser.add_argument("--model-name")
    parser.add_argument("--model-id", default="student-v0-v3-nash-p-hbm")
    parser.add_argument("--work-dir", help="existing writable temporary root; default OS temp")
    parser.add_argument("--trace", action="store_true")
    parser.add_argument("--metrics", action="store_true", help="metrics JSONL on stderr")
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--serve", action="store_true")
    modes.add_argument("--describe", action="store_true")
    modes.add_argument("--prepare", metavar="REQUEST_JSON")
    modes.add_argument("--decode", metavar="REQUEST_JSON")
    parser.add_argument("--tensor-dir", help="directory for --prepare / --decode")
    args = parser.parse_args()
    torch.set_num_threads(1)
    if args.prepare or args.decode:
        if not args.tensor_dir:
            parser.error("--prepare/--decode requires --tensor-dir")
        request = json.loads(Path(args.prepare or args.decode).read_text(encoding="utf-8-sig"))
        if args.prepare:
            prepare(request, Path(args.tensor_dir))
        else:
            print(json.dumps(decode(request, Path(args.tensor_dir), args.model_id), ensure_ascii=False))
        return
    if not args.model:
        parser.error("--serve/--describe requires --model MODEL.hbm")
    if sys.byteorder != "little":
        parser.error("SDK bridge requires little-endian CPU")
    if args.describe:
        result = subprocess.run(command(args, "--describe"), check=True, capture_output=True, text=True)
        lines = [line for line in result.stdout.splitlines() if line.startswith('{"backend":')]
        if len(lines) != 1:
            raise RuntimeError("SDK describe did not return one tensor metadata record")
        identity = json.loads(lines[0])
        identity.update(model_sha256=digest(Path(args.model)), model_id=args.model_id,
                        march="nash-p", openexplorer_version="3.9.1", hbdk_version="4.11.11",
                        horizon_tc_ui_version="3.5.16", batch=1)
        print(json.dumps(identity, ensure_ascii=False))
    else:
        serve(args)

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"student_board: {exc}", file=sys.stderr)
        raise SystemExit(1)
