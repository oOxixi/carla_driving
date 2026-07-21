from __future__ import annotations

import json
import re


from .schemas import (
    Action,
    DrivingIntent,
    ALLOWED_ACTIONS,
)



def extract_json(text: str):

    # 兼容:
    # 1. Qwen原始字符串输出
    # 2. qwen_adapter已经解析后的dict


    if isinstance(text, dict):

        return text


    if not isinstance(text, str):

        return {}


    blocks = re.findall(
        r"```json\s*(.*?)```",
        text,
        flags=re.S|re.I
    )


    candidates = blocks + [text]


    for item in candidates:

        start=item.find("{")
        end=item.rfind("}")


        if start<0 or end<=start:
            continue


        content=item[start:end+1]


        try:

            data=json.loads(content)

            if isinstance(data,dict):
                return data

        except Exception:
            pass


    return {}



def build_action(item):


    action_name=str(
        item.get(
            "action",
            ""
        )
    ).upper()


    if action_name not in ALLOWED_ACTIONS:
        return None



    return Action(

        action=action_name,

        target_id=str(
            item.get(
                "target_id",
                ""
            )
        ),


        target_speed_kmh=float(
            item.get(
                "target_speed_kmh",
                0.0
            )
        )

    )





def convert_intent_to_actions(data):

    """
    兼容旧QwenDrivingAdapter输出

    intent:
        SLOW_DOWN
        STOP
        SPEED_UP

    转换为Day20 DrivingIntent
    """


    intent=str(
        data.get(
            "intent",
            ""
        )
    ).upper()



    if intent=="SLOW_DOWN":

        return [

            Action(
                action="SET_SPEED",
                target_id="",
                target_speed_kmh=20
            )

        ]



    if intent=="STOP":

        return [

            Action(
                action="STOP"
            )

        ]



    if intent=="EMERGENCY_STOP":

        return [

            Action(
                action="EMERGENCY_BRAKE"
            )

        ]



    if intent=="CHANGE_LANE":

        return [

            Action(
                action="CHANGE_LANE_RIGHT"
            )

        ]



    if intent=="AVOID_OBSTACLE":

        return [

            Action(
                action="AVOID_OBJECT"
            )

        ]



    return []





def parse_intent(raw_output):


    data=extract_json(
        raw_output
    )


    actions=[]



    # 新格式
    if isinstance(
        data.get("actions"),
        list
    ):


        for item in data["actions"]:


            if isinstance(item,dict):

                action=build_action(item)

                if action:
                    actions.append(action)



    # 旧格式兼容
    if not actions:

        actions=convert_intent_to_actions(
            data
        )



    confidence=float(
        data.get(
            "confidence",
            data.get(
                "intent_confidence",
                0.0
            )
        )
    )


    confidence=max(
        0.0,
        min(
            1.0,
            confidence
        )
    )



    return DrivingIntent(

        command_id="day20_qwen001",

        actions=actions,

        confidence=confidence,

        reason=str(
            data.get(
                "reason",
                ""
            )
        )

    )

