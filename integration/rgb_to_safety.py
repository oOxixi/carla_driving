from __future__ import annotations


def rgb_to_state(
        vision_result,
        vehicle_state):

    state = dict(vehicle_state)

    summary = vision_result.get(
        "scene_summary",
        {}
    )

    objects = vision_result.get(
        "objects",
        []
    )


    # 前方车辆风险
    if summary.get("front_vehicle", False):

        for obj in objects:
            if obj.get("category") == "VEHICLE":

                distance = (
                    obj
                    .get("metadata", {})
                    .get("distance_m_debug")
                )

                if distance is not None:
                    state["front_distance_m"] = distance
                else:
                    state["front_distance_m"] = 15.0


    # 红绿灯
    light = vision_result.get(
        "traffic_light",
        {}
    )

    state["traffic_light"] = (
        light.get(
            "state",
            "UNKNOWN"
        )
        .upper()
    )


    return state
