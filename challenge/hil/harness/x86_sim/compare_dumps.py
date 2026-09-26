"""Compare hrt_model_exec X86-simulation dumps against the ONNX reference.

The runtime stores every output row with the aligned stride reported by
`hrt_model_exec model_info` (e.g. 14 floats padded to 16), so the dumps must be
un-padded before comparing.

Usage:
    python3 compare_dumps.py <case_dir> <dump_dir> <model_info_log> <out_json>
"""
import json
import os
import re
import sys

import numpy as np
import onnxruntime as ort

ONNX = "/work/student/student_v0_fp32.onnx"


def cosine(a, b):
    a = np.asarray(a, dtype=np.float64).ravel()
    b = np.asarray(b, dtype=np.float64).ravel()
    n = np.linalg.norm(a) * np.linalg.norm(b)
    if n == 0:
        return float("nan")
    return float(np.dot(a, b) / n)


def parse_model_info(path):
    """Return [(name, shape, stride_bytes)] for every output tensor."""
    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
        text = fh.read()
    text = re.sub(r"\x1b\[[0-9;]*m", "", text)
    outputs = []
    for block in text.split("output[")[1:]:
        name = re.search(r"name:\s*(\S+)", block)
        shape = re.search(r"valid shape:\s*\(([^)]*)\)", block)
        stride = re.search(r"stride:\s*\(([^)]*)\)", block)
        if not (name and shape and stride):
            continue
        shape = tuple(int(x) for x in shape.group(1).split(","))
        stride = tuple(int(x) for x in stride.group(1).split(","))
        outputs.append((name.group(1), shape, stride))
    return outputs


def unpad(raw, shape, stride):
    """Undo the per-row stride padding of a dumped tensor."""
    row = shape[-1]
    # stride[-1] is the innermost (element) stride; the row pitch is stride[-2].
    if len(stride) >= 2:
        step = stride[-2] // raw.dtype.itemsize
    else:
        step = row
    rows = int(np.prod(shape[:-1])) if len(shape) > 1 else 1
    out = np.empty(rows * row, dtype=raw.dtype)
    for i in range(rows):
        out[i * row:(i + 1) * row] = raw[i * step:i * step + row]
    return out.reshape(shape)


def main() -> int:
    case_dir, dump_dir, info_log, out_json = sys.argv[1:5]
    info = parse_model_info(info_log)
    sess = ort.InferenceSession(ONNX, providers=["CPUExecutionProvider"])
    feed = {i.name: np.load(os.path.join(case_dir, f"{i.name}.npy")).astype(np.float32)
            for i in sess.get_inputs()}
    names = [o.name for o in sess.get_outputs()]
    ref = dict(zip(names, sess.run(names, feed)))

    report = {"case_dir": case_dir, "dump_dir": dump_dir, "outputs": {}}
    print(f"{'idx':<4}{'output':<32}{'shape':<16}{'raw':>8}{'cosine':>10}{'max_abs':>12}")
    for idx, (name, shape, stride) in enumerate(info):
        path = os.path.join(dump_dir, f"model_infer_output_{idx}_{name}.bin")
        raw = np.fromfile(path, dtype=np.float32)
        got = unpad(raw, shape, stride)
        r = ref[name].reshape(shape)
        cos = cosine(got, r)
        max_abs = float(np.max(np.abs(got - r)))
        report["outputs"][name] = {
            "index": idx,
            "shape": list(shape),
            "stride_bytes": list(stride),
            "dump_floats": int(raw.size),
            "valid_floats": int(got.size),
            "cosine": round(cos, 6),
            "max_abs_diff": round(max_abs, 6),
        }
        print(f"{idx:<4}{name:<32}{str(shape):<16}{raw.size:>8}{cos:>10.6f}{max_abs:>12.3e}")

    cosines = [v["cosine"] for v in report["outputs"].values()]
    report["min_cosine"] = round(float(min(cosines)), 6)
    report["mean_cosine"] = round(float(sum(cosines) / len(cosines)), 6)
    os.makedirs(os.path.dirname(out_json), exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)
    print(f"\nmin={report['min_cosine']} mean={report['mean_cosine']}")
    print(f"wrote {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
