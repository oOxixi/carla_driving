#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import json
from datetime import datetime


INPUT = (
"datasets/final_benchmark/"
"CARLA_language_benchmark_v1.json"
)


OUTPUT = (
"datasets/final_benchmark/"
"CARLA_language_benchmark_v1_normalized.json"
)


DEFAULTS={

"variables": {},

"expected_parameters": {},

"scene_constraints": {},

"safety_policy":"normal"

}



def main():


    with open(
        INPUT,
        encoding="utf-8"
    ) as f:

        data=json.load(f)



    fixed=0


    for item in data:


        for k,v in DEFAULTS.items():

            if k not in item:

                item[k]=v

                fixed+=1



    with open(
        OUTPUT,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )



    print(
        json.dumps(
        {
        "created":
        datetime.now().isoformat(),

        "records":
        len(data),

        "fields_added":
        fixed,

        "output":
        OUTPUT
        },

        ensure_ascii=False,

        indent=2
        )
    )


if __name__=="__main__":
    main()
