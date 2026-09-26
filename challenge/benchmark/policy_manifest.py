"""Canonical B2 policy-manifest construction and hashing."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml


class PolicyManifestError(ValueError):
    """Raised when the B2 policy is not complete enough to sign."""


def load_benchmark_policy_config(
    path: str | Path,
) -> dict[str, Any]:
    config_path = Path(path)

    try:
        loaded = yaml.safe_load(
            config_path.read_text(encoding="utf-8")
        )
    except (OSError, yaml.YAMLError) as error:
        raise PolicyManifestError(
            f"cannot load benchmark policy config: {error}"
        ) from error

    if not isinstance(loaded, dict):
        raise PolicyManifestError(
            "benchmark policy config must be an object"
        )

    return loaded


def build_policy_manifest(
    config: Mapping[str, Any],
) -> dict[str, Any]:
    """
    Build a formal B2 policy manifest.

    This function intentionally refuses to sign a policy while B2 governance
    fields remain incomplete.
    """
    if not isinstance(config, Mapping):
        raise PolicyManifestError(
            "benchmark policy config must be an object"
        )

    formal = config.get("formal_policy")

    if not isinstance(formal, Mapping):
        raise PolicyManifestError(
            "formal policy is incomplete: formal_policy is missing"
        )

    if formal.get("status") != "FROZEN":
        raise PolicyManifestError(
            "formal policy is not frozen"
        )
    policy_version = formal.get("policy_version")
    slice_minimum_denominators = formal.get(
        "slice_minimum_denominators"
    )
    multi_run_merge_rule = formal.get(
        "multi_run_merge_rule"
    )

    missing: list[str] = []

    if not isinstance(policy_version, str) or not policy_version.strip():
        missing.append("policy_version")

    if not isinstance(
        slice_minimum_denominators,
        Mapping,
    ) or not slice_minimum_denominators:
        missing.append(
            "slice_minimum_denominators"
        )

    if (
        not isinstance(multi_run_merge_rule, str)
        or not multi_run_merge_rule.strip()
    ):
        missing.append("multi_run_merge_rule")

    if missing:
        raise PolicyManifestError(
            "formal policy is incomplete: "
            + ", ".join(missing)
        )

    metric_policy = _required_mapping(
        config,
        "gate_metric_policy",
    )
    gate = _required_mapping(
        config,
        "gate",
    )
    replay_transport = _required_mapping(
        config,
        "replay_transport",
    )
    case_policy = _required_mapping(
        config,
        "case_policy",
    )
    metrics = _required_mapping(
        config,
        "metrics",
    )

    manifest = {
        "schema_version": "1.0",
        "policy_version": policy_version.strip(),
        "purpose": _required_text(
            config.get("purpose"),
            "purpose",
        ),
        "metrics": dict(metrics),
        "gate": dict(gate),
        "gate_metric_policy": dict(
            metric_policy
        ),
        "case_policy": dict(
            case_policy
        ),
        "replay_transport": dict(
            replay_transport
        ),
        "slice_minimum_denominators": dict(
            slice_minimum_denominators
        ),
        "multi_run_merge_rule": (
            multi_run_merge_rule.strip()
        ),
    }

    return manifest


def canonical_policy_manifest_json(
    manifest: Mapping[str, Any],
) -> bytes:
    if not isinstance(manifest, Mapping) or not manifest:
        raise PolicyManifestError(
            "policy manifest must be a non-empty object"
        )

    try:
        encoded = json.dumps(
            dict(manifest),
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
    except (TypeError, ValueError) as error:
        raise PolicyManifestError(
            "policy manifest is not canonical JSON"
        ) from error

    return (encoded + "\n").encode("utf-8")


def policy_manifest_sha256(
    manifest: Mapping[str, Any],
) -> str:
    return hashlib.sha256(
        canonical_policy_manifest_json(
            manifest
        )
    ).hexdigest()


def write_policy_manifest(
    path: str | Path,
    manifest: Mapping[str, Any],
) -> str:
    destination = Path(path)
    payload = canonical_policy_manifest_json(
        manifest
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = destination.with_name(
        destination.name + ".tmp"
    )
    temporary.write_bytes(payload)
    temporary.replace(destination)

    return hashlib.sha256(payload).hexdigest()


def _required_mapping(
    config: Mapping[str, Any],
    field: str,
) -> Mapping[str, Any]:
    value = config.get(field)

    if not isinstance(value, Mapping):
        raise PolicyManifestError(
            f"{field} must be an object"
        )

    return value


def _required_text(
    value: Any,
    field: str,
) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PolicyManifestError(
            f"{field} must be a non-empty string"
        )

    return value.strip()


__all__ = [
    "PolicyManifestError",
    "build_policy_manifest",
    "canonical_policy_manifest_json",
    "load_benchmark_policy_config",
    "policy_manifest_sha256",
    "write_policy_manifest",
]