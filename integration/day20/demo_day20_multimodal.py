import json


from .scene_builder import build_demo_scene

from .qwen_vl_adapter import QwenVLIntentAdapter

from .parser import parse_intent

from .schemas import validate_driving_intent



def main():


    scene=build_demo_scene()


    print(
        "SCENE:"
    )


    print(

        json.dumps(

            scene.to_dict(),

            ensure_ascii=False,

            indent=2

        )

    )



    qwen=QwenVLIntentAdapter()



    raw=qwen.infer(

        command_text=

        "前方车辆减速，请降低速度保持距离",

        scene_state=

            scene.to_dict(),

        image_path=None

    )



    intent=parse_intent(raw)



    print(
        "===== INTENT ====="
    )


    print(

        json.dumps(

            intent.to_dict(),

            ensure_ascii=False,

            indent=2

        )

    )


    print(
        validate_driving_intent(intent)
    )



if __name__=="__main__":

    main()
