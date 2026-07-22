from __future__ import annotations


from dataclasses import dataclass



@dataclass
class IntentControlOutput:
    """
    Day20高层意图转换结果

    注意:
    这里只产生给控制模块的目标
    不产生steer/brake/throttle
    """

    target_speed_kmh: float = 0.0

    emergency_stop: bool = False

    stop: bool = False

    reason: str = ""



class Day20IntentExecutor:
    """
    DrivingIntent
        |
        |
    Longitudinal目标

    不替代C模块
    不直接控制CARLA
    """


    def __init__(
        self,
        default_speed=30.0
    ):

        self.default_speed = default_speed



    def execute(
        self,
        driving_intent
    ):

        """
        输入:
            DrivingIntent dataclass

        输出:
            IntentControlOutput
        """


        output = IntentControlOutput()



        for action in driving_intent.actions:


            name = action.action.upper()



            if name == "SET_SPEED":


                output.target_speed_kmh = (
                    float(
                        action.target_speed_kmh
                    )
                )


                output.reason = (
                    "Qwen requested target speed"
                )



            elif name == "STOP":


                output.target_speed_kmh = 0.0

                output.stop = True

                output.reason = (
                    "STOP command"
                )



            elif name == "EMERGENCY_BRAKE":


                output.target_speed_kmh = 0.0

                output.emergency_stop = True

                output.reason = (
                    "Emergency brake command"
                )



            elif name == "START":


                output.target_speed_kmh = (
                    self.default_speed
                )

                output.reason = (
                    "START command"
                )



            elif name in (
                "AVOID_OBJECT",
                "CHANGE_LANE_LEFT",
                "CHANGE_LANE_RIGHT",
                "TURN_LEFT",
                "TURN_RIGHT",
                "RETURN_TO_LANE"
            ):


                # 横向动作交给B模块
                output.reason = (
                    f"lateral action:{name}"
                )



        return output
