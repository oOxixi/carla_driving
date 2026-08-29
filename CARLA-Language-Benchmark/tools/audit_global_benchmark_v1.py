#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import json
import sys
from collections import Counter


VALID_ACTIONS={

"START",
"KEEP_LANE",
"TURN_LEFT",
"TURN_RIGHT",
"CHANGE_LANE_LEFT",
"CHANGE_LANE_RIGHT",
"SET_SPEED",
"STOP",
"EMERGENCY_STOP",
"AVOID_OBJECT",
"REQUEST_CONFIRMATION"

}



REQUIRED_FIELDS=[

"id",
"category",
"template",
"variables",
"semantic_intent",
"scene_generator",
"scene_constraints",
"expected_action",
"expected_parameters",
"safety_policy"

]



def load_json(path):

    with open(
        path,
        encoding="utf-8"
    ) as f:

        return json.load(f)



def main():

    path=sys.argv[1]


    data=load_json(path)


    errors=[]

    ids=set()

    category=Counter()

    actions=Counter()


    for item in data:


        iid=item.get("id")


        if iid in ids:

            errors.append(
            {
            "id":iid,
            "error":"duplicate_id"
            })

        ids.add(iid)



        for f in REQUIRED_FIELDS:

            if f not in item:

                errors.append(
                {
                "id":iid,
                "error":"missing_field",
                "field":f
                })



        action=item.get(
            "expected_action"
        )


        actions[action]+=1


        if action not in VALID_ACTIONS:

            errors.append(
            {
            "id":iid,
            "error":"invalid_action",
            "value":action
            })



        category[
            item.get("category")
        ]+=1



    report={

    "input":
    path,

    "records":
    len(data),

    "errors":
    len(errors),

    "error_examples":
    errors[:50],

    "category_distribution":
    dict(category),

    "action_distribution":
    dict(actions)

    }



    print(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2
        )
    )



if __name__=="__main__":

    main()
