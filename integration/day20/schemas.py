from __future__ import annotations

from dataclasses import dataclass


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
class Action:


    action: str

    target_id: str = ""

    target_speed_kmh: float = 0.0


    def to_dict(self):

        return {

            "action":
                self.action,

            "target_id":
                self.target_id,

            "target_speed_kmh":
                self.target_speed_kmh,
        }



@dataclass
class DrivingIntent:


    command_id: str

    actions: list[Action]

    confidence: float

    reason: str


    def to_dict(self):

        return {

            "command_id":
                self.command_id,


            "actions":
                [
                    a.to_dict()
                    for a in self.actions
                ],


            "confidence":
                self.confidence,


            "reason":
                self.reason,
        }



def validate_driving_intent(intent: DrivingIntent):

    errors = []

    if not intent.actions:
        errors.append(
            "actions must not be empty"
        )

    for action in intent.actions:


        if action.action not in ALLOWED_ACTIONS:

            errors.append(
                f"invalid action:{action.action}"
            )


    if not 0<=intent.confidence<=1:

        errors.append(
            "confidence error"
        )


    return {

        "valid":
            len(errors)==0,

        "errors":
            errors
    }
