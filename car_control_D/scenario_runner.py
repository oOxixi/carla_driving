from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from .metrics import ScenarioRecorder
from .official_score import score_scenario


class ScenarioRunner:
    def __init__(self, recorder: Optional[ScenarioRecorder] = None) -> None:
        self.recorder = recorder or ScenarioRecorder()

    def run(self, scenario_id: str, difficulty: str, fn: Callable[[], Dict[str, Any]]) -> Dict[str, Any]:
        self.recorder.log_event("SCENARIO_START", scenario_id=scenario_id, difficulty=difficulty)
        try:
            result = fn()
            result.setdefault("scenario_id", scenario_id)
            result.setdefault("difficulty", difficulty)
            result.setdefault("status", "SUCCEEDED")
        except Exception as exc:
            result = {"scenario_id": scenario_id, "difficulty": difficulty, "status": "FAILED", "error": str(exc), "unfinished_task_count": 1}
            self.recorder.log_event("SCENARIO_ERROR", scenario_id=scenario_id, error=str(exc))
        score = score_scenario(result).to_dict()
        result["score"] = score
        self.recorder.write_result(result)
        self.recorder.log_event("SCENARIO_END", scenario_id=scenario_id, status=result.get("status"), score=score)
        return result
