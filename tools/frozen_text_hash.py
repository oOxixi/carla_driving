"""Stable checksums for frozen, text-only validation artifacts."""
from __future__ import annotations

import hashlib
from pathlib import Path


def canonical_crlf_bytes(raw: bytes) -> bytes:
    """Return text bytes with every newline represented as CRLF.

    Frozen benchmark and RTX 5070 manifests were originally published from a
    Windows checkout.  Normalizing before hashing preserves those published
    digests while making verification independent of checkout policy.
    """

    normalized = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return normalized.replace(b"\n", b"\r\n")


def frozen_text_sha256(path: Path) -> str:
    return hashlib.sha256(canonical_crlf_bytes(Path(path).read_bytes())).hexdigest()


__all__ = ["canonical_crlf_bytes", "frozen_text_sha256"]
