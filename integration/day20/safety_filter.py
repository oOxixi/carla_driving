from __future__ import annotations


from .schemas import (
    DrivingIntent,
    Action,
)



MAX_SPEED=120.0
MIN_SPEED=0.0



def safety_filter(
    intent:DrivingIntent
):


    new_actions=[]


    for action in intent.actions:


        if action.action=="SET_SPEED":


            speed=max(
                MIN_SPEED,
                min(
                    MAX_SPEED,
                    action.target_speed_kmh
                )
            )


            new_actions.append(
                Action(

                    action="SET_SPEED",

                    target_id=action.target_id,

                    target_speed_kmh=speed

                )
            )



        elif action.action in {

            "STOP",

            "EMERGENCY_BRAKE"

        }:


            new_actions.append(
                action
            )


        else:

            new_actions.append(
                action
            )



    intent.actions=new_actions



    intent.confidence=max(
        0.0,
        min(
            1.0,
            intent.confidence
        )
    )



    return intent
