from pathlib import Path

from tools.run_carla_scenario_matrix import _record_from_summary


def test_matrix_record_preserves_percentiles_and_resume_state(tmp_path: Path) -> None:
    summary_path = tmp_path / "run.summary.json"
    summary = {
        "status": "SUCCEEDED",
        "score": {"final_score": 25.0},
        "collision_count": 0,
        "red_light_violation_count": 0,
        "route_deviation_count": 0,
        "min_gap_m": 6.5,
        "latency": {
            "sensor_to_control_avg_ms": 0.7,
            "sensor_to_control_p95_ms": 0.9,
            "sensor_to_control_p99_ms": 1.1,
            "sensor_to_control_max_ms": 1.4,
        },
    }
    record = _record_from_summary(
        scenario=Path("scenarios/safety_D/D03.json"),
        seed=2,
        repeat=3,
        returncode=0,
        summary_path=summary_path,
        summary=summary,
        resumed=True,
    )
    assert record["repeat"] == 4
    assert record["resumed"] is True
    assert record["sensor_to_control_p95_ms"] == 0.9
    assert record["sensor_to_control_p99_ms"] == 1.1
