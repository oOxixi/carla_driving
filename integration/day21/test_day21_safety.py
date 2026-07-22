

from .safety_state import SafetyStateSummary
from .safety_override import apply_safety_override



def test_red_light_override():


    safety=SafetyStateSummary(
        traffic_light="RED"
    )


    result=apply_safety_override(

        {
        "action":"START"
        },

        safety.to_dict()

    )


    assert result["action"]=="STOP"



def test_ttc_override():


    safety=SafetyStateSummary(
        ttc_s=0.8
    )


    result=apply_safety_override(

        {
        "action":"START"
        },

        safety.to_dict()

    )


    assert result["action"]=="EMERGENCY_STOP"



if __name__=="__main__":

    test_red_light_override()

    test_ttc_override()

    print(
        "DAY21 SAFETY TEST PASS"
    )
