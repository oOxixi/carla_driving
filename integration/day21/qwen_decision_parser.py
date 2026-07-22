from __future__ import annotations

import json
import re



def extract_json(text):

    if not isinstance(text,str):

        return {}


    blocks = re.findall(
        r"```json\s*(.*?)```",
        text,
        flags=re.S
    )


    candidates = blocks + [text]


    for item in candidates:

        s=item.find("{")

        e=item.rfind("}")


        if s>=0 and e>s:

            try:

                return json.loads(
                    item[s:e+1]
                )

            except Exception:

                pass


    return {}




def parse_qwen_output(text):


    data=extract_json(text)


    return {

        "action":
            str(
                data.get(
                    "action",
                    "UNKNOWN"
                )
            ).upper(),


        "target_speed_mps":
            data.get(
                "target_speed_mps"
            ),


        "confidence":
            float(
                data.get(
                    "confidence",
                    0.0
                )
            ),


        "reason_zh":
            str(
                data.get(
                    "reason_zh",
                    ""
                )
            )

    }
