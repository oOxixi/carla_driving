"""Human-readable, versioned summary for each A3 training run."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence


def write_training_report(
    path: str | Path,
    summary: Mapping[str, Any],
    history: Sequence[Mapping[str, Any]],
) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    last_validation = history[-1].get("validation", {}) if history else {}
    lines = [
        "# A3 Training Run",
        "",
        f"- Git SHA: `{summary.get('git_sha', 'UNKNOWN')}`",
        f"- Teacher SHA/model: `{summary.get('teacher_git_sha')}` / `{summary.get('teacher_model_id')}`",
        f"- Student: `{summary.get('model_id')}`",
        f"- Dataset: `{summary.get('dataset_version')}`",
        f"- Config: `{summary.get('config_id')}`; seed `{summary.get('seed')}`",
        f"- Smoke only: `{summary.get('smoke_only')}`; integration gate only: `{summary.get('integration_smoke_only')}`",
        f"- Train/Validation records: `{summary.get('train_samples')}` / `{summary.get('validation_samples')}`",
        f"- Epochs/updates: `{summary.get('epochs_completed')}` / `{summary.get('global_step')}`",
        f"- Best checkpoint SHA-256: `{summary.get('best_checkpoint_sha256')}`",
        f"- Candidate weights SHA-256: `{summary.get('candidate_weights_sha256')}`",
        f"- Candidate gate status: `{summary.get('candidate_gate_status')}`",
        f"- Validation hard cases: `{summary.get('hard_case_count')}`",
        "",
        "## Last validation",
        "",
    ]
    for name, value in sorted(last_validation.items()):
        lines.append(f"- {name}: `{_format(value)}`")
    lines.extend([
        "",
        "Smoke and integration-gate values prove pipeline health only. They are not",
        "competition accuracy and must not be used to tune against frozen Test data.",
        "",
    ])
    temporary = destination.with_name(destination.name + ".tmp")
    temporary.write_text("\n".join(lines), encoding="utf-8")
    temporary.replace(destination)
    return destination


def _format(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


__all__ = ["write_training_report"]
