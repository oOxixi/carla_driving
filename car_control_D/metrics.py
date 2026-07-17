from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from .event_logger import append_jsonl, write_json, ensure_dir
from .official_score import OfficialScorer


class ScenarioRecorder:
    def __init__(self, log_dir: str | Path = "logs") -> None:
        self.log_dir = ensure_dir(log_dir)
        self.events: List[Dict[str, Any]] = []
        self.frames: List[Dict[str, Any]] = []
        self.commands: List[Dict[str, Any]] = []

    def log_event(self, event_type: str, **fields: Any) -> None:
        record = {"event_type": event_type, **fields}
        self.events.append(record)
        append_jsonl(self.log_dir / "event_log.jsonl", record)

    def log_frame(self, **fields: Any) -> None:
        self.frames.append(fields)
        append_jsonl(self.log_dir / "frame_log.jsonl", fields)

    def log_command(self, command: Dict[str, Any]) -> None:
        self.commands.append(command)
        append_jsonl(self.log_dir / "command_log.jsonl", command)

    def write_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        write_json(self.log_dir / "result.json", result)
        return result

    def write_score_report(self, scenario_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        report = OfficialScorer().summarize(scenario_results, command_records=self.commands)
        write_json(self.log_dir / "score_report.json", report)
        return report
