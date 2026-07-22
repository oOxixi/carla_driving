from __future__ import annotations

import uuid
import time



def build_command(
    decision,
    source_text
):


    parameters={}


    if decision.get(
        "action"
    )=="SET_SPEED":


        parameters={

            "speed":
                float(
                    decision.get(
                        "target_speed_mps",
                        0
                    )
                ),

            "unit":
                "m/s"

        }



    return {


        "schema_version":
            "1.0",


        "command_id":
            "qwen_day21_" +
            uuid.uuid4().hex[:8],


        "source_text":
            source_text,


        "intent":
            decision.get(
                "action"
            ),


        "parameters":
            parameters,


        "confidence":
            float(
                decision.get(
                    "confidence",
                    0
                )
            ),


        "status":
            "valid",


        "ambiguity_type":
            "NONE",


        "confirm_required":
            bool(
                decision.get(
                    "requires_confirmation",
                    False
                )
            ),


        "errors":
            [],


        "warnings":
            [],


        "valid_duration_s":
            3.0,


        "t_audio_start_ns":
            None,


        "t_asr_end_ns":
            None,


        "t_intent_end_ns":
            time.monotonic_ns()

    }
