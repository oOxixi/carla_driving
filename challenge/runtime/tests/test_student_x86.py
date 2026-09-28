from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from challenge.hil.tensors import dump_tensors_for_request


ROOT = Path(__file__).resolve().parents[3]
MODEL = ROOT / "challenge" / "student_v0_fp32.onnx"
REQUESTS = ROOT / "challenge" / "dataset" / "smoke_v0" / "data" / "smoke_valid.jsonl"


def load_request(index: int = 0) -> dict:
    rows = REQUESTS.read_text(encoding="utf-8").splitlines()
    return json.loads(rows[index])["model_request"]


def run_runtime(*args: str, input_text: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "challenge.runtime.student_x86",
            "--model",
            str(MODEL),
            *args,
        ],
        cwd=ROOT,
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )


def test_describe_returns_bound_model_identity() -> None:
    result = run_runtime("--describe")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert len(payload["git_sha"]) == 40
    assert len(payload["model_sha256"]) == 64
    assert payload["model_id"] == "student-v0-r3-fp32"
    assert payload["precision"] == "fp32"
    assert payload["batch"] == 1
    assert payload["input_shapes"]["rgb"] == [1, 3, 224, 224]


def test_describe_overrides_resident_mode_for_contract_driver() -> None:
    result = run_runtime("--serve", "--describe")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["model_id"] == "student-v0-r3-fp32"


def test_trace_contains_strictly_increasing_required_stages() -> None:
    request = load_request()
    result = run_runtime(
        "--serve",
        "--trace",
        input_text=json.dumps(request, ensure_ascii=False) + "\n",
    )

    assert result.returncode == 0, result.stderr
    plan = json.loads(result.stdout)
    expected = [
        "input_arrival",
        "preprocess_end",
        "packing_end",
        "inference_start",
        "inference_end",
        "postprocess_end",
        "adapter_end",
        "plan_ready",
    ]
    trace = plan["trace"]
    assert list(trace) == expected
    values = list(trace.values())
    assert all(isinstance(value, int) for value in values)
    assert all(left < right for left, right in zip(values, values[1:]))


def test_trace_does_not_change_plan_fields() -> None:
    request = load_request()
    input_text = json.dumps(request, ensure_ascii=False) + "\n"

    plain = run_runtime("--serve", input_text=input_text)
    traced = run_runtime("--serve", "--trace", input_text=input_text)

    assert plain.returncode == 0, plain.stderr
    assert traced.returncode == 0, traced.stderr
    plain_plan = json.loads(plain.stdout)
    traced_plan = json.loads(traced.stdout)
    traced_plan.pop("trace")
    assert traced_plan == plain_plan


def test_model_only_returns_all_output_checksums(tmp_path: Path) -> None:
    request = load_request()
    dump_dir = tmp_path / "tensor_dump"
    dump_tensors_for_request(ROOT, request, dump_dir, case_id="x86-test")

    result = run_runtime(
        "--model-only",
        "--input",
        str(dump_dir),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "OK"
    assert set(payload["outputs"]) == {
        "plan_length_logits",
        "behavior_logits",
        "target_pointer_logits",
        "target_lane_logits",
        "target_speed_mps",
        "completion_type_logits",
        "on_failure_logits",
        "confidence",
        "requires_confirmation_logits",
        "replan_condition_logits",
    }


def test_resident_mode_handles_two_requests() -> None:
    requests = [load_request(0), load_request(1)]
    input_text = "".join(
        json.dumps(request, ensure_ascii=False) + "\n"
        for request in requests
    )

    result = run_runtime("--serve", input_text=input_text)

    assert result.returncode == 0, result.stderr
    plans = [json.loads(line) for line in result.stdout.splitlines()]
    assert [plan["request_id"] for plan in plans] == [
        request["request_id"] for request in requests
    ]
