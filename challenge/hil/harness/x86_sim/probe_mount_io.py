"""Measure whether the dataset is being read through a Windows-drive mount.

Reading the same JPEG from ``/mnt/d`` (a Windows drive bind-mounted into the
container) costs orders of magnitude more than reading it from the container's
own filesystem, which silently inflates any latency measured inside Docker on
Windows. Run this before trusting an in-container latency number.

Usage (inside the image): python3 probe_mount_io.py [<jpg_glob>] [<sample_count>]
"""
import glob
import shutil
import time
from pathlib import Path

from PIL import Image


def bench(paths: list[str], label: str) -> dict:
    t0 = time.perf_counter()
    for path in paths:
        Path(path).read_bytes()
    read_ms = (time.perf_counter() - t0) * 1000 / len(paths)

    t0 = time.perf_counter()
    for path in paths:
        with Image.open(path) as image:
            image = image.convert("RGB")
            image.thumbnail((224, 224), Image.Resampling.BILINEAR)
    decode_ms = (time.perf_counter() - t0) * 1000 / len(paths)
    print(f"{label:<30} read={read_ms:8.3f} ms  decode+resize={decode_ms:8.3f} ms")
    return {"read_ms": round(read_ms, 4), "decode_resize_ms": round(decode_ms, 4)}


def main() -> int:
    pattern = "/repo/challenge/hil/frozen/d2_v1_1_val/rgb/*.jpg"
    count = 20
    import sys
    if len(sys.argv) > 1:
        pattern = sys.argv[1]
    if len(sys.argv) > 2:
        count = int(sys.argv[2])

    cases = sorted(glob.glob(pattern))[:count]
    if not cases:
        print(f"no files matched {pattern}")
        return 1
    local_dir = Path("/tmp/rgbprobe")
    local_dir.mkdir(parents=True, exist_ok=True)
    local = []
    for index, path in enumerate(cases):
        target = local_dir / f"{index}.jpg"
        shutil.copyfile(path, target)
        local.append(str(target))

    import json
    report = {"sample_count": len(cases), "source": pattern,
              "mounted": bench(cases, "mounted (Windows drive)"),
              "container_local": bench(local, "container-local")}
    report["ratio"] = {
        "read": round(report["mounted"]["read_ms"] / max(report["container_local"]["read_ms"], 1e-6), 1),
        "decode_resize": round(report["mounted"]["decode_resize_ms"] / max(report["container_local"]["decode_resize_ms"], 1e-6), 1),
    }
    print(json.dumps(report["ratio"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
