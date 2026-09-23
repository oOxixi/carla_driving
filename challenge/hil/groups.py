"""Group-aware replay analysis: Seen / Variant / Unseen, without owning them.

`docs/modules/B3_HIL_J6P_INDEPENDENT_VALIDATION.md` §7 requires the replay to be
reported per group and §12 makes "Variant/Unseen 无模板化错误" a Gate, but B3 does
**not** own the Seen/Variant/Unseen definitions.  So this module never invents a
grouping: it reads the label the frozen input carries (B2's manifest field, or a
`--group-map` file supplied by B2), keeps any label it does not recognise as a
literal string, and marks everything else `UNLABELED`.

What B3 does own is the arithmetic on top of those labels, and that is what this
module adds:

* per-group pass rates, so a group with structural failures cannot hide inside a
  healthy total;
* output-collapse detection, so "the Student answers every Variant case with the
  same plan" becomes a number instead of an impression;
* request-distinctness counting, because the comparison is only worth something
  if the instructions in a group are actually different from each other.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


UNLABELED = "UNLABELED"

#: Canonical labels this module recognises.  Anything else is kept verbatim and
#: flagged as unrecognised rather than silently mapped onto one of these.
CANONICAL_GROUPS: tuple[str, ...] = ("SEEN", "VARIANT", "UNSEEN")

#: Keys a frozen case record may use to declare its group.
GROUP_KEYS: tuple[str, ...] = ("group", "split", "evaluation_group", "dataset_group")

#: Share of a group's cases that may share one identical Student output before it
#: is reported as a collapse *signal* (not a verdict; a small group can collapse
#: by chance and a legitimate planner may be genuinely constant).
DOMINANT_OUTPUT_SIGNAL_SHARE = 0.9

#: Average number of cases sharing one instruction text at which a group stops
#: being a set of independent instructions.  2 means "on average each text is
#: used at least twice", which is enough to warn that behaviour matching on that
#: group cannot by itself demonstrate generalisation.  The number is a reading
#: aid: the raw counts are reported next to it.
SOURCE_TEXT_REUSE_SIGNAL = 2.0


def normalize_group(label: Any) -> str | None:
    """Upper-case a non-empty label; return None when there is nothing to read."""
    if label is None:
        return None
    text = str(label).strip()
    return text.upper() if text else None


def label_from_case(case: Any) -> str | None:
    for key in GROUP_KEYS:
        value = getattr(case, key, None)
        if value is None and isinstance(case, Mapping):
            value = case.get(key)
        normalised = normalize_group(value)
        if normalised:
            return normalised
    return None


def case_group(case: Any, override: Mapping[str, str] | None = None) -> str:
    """Resolve one case's group: explicit override first, then the case label."""
    if override:
        for key in ("case_id", "sample_id", "scenario_id"):
            value = getattr(case, key, None)
            if value is None and isinstance(case, Mapping):
                value = case.get(key)
            if value is not None and str(value) in override:
                return normalize_group(override[str(value)]) or UNLABELED
    return label_from_case(case) or UNLABELED


def apply_group_map(
    cases: Iterable[Any],
    override: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build the `case_id -> group` map used everywhere else in the harness."""
    groups: dict[str, str] = {}
    for case in cases:
        case_id = getattr(case, "case_id", None)
        if case_id is None and isinstance(case, Mapping):
            case_id = case.get("case_id")
        groups[str(case_id)] = case_group(case, override)
    return groups


def groups_from_rows(
    rows: Iterable[Mapping[str, Any]],
    override: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Fallback grouping for a finished run whose cases are no longer loaded.

    Without the frozen input only an explicit `--group-map` can label a row; the
    scenario prefix is deliberately not interpreted, because interpreting it
    would mean B3 guessing at a definition it does not own.
    """
    groups: dict[str, str] = {}
    for row in rows:
        case_id = str(row.get("case_id", ""))
        group = UNLABELED
        if override:
            for key in ("sample_id", "scenario_id", "case_id"):
                value = row.get(key)
                if value is not None and str(value) in override:
                    group = normalize_group(override[str(value)]) or UNLABELED
                    break
        groups[case_id] = group
    return groups


def source_text_of(case: Any) -> str:
    request = getattr(case, "request", None)
    if request is None and isinstance(case, Mapping):
        request = case.get("request")
    if isinstance(request, Mapping):
        return str(request.get("source_text", ""))
    return ""


def student_output_key(row: Mapping[str, Any]) -> str:
    """Canonical identity of one Student output for collapse counting."""
    behaviors = str(row.get("student_behavior_sequence", ""))
    targets = str(row.get("student_target_sequence", ""))
    return f"{behaviors}||{targets}"


def teacher_output_key(row: Mapping[str, Any]) -> str:
    behaviors = str(row.get("teacher_behavior_sequence", ""))
    targets = str(row.get("teacher_target_sequence", ""))
    return f"{behaviors}||{targets}"


def _share(numerator: int, denominator: int) -> float | None:
    return (numerator / denominator) if denominator else None


def _mean(values: Sequence[float]) -> float | None:
    return (sum(values) / len(values)) if values else None


def _group_rows(
    rows: Iterable[Mapping[str, Any]],
    groups: Mapping[str, str],
) -> dict[str, list[Mapping[str, Any]]]:
    buckets: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        case_id = str(row.get("case_id", ""))
        buckets.setdefault(groups.get(case_id, UNLABELED), []).append(row)
    return buckets


def group_report(
    rows: Iterable[Mapping[str, Any]],
    *,
    groups: Mapping[str, str],
    source_texts: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Per-group facts plus the collapse signals that depend on them."""
    row_list = [row for row in rows]
    buckets = _group_rows(row_list, groups)
    source_texts = source_texts or {}

    groups_out: dict[str, Any] = {}
    for name in sorted(buckets, key=lambda item: (item == UNLABELED, item)):
        bucket = buckets[name]
        outputs: dict[str, int] = {}
        teachers: set[str] = set()
        for row in bucket:
            key = student_output_key(row)
            outputs[key] = outputs.get(key, 0) + 1
            teachers.add(teacher_output_key(row))
        dominant_key, dominant_count = (
            max(outputs.items(), key=lambda item: item[1]) if outputs else ("", 0)
        )
        ready = sum(1 for row in bucket if row.get("outcome") == "READY")
        structural = sum(1 for row in bucket if not row.get("structural_failures"))
        behavior_ratios = [
            float(row["behavior_match_ratio"])
            for row in bucket
            if isinstance(row.get("behavior_match_ratio"), (int, float))
        ]
        target_ratios = [
            float(row["target_match_ratio"])
            for row in bucket
            if isinstance(row.get("target_match_ratio"), (int, float))
        ]
        texts = {
            source_texts[str(row.get("case_id", ""))]
            for row in bucket
            if str(row.get("case_id", "")) in source_texts
        }
        distinct_texts = len(texts)
        collapse = bool(
            len(outputs) == 1
            and len(teachers) >= 2
            and len(bucket) >= 2
        )
        dominant_share = _share(dominant_count, len(bucket))
        groups_out[name] = {
            "recognized": name in CANONICAL_GROUPS,
            "case_count": len(bucket),
            "ready": ready,
            "ready_rate": _share(ready, len(bucket)),
            "structural_pass": structural,
            "structural_pass_rate": _share(structural, len(bucket)),
            "distinct_student_outputs": len(outputs),
            "distinct_teacher_outputs": len(teachers),
            "dominant_student_output": dominant_key,
            "dominant_student_output_share": dominant_share,
            "constant_student_output": len(outputs) == 1,
            "teacher_varies_student_constant": collapse,
            "dominant_output_signal": bool(
                dominant_share is not None
                and dominant_share >= DOMINANT_OUTPUT_SIGNAL_SHARE
                and len(bucket) >= 2
            ),
            "mean_behavior_match_ratio": _mean(behavior_ratios),
            "mean_target_match_ratio": _mean(target_ratios),
            "distinct_source_texts": distinct_texts if texts else None,
            "cases_per_distinct_source_text": (
                (len(bucket) / distinct_texts) if texts and distinct_texts else None
            ),
            "instruction_text_reuse_signal": bool(
                texts
                and distinct_texts
                and (len(bucket) / distinct_texts) >= SOURCE_TEXT_REUSE_SIGNAL
            ),
            "instruction_text_collapsed": (
                None if not texts else bool(distinct_texts == 1 and len(bucket) >= 2)
            ),
        }

    collapse_groups = sorted(
        name for name, item in groups_out.items() if item["teacher_varies_student_constant"]
    )
    dominant_groups = sorted(
        name for name, item in groups_out.items() if item["dominant_output_signal"]
    )
    collapsed_text_groups = sorted(
        name for name, item in groups_out.items() if item["instruction_text_collapsed"]
    )
    reused_text_groups = sorted(
        name for name, item in groups_out.items() if item["instruction_text_reuse_signal"]
    )
    unrecognized = sorted(
        name
        for name, item in groups_out.items()
        # UNLABELED is "no label was provided", not an unrecognised B2 label.
        if not item["recognized"] and name != UNLABELED
    )
    return {
        "schema_version": "1.0",
        "case_count": len(row_list),
        "groups": groups_out,
        "template_collapse_groups": collapse_groups,
        "dominant_output_groups": dominant_groups,
        "instruction_text_collapsed_groups": collapsed_text_groups,
        "instruction_text_reused_groups": reused_text_groups,
        "unrecognized_group_labels": unrecognized,
        "notes": (
            "Group labels come from the frozen input (or an explicit --group-map) and "
            "are not interpreted or re-defined by B3. UNLABELED means no label was "
            "provided, which is the normal state until B2 issues the Seen/Variant/"
            "Unseen manifest. Collapse flags are signals that a group's comparison "
            "cannot support a generalisation claim; the accuracy verdict stays with B2."
        ),
    }


def read_group_map(path: str | Path) -> dict[str, str]:
    """Load a B2-supplied label map without touching the frozen snapshot.

    Accepted shapes: ``{"<key>": "SEEN"}`` or ``{"groups": {"SEEN": [ids...]}}``.
    """
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("group map must be a JSON object")
    mapping: dict[str, str] = {}
    nested = payload.get("groups")
    if isinstance(nested, Mapping):
        for label, members in nested.items():
            normalised = normalize_group(label)
            if not normalised or not isinstance(members, Sequence) or isinstance(members, (str, bytes)):
                continue
            for member in members:
                mapping[str(member)] = normalised
        return mapping
    for key, label in payload.items():
        normalised = normalize_group(label)
        if normalised:
            mapping[str(key)] = normalised
    return mapping


__all__ = [
    "CANONICAL_GROUPS",
    "DOMINANT_OUTPUT_SIGNAL_SHARE",
    "GROUP_KEYS",
    "UNLABELED",
    "apply_group_map",
    "case_group",
    "group_report",
    "groups_from_rows",
    "label_from_case",
    "normalize_group",
    "read_group_map",
    "source_text_of",
    "student_output_key",
    "teacher_output_key",
]
