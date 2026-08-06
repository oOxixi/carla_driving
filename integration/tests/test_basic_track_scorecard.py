from tools.build_basic_track_scorecard import build_scorecard


def test_scorecard_requires_all_four_promotion_metrics_and_parse_latency() -> None:
    carla = {
        "scenario_count_expected": 84,
        "scenario_count_finished": 84,
        "scenario_accuracy_percent": 92.0,
        "multimodal_semantic_alignment": {"accuracy_percent": 99.0, "count": 84},
        "official_first_50_sensor_to_trajectory_ms": {"p95": 140.0, "count": 50},
    }
    voice = {"overall": {
        "asr_character_accuracy": 0.96,
        "latency": {"nlu_ms": {"p95_ms": 12.0}},
    }}
    result = build_scorecard(carla, voice)
    assert result["promotion_ready"] is True
    assert all(result["gates"].values())


def test_scorecard_does_not_treat_missing_evidence_as_pass() -> None:
    result = build_scorecard({}, {})
    assert result["promotion_ready"] is False
    assert not any(result["gates"].values())


def test_scorecard_rejects_partial_run_even_when_observed_values_pass() -> None:
    carla = {
        "scenario_count_expected": 84,
        "scenario_count_finished": 1,
        "scenario_accuracy_percent": 100.0,
        "multimodal_semantic_alignment": {"accuracy_percent": 100.0, "count": 1},
        "official_first_50_sensor_to_trajectory_ms": {"p95": 80.0, "count": 1},
    }
    voice = {"overall": {
        "asr_character_accuracy": 1.0,
        "latency": {"nlu_ms": {"p95_ms": 10.0}},
    }}
    result = build_scorecard(carla, voice)
    assert result["promotion_ready"] is False
    assert result["gates"]["scenario_task_completion_ge_90"] is False
    assert result["gates"]["multimodal_alignment_ge_98"] is False
    assert result["gates"]["sensor_to_trajectory_p95_le_150_ms"] is False
