from tools.run_qwen_batch_benchmark import _context, _evaluate


def test_context_uses_per_case_rgb_and_detected_objects():
    case = {
        "case_id": "assoc-1",
        "voice_command": "跟随左侧车辆",
        "rgb_ref": "images/one.png",
        "perception": {
            "detected_objects": [{"track_id": "vehicle_left"}],
        },
    }

    context = _context(case, "fallback.png", 3)

    assert context.rgb_ref == "images/one.png"
    assert context.perception["detected_objects"][0]["track_id"] == "vehicle_left"


def test_evaluate_requires_exact_target_track_id():
    case = {
        "expected": {
            "action": "SLOW_DOWN",
            "requires_confirmation": False,
            "target_track_id": "vehicle_left",
        },
    }

    correct = _evaluate(
        case,
        {
            "action": "SLOW_DOWN",
            "requires_confirmation": False,
            "target_track_id": "vehicle_left",
        },
    )
    missing = _evaluate(
        case,
        {
            "action": "SLOW_DOWN",
            "requires_confirmation": False,
        },
    )

    assert correct["target_association"] is True
    assert correct["all"] is True
    assert missing["target_association"] is False
    assert missing["all"] is False


def test_evaluate_preserves_legacy_cases_without_target():
    checks = _evaluate(
        {"expected": {"action": "STOP", "requires_confirmation": False}},
        {"action": "STOP", "requires_confirmation": False},
    )

    assert checks["target_association"] is True
    assert checks["all"] is True
