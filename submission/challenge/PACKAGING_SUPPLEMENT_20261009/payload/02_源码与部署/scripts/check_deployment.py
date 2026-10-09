#!/usr/bin/env python3
"""Inspect deployment files/imports; never connect to CARLA or infer a model."""
from __future__ import annotations
import argparse
import hashlib
import importlib
import importlib.metadata
import json
from pathlib import Path
import sys

PACKAGE = Path(__file__).resolve().parents[2]
SOURCE = PACKAGE / "02_源码与部署/source"
MODULES = {
    "files": (),
    "student": ("numpy", "torch", "onnxruntime", "PIL", "jsonschema", "yaml", "challenge.hil.carla.student_action_service"),
    "controller": ("numpy", "carla", "pygame", "yaml", "integration.carla_runner"),
    "voice": ("torch", "torchaudio", "soundfile", "funasr", "modelscope", "peft", "safetensors", "faster_whisper", "opencc", "voice_group.pipeline"),
}

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=MODULES, default="files")
    args = parser.parse_args()
    sys.path.insert(0, str(SOURCE))
    errors = []
    matrix_path = SOURCE / "scenarios/acceptance_suite/matrix.json"
    total = 0
    try:
        matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
        total = len(matrix["scenarios"])
        if total != 83 or matrix["counts"]["total"] != 83:
            errors.append("acceptance matrix must contain the restored 83-scenario suite")
        for row in matrix["scenarios"]:
            if not (matrix_path.parent / row["path"]).is_file():
                errors.append("Missing acceptance scenario: " + row["path"])
    except (OSError, KeyError, ValueError) as exc:
        errors.append("Cannot read acceptance matrix: " + str(exc))
    for relative in (
        "config/driving_policy.json", "interfaces/model_request.schema.json",
        "scenarios/smoke/S01_set_speed_20.json", "scenarios/regression/REG_008_challenge_pedestrian.json",
        "scenarios/safety_D/D07_low_ttc_emergency_brake.json",
    ):
        if not (SOURCE / relative).is_file():
            errors.append("Missing runtime asset: " + relative)
    versions = {}
    for module in MODULES[args.profile]:
        try:
            imported = importlib.import_module(module)
            versions[module] = getattr(imported, "__version__", "imported")
        except Exception as exc:
            errors.append(f"{module}: {type(exc).__name__}: {exc}")
    if args.profile == "voice":
        weights = SOURCE / "voice_group/lora_dialect/adapter_model.safetensors"
        manifest = SOURCE / "voice_group/MODEL_MANIFEST.json"
        try:
            expected = json.loads(manifest.read_text(encoding="utf-8"))["adapters"][0]["sha256"]
            if not weights.is_file() or hashlib.sha256(weights.read_bytes()).hexdigest() != expected:
                errors.append("Voice LoRA missing or does not match MODEL_MANIFEST.json")
        except (OSError, KeyError, ValueError) as exc:
            errors.append("Cannot validate voice LoRA: " + str(exc))
    print(json.dumps({"status": "FAIL" if errors else "PASS", "profile": args.profile,
        "acceptance_scenario_count": total, "imported_versions": versions,
        "errors": errors, "model_inference_run": False, "carla_connection_attempted": False}, ensure_ascii=False, indent=2))
    return 1 if errors else 0

if __name__ == "__main__":
    raise SystemExit(main())
