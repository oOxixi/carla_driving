#!/usr/bin/env python3
"""Fail on baseline drift; print actual package versions without model inference."""
import argparse
import importlib
from importlib.metadata import version
import json
from pathlib import Path
import platform

CORE = {"torch": "2.8.0+cpu", "onnxruntime": "1.19.0", "numpy": "1.23.0", "Pillow": "9.3.0"}
EXTRAS = {"jsonschema": "4.25.1", "psutil": "7.2.1"}
MODULES = {"Pillow": "PIL", "PyYAML": "yaml"}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", action="store_true")
    args = parser.parse_args()
    if platform.python_version() != "3.10.12":
        raise RuntimeError("Expected OE baseline Python 3.10.12; got " + platform.python_version())
    expected = dict(CORE)
    if not args.base:
        expected.update(EXTRAS)
    actual = {}
    for package, pinned in expected.items():
        actual[package] = version(package)
        if actual[package] != pinned:
            raise RuntimeError(f"{package}: expected {pinned}, got {actual[package]}; use matching OE v3.9.1 base")
        importlib.import_module(MODULES.get(package, package))
    if not args.base:
        actual["PyYAML"] = version("PyYAML")
        if not (6 <= int(actual["PyYAML"].split(".")[0]) < 7):
            raise RuntimeError("Expected PyYAML >=6,<7")
        importlib.import_module("yaml")
        package = Path(__file__).resolve().parents[2]
        for relative in (
            "03_训练与模型/A2模型与量化/models/full_int8/student_int8.onnx",
            "03_训练与模型/A2模型与量化/models/student_v0_fp32_candidate.onnx",
            "03_训练与模型/A2模型与量化/models/mixed_precision_top3/student_int8_mixed_top3.onnx",
        ):
            if not (package / relative).is_file():
                raise RuntimeError("Missing packaged model: " + relative)
    print(json.dumps({"status": "VERIFIED", "python": platform.python_version(),
        "packages": actual, "PyYAML_exact_baseline": "NOT_RECORDED",
        "model_inference_run": False}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
