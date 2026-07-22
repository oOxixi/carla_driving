from .safety_schema import SafetyStateSummary
from .safety_override import apply_safety_override



def test_red_light_conflict():

    user={
        "action":"START"
    }


    safety=SafetyStateSummary(

        traffic_light="RED"

    )


    result=apply_safety_override(

        user,

        safety.to_dict()

    )


    assert result["action"]=="STOP"




def test_ttc():

    user={
        "action":"START"
    }


    safety=SafetyStateSummary(

        ttc_s=1.0

    )


    result=apply_safety_override(

        user,

        safety.to_dict()

    )


    assert result["action"]=="EMERGENCY_STOP"




def test_pedestrian():

    user={
        "action":"START"
    }


    safety=SafetyStateSummary(

        pedestrian_risk=True

    )


    result=apply_safety_override(

        user,

        safety.to_dict()

    )


    assert result["action"]=="STOP"




if __name__=="__main__":

    test_red_light_conflict()

    test_ttc()

    test_pedestrian()


    print(
        "DAY21 MULTIMODAL TEST PASS"
    )
