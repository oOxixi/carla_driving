#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import json
import os
from collections import Counter
from datetime import datetime


INPUT_FILES = [

    (
    "ordinary",
    "datasets/language_v11_candidate/"
    "carla_language_ordinary_final_v1.json"
    ),


    (
    "ambiguous_target",
    "datasets/hard_case_templates/"
    "ambiguous_target/ambiguous_target_final.json"
    ),


    (
    "missing_target",
    "datasets/hard_case_templates/"
    "missing_target/missing_target_final.json"
    ),


    (
    "safety_conflict",
    "datasets/hard_case_templates/"
    "safety_conflict/safety_conflict_final_60.json"
    ),


    (
    "occlusion",
    "datasets/hard_case_templates/"
    "occlusion/occlusion_final_72.json"
    ),


    (
    "detector_error",
    "datasets/hard_case_templates/"
    "detector_error/detector_error_clean_v1.json"
    ),


    (
    "dense_target",
    "datasets/hard_case_templates/"
    "dense_target/dense_target_final.json"
    ),


    (
    "compound",
    "datasets/hard_case_templates/"
    "compound/compound_clean_v1.json"
    ),


    (
    "exposure",
    "datasets/hard_case_templates/"
    "exposure/exposure_final.json"
    ),


    (
    "navigation_error",
    "datasets/hard_case_templates/"
    "navigation_error/navigation_error_final.json"
    ),


    (
    "weather_failure",
    "datasets/hard_case_templates/"
    "weather_failure/weather_failure_final.json"
    )

]


OUTPUT_DIR="datasets/final_benchmark"


OUTPUT_FILE=(
"datasets/final_benchmark/"
"CARLA_language_benchmark_v1.json"
)


MANIFEST_FILE=(
"datasets/final_benchmark/"
"dataset_manifest_v1.json"
)



def load_json(path):

    with open(
        path,
        encoding="utf-8"
    ) as f:
        return json.load(f)



def save_json(path,data):

    os.makedirs(
        os.path.dirname(path),
        exist_ok=True
    )

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )



def main():


    merged=[]

    source_stats={}


    for name,path in INPUT_FILES:

        if not os.path.exists(path):

            raise FileNotFoundError(path)


        data=load_json(path)


        source_stats[name]=len(data)


        for item in data:

            merged.append(item)



    # global id rebuild

    for idx,item in enumerate(merged):

        item["id"]=(
            f"carla_language_benchmark_v1_{idx:06d}"
        )



    save_json(
        OUTPUT_FILE,
        merged
    )


    manifest={

        "created":
        datetime.now().isoformat(),

        "version":
        "v1",

        "total_records":
        len(merged),

        "sources":
        source_stats,


        "category_distribution":
        dict(
            Counter(
                x.get("category")
                for x in merged
            )
        ),


        "action_distribution":
        dict(
            Counter(
                x.get("expected_action")
                for x in merged
            )
        )

    }


    save_json(
        MANIFEST_FILE,
        manifest
    )


    print(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2
        )
    )


    print(
        "output:",
        OUTPUT_FILE
    )



if __name__=="__main__":
    main()

