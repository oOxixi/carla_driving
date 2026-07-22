from __future__ import annotations

import os
import json
import time
import queue

import carla


from .scene_builder import build_scene_state
from .qwen_vl_adapter import QwenVLAdapter
from .parser import parse_intent
from .schemas import validate_driving_intent



IMAGE_DIR = "artifacts/day20_rgb_frames"



class RGBSensor:


    def __init__(self):

        self.queue = queue.Queue()



    def callback(self, image):

        self.queue.put(image)



    def get_latest(self):

        image=None


        while not self.queue.empty():

            image=self.queue.get()


        return image





def spawn_vehicle(world):


    library = world.get_blueprint_library()


    vehicles = library.filter(
        "vehicle.tesla.model3"
    )


    if not vehicles:

        vehicles = library.filter(
            "vehicle.*"
        )


    if not vehicles:

        raise RuntimeError(
            "no vehicle blueprint"
        )


    spawn_points = (
        world
        .get_map()
        .get_spawn_points()
    )


    for point in spawn_points:


        vehicle = world.try_spawn_actor(
            vehicles[0],
            point
        )


        if vehicle:

            return vehicle



    raise RuntimeError(
        "spawn failed"
    )





def attach_camera(world, vehicle):


    bp = world.get_blueprint_library().find(
        "sensor.camera.rgb"
    )


    bp.set_attribute(
        "image_size_x",
        "1280"
    )

    bp.set_attribute(
        "image_size_y",
        "720"
    )


    transform = carla.Transform(
        carla.Location(
            x=1.5,
            z=2.4
        )
    )


    camera = world.spawn_actor(
        bp,
        transform,
        attach_to=vehicle
    )


    return camera





def save_image(image, frame):


    os.makedirs(
        IMAGE_DIR,
        exist_ok=True
    )


    path=os.path.join(
        IMAGE_DIR,
        f"{frame}.png"
    )


    image.save_to_disk(
        path
    )


    return path





def main():


    client=carla.Client(
        "127.0.0.1",
        2000
    )


    client.set_timeout(
        30
    )


    world=client.get_world()


    print(
        "CARLA:",
        world.get_map().name
    )



    vehicle=None
    camera=None



    try:


        vehicle=spawn_vehicle(
            world
        )


        print(
            "ego vehicle:",
            vehicle.id
        )



        sensor=RGBSensor()


        camera=attach_camera(
            world,
            vehicle
        )


        camera.listen(
            sensor.callback
        )



        qwen=QwenVLAdapter()



        for _ in range(10):


            frame=world.tick()



            image=sensor.get_latest()


            if image is None:

                continue



            image_path=save_image(
                image,
                frame
            )



            scene=build_scene_state(
                frame_id=frame,
                vehicle=vehicle
            )



            print(
                "\n===== SCENE STATE ====="
            )


            print(
                json.dumps(
                    scene,
                    indent=2,
                    ensure_ascii=False
                )
            )



            raw_command=qwen.infer(

                command=
                "前方车辆减速，请降低速度保持安全距离",

                scene_state=scene,

                image_path=image_path
            )



            intent=parse_intent(
                raw_command
            )



            print(
                "\n===== DRIVING INTENT ====="
            )


            print(
                json.dumps(
                    intent.to_dict(),
                    indent=2,
                    ensure_ascii=False
                )
            )



            print(
                "\n===== DAY20 VALIDATE ====="
            )


            print(
                validate_driving_intent(
                    intent
                )
            )


            time.sleep(1)




    finally:


        if camera:

            camera.stop()
            camera.destroy()



        if vehicle:

            vehicle.destroy()



        print(
            "cleanup"
        )





if __name__=="__main__":

    main()

