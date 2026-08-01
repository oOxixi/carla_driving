from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "voice_group" / "MODEL_MANIFEST.json"


def main() -> int:
    spec = json.loads(MANIFEST.read_text(encoding="utf-8"))
    failures: list[str] = []
    for adapter in spec["adapters"]:
        path = ROOT / "voice_group" / adapter["path"]
        if not path.is_file():
            failures.append(f"missing: {path}")
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        size = path.stat().st_size
        ok = digest == adapter["sha256"] and size == adapter["bytes"]
        print(f"{'PASS' if ok else 'FAIL'} {adapter['path']} {size} {digest}")
        if not ok:
            failures.append(adapter["path"])
    if failures:
        print("weight verification failed:", ", ".join(failures))
        return 1
    print("all voice weights match MODEL_MANIFEST.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
