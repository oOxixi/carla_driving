from __future__ import annotations

import json


RESULT_FILE="integration/day21/day21_multimodal_results.json"

OUTPUT_FILE="integration/day21/day21_validation_report.json"



def main():


    with open(
        RESULT_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        results=json.load(f)



    total=len(results)

    passed=0

    failed=[]



    for item in results:


        expected=item["expected"]


        actual=item["decision"]["action"]



        # STOP_CONFIRM允许映射为STOP

        if expected=="STOP_CONFIRM":

            ok = (

                actual=="STOP"

                and

                item["decision"].get(
                    "requires_confirmation",
                    False
                )

            )

        else:

            ok = actual==expected



        if ok:

            passed+=1

        else:

            failed.append(

                {

                    "case":
                        item["case"],

                    "expected":
                        expected,

                    "actual":
                        actual

                }

            )



    report={


        "schema_version":
            "1.0",


        "total_cases":
            total,


        "passed":
            passed,


        "failed":
            len(failed),


        "accuracy":
            passed/total if total else 0,


        "failed_cases":
            failed

    }



    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:


        json.dump(

            report,

            f,

            indent=2,

            ensure_ascii=False

        )


    print(
        "saved:",
        OUTPUT_FILE
    )



if __name__=="__main__":

    main()
