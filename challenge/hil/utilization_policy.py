"""Intake for the frozen heterogeneous-utilization formula (B2/A4 owned).

The Gate says "异构算力利用率 ≥80%，使用 B2 固定公式".  B3 does not own that
formula and will not invent one, so this module does two things and nothing more:

* it validates a policy file against the fields a formula needs before it can be
  applied (numerator source, denominator source, sampling window, probe scope,
  exclusivity, signer) and records its identity;
* it computes the ratio **only** when the policy names fields that B3 actually
  sampled, so a policy that talks about unsigned counters cannot silently turn
  into a number.

Without a policy the report keeps saying `NOT_MEASURED`/no conclusion, exactly as
before: absence of the formula is not a licence to guess one.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .identity import sha256_file


POLICY_SCHEMA_VERSION = "1.0"

#: Every field a policy must declare before B3 will apply it.
REQUIRED_FIELDS: tuple[str, ...] = (
    "policy_id",
    "metric_name",
    "numerator_source",
    "denominator_source",
    "sampling_window",
    "probe_scope",
    "exclusive_use",
    "signer",
)

#: Sample fields B3 can actually read out of `utilization_raw.csv`, so a policy
#: may name them as its numerator/denominator.
AVAILABLE_SAMPLE_FIELDS: tuple[str, ...] = (
    "cpu_percent",
    "bpu_percent",
    "ddr_bandwidth_gbps",
)


@dataclass(frozen=True, slots=True)
class UtilizationPolicy:
    raw: Mapping[str, Any]
    path: str
    sha256: str

    @property
    def policy_id(self) -> str:
        return str(self.raw.get("policy_id", ""))

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": POLICY_SCHEMA_VERSION,
            "policy_id": self.policy_id,
            "metric_name": self.raw.get("metric_name"),
            "numerator_source": self.raw.get("numerator_source"),
            "denominator_source": self.raw.get("denominator_source"),
            "sampling_window": self.raw.get("sampling_window"),
            "probe_scope": self.raw.get("probe_scope"),
            "exclusive_use": self.raw.get("exclusive_use"),
            "signer": self.raw.get("signer"),
            "policy_path": self.path,
            "policy_sha256": self.sha256,
            "loaded_at_utc": datetime.now(timezone.utc).isoformat(),
        }


def load_policy(path: str | Path) -> UtilizationPolicy:
    """Read and validate a policy file; raise when anything required is missing."""
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("utilization policy must be a JSON object")
    missing = [
        name
        for name in REQUIRED_FIELDS
        if payload.get(name) in (None, "", [], {})
    ]
    if missing:
        raise ValueError(f"utilization policy is missing: {missing}")
    return UtilizationPolicy(
        raw=dict(payload),
        path=str(source.resolve()),
        sha256=sha256_file(source),
    )


def apply_policy(
    policy: UtilizationPolicy | None,
    *,
    samples: Mapping[str, float | None] | None,
    sample_count: int | None = None,
) -> dict[str, Any]:
    """Compute the ratio when the policy's sources are measured fields.

    Returns a status block the report can print verbatim.  `NOT_APPLICABLE`,
    `POLICY_NOT_PROVIDED` and `FORMULA_NOT_EVALUABLE` are different states and
    none of them is a pass.
    """
    if policy is None:
        return {
            "status": "POLICY_NOT_PROVIDED",
            "detail": (
                "B2/A4 尚未提供固定的异构利用率公式；本报告只给原始采样值，不给结论行。"
            ),
        }
    samples = samples or {}
    numerator = str(policy.raw.get("numerator_source"))
    denominator = str(policy.raw.get("denominator_source"))
    unknown = [
        name
        for name in (numerator, denominator)
        if name not in AVAILABLE_SAMPLE_FIELDS
    ]
    if unknown:
        return {
            "status": "FORMULA_NOT_EVALUABLE",
            "detail": (
                f"策略 {policy.policy_id} 引用了 B3 未采样的字段 {unknown}；"
                "原始采样已随包交付，比例由 B2 按该策略复算。"
            ),
            "policy": policy.as_dict(),
            "available_sample_fields": list(AVAILABLE_SAMPLE_FIELDS),
        }
    numerator_value = samples.get(numerator)
    denominator_value = samples.get(denominator)
    if not isinstance(numerator_value, (int, float)) or not isinstance(
        denominator_value, (int, float)
    ):
        return {
            "status": "NOT_MEASURED",
            "detail": (
                f"策略 {policy.policy_id} 可计算，但本次运行缺少 {numerator} 或 "
                f"{denominator} 的采样值。"
            ),
            "policy": policy.as_dict(),
        }
    if denominator_value == 0:
        return {
            "status": "NOT_EVALUABLE_ZERO_DENOMINATOR",
            "detail": f"策略 {policy.policy_id} 的分母 {denominator} 为 0。",
            "policy": policy.as_dict(),
        }
    ratio = float(numerator_value) / float(denominator_value)
    return {
        "status": "COMPUTED",
        "policy": policy.as_dict(),
        "numerator_field": numerator,
        "denominator_field": denominator,
        "numerator_value": float(numerator_value),
        "denominator_value": float(denominator_value),
        "ratio": ratio,
        "sample_count": sample_count,
        "detail": (
            f"按 {policy.policy_id}（签署方 {policy.raw.get('signer')}）计算："
            f"{numerator}={numerator_value} / {denominator}={denominator_value}"
            f" = {ratio:.4f}；采样窗口 {policy.raw.get('sampling_window')}，"
            f"取电/采集范围 {policy.raw.get('probe_scope')}，"
            f"独占使用={policy.raw.get('exclusive_use')}。"
        ),
    }


__all__ = [
    "AVAILABLE_SAMPLE_FIELDS",
    "POLICY_SCHEMA_VERSION",
    "REQUIRED_FIELDS",
    "UtilizationPolicy",
    "apply_policy",
    "load_policy",
]
