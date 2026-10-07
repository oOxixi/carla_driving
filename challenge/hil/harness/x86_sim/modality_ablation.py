"""Zero-one-out modality ablation for the Student ONNX (fusion-effectiveness proxy).

Replaces one input modality at a time with its zero value, decodes the plan with
the repository's own adapter, and reports how often the decoded behaviour changes
and how much the logits move. This is the closest measurable proxy for the
"multimodal fusion effectiveness" scoring item when the official benchmark and
labelled data are unavailable.

Caveat: zeroing is not the same as removing evidence -- a black image is still an
image and zero tokens are still a token sequence -- so the numbers describe
sensitivity to the zero value, not a modality's true contribution.

Usage:
    python3 modality_ablation.py --onnx <model.onnx> --dumps <dump_dir> \
        --frozen <snapshot_dir> [--limit N] [--out <json>]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import onnxruntime as ort
import torch

from challenge.planner.student_adapter import StudentPlanAdapter


def cosine(a, b) -> float:
    a = np.asarray(a, dtype=np.float64).ravel()
    b = np.asarray(b, dtype=np.float64).ravel()
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    return float(abs(np.dot(a, b) / norm)) if norm else float("nan")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--onnx", required=True)
    parser.add_argument("--dumps", required=True)
    parser.add_argument("--frozen", required=True)
    parser.add_argument("--limit", type=int, default=150)
    parser.add_argument("--out")
    args = parser.parse_args()

    session = ort.InferenceSession(args.onnx, providers=["CPUExecutionProvider"])
    names = [i.name for i in session.get_inputs()]
    outputs = [o.name for o in session.get_outputs()]
    adapter = StudentPlanAdapter()

    index = json.loads((Path(args.dumps) / "dump_index.json").read_text(encoding="utf-8"))
    frozen = {}
    for line in (Path(args.frozen) / "cases.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            case = json.loads(line)
            frozen[case["case_id"]] = case

    def infer(feed):
        return {name: torch.from_numpy(array) for name, array in zip(outputs, session.run(outputs, feed))}

    stats = {m: {"behaviour_changed": 0, "step_count_changed": 0, "cos_min_sum": 0.0,
                 "rel_change_sum": 0.0, "argmax_flip": 0} for m in names}
    cases = 0
    for entry in index["dumps"][:args.limit]:
        case = frozen.get(entry["case_id"])
        if case is None:
            continue
        directory = Path(entry["directory"])
        feed = {m: np.load(directory / f"{m}.npy").astype(np.float32) for m in names}
        baseline = infer(feed)
        base_behaviour = [s.get("behavior") for s in adapter.decode(case["request"], baseline)["steps"]]
        cases += 1
        for modality in names:
            ablated = dict(feed)
            ablated[modality] = np.zeros_like(feed[modality])
            after = infer(ablated)
            behaviour = [s.get("behavior") for s in adapter.decode(case["request"], after)["steps"]]
            row = stats[modality]
            if behaviour != base_behaviour:
                row["behaviour_changed"] += 1
            if len(behaviour) != len(base_behaviour):
                row["step_count_changed"] += 1
            row["cos_min_sum"] += min(cosine(baseline[k], after[k]) for k in outputs)
            base_head = np.asarray(baseline["behavior_logits"], dtype=np.float64).ravel()
            after_head = np.asarray(after["behavior_logits"], dtype=np.float64).ravel()
            row["rel_change_sum"] += float(
                np.linalg.norm(base_head - after_head) / (np.linalg.norm(base_head) + 1e-12))
            if int(np.argmax(base_head)) != int(np.argmax(after_head)):
                row["argmax_flip"] += 1

    report = {
        "model": args.onnx, "cohort": Path(args.frozen).name, "cases": cases,
        "modalities": {
            m: {
                "behaviour_changed": f"{r['behaviour_changed']}/{cases}",
                "step_count_changed": r["step_count_changed"],
                "worst_head_cosine_mean": round(r["cos_min_sum"] / max(cases, 1), 6),
                "behaviour_rel_change_mean": round(r["rel_change_sum"] / max(cases, 1), 6),
                "behaviour_argmax_flip": f"{r['argmax_flip']}/{cases}",
            }
            for m, r in stats.items()
        },
        "caveat": "zeroing is not removing evidence; X86 numerical diagnostic, not an accuracy result",
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
