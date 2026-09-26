"""Build hb_compile calibration dirs (one per model input) from tensor dumps.

`cal_data_dir` must list one directory per model input, and each directory must
hold the same number of samples in the same order.

Usage: python3 build_cal_dirs.py <dump_root> <cal_root> [limit]
"""
import os
import shutil
import sys

import numpy as np


def main() -> int:
    dump_root, cal_root = sys.argv[1], sys.argv[2]
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else 10 ** 6

    cases = sorted(d for d in os.listdir(dump_root)
                   if os.path.isdir(os.path.join(dump_root, d)))[:limit]
    if os.path.isdir(cal_root):
        shutil.rmtree(cal_root)
    for index, case in enumerate(cases):
        for name in ("rgb", "text_tokens", "targets", "state"):
            src = os.path.join(dump_root, case, f"{name}.npy")
            dst_dir = os.path.join(cal_root, name)
            os.makedirs(dst_dir, exist_ok=True)
            arr = np.load(src).astype(np.float32)
            np.save(os.path.join(dst_dir, f"sample_{index:04d}.npy"), arr)

    print(f"cases: {len(cases)}")
    for name in ("rgb", "text_tokens", "targets", "state"):
        files = sorted(os.listdir(os.path.join(cal_root, name)))
        shape = np.load(os.path.join(cal_root, name, files[0])).shape
        print(f"  {name:<12} {len(files)} files, per-sample shape {shape}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
