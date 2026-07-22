from __future__ import annotations


import os
import time
import json

import carla


from .qwen_vl_adapter import QwenVLAdapter
from .scene_builder import build_scene_state
from .parser import parse_intent
from .schemas import validate_driving_intent
from .day20_intent_executor import Day20IntentExecutor, IntentControlOutput
from .carla_control_adapter import CarlaControlAdapter
from .safety_filter import safety_filter



MODEL_PATH = "models/Qwen2.5-VL-7B"



ARTIFACT_DIR = "artifacts/day20"



def save_json(
    filename,
    data
):

    os.makedirs(
        ARTIFACT_DIR,
        exist_ok=True
    )


    path=os.path.join(
        ARTIFACT_DIR,
        filename
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


    return path




def spawn_vehicle(
    world,
    vehicle_filter
):

    bp_lib = world.get_blueprint_library()


    vehicles = bp_lib.filter(
        vehicle_filter
    )


    if not vehicles:

        raise RuntimeError(
            f"vehicle not found:{vehicle_filter}"
        )


    bp=vehicles[0]


    for sp in world.get_map().get_spawn_points():

        actor=world.try_spawn_actor(
            bp,
            sp
        )


        if actor:

            return actor,sp



    raise RuntimeError(
        "spawn failed"
    )





def apply_scenario_actor_speed(
    vehicle,
    throttle
):

    control=carla.VehicleControl()

    control.throttle=throttle

    control.brake=0.0

    control.steer=0.0


    vehicle.apply_control(
        control
    )





def brake_scenario_actor(
    vehicle
):

    control=carla.VehicleControl()

    control.throttle=0.0

    control.brake=1.0

    control.steer=0.0


    vehicle.apply_control(
        control
    )






def attach_rgb_camera(
    world,
    ego
):

    bp=(
        world
        .get_blueprint_library()
        .find(
            "sensor.camera.rgb"
        )
    )


    bp.set_attribute(
        "image_size_x",
        "800"
    )


    bp.set_attribute(
        "image_size_y",
        "600"
    )


    transform=carla.Transform(

        carla.Location(
            x=1.5,
            z=2.4
        )

    )


    return world.spawn_actor(
        bp,
        transform,
        attach_to=ego
    )





def main():


    os.makedirs(
        ARTIFACT_DIR,
        exist_ok=True
    )


    client=carla.Client(
        "127.0.0.1",
        2000
    )


    client.set_timeout(
        30
    )


    world=client.get_world()



    print(
        "MAP:",
        world.get_map().name
    )



    ego=None

    front=None

    camera=None



    try:


        ego,ego_tf=spawn_vehicle(

            world,

            "vehicle.tesla.model3"

        )


        print(
            "ego:",
            ego.id
        )




        front_tf=carla.Transform(

            ego_tf.location+
            carla.Location(
                x=25
            ),

            ego_tf.rotation

        )



        front_bp=(

            world
            .get_blueprint_library()
            .filter(
                "vehicle.audi.a2"
            )[0]

        )



        front=world.try_spawn_actor(

            front_bp,

            front_tf

        )



        if front is None:

            raise RuntimeError(
                "front spawn failed"
            )



        print(
            "front vehicle:",
            front.id
        )




        apply_scenario_actor_speed(
            front,
            0.25
        )





        camera=attach_rgb_camera(
            world,
            ego
        )


        print(
            "RGB camera ready"
        )



        rgb={
            "path":None
        }





        def callback(image):


            os.makedirs(
                "artifacts",
                exist_ok=True
            )


            path=(

                f"artifacts/day20_rgb_{image.frame}.png"

            )


            image.save_to_disk(
                path
            )


            rgb["path"]=path




        camera.listen(
            callback
        )




        qwen=QwenVLAdapter(
            MODEL_PATH
        )


        executor=Day20IntentExecutor()


        controller=CarlaControlAdapter()

        controller.apply(
            ego,
            IntentControlOutput(
                target_speed_kmh=20.0,
                reason="Day20 bootstrap through D",
            ),
            scene_state=build_scene_state(world, ego),
            command_id="day20_bootstrap",
            confidence=1.0,
        )



        triggered=False

        decision_done=False




        for step in range(100):


            world.tick()


            time.sleep(
                0.05
            )



            if step==30:


                print(
                    "front vehicle brake"
                )


                brake_scenario_actor(
                    front
                )


                triggered=True





            scene=build_scene_state(

                world,

                ego

            )




            if step%10==0:


                print(
                    "===== SCENE ====="
                )


                print(

                    json.dumps(

                        scene,

                        indent=2,

                        ensure_ascii=False

                    )

                )



                save_json(

                    f"scene_{scene['frame_id']}.json",

                    scene

                )





            if (

                not triggered

                or decision_done

                or rgb["path"] is None

            ):

                continue





            command=(

                "前方车辆减速，请降低速度保持安全距离"

            )





            raw=qwen.infer(

                command,

                scene,

                rgb["path"]

            )





            save_json(

                "qwen_raw_output.json",

                {

                    "command":command,

                    "scene":scene,

                    "rgb":rgb["path"],

                    "raw_output":raw

                }

            )






            intent=parse_intent(
                raw
            )



            # =========================
            # Safety Layer
            # =========================

            intent=safety_filter(
                intent
            )



            print(
                "===== DRIVING INTENT ====="
            )


            print(

                json.dumps(

                    intent.to_dict(),

                    indent=2,

                    ensure_ascii=False

                )

            )



            save_json(

                "driving_intent.json",

                intent.to_dict()

            )




            validation=validate_driving_intent(

                intent

            )


            print(
                validation
            )






            target=executor.execute(

                intent

            )



            print(
                "===== EXECUTOR ====="
            )


            print(
                target.__dict__
            )



            save_json(

                "executor_target.json",

                target.__dict__

            )






            result=controller.apply(

                ego,

                target,

                scene_state=scene,

                command_id=intent.command_id,

                confidence=intent.confidence,

            )



            print(
                "===== CARLA CONTROL ====="
            )


            print(
                result
            )



            save_json(

                "carla_control.json",

                result

            )



            decision_done=True


            break






    finally:



        if camera:

            camera.stop()

            camera.destroy()



        if front:

            front.destroy()



        if ego:

            ego.destroy()



        print(
            "cleanup"
        )





if __name__=="__main__":

    main()
