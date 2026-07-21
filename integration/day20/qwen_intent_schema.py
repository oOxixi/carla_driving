from dataclasses import dataclass, field
from typing import Dict, Any, List


ALLOWED_ACTIONS = {
    "START",
    "STOP",
    "SET_SPEED",
    "TURN_LEFT",
    "TURN_RIGHT",
    "CHANGE_LANE_LEFT",
    "CHANGE_LANE_RIGHT",
    "AVOID_OBJECT",
    "EMERGENCY_BRAKE",
    "RETURN_TO_LANE",
}


@dataclass
class ActionStep:

    action: str

    target_id: str = ""

    target_speed_kmh: float = 0.0


    def to_dict(self):

        return {
            "action": self.action,
            "target_id": self.target_id,
            "target_speed_kmh": self.target_speed_kmh,
        }



@dataclass
class DrivingIntent:

    command_id: str

    actions: List[ActionStep]

    confidence: float

    reason: str


    def to_dict(self):

        return {

            "command_id":
                self.command_id,


            "actions":
                [
                    x.to_dict()
                    for x in self.actions
                ],


            "confidence":
                self.confidence,


            "reason":
                self.reason,
        }



def validate_intent(intent: DrivingIntent):


    errors=[]


    for action in intent.actions:

        if action.action not in ALLOWED_ACTIONS:

            errors.append(
                f"invalid action {action.action}"
            )


    if not 0<=intent.confidence<=1:

        errors.append(
            "invalid confidence"
        )


    return {

        "valid":
            len(errors)==0,

        "errors":
            errors
    }
