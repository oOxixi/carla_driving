import json


from integration.qwen_adapter import QwenDrivingAdapter


from integration.day20.qwen_scene_adapter import (
    build_demo_scene
)


from integration.day20.qwen_intent_schema import (
    DrivingIntent,
    ActionStep,
    validate_intent
)



PROMPT = """

你是自动驾驶行为决策模块。

输入:

1.驾驶员语音指令
2.SceneState


输出DrivingIntent JSON。


禁止输出:

throttle
brake
steer


只能输出:

START
STOP
SET_SPEED
TURN_LEFT
TURN_RIGHT
CHANGE_LANE_LEFT
CHANGE_LANE_RIGHT
AVOID_OBJECT
EMERGENCY_BRAKE
RETURN_TO_LANE


格式:

{
"actions":[
{
"action":"",
"target_id":"",
"target_speed_kmh":0
}
],
"confidence":0.0,
"reason":""
}

"""


def parse_result(data):


    actions=[]


    for a in data.get(
        "actions",
        []
    ):

        actions.append(

            ActionStep(

                action=
                    a.get(
                        "action",
                        "STOP"
                    ),


                target_id=
                    a.get(
                        "target_id",
                        ""
                    ),


                target_speed_kmh=
                    a.get(
                        "target_speed_kmh",
                        0
                    )
            )
        )


    return DrivingIntent(

        command_id=
            "qwen_day20_multimodal_001",


        actions=
            actions,


        confidence=
            float(
                data.get(
                    "confidence",
                    0
                )
            ),


        reason=
            data.get(
                "reason",
                ""
            )
    )





def main():


    scene = build_demo_scene()


    print(
        "===== SCENE STATE ====="
    )


    print(
        json.dumps(
            scene.to_dict(),
            ensure_ascii=False,
            indent=2
        )
    )



    qwen=QwenDrivingAdapter()



    text="""

前方车辆减速，
请降低速度并保持安全距离

"""


    qwen_text = (

        PROMPT

        +

        "\n驾驶员:"
        +

        text

        +

        "\nSceneState:"

        +

        json.dumps(
            scene.to_dict(),
            ensure_ascii=False
        )

    )



    raw = qwen.infer(
        qwen_text
    )


    print(
        "===== RAW COMMAND ====="
    )

    print(raw)



    # demo fallback
    # 后续替换为独立parser


    intent=DrivingIntent(

        command_id=
            "qwen_day20_multimodal_001",


        actions=[

            ActionStep(

                action=
                    "SET_SPEED",

                target_speed_kmh=15
            )
        ],


        confidence=0.95,


        reason=
        "front vehicle slowing detected"
    )



    print(
        "===== DRIVING INTENT ====="
    )


    print(
        json.dumps(
            intent.to_dict(),
            ensure_ascii=False,
            indent=2
        )
    )


    print(
        "===== VALIDATE ====="
    )


    print(
        validate_intent(intent)
    )




if __name__=="__main__":

    main()
