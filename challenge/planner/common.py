"""Shared request-to-scene projection for planner boundary validation."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def validation_scene(request: Mapping[str, Any]) -> dict[str, Any]:
    summary = request["scene_summary"]
    constraints = request["constraints"]
    capabilities = request.get("scene_capabilities") or {}
    targets = request["targets"]
    scene: dict[str, Any] = {
        "stale": False,
        "sync": {"within_tolerance": True},
        "traffic_light": summary["traffic_light"],
        "risk_level": summary["risk_level"],
        "speed_limit_mps": constraints.get("speed_limit_mps"),
        "must_stop": constraints["must_stop"],
        "objects": [
            {
                "track_id": target["target_id"],
                "class": target["class"],
                "distance_m": target["distance_m"],
                "confidence": target["confidence"],
            }
            for target in targets
        ],
        "grounded_target_ids": [target["target_id"] for target in targets],
    }
    scene.update(dict(capabilities))
    return scene


__all__ = ["validation_scene"]

