

def apply_safety_override(
    decision,
    safety
):


    if safety.get(
        "ttc_s"
    ) is not None:


        if safety["ttc_s"] < 1.5:

            return {
                "action":"EMERGENCY_STOP",
                "confidence":0.99,
                "requires_confirmation":False,
                "reason_zh":"TTC风险过高"
            }



    if safety.get(
        "traffic_light"
    )=="RED":


        return {
            "action":"STOP",
            "confidence":0.98,
            "requires_confirmation":False,
            "reason_zh":"红灯安全约束优先"
        }



    if safety.get(
        "pedestrian_risk"
    ):


        return {
            "action":"STOP",
            "confidence":0.98,
            "requires_confirmation":False,
            "reason_zh":"检测到行人风险"
        }



    return decision
