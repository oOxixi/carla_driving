"""Offline adapter audit and structured Qwen shadow generation. No CARLA calls."""
from __future__ import annotations

import argparse
import copy
from collections.abc import Iterator
import hashlib
import json
import math
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from integration.evidence_provenance import collect_provenance
from integration.qwen_profiles import (
    PRODUCTION_QWEN_MODEL, PRODUCTION_QWEN_REVISION, PRODUCTION_QWEN_ARTIFACT_SHA256,
)
from qwen_service.planner_audit import PlannerAuditLog, summarize_choice_audit
from qwen_service.service import VllmQwenPlannerBackend
from qwen_service.shadow_planner import StructuredShadowPlanner


def read_records(path: Path) -> list[dict]:
    records = []
    with path.open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            record = json.loads(line)
            if not isinstance(record, dict):
                raise ValueError(f"line {number} must contain an object")
            records.append(record)
    if not records:
        raise ValueError("input contains no records")
    return records


def extract_requests(path: Path, *, limit: int) -> list[dict]:
    """Freeze real submitted requests from runner JSONL, not reconstructed hints."""
    records = []
    seen = set()
    with path.open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            record = json.loads(line)
            if not isinstance(record, dict):
                raise ValueError(f"line {number} must contain an object")
            payload = record.get("payload", {})
            orchestration = payload.get("orchestration", {}) if isinstance(payload, dict) else {}
            orchestration = orchestration if isinstance(orchestration, dict) else {}
            request = record.get("request") or orchestration.get("model_request")
            if request is None and record.get("schema_version") == "1.0" and "source_text" in record:
                request = record
            if not isinstance(request, dict) or not request.get("request_id"):
                continue
            request_id = request["request_id"]
            if request_id in seen:
                continue
            from runtime.interface_registry import InterfaceRegistry
            frozen = InterfaceRegistry().validate("model_request", request)
            records.append({"request": frozen, "source_line": number})
            seen.add(request_id)
            if len(records) >= limit:
                break
    if not records:
        raise ValueError("no complete ModelRequest found; no synthetic reconstruction performed")
    return records


def run_shadow(records: list[dict], planner: StructuredShadowPlanner, *, visions: list[str]) -> Iterator[dict]:
    for index, record in enumerate(records):
        request = record.get("request", record)
        for vision in dict.fromkeys(visions):
            started = time.perf_counter_ns()
            try:
                report = planner.generate(request, vision=vision)
            except Exception as error:
                # Transport/schema errors are evidence, never a rule-generated plan.
                report = {"scope": "OFFLINE_SHADOW_NOT_EXECUTABLE_NOT_GATE", "vision": vision,
                          "validation": "ERROR", "error_type": type(error).__name__,
                          "error": str(error)}
            report.update(input_index=index, elapsed_ms=(time.perf_counter_ns() - started) / 1e6)
            yield report


def run_choice(records: list[dict], transport: VllmQwenPlannerBackend, *, visions: list[str]) -> Iterator[dict]:
    """Replay the unchanged production adapter without a service or actuator."""
    for index, record in enumerate(records):
        for vision in dict.fromkeys(visions):
            request = copy.deepcopy(record.get("request", record))
            started = time.perf_counter_ns()
            report = {"scope": "OFFLINE_CHOICE_REPLAY_NOT_EXECUTION_OR_GATE", "vision": vision,
                      "input_index": index, "request_id": request.get("request_id")}
            try:
                if vision == "no_rgb":
                    request["rgb_ref"] = None
                elif vision != "original":
                    raise ValueError("vision must be original or no_rgb")
                elif transport._resolve_image(request.get("rgb_ref")) is None:
                    raise ValueError("original vision requires an existing rgb_ref")
                report["adapter_plan"] = transport.infer(request)
                report["validation"] = "ADAPTER_RETURNED_NOT_VALIDATED"
            except Exception as error:
                report.update(validation="ERROR", error_type=type(error).__name__, error=str(error))
            report["elapsed_ms"] = (time.perf_counter_ns() - started) / 1e6
            yield report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("capture", "audit", "choice", "shadow"))
    parser.add_argument("--input", type=Path, required=True, help="private JSONL requests or adapter audits")
    parser.add_argument("--output-dir", type=Path, required=True, help="new artifact directory, never overwritten")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/v1")
    parser.add_argument("--image-root", type=Path)
    parser.add_argument("--vision", choices=("original", "no_rgb"), action="append")
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument("--shadow-format", choices=("full_json", "flag_sets_v1"), default="flag_sets_v1",
                        help="unique enum sets as true-key objects; original full JSON remains available")
    parser.add_argument("--timeout-s", type=float, default=120.0)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--health-url", default="http://127.0.0.1:18005/health",
                        help="pinned production adapter on the same host as vLLM")
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be positive")
    if not math.isfinite(args.timeout_s) or args.timeout_s <= 0:
        parser.error("--timeout-s must be finite and positive")
    if args.output_dir.exists():
        parser.error("--output-dir already exists; preserve evidence and choose a new directory")
    records = extract_requests(args.input, limit=args.limit) if args.mode == "capture" else read_records(args.input)
    selected = records if args.mode == "audit" else records[:args.limit]
    metadata = None
    if args.mode in {"choice", "shadow"}:
        from urllib.request import urlopen
        with urlopen(args.health_url, timeout=10) as response:
            metadata = json.load(response)
        for field, expected in (("model_id", PRODUCTION_QWEN_MODEL),
                                ("model_revision", PRODUCTION_QWEN_REVISION),
                                ("artifact_sha256", PRODUCTION_QWEN_ARTIFACT_SHA256),
                                ("status", "READY"), ("production_ready", True)):
            if metadata.get(field) != expected:
                raise ValueError(f"pinned Teacher health mismatch: {field}")
        # Health is independently recorded, not proof of arbitrary URL identity.
        # Pin endpoint host and model list as well; do not send to a remote model by accident.
        from urllib.parse import urlparse
        if urlparse(args.health_url).hostname != urlparse(args.base_url).hostname:
            raise ValueError("health and vLLM must be on the same explicitly configured host")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    manifest = {"scope": "OFFLINE_ONLY_NOT_FORMAL_GATE", "mode": args.mode,
                "status": "RUNNING",
                "input_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
                "selected_records": len(selected), "teacher_health": metadata,
                "base_url": args.base_url if args.mode in {"choice", "shadow"} else None,
                "provenance": collect_provenance(ROOT),
                "rgb_detector_activation_verified": False,
                "shadow_format": args.shadow_format, "max_tokens": args.max_tokens,
                "visions": args.vision or ["original", "no_rgb"],
                "causal_benefit_measured": False}
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.mode == "capture":
        with (args.output_dir / "requests.jsonl").open("x", encoding="utf-8") as stream:
            for record in selected:
                stream.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
        manifest["status"] = "COMPLETE"
        (args.output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"captured_requests": len(selected), "scope": "CAPTURE_ONLY_NO_MODEL_CALL"}))
        return 0
    if args.mode == "audit":
        summary = summarize_choice_audit(selected)
        (args.output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(summary, ensure_ascii=False))
        manifest["status"] = "COMPLETE"
        (args.output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0 if summary["requests"] else 1
    transport = VllmQwenPlannerBackend(base_url=args.base_url, model=PRODUCTION_QWEN_MODEL,
                                      image_root=args.image_root, timeout_s=args.timeout_s)
    try:
        served = {model.id for model in transport._client.models.list().data}
        if PRODUCTION_QWEN_MODEL not in served:
            raise ValueError("pinned Qwen3.5-2B not exposed by configured vLLM endpoint")
        reports = []
        visions = args.vision or ["original", "no_rgb"]
        if args.mode == "choice":
            transport.audit_log = PlannerAuditLog(args.output_dir / "choice_audit.jsonl")
            iterator = run_choice(selected, transport, visions=visions)
        else:
            iterator = run_shadow(selected, StructuredShadowPlanner(
                transport, max_tokens=args.max_tokens, wire_format=args.shadow_format), visions=visions)
        with (args.output_dir / f"{args.mode}_results.jsonl").open("x", encoding="utf-8") as stream:
            for report in iterator:
                stream.write(json.dumps(report, ensure_ascii=False, allow_nan=False) + "\n")
                stream.flush()
                reports.append(report)
    finally:
        transport.close()
    counts = {status: sum(r["validation"] == status for r in reports)
              for status in ("CONTRACT_PASS_ONLY", "ADAPTER_RETURNED_NOT_VALIDATED", "REJECTED", "ERROR")}
    summary = {"scope": "CONTRACT_VALIDITY_NOT_TASK_ACCURACY_OR_GATE", "counts": counts,
               "task_accuracy": "NOT_MEASURED", "ready_for_vehicle_execution": False}
    if args.mode == "choice":
        audit_path = args.output_dir / "choice_audit.jsonl"
        summary["adapter_audit"] = (
            summarize_choice_audit(read_records(audit_path)) if audit_path.stat().st_size else None
        )
    (args.output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    manifest["status"] = "COMPLETE"
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary))
    expected = "CONTRACT_PASS_ONLY" if args.mode == "shadow" else "ADAPTER_RETURNED_NOT_VALIDATED"
    return 0 if counts[expected] == len(reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
