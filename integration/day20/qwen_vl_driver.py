from __future__ import annotations

from integration.qwen_adapter import QwenDrivingAdapter

from .parser import parse_intent



class QwenVLDriver:


    def __init__(self):

        self.model = QwenDrivingAdapter()



    def infer(
        self,
        command_text,
        scene_state,
        image_path=None
    ):


        prompt = f"""
你是自动驾驶行为决策模块。


输入:

1.驾驶员语音指令
2.RGB图像
3.SceneState


你的任务:
输出驾驶行为决策。


禁止输出:

throttle
brake
steer


只能输出以下action:

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


输出严格JSON:

{{
"actions":[
{{
"action":"",
"target_id":"",
"target_speed_kmh":0
}}
],
"confidence":0.0,
"reason":""
}}


驾驶员指令:

{command_text}


SceneState:

{scene_state}
"""


        raw = self.model.raw_generate(
            prompt,
            image_path
        )


        intent = parse_intent(
            raw
        )


        return intent
