"""Structured preflight for interfaces, Qwen, CARLA and local dependencies."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import PackageNotFoundError, version as package_version
import json
from pathlib import Path
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from integration.qwen_profiles import (
    PRODUCTION_QWEN_ARTIFACT_SHA256,
    PRODUCTION_QWEN_MODEL,
    PRODUCTION_QWEN_PROFILE,
    PRODUCTION_QWEN_REVISION,
)
from .interface_registry import INTERFACE_NAMES, InterfaceRegistry


ROOT = Path(__file__).resolve().parents[1]


def _http_json(url: str, timeout_s: float) -> tuple[bool, dict[str, Any] | None, str]:
    try:
        with urlopen(url, timeout=timeout_s) as response:
            return True, json.loads(response.read()), "HTTP_OK"
    except HTTPError as error:
        try:
            payload = json.loads(error.read())
        except Exception:
            payload = None
        return False, payload, f"HTTP_{error.code}"
    except (URLError, TimeoutError, json.JSONDecodeError) as error:
        return False, None, f"{type(error).__name__}: {error}"


def _interfaces() -> dict[str, Any]:
    registry = InterfaceRegistry()
    records = []
    for name in sorted(INTERFACE_NAMES):
        schema_path = ROOT / "interfaces" / f"{name}.schema.json"
        example_path = ROOT / "interfaces" / "examples" / f"{name}.json"
        payload = json.loads(example_path.read_text(encoding="utf-8"))
        registry.validate(name, payload)
        records.append({
            "name": name,
            "schema": str(schema_path.relative_to(ROOT)),
            "sha256": hashlib.sha256(schema_path.read_bytes()).hexdigest(),
            "example_valid": True,
        })
    return {"status": "PASS", "interfaces": records}


def _dependencies() -> dict[str, Any]:
    modules = ("carla", "numpy", "PIL", "onnxruntime", "jsonschema", "torch", "transformers")
    distributions = {
        "carla": "carla",
        "numpy": "numpy",
        "PIL": "Pillow",
        "onnxruntime": "onnxruntime-gpu",
        "jsonschema": "jsonschema",
        "torch": "torch",
        "transformers": "transformers",
    }
    result = {}
    for module in modules:
        try:
            __import__(module)
            try:
                installed_version = package_version(distributions[module])
            except PackageNotFoundError:
                installed_version = None
            result[module] = {"available": True, "version": installed_version}
        except Exception as error:
            result[module] = {"available": False, "error": f"{type(error).__name__}: {error}"}
    required = ("carla", "numpy", "PIL", "onnxruntime", "jsonschema")
    return {
        "status": "PASS" if all(result[name]["available"] for name in required) else "FAIL",
        "modules": result,
    }


def _carla(host: str, port: int, timeout_s: float) -> dict[str, Any]:
    try:
        import carla
        client = carla.Client(host, port)
        client.set_timeout(timeout_s)
        world = client.get_world()
        return {
            "status": "PASS",
            "host": host,
            "port": port,
            "map": world.get_map().name,
            "actors": len(world.get_actors()),
        }
    except Exception as error:
        return {
            "status": "UNAVAILABLE",
            "host": host,
            "port": port,
            "error": f"{type(error).__name__}: {error}",
        }


def run_healthcheck(
    *,
    qwen_url: str,
    carla_host: str,
    carla_port: int,
    timeout_s: float,
    require_qwen: bool,
    require_carla: bool,
    expected_qwen_model: str = PRODUCTION_QWEN_MODEL,
    expected_qwen_revision: str = PRODUCTION_QWEN_REVISION,
    expected_qwen_artifact_sha256: str = PRODUCTION_QWEN_ARTIFACT_SHA256,
    expected_qwen_mode: str = "planner_v2",
) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    try:
        checks["interfaces"] = _interfaces()
    except Exception as error:
        checks["interfaces"] = {"status": "FAIL", "error": f"{type(error).__name__}: {error}"}
    checks["dependencies"] = _dependencies()
    ok, payload, reason = _http_json(qwen_url.rstrip("/") + "/health", timeout_s)
    checks["qwen"] = payload or {"status": "UNAVAILABLE", "reason": reason}
    checks["qwen"]["http_reachable"] = ok or payload is not None
    checks["qwen"]["http_result"] = reason
    qwen_contract = {
        "http_reachable": bool(checks["qwen"]["http_reachable"]),
        "status_ready": checks["qwen"].get("status") == "READY",
        "production_ready": checks["qwen"].get("production_ready") is True,
        "model_exact": checks["qwen"].get("model_id") == expected_qwen_model,
        "revision_exact": (
            checks["qwen"].get("model_revision") == expected_qwen_revision
        ),
        "artifact_exact": (
            checks["qwen"].get("artifact_sha256")
            == expected_qwen_artifact_sha256
        ),
        "planner_mode": checks["qwen"].get("qwen_mode") == expected_qwen_mode,
    }
    checks["qwen"]["contract"] = qwen_contract
    checks["carla"] = _carla(carla_host, carla_port, timeout_s)
    failures = []
    if checks["interfaces"]["status"] != "PASS":
        failures.append("interfaces")
    if checks["dependencies"]["status"] != "PASS":
        failures.append("dependencies")
    if require_qwen:
        failures.extend(
            f"qwen_{name}"
            for name, passed in qwen_contract.items()
            if not passed
        )
    if require_carla and checks["carla"]["status"] != "PASS":
        failures.append("carla")
    return {
        "schema_version": "1.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if not failures else "FAIL",
        "required": {
            "qwen": require_qwen,
            "carla": require_carla,
            "qwen_contract": {
                "profile": PRODUCTION_QWEN_PROFILE,
                "model": expected_qwen_model,
                "revision": expected_qwen_revision,
                "artifact_sha256": expected_qwen_artifact_sha256,
                "mode": expected_qwen_mode,
            },
        },
        "failed_checks": failures,
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qwen-url", default="http://127.0.0.1:8765")
    parser.add_argument("--expected-qwen-model", default=PRODUCTION_QWEN_MODEL)
    parser.add_argument(
        "--expected-qwen-revision",
        default=PRODUCTION_QWEN_REVISION,
    )
    parser.add_argument(
        "--expected-qwen-artifact-sha256",
        default=PRODUCTION_QWEN_ARTIFACT_SHA256,
    )
    parser.add_argument(
        "--expected-qwen-mode",
        choices=("atomic_v1", "planner_v2"),
        default="planner_v2",
    )
    parser.add_argument("--carla-host", default="127.0.0.1")
    parser.add_argument("--carla-port", type=int, default=2000)
    parser.add_argument("--timeout-s", type=float, default=3.0)
    parser.add_argument("--require-qwen", action="store_true")
    parser.add_argument("--require-carla", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run_healthcheck(
        qwen_url=args.qwen_url,
        carla_host=args.carla_host,
        carla_port=args.carla_port,
        timeout_s=args.timeout_s,
        require_qwen=args.require_qwen,
        require_carla=args.require_carla,
        expected_qwen_model=args.expected_qwen_model,
        expected_qwen_revision=args.expected_qwen_revision,
        expected_qwen_artifact_sha256=args.expected_qwen_artifact_sha256,
        expected_qwen_mode=args.expected_qwen_mode,
    )
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
