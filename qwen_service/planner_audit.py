"""Opt-in adapter evidence, deliberately outside the strict plan response schema."""
from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Any, Mapping


class PlannerAuditLog:
    """Append adapter evidence without turning an audit disk error into braking.

    Records may contain user instructions and target IDs. Enable only in an
    access-controlled artifact directory; no credentials or image bytes belong
    here. Adapter success does NOT mean service validation or execution success.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Fail deployment early when the configured destination is unwritable.
        with self.path.open("a", encoding="utf-8"):
            pass
        self._lock = Lock()
        self.write_errors = 0
        self.last_error: str | None = None

    def append(self, record: Mapping[str, Any]) -> None:
        with self._lock:
            try:
                line = json.dumps(dict(record), ensure_ascii=False, allow_nan=False)
                with self.path.open("a", encoding="utf-8") as stream:
                    stream.write(line + "\n")
            except (OSError, TypeError, ValueError) as error:
                self.write_errors += 1
                self.last_error = f"{type(error).__name__}: {error}"

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {"enabled": True, "path": str(self.path),
                    "write_errors": self.write_errors, "last_error": self.last_error}


def summarize_choice_audit(records: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Describe recorded choice constraints, never infer causal model benefit."""
    selected = [r for r in records if r.get("record_type") == "qwen_choice_adapter_audit"]
    returned = [r for r in selected if r.get("status") == "ADAPTER_RETURNED"]
    counts = [len(r["candidate_codes"]) for r in returned if "candidate_codes" in r]
    single = sum(count == 1 for count in counts)
    return {
        "scope": "ADAPTER_ONLY_NOT_EXECUTION_OR_CAUSAL_BENEFIT",
        "requests": len(selected), "adapter_returned": len(returned),
        "errors": len(selected) - len(returned),
        "single_candidate_requests": single,
        "single_candidate_fraction": single / len(counts) if counts else None,
        "multiple_candidate_requests": sum(count > 1 for count in counts),
        "post_model_override_requests": sum(bool(r.get("overrides")) for r in returned),
        "image_sent_requests": sum(r.get("image_sent") is True for r in selected),
    }
