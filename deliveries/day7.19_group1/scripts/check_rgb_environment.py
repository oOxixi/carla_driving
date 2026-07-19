from __future__ import annotations

import importlib
import json
import sys

modules = ["carla", "numpy", "cv2", "onnxruntime"]
result = {"python": sys.version, "modules": {}}
for name in modules:
    try:
        module = importlib.import_module(name)
        result["modules"][name] = {
            "ok": True,
            "version": getattr(module, "__version__", "unknown"),
            "path": getattr(module, "__file__", "unknown"),
        }
    except Exception as exc:
        result["modules"][name] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

try:
    import onnxruntime as ort
    result["onnxruntime_providers"] = ort.get_available_providers()
except Exception:
    pass

print(json.dumps(result, ensure_ascii=False, indent=2))
