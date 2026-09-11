"""Reproducible checkpoint save/resume helpers."""

from __future__ import annotations

import hashlib
from pathlib import Path
import random
from typing import Any, Mapping

import torch


def save_checkpoint(
    path: str | Path,
    *,
    model: torch.nn.Module,
    optimizer: torch.optim.Optimizer,
    epoch: int,
    global_step: int,
    best_metric: float,
    metadata: Mapping[str, Any],
    scheduler: Any = None,
    extra_state: Mapping[str, Any] | None = None,
) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".tmp")
    payload = {
        "format_version": 1,
        "model_state": model.state_dict(),
        "optimizer_state": optimizer.state_dict(),
        "scheduler_state": None if scheduler is None else scheduler.state_dict(),
        "epoch": int(epoch),
        "global_step": int(global_step),
        "best_metric": float(best_metric),
        "metadata": dict(metadata),
        "extra_state": dict(extra_state or {}),
        "rng": {
            "python": random.getstate(),
            "torch": torch.get_rng_state(),
            "torch_cuda": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else None,
        },
    }
    torch.save(payload, temporary)
    temporary.replace(destination)
    return destination


def load_checkpoint(
    path: str | Path,
    *,
    model: torch.nn.Module,
    optimizer: torch.optim.Optimizer | None = None,
    scheduler: Any = None,
    map_location: str | torch.device = "cpu",
) -> dict[str, Any]:
    source = Path(path)
    payload = torch.load(source, map_location=map_location, weights_only=False)
    if payload.get("format_version") != 1:
        raise ValueError("unsupported checkpoint format")
    model.load_state_dict(payload["model_state"])
    if optimizer is not None:
        optimizer.load_state_dict(payload["optimizer_state"])
    if scheduler is not None and payload.get("scheduler_state") is not None:
        scheduler.load_state_dict(payload["scheduler_state"])
    rng = payload.get("rng", {})
    if rng.get("python") is not None:
        random.setstate(rng["python"])
    if rng.get("torch") is not None:
        torch.set_rng_state(rng["torch"])
    if torch.cuda.is_available() and rng.get("torch_cuda") is not None:
        torch.cuda.set_rng_state_all(rng["torch_cuda"])
    return payload


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


__all__ = ["load_checkpoint", "save_checkpoint", "sha256_file"]
