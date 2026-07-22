from __future__ import annotations


CASES = [
    {
        "case": "red_light_near_stop_line",
        "voice": "继续走",
        "safety_state": {
            "traffic_light": "RED",
            "distance_to_stop_line_m": 5.0,
        },
        "expected": "STOP",
        "expected_confirmation": False,
    },
    {
        "case": "pedestrian",
        "voice": "继续",
        "safety_state": {
            "object_class": "PEDESTRIAN",
            "object_confidence": 0.95,
            "visual_valid": True,
        },
        "expected": "STOP",
        "expected_confirmation": False,
    },
    {
        "case": "front_vehicle",
        "voice": "保持速度",
        "safety_state": {
            "front_distance_m": 8.0,
            "closing_speed_mps": 1.0,
            "ttc_s": 8.0,
            "lidar_valid": True,
        },
        "expected": "SLOW_DOWN",
        "expected_confirmation": False,
    },
    {
        "case": "ttc_emergency",
        "voice": "继续",
        "safety_state": {
            "front_distance_m": 4.0,
            "closing_speed_mps": 4.0,
            "ttc_s": 1.0,
            "lidar_valid": True,
        },
        "expected": "EMERGENCY_STOP",
        "expected_confirmation": False,
    },
    {
        "case": "low_confidence",
        "voice": "继续",
        "safety_state": {
            "input_confidence": 0.4,
        },
        "expected": "STOP",
        "expected_confirmation": True,
    },
    {
        "case": "safe",
        "voice": "继续",
        "safety_state": {
            "front_distance_m": 50.0,
            "input_confidence": 1.0,
            "lidar_valid": True,
        },
        "expected": "START",
        "expected_confirmation": False,
    },
    {
        "case": "rain",
        "voice": "继续",
        "safety_state": {
            "weather": "rain",
            "lidar_valid": True,
        },
        "expected": "SET_SPEED",
        "expected_confirmation": False,
    },
    {
        "case": "user_speed_conflict",
        "voice": "加速",
        "safety_state": {
            "traffic_light": "RED",
            "distance_to_stop_line_m": 4.0,
        },
        "expected": "STOP",
        "expected_confirmation": False,
    },
    {
        "case": "lidar_only",
        "voice": "继续",
        "safety_state": {
            "front_distance_m": 8.0,
            "lidar_valid": True,
            "visual_valid": False,
            "object_class": None,
            "object_confidence": 0.0,
            "fusion_mode": "LIDAR_ONLY",
        },
        "expected": "SLOW_DOWN",
        "expected_confirmation": False,
    },
    {
        "case": "full_brake",
        "voice": "继续",
        "safety_state": {
            "recommended_action": "FULL_BRAKE",
            "fusion_mode": "FAIL_CLOSED",
        },
        "expected": "STOP",
        "expected_confirmation": False,
    },
    {
        "case": "no_false_pedestrian",
        "voice": "继续",
        "safety_state": {
            "front_distance_m": 80.0,
            "object_class": None,
            "object_confidence": 0.0,
            "visual_valid": False,
            "lidar_valid": True,
        },
        "expected": "START",
        "expected_confirmation": False,
    },
    {
        "case": "sensor_missing",
        "voice": "继续",
        "safety_state": {
            "visual_valid": False,
            "lidar_valid": False,
            "fused_valid": False,
            "input_confidence": 0.3,
        },
        "expected": "STOP",
        "expected_confirmation": True,
    },
]
