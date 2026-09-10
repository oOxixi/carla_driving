"""Byte-level fingerprints for the Teacher/Student planner boundary."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from runtime.interface_registry import InterfaceRegistry


FROZEN_CONTRACT_SHA256 = {
    "model_request": "7e68bc0d43ea2a37643c0dbf846766202b7f206190475d6b917471ffcd1a4ccf",
    "maneuver_plan": "6fb4c94c73b493be107cda3abef64033efdec88918887a4ae0e66120aa72b0d7",
}


def canonical_schema_sha256(path: str | Path) -> str:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def assert_frozen_contracts(registry: InterfaceRegistry) -> None:
    for name, expected in FROZEN_CONTRACT_SHA256.items():
        path = Path(registry.root) / f"{name}.schema.json"
        actual = canonical_schema_sha256(path)
        if actual != expected:
            raise RuntimeError(
                f"frozen {name} contract changed: {actual} != {expected}; "
                "create a versioned A1 contract update before loading a backend"
            )


__all__ = ["FROZEN_CONTRACT_SHA256", "assert_frozen_contracts", "canonical_schema_sha256"]
