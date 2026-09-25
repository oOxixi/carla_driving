"""Convert B3 dump-tensors .npy inputs into raw float32 .bin files.

Usage: python3 make_bins.py <case_dir> <out_dir>
The tensor order follows the case manifest (rgb, text_tokens, targets, state).
"""
import json
import os
import sys

import numpy as np


def main() -> int:
    case_dir, out_dir = sys.argv[1], sys.argv[2]
    with open(os.path.join(case_dir, "manifest.json"), "r", encoding="utf-8") as fh:
        manifest = json.load(fh)
    order = manifest.get("tensor_order") or ["rgb", "text_tokens", "targets", "state"]
    os.makedirs(out_dir, exist_ok=True)
    for name in order:
        arr = np.load(os.path.join(case_dir, f"{name}.npy")).astype(np.float32)
        path = os.path.join(out_dir, f"{name}.bin")
        arr.tofile(path)
        print(f"{name}: shape={arr.shape} dtype={arr.dtype} -> {path} ({os.path.getsize(path)} B)")
    with open(os.path.join(out_dir, "order.txt"), "w", encoding="utf-8") as fh:
        fh.write(",".join(order) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
