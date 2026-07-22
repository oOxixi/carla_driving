from __future__ import annotations


from .qwen_decision_parser import parse_qwen_output
from .command_adapter import build_qwen_command


def main():


    qwen_output="""

{
"action":"STOP",
"target_speed_mps":null,
"confidence":0.96,
"reason_zh":"前方红灯停车"
}

"""


    decision=parse_qwen_output(
        qwen_output
    )


    command=build_qwen_command(
        decision,
        "前方红灯停车"
    )


    print(
        "===== DAY21 COMMAND ====="
    )


    import json

    print(
        json.dumps(
            command,
            indent=2,
            ensure_ascii=False
        )
    )



if __name__=="__main__":

    main()
