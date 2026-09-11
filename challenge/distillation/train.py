"""Configuration-driven A3 distillation trainer.

The default configuration runs only the explicit D1 mock pipeline.  Production
training requires separate B1 train/validation manifests and an A1 model
factory; frozen Test data is intentionally not accepted by this entry point.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import importlib
import json
import math
from pathlib import Path
import random
import subprocess
from typing import Any, Mapping

import torch
from torch.utils.data import DataLoader
import yaml

from challenge.student import StudentModelConfig, StudentPlannerV0

from .class_balance import compute_class_weights
from .artifacts import export_candidate_weights
from .checkpoint import load_checkpoint, save_checkpoint, sha256_file
from .dataset import (
    DistillationDataset,
    build_mock_records,
    load_jsonl,
    make_collate_fn,
)
from .evaluate import evaluate, move_batch_to_device
from .hard_cases import collect_hard_cases, write_hard_case_bundle
from .label_encoder import DistillationLabelEncoder
from .losses import LossWeights, MultiHeadDistillationLoss
from .preflight import preflight_datasets, write_preflight_report
from .run_report import write_training_report
from .student_contract import (
    forward_student,
    validate_finite_gradients,
    validate_student_outputs,
)


def run_training(
    config: Mapping[str, Any],
    *,
    smoke: bool = False,
    output_dir_override: str | Path | None = None,
    resume_override: str | Path | None = None,
    integration_smoke: bool = False,
) -> dict[str, Any]:
    if smoke and integration_smoke:
        raise ValueError("mock smoke and production integration smoke are mutually exclusive")
    cfg = _validate_config(deepcopy(config))
    _validate_frozen_identities(cfg, integration_smoke=integration_smoke)
    if not smoke and not integration_smoke and _git_is_dirty():
        raise RuntimeError(
            "production A3 training requires a clean committed challenge worktree"
        )
    if integration_smoke:
        cfg["training"]["epochs"] = 1
        cfg["training"]["max_updates"] = min(
            2, int(cfg["training"].get("max_updates") or 2),
        )
    seed = int(cfg["seed"])
    _seed_everything(seed)
    device = _device(str(cfg["training"].get("device", "auto")))
    default_output = Path(cfg["output"]["directory"])
    if integration_smoke:
        default_output = default_output / "integration_gate"
    output_dir = Path(output_dir_override or default_output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    max_steps = int(cfg["contract"]["max_steps"])
    max_targets = int(cfg["contract"]["max_targets"])
    feature_dim = int(cfg["model"]["options"].get("feature_dim", 32))
    encoder = DistillationLabelEncoder(max_steps=max_steps, max_targets=max_targets)
    if not smoke:
        dataset_cfg = cfg["dataset"]
        if not dataset_cfg.get("train_path") or not dataset_cfg.get("val_path"):
            raise ValueError("production training requires separate train_path and val_path")
        expected_version = str(dataset_cfg["version"])
        if expected_version.startswith("PENDING_"):
            raise ValueError("replace dataset.version before production training")
        preflight = preflight_datasets(
            dataset_cfg.get("train_path"),
            dataset_cfg.get("val_path"),
            max_steps=max_steps,
            max_targets=max_targets,
            expected_version=expected_version,
            expected_teacher_git_sha=(
                str(cfg["teacher"]["git_sha"])
                if dataset_cfg.get("verify_teacher_identity") else None
            ),
            expected_teacher_model_id=(
                str(cfg["teacher"]["model_id"])
                if dataset_cfg.get("verify_teacher_identity") else None
            ),
            expected_teacher_model_revision=(
                str(cfg["teacher"]["model_revision"])
                if dataset_cfg.get("require_pinned_teacher_provenance") else None
            ),
            expected_teacher_artifact_fingerprint_sha256=(
                str(cfg["teacher"]["artifact_fingerprint_sha256"])
                if dataset_cfg.get("require_pinned_teacher_provenance") else None
            ),
            asset_root=dataset_cfg.get("asset_root"),
            require_rgb=bool(dataset_cfg.get("require_rgb", False)),
        )
        write_preflight_report(output_dir / "dataset_preflight.json", preflight)
        if not preflight["valid"]:
            first = preflight["errors"][0]["message"] if preflight["errors"] else "unknown"
            raise ValueError(
                f"dataset preflight failed with {preflight['error_count']} error(s): {first}"
            )
    train_records, val_records, dataset_version = _records(
        cfg, smoke=smoke, record_limit=50 if integration_smoke else None,
    )
    quarantined = _audit_quarantined_hard_cases(cfg, smoke=smoke)
    if quarantined:
        (output_dir / "quarantined_hard_cases_audit.json").write_text(
            json.dumps(_strict_json(quarantined), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    sample_weights = cfg["sampling"]["weights"]
    train_dataset = DistillationDataset(
        train_records, label_encoder=encoder, sample_weights=sample_weights,
        asset_root=cfg["dataset"].get("asset_root"),
        require_rgb=bool(cfg["dataset"].get("require_rgb", False)),
    )
    val_dataset = DistillationDataset(
        val_records, label_encoder=encoder, sample_weights=sample_weights,
        asset_root=cfg["dataset"].get("asset_root"),
        require_rgb=bool(cfg["dataset"].get("require_rgb", False)),
    )
    balance_cfg = cfg.get("class_balance", {})
    class_weights: dict[str, list[float]] = {}
    class_counts: dict[str, list[int]] = {}
    if bool(balance_cfg.get("enabled", False)):
        class_weights, class_counts = compute_class_weights(
            (train_dataset[index] for index in range(len(train_dataset))),
            heads=tuple(balance_cfg.get("heads", ("behavior",))),
            max_steps=max_steps,
            max_targets=max_targets,
            smoothing=float(balance_cfg.get("smoothing", 1.0)),
            max_weight=float(balance_cfg.get("max_weight", 5.0)),
        )
    input_packer = _build_input_packer(
        cfg.get("input"), max_steps=max_steps, max_targets=max_targets,
    )
    collate = make_collate_fn(feature_dim=feature_dim, input_packer=input_packer)
    generator = torch.Generator().manual_seed(seed)
    training = cfg["training"]
    train_loader = DataLoader(
        train_dataset,
        batch_size=int(training["batch_size"]),
        shuffle=True,
        num_workers=0,
        collate_fn=collate,
        generator=generator,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=int(training["batch_size"]),
        shuffle=False,
        num_workers=0,
        collate_fn=collate,
    )

    model = _build_model(cfg["model"], max_steps=max_steps, max_targets=max_targets)
    model.to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(training["learning_rate"]),
        weight_decay=float(training["weight_decay"]),
    )
    loss_fn = MultiHeadDistillationLoss(
        LossWeights.from_mapping(cfg["loss_weights"]),
        soft_alpha=float(cfg["distillation"].get("soft_alpha", 0.0)),
        temperature=float(cfg["distillation"].get("temperature", 1.0)),
        class_weights=class_weights,
    )

    metadata = {
        "git_sha": _git_sha(),
        "git_dirty": _git_is_dirty(),
        "teacher_git_sha": str(cfg["teacher"]["git_sha"]),
        "teacher_model_id": str(cfg["teacher"]["model_id"]),
        "teacher_model_revision": str(cfg["teacher"]["model_revision"]),
        "teacher_artifact_fingerprint_sha256": str(
            cfg["teacher"]["artifact_fingerprint_sha256"]
        ),
        "teacher_identity_policy": str(
            cfg["teacher"].get("identity_policy", "frozen_manifest")
        ),
        "model_id": str(cfg["model"]["model_id"]),
        "model_config_id": str(cfg["model"].get("config_id", cfg["config_id"])),
        "dataset_version": dataset_version,
        "config_id": str(cfg["config_id"]),
        "seed": seed,
        "smoke_only": bool(smoke),
        "integration_smoke_only": bool(integration_smoke),
        "class_balance": {
            "enabled": bool(class_weights),
            "counts": class_counts,
            "weights": class_weights,
        },
    }
    start_epoch = 0
    global_step = 0
    best_metric = -math.inf
    resume_path = resume_override or training.get("resume")
    if resume_path:
        restored = load_checkpoint(
            resume_path, model=model, optimizer=optimizer, map_location=device,
        )
        start_epoch = int(restored["epoch"]) + 1
        global_step = int(restored["global_step"])
        best_metric = float(restored["best_metric"])
        data_generator_state = restored.get("extra_state", {}).get("data_generator_state")
        if data_generator_state is not None:
            generator.set_state(data_generator_state.cpu())

    log_path = output_dir / "training.jsonl"
    best_path = output_dir / "student_fp32_best.pt"
    last_path = output_dir / "student_fp32_last.pt"
    epochs = int(training["epochs"])
    max_updates = int(training.get("max_updates", 0))
    selection_metric = str(training.get("selection_metric", "plan_sequence_accuracy"))
    if not resume_path and log_path.is_file():
        log_path.unlink()
    history: list[dict[str, Any]] = []
    for epoch in range(start_epoch, epochs):
        model.train()
        train_losses = []
        for batch in train_loader:
            moved = move_batch_to_device(batch, device)
            optimizer.zero_grad(set_to_none=True)
            outputs = forward_student(model, moved["model_inputs"])
            validate_student_outputs(outputs, moved["labels"], max_targets=max_targets)
            loss, _components = loss_fn(outputs, moved["labels"])
            if not torch.isfinite(loss):
                raise RuntimeError(f"non-finite training loss at step {global_step}")
            loss.backward()
            validate_finite_gradients(model)
            gradient_norm = torch.nn.utils.clip_grad_norm_(
                model.parameters(), float(training["gradient_clip_norm"]),
                error_if_nonfinite=True,
            )
            if not torch.isfinite(gradient_norm):
                raise RuntimeError(f"non-finite gradient norm at step {global_step}")
            optimizer.step()
            global_step += 1
            train_losses.append(float(loss.item()))
            if max_updates and global_step >= max_updates:
                break

        validation = evaluate(
            model, val_loader, loss_fn, device=device, max_targets=max_targets,
        )
        if selection_metric not in validation:
            raise ValueError(f"unknown selection metric: {selection_metric}")
        candidate = float(validation[selection_metric])
        entry = {
            "epoch": epoch,
            "global_step": global_step,
            "train_loss": sum(train_losses) / max(1, len(train_losses)),
            "validation": validation,
        }
        history.append(entry)
        with log_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(_strict_json(entry), ensure_ascii=False) + "\n")
        if math.isfinite(candidate) and candidate > best_metric:
            best_metric = candidate
            save_checkpoint(
                best_path,
                model=model,
                optimizer=optimizer,
                epoch=epoch,
                global_step=global_step,
                best_metric=best_metric,
                metadata=metadata,
                extra_state={"data_generator_state": generator.get_state()},
            )
        save_checkpoint(
            last_path,
            model=model,
            optimizer=optimizer,
            epoch=epoch,
            global_step=global_step,
            best_metric=best_metric,
            metadata=metadata,
            extra_state={"data_generator_state": generator.get_state()},
        )
        if max_updates and global_step >= max_updates:
            break

    if not best_path.is_file():
        raise RuntimeError("training produced no finite validation candidate")
    load_checkpoint(best_path, model=model, map_location=device)
    hard_rows = []
    model.eval()
    with torch.no_grad():
        for batch in val_loader:
            moved = move_batch_to_device(batch, device)
            hard_rows.extend(collect_hard_cases(
                batch, _validated_forward(
                    model, moved, max_targets=max_targets,
                ), split="validation",
            ))
    hard_case_summary = write_hard_case_bundle(output_dir / "hard_cases", hard_rows)

    best_checkpoint_sha = sha256_file(best_path)
    candidate = export_candidate_weights(
        output_dir,
        model=model,
        identity=metadata,
        validation=history[-1]["validation"] if history else {},
        checkpoint_sha256=best_checkpoint_sha,
    )
    summary = {
        **metadata,
        "device": str(device),
        "train_samples": len(train_dataset),
        "validation_samples": len(val_dataset),
        "quarantined_hard_case_count": int(quarantined.get("count", 0)),
        "quarantined_hard_case_reasons": quarantined.get("reasons", {}),
        "epochs_completed": len(history),
        "global_step": global_step,
        "selection_metric": selection_metric,
        "best_metric": best_metric,
        "best_checkpoint": str(best_path),
        "best_checkpoint_sha256": best_checkpoint_sha,
        "candidate_weights": candidate["weights_path"],
        "candidate_weights_sha256": candidate["weights_sha256"],
        "candidate_gate_status": candidate["gate_status"],
        "hard_case_count": len(hard_rows),
        "hard_case_categories": hard_case_summary["category_counts"],
        "last_epoch": history[-1] if history else None,
    }
    (output_dir / "training_summary.json").write_text(
        json.dumps(_strict_json(summary), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_training_report(output_dir / "training_report.md", summary, history)
    return summary


def _validated_forward(
    model: torch.nn.Module,
    batch: Mapping[str, Any],
    *,
    max_targets: int,
) -> Mapping[str, torch.Tensor]:
    outputs = forward_student(model, batch["model_inputs"])
    validate_student_outputs(outputs, batch["labels"], max_targets=max_targets)
    return outputs


def _records(
    cfg: Mapping[str, Any], *, smoke: bool, record_limit: int | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
    dataset = cfg["dataset"]
    if smoke:
        records = build_mock_records(int(dataset.get("mock_samples", 256)))
        split = max(1, int(len(records) * float(dataset.get("mock_train_fraction", 0.8))))
        split = min(split, len(records) - 1)
        return records[:split], records[split:], "mock-v1"
    train_path, val_path = dataset.get("train_path"), dataset.get("val_path")
    if not train_path or not val_path:
        raise ValueError("production training requires separate train_path and val_path")
    for value in (str(train_path), str(val_path)):
        if "test" in Path(value).name.lower() or "frozen" in Path(value).name.lower():
            raise ValueError("the A3 trainer refuses frozen Test manifests")
    train_records, val_records = load_jsonl(train_path), load_jsonl(val_path)
    if record_limit is not None:
        train_records = train_records[:record_limit]
        val_records = val_records[:record_limit]
    return train_records, val_records, str(dataset["version"])


def _audit_quarantined_hard_cases(
    cfg: Mapping[str, Any], *, smoke: bool,
) -> dict[str, Any]:
    path = cfg["dataset"].get("hard_cases_path")
    if smoke or not path:
        return {}
    records = load_jsonl(path)
    reasons: dict[str, int] = {}
    sample_ids: list[str] = []
    train_ids = {
        str(record.get("sample_id"))
        for manifest in (cfg["dataset"]["train_path"], cfg["dataset"]["val_path"])
        for record in load_jsonl(manifest)
    }
    for record in records:
        sample_id = str(record.get("sample_id", "")).strip()
        if not sample_id:
            raise ValueError("quarantined hard case is missing sample_id")
        if sample_id in train_ids:
            raise ValueError(f"quarantined hard case leaked into Train/Val: {sample_id}")
        if str(record.get("dataset_version")) != str(cfg["dataset"]["version"]):
            raise ValueError(f"hard case dataset version mismatch: {sample_id}")
        metadata = record.get("metadata", {})
        plan = record.get("teacher_plan", {})
        if metadata.get("teacher_git_sha") != cfg["teacher"]["git_sha"]:
            raise ValueError(f"hard case Teacher SHA mismatch: {sample_id}")
        if (metadata.get("teacher_model_id") or plan.get("model_id")) != cfg["teacher"]["model_id"]:
            raise ValueError(f"hard case Teacher model mismatch: {sample_id}")
        policy = record.get("training_policy", {})
        if policy.get("train_eligible") is not False:
            raise ValueError(f"hard case must be excluded from ordinary training: {sample_id}")
        if policy.get("policy_class") != "QUARANTINED_HARD_CASE":
            raise ValueError(f"hard case policy_class is invalid: {sample_id}")
        if policy.get("closed_loop_success") is not False:
            raise ValueError(f"hard case must retain failed closed-loop evidence: {sample_id}")
        # Resolve and hash-check the packaged image without adding this record to training.
        DistillationDataset(
            [record], asset_root=cfg["dataset"].get("asset_root"), require_rgb=True,
        )[0]
        for reason in policy.get("quarantine_reasons", ()):
            key = str(reason)
            reasons[key] = reasons.get(key, 0) + 1
        sample_ids.append(sample_id)
    return {"count": len(records), "sample_ids": sample_ids, "reasons": reasons}


def _build_model(
    config: Mapping[str, Any], *, max_steps: int, max_targets: int,
) -> torch.nn.Module:
    module_name, separator, attribute = str(config["factory"]).partition(":")
    if not separator:
        raise ValueError("model.factory must use module:callable syntax")
    factory = getattr(importlib.import_module(module_name), attribute)
    options = dict(config.get("options", {}))
    options.update({"max_steps": max_steps, "max_targets": max_targets})
    model = factory(options)
    if not isinstance(model, torch.nn.Module):
        raise TypeError("model factory must return torch.nn.Module")
    return model


def _build_input_packer(
    config: Mapping[str, Any] | None,
    *,
    max_steps: int,
    max_targets: int,
) -> Any:
    if not config:
        return None
    module_name, separator, attribute = str(config["factory"]).partition(":")
    if not separator:
        raise ValueError("input.factory must use module:callable syntax")
    factory = getattr(importlib.import_module(module_name), attribute)
    options = dict(config.get("options", {}))
    options.update({"max_steps": max_steps, "max_targets": max_targets})
    packer = factory(options)
    if not callable(packer):
        raise TypeError("input factory must return a callable batch packer")
    return packer


def _validate_config(value: Mapping[str, Any]) -> dict[str, Any]:
    cfg = dict(value)
    required = {
        "config_id", "seed", "teacher", "contract", "dataset", "model",
        "training", "sampling", "loss_weights", "distillation", "output",
    }
    missing = required.difference(cfg)
    if missing:
        raise ValueError("missing training config keys: " + ", ".join(sorted(missing)))
    if int(cfg["contract"]["max_steps"]) != 4:
        raise ValueError("ManeuverPlan V2 Student contract requires max_steps=4")
    if int(cfg["contract"]["max_targets"]) < 1:
        raise ValueError("max_targets must be positive")
    if int(cfg["training"]["batch_size"]) < 1 or int(cfg["training"]["epochs"]) < 1:
        raise ValueError("batch_size and epochs must be positive")
    return cfg


def _validate_frozen_identities(
    cfg: Mapping[str, Any], *, integration_smoke: bool = False,
) -> None:
    policy = str(cfg["teacher"].get("identity_policy", "frozen_manifest"))
    if policy not in {"frozen_manifest", "legacy_unpinned_smoke"}:
        raise ValueError(f"unsupported teacher identity_policy: {policy}")
    manifest_path = Path(__file__).resolve().parents[1] / "teacher_baseline_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_teacher = {
        "git_sha": manifest["git_sha"],
        "model_id": manifest["model_id"],
        "model_revision": manifest["model_revision"],
        "artifact_fingerprint_sha256": manifest["artifact_fingerprint_sha256"],
    }
    actual_teacher = {
        key: cfg["teacher"].get(key) for key in expected_teacher
    }
    if policy == "legacy_unpinned_smoke":
        if not integration_smoke:
            raise ValueError(
                "legacy unpinned Teacher data is allowed only for integration smoke"
            )
        if actual_teacher["git_sha"] != expected_teacher["git_sha"]:
            raise ValueError("legacy Smoke Teacher git_sha does not match frozen baseline")
        if actual_teacher["model_id"] != expected_teacher["model_id"]:
            raise ValueError("legacy Smoke Teacher model_id does not match frozen baseline")
        if actual_teacher["model_revision"] != "NOT_RECORDED_BY_B1_SMOKE":
            raise ValueError("legacy Smoke must not claim a model revision")
        if actual_teacher["artifact_fingerprint_sha256"] != "NOT_RECORDED_BY_B1_SMOKE":
            raise ValueError("legacy Smoke must not claim an artifact fingerprint")
    elif actual_teacher != expected_teacher:
        raise ValueError(
            "teacher identity does not match challenge/teacher_baseline_manifest.json"
        )
    if cfg["model"].get("model_id") == StudentPlannerV0.model_id:
        if cfg["model"].get("config_id") != StudentModelConfig().config_id:
            raise ValueError("Student config_id does not match A1 V0 r3")


def _device(value: str) -> torch.device:
    normalized = value.lower()
    if normalized == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    device = torch.device(value)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is unavailable")
    return device


def _seed_everything(seed: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "UNKNOWN"


def _git_is_dirty() -> bool:
    try:
        return bool(subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            text=True, stderr=subprocess.DEVNULL,
        ).strip())
    except (OSError, subprocess.CalledProcessError):
        return True


def _strict_json(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: _strict_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_strict_json(item) for item in value]
    return value


def _load_config(path: str | Path) -> dict[str, Any]:
    value = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("training config must be a YAML object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="challenge/distillation/train_config.yaml")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--smoke", action="store_true", help="contract-valid mock pipeline")
    mode.add_argument(
        "--integration-smoke", action="store_true",
        help="preflight all real records, then train at most 50+50 records for two updates",
    )
    parser.add_argument("--output-dir")
    parser.add_argument("--resume")
    args = parser.parse_args()
    summary = run_training(
        _load_config(args.config), smoke=args.smoke,
        output_dir_override=args.output_dir, resume_override=args.resume,
        integration_smoke=args.integration_smoke,
    )
    print(json.dumps(_strict_json(summary), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
