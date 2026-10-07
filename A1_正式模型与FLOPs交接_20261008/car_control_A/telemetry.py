"""Monotonic, replay-friendly command latency tracing."""

from __future__ import annotations

import json
from pathlib import Path
import time
from typing import Mapping


class LatencyTrace:
    def __init__(self, command_id: str) -> None:
        if type(command_id) is not str or not command_id:
            raise ValueError("command_id must be a non-empty string")
        self.command_id = command_id
        self._marks: dict[str, int] = {}

    def mark(self, stage: str, *, timestamp_ns: int | None = None) -> None:
        if type(stage) is not str or not stage:
            raise ValueError("stage must be a non-empty string")
        if stage in self._marks:
            raise ValueError("stage already marked")
        stamp = time.monotonic_ns() if timestamp_ns is None else timestamp_ns
        if type(stamp) is not int or stamp < 0:
            raise ValueError("timestamp_ns must be a non-negative integer")
        if self._marks and stamp < max(self._marks.values()):
            raise ValueError("timestamps must be monotonic")
        self._marks[stage] = stamp

    def segment_ms(self, start_stage: str, end_stage: str) -> float:
        return (self._marks[end_stage] - self._marks[start_stage]) / 1_000_000

    @property
    def end_to_end_ms(self) -> float | None:
        if len(self._marks) < 2:
            return None
        values = tuple(self._marks.values())
        return (values[-1] - values[0]) / 1_000_000

    def to_dict(self) -> dict[str, object]:
        return {"command_id": self.command_id, "timestamps_ns": dict(self._marks), "end_to_end_ms": self.end_to_end_ms}

    def append_jsonl(self, path: str | Path, *, extra: Mapping[str, object] | None = None) -> None:
        record = self.to_dict()
        if extra is not None:
            overlap = set(record).intersection(extra)
            if overlap:
                raise ValueError(f"extra may not overwrite trace fields: {sorted(overlap)}")
            record.update(extra)
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, allow_nan=False, sort_keys=True) + "\n")
