from car_control_D.official_score import calculate_deduction, score_scenario, weighted_completion_score, latency_report


def test_deduction_rules():
    result = {"collision_count": 1, "route_deviation_count": 1, "unfinished_task_count": 2}
    assert calculate_deduction(result) == 45


def test_score_floor_zero():
    score = score_scenario({"scenario_id": "S01", "difficulty": "basic", "collision_count": 2})
    assert score.final_score == 0


def test_weighted_completion():
    summary = weighted_completion_score([
        {"difficulty": "basic", "status": "SUCCEEDED"},
        {"difficulty": "advanced", "status": "FAILED"},
        {"difficulty": "challenge", "status": "SUCCEEDED"},
    ])
    assert summary["weighted_completion_rate"] == 0.6


def test_latency_report():
    report = latency_report([{"e2e_latency_ms": 135.0}, {"e2e_latency_ms": 170.0}])
    assert report["e2e_under_150ms_rate"] == 0.5
