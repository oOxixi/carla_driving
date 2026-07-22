from __future__ import annotations


from .safety_override import apply_safety_override



class Day21QwenAdapter:
    """
    Day21 Multimodal Qwen Decision Adapter


    输入:

        Day21Context

        {
            voice_command,
            scene_state,
            perception,
            safety_state
        }


    SafetyState来源:

        第二组:
            LiDAR摘要
            perception摘要
            safety module


    输出:

        High-level driving decision


    不输出:

        throttle
        brake
        steer


    输出供:

        command_adapter

    """



    def __init__(self):

        pass



    def infer(
        self,
        context
    ):


        safety = context.safety_state or {}



        decision = self.rule_decision(

            safety,

            context.voice_command

        )



        # Safety override

        decision = apply_safety_override(

            decision,

            safety

        )



        return decision




    def rule_decision(
        self,
        safety,
        voice=""
    ):


        """
        Safety-first multimodal decision


        优先级:

        TTC emergency

        >

        traffic light

        >

        pedestrian

        >

        obstacle

        >

        front vehicle

        >

        weather

        >

        confidence

        >

        normal


        """



        # ==========================
        # 1. TTC emergency
        # ==========================


        ttc = safety.get(
            "ttc_s"
        )


        if (
            ttc is not None
            and ttc < 1.5
        ):


            return {

                "action":
                    "EMERGENCY_STOP",


                "target_speed_mps":
                    None,


                "confidence":
                    0.99,


                "requires_confirmation":
                    False,


                "reason_zh":
                    "TTC风险过高，紧急停车"

            }




        # ==========================
        # 2. traffic light
        # ==========================


        if safety.get(
            "traffic_light"
        ) == "RED":


            return {

                "action":
                    "STOP",


                "target_speed_mps":
                    None,


                "confidence":
                    0.98,


                "requires_confirmation":
                    False,


                "reason_zh":
                    "红灯安全约束优先"

            }




        # ==========================
        # 3. pedestrian
        # ==========================


        if safety.get(
            "pedestrian_risk",
            False
        ):


            return {

                "action":
                    "STOP",


                "target_speed_mps":
                    None,


                "confidence":
                    0.98,


                "requires_confirmation":
                    False,


                "reason_zh":
                    "检测到行人风险"

            }




        # ==========================
        # 4. obstacle
        # ==========================


        if safety.get(
            "obstacle_risk",
            False
        ):


            return {

                "action":
                    "STOP",


                "target_speed_mps":
                    None,


                "confidence":
                    0.98,


                "requires_confirmation":
                    False,


                "reason_zh":
                    "检测到障碍物风险"

            }





        # ==========================
        # 5. front vehicle
        # ==========================


        front_distance = safety.get(
            "front_distance_m",
            999
        )


        if front_distance < 15:


            return {


                "action":
                    "SET_SPEED",


                "target_speed_mps":
                    3.0,


                "confidence":
                    0.90,


                "requires_confirmation":
                    False,


                "reason_zh":
                    "前车距离过近，降低速度"

            }





        # ==========================
        # 6. rain weather
        # ==========================


        weather = safety.get(
            "weather",
            "clear"
        )


        if weather in [

            "rain",

            "heavy_rain"

        ]:


            return {


                "action":
                    "SET_SPEED",


                "target_speed_mps":
                    5.0,


                "confidence":
                    0.85,


                "requires_confirmation":
                    False,


                "reason_zh":
                    "雨天降低速度保持安全"

            }





        # ==========================
        # 7. low confidence
        # ==========================


        confidence = safety.get(

            "input_confidence",

            safety.get(

                "confidence",

                1.0

            )

        )


        if confidence < 0.6:


            return {


                "action":
                    "STOP",


                "target_speed_mps":
                    None,


                "confidence":
                    confidence,


                "requires_confirmation":
                    True,


                "reason_zh":
                    "输入安全状态置信度不足，需要确认"

            }





        # ==========================
        # 8. normal
        # ==========================


        return {


            "action":
                "START",


            "target_speed_mps":
                None,


            "confidence":
                0.90,


            "requires_confirmation":
                False,


            "reason_zh":
                "安全状态正常"

        }
