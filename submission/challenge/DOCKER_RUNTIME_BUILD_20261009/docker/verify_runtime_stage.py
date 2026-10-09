#!/usr/bin/env python3
"""Verify runtime-only dependencies without pretending private models exist."""
import importlib
from importlib.metadata import version
import json
import platform

from verify_runtime import CORE, EXTRAS, MODULES


def main():
    if platform.python_version() != "3.10.12":
        raise RuntimeError("Expected OE baseline Python 3.10.12; got " + platform.python_version())
    actual = {}
    for name, pinned in {**CORE, **EXTRAS}.items():
        actual[name] = version(name)
        if actual[name] != pinned:
            raise RuntimeError(f"{name}: expected {pinned}, got {actual[name]}")
        importlib.import_module(MODULES.get(name, name))
    actual["PyYAML"] = version("PyYAML")
    if not (6 <= int(actual["PyYAML"].split(".")[0]) < 7):
        raise RuntimeError("Expected PyYAML >=6,<7")
    importlib.import_module("yaml")
    print(json.dumps({
        "status": "RUNTIME_STAGE_VERIFIED_WITHOUT_MODEL_FILES",
        "python": platform.python_version(), "packages": actual,
        "PyYAML_exact_baseline": "NOT_RECORDED",
        "private_model_files_included": False,
        "final_student_image_built": False, "model_inference_run": False,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
