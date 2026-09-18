"""Decode every A3 D2 Train/Val sample through A1's real four-modal packer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

import torch

from .a1_student import build_a1_input_packer
from .audit_d2_view import audit_view
from .dataset import DistillationDataset, load_jsonl, make_collate_fn


EXPECTED_SHAPES = {
    "rgb": (3, 224, 224),
    "text_tokens": (32,),
    "targets": (8, 14),
    "state": (64,),
}


def check_packed_batch(batch: Mapping[str, Any], expected_size: int) -> None:
    inputs = batch["model_inputs"]
    if set(inputs) != set(EXPECTED_SHAPES):
        raise ValueError(f"A1 modalities mismatch: {sorted(inputs)}")
    for name, shape in EXPECTED_SHAPES.items():
        value = inputs[name]
        if not torch.is_tensor(value) or tuple(value.shape) != (expected_size, *shape):
            raise ValueError(f"A1 {name} has wrong shape")
        if not torch.isfinite(value).all().item():
            raise ValueError(f"A1 {name} contains non-finite values")
    if batch["labels"]["step_mask"].shape != (expected_size, 4):
        raise ValueError("A3 step mask has wrong shape")


def validate_inputs(
    release_dir: Path,
    view_dir: Path,
    asset_root: Path,
    *,
    batch_size: int = 8,
    max_errors: int = 20,
) -> dict[str, Any]:
    if batch_size < 1 or max_errors < 1:
        raise ValueError("batch_size and max_errors must be positive")
    coverage = audit_view(release_dir, view_dir)
    collate = make_collate_fn(input_packer=build_a1_input_packer())
    summary: dict[str, Any] = {
        "status": "PASS",
        "view_manifest_sha256": coverage["view_manifest_sha256"],
        "batch_size": batch_size,
        "splits": {},
        "errors": [],
    }
    for split in ("train", "val"):
        rows = load_jsonl(view_dir / f"{split}.jsonl")
        dataset = DistillationDataset(rows, asset_root=asset_root, require_rgb=True)
        checked = batches = 0
        for start in range(0, len(dataset), batch_size):
            samples = []
            for index in range(start, min(start + batch_size, len(dataset))):
                try:
                    samples.append(dataset[index])
                except (OSError, KeyError, TypeError, ValueError) as error:
                    summary["errors"].append({
                        "split": split,
                        "sample_id": str(rows[index].get("sample_id")),
                        "reason": str(error),
                    })
            if samples:
                try:
                    check_packed_batch(collate(samples), len(samples))
                    checked += len(samples)
                    batches += 1
                except (OSError, KeyError, TypeError, ValueError, RuntimeError) as error:
                    summary["errors"].append({
                        "split": split,
                        "sample_ids": [item["sample_id"] for item in samples],
                        "reason": str(error),
                    })
            if len(summary["errors"]) >= max_errors:
                break
        summary["splits"][split] = {
            "expected_samples": len(dataset),
            "checked_samples": checked,
            "checked_batches": batches,
        }
        if len(summary["errors"]) >= max_errors:
            break
    if summary["errors"] or any(
        item["expected_samples"] != item["checked_samples"]
        for item in summary["splits"].values()
    ):
        summary["status"] = "FAIL"
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate every A3 D2 sample with A1 input packing")
    parser.add_argument("--release-dir", type=Path, default=Path("challenge/dataset/releases/d2_v1_1"))
    parser.add_argument("--view-dir", type=Path, default=Path("artifacts/a3_d2_v1_1_positive_view_v1"))
    parser.add_argument("--asset-root", type=Path, default=Path("."))
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--output", type=Path, default=Path("artifacts/a3_d2_prep/a1_full_input_check.json"))
    args = parser.parse_args()
    report = validate_inputs(
        args.release_dir, args.view_dir, args.asset_root, batch_size=args.batch_size,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
