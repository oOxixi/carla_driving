from __future__ import annotations


import json


from .multimodal_qwen_adapter import (
    Day21QwenAdapter
)

from .safety_state import (
    SafetyStateSummary
)

from .safety_override import (
    apply_safety_override
)



def run_case(
    name,
    voice,
    safety
):


    print(
        "\nCASE:",
        name
    )


    scene={

        "ego_speed_mps":5.0,

        "lane_id":1

    }


    rgb={

        "objects":[

            "vehicle",

            "pedestrian"

        ]

    }



    adapter=Day21QwenAdapter()



    result=adapter.run(

        voice,

        scene,

        safety.to_dict(),

        rgb

    )



    result=apply_safety_override(

        result,

        safety.to_dict()

    )



    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False
        )
    )


    return result




def main():


    cases=[


        (

        "red_light_conflict",

        "继续走",

        SafetyStateSummary(

            traffic_light="RED"

        )

        ),



        (

        "pedestrian",

        "继续前进",

        SafetyStateSummary(

            pedestrian_risk=True

        )

        ),



        (

        "ttc",

        "",

        SafetyStateSummary(

            ttc_s=0.8

        )

        ),



        (

        "safe",

        "继续",

        SafetyStateSummary()

        )


    ]



    results=[]



    for c in cases:


        results.append(

            run_case(

                c[0],

                c[1],

                c[2]

            )

        )



    print(

        "\nDAY21 MULTIMODAL TEST DONE"

    )




if __name__=="__main__":

    main()
