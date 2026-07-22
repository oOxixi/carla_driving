from __future__ import annotations


import json


from .context import Day21Context
from .multimodal_qwen_adapter import Day21QwenAdapter
from .command_adapter import build_command
from .multimodal_results import RESULTS




OUTPUT="integration/day21/day21_multimodal_results.json"





def main():


    qwen=Day21QwenAdapter()


    outputs=[]



    for item in RESULTS:


        context=Day21Context(

            voice_command=
                item.get(
                    "voice",
                    ""
                ),


            scene_state=
                {},



            perception=
                {},



            safety_state=
                item.get(
                    "safety_state",
                    item.get(
                        "safety",
                        {}
                    )
                )

        )



        decision=qwen.infer(
            context
        )



        command=build_command(

            decision,

            context.voice_command

        )



        outputs.append(

            {

                "case":
                    item["case"],



                "expected":
                    item["expected"],



                "decision":
                    decision,



                "command":
                    command,



                "input":

                    {

                        "voice":
                            context.voice_command,


                        "safety_state":
                            context.safety_state

                    }

            }

        )



    with open(

        OUTPUT,

        "w",

        encoding="utf-8"

    ) as f:


        json.dump(

            outputs,

            f,

            indent=2,

            ensure_ascii=False

        )


    print(
        "saved:",
        OUTPUT
    )





if __name__=="__main__":

    main()
