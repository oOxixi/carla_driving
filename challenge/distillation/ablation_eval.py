"""Read-only A3 Validation modality ablations for an existing FP32 checkpoint."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

import torch
from torch.utils.data import DataLoader
import yaml

from .a1_student import build_a1_input_packer, build_a1_student
from .audit_d2_view import audit_view
from .checkpoint import load_checkpoint, sha256_file
from .dataset import DistillationDataset, load_jsonl, make_collate_fn
from .evaluate import evaluate
from .losses import LossWeights, MultiHeadDistillationLoss


MODALITIES = ("rgb", "text_tokens", "targets", "state")


def masked_batches(batches: Iterable[dict[str, Any]], modality: str) -> Iterable[dict[str, Any]]:
    if modality not in MODALITIES:
        raise ValueError(f"unknown modality: {modality}")
    for batch in batches:
        yield {
            **batch,
            "model_inputs": {
                **batch["model_inputs"],
                modality: torch.zeros_like(batch["model_inputs"][modality]),
            },
        }


def run_ablation(config_path: Path, output_dir: Path) -> dict[str, Any]:
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    dataset_cfg = cfg["dataset"]
    audit = audit_view(
        Path(dataset_cfg["release_manifest_path"]).parent,
        Path(dataset_cfg["view_manifest_path"]).parent,
    )
    summary_path = output_dir / "training_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if (
        summary.get("git_dirty") is not False
        or summary.get("integration_smoke_only") is not False
        or summary.get("smoke_only") is not False
        or summary.get("candidate_gate_status") != "PENDING_A3_FP32_GATE"
        or summary.get("a3_view_manifest_sha256") != audit["view_manifest_sha256"]
        or summary.get("release_manifest_sha256") != audit["release_manifest_sha256"]
        or summary.get("config_id") != cfg["config_id"]
    ):
        raise ValueError("checkpoint is not a matching clean formal A3 candidate")
    checkpoint = output_dir / "student_fp32_best.pt"
    if sha256_file(checkpoint) != summary["best_checkpoint_sha256"]:
        raise ValueError("best checkpoint hash mismatch")

    model = build_a1_student({"max_steps": 4, "max_targets": 8})
    load_checkpoint(checkpoint, model=model, map_location="cpu", restore_rng=False)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    records = load_jsonl(dataset_cfg["val_path"])
    dataset = DistillationDataset(
        records, asset_root=dataset_cfg["asset_root"], require_rgb=True,
        sample_weights=cfg["sampling"]["weights"],
    )
    collate = make_collate_fn(input_packer=build_a1_input_packer())
    loader = DataLoader(
        dataset, batch_size=int(cfg["training"]["batch_size"]), shuffle=False,
        num_workers=0, collate_fn=collate,
    )
    loss_fn = MultiHeadDistillationLoss(LossWeights.from_mapping(cfg["loss_weights"]))
    results = {
        "full": evaluate(model, loader, loss_fn, device=device, max_targets=8),
    }
    for modality in MODALITIES:
        results[f"zero_{modality}"] = evaluate(
            model, masked_batches(loader, modality), loss_fn,
            device=device, max_targets=8,
        )
    report = {
        "status": "DIAGNOSTIC_ONLY",
        "view_manifest_sha256": audit["view_manifest_sha256"],
        "checkpoint_sha256": summary["best_checkpoint_sha256"],
        "validation_samples": len(dataset),
        "device": str(device),
        "metrics": {
            condition: {
                key: value if value == value else None
                for key, value in metrics.items()
            }
            for condition, metrics in results.items()
        },
        "note": (
            "Zero-input ablation is a sensitivity check on the same template-heavy "
            "Validation set; it is not a causal importance score or an unseen-scenario gate."
        ),
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate A3 FP32 modality sensitivity on Val")
    parser.add_argument("--config", type=Path, default=Path("challenge/distillation/d2_v1_1_formal_config.yaml"))
    parser.add_argument("--run-dir", type=Path, default=Path("artifacts/challenge/distillation/d2_v1_1_fp32_baseline_v1"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/a3_d2_prep/modality_ablation.json"))
    args = parser.parse_args()
    report = run_ablation(args.config, args.run_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    compact = {
        key: {
            name: value for name, value in metrics.items()
            if name in {"plan_sequence_accuracy", "behavior_accuracy", "target_speed_mae"}
        }
        for key, metrics in report["metrics"].items()
    }
    print(json.dumps(compact, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
