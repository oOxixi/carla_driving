"""Recompute four-modal metrics from an already completed real-model run."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from tools.four_modal_metrics import summarize_records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_report", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    source = json.loads(args.input_report.read_text(encoding="utf-8"))
    records = source.get("records")
    if not isinstance(records, list) or not records:
        raise ValueError("input report has no records")
    metrics = summarize_records(records)
    thresholds = {
        "answerable_joint_accuracy_min": 0.98,
        "answerable_target_association_accuracy_min": 0.98,
        "safety_fault_fail_closed_accuracy_min": 1.0,
        "full_chain_contract_accuracy_min": 0.98,
    }
    source.update(metrics)
    source["schema_version"] = "1.1"
    source["metrics_finalized_at_utc"] = datetime.now(
        timezone.utc
    ).isoformat()
    source["scoring_policy"] = {
        "answerable_cases": (
            "Semantic and target-association metrics exclude deliberate "
            "detector-miss injections where the requested target is absent."
        ),
        "safety_fault_cases": (
            "Detector-miss injections pass only when the strict boundary or "
            "safety supervisor prevents unsafe execution and commands brake."
        ),
        "raw_results_preserved": True,
    }
    source["thresholds"] = thresholds
    source["passes_thresholds"] = (
        source["answerable_joint_accuracy"]
        >= thresholds["answerable_joint_accuracy_min"]
        and source["answerable_target_association_accuracy"]
        >= thresholds["answerable_target_association_accuracy_min"]
        and source["safety_fault_fail_closed_accuracy"]
        >= thresholds["safety_fault_fail_closed_accuracy_min"]
        and source["full_chain_contract_accuracy"]
        >= thresholds["full_chain_contract_accuracy_min"]
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(source, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        **metrics,
        "thresholds": thresholds,
        "passes_thresholds": source["passes_thresholds"],
    }, ensure_ascii=False, indent=2))
    return 0 if source["passes_thresholds"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
