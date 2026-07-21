from __future__ import annotations


import carla
import time


from car_control_D.safety_supervisor import SafetySupervisor


from integration.day20.carla_rgb_adapter import CarlaRGBCamera

from integration.day20.carla_scene_builder import build_scene_state

from integration.day20.qwen_multimodal import QwenMultimodalDriver



def spawn_vehicle(world):


    bp=world.get_blueprint_library().filter(
        "vehicle.tesla.model3"
    )[0]


    for p in world.get_map().get_spawn_points():

        v=world.try_spawn_actor(
            bp,
            p
        )

        if v:
            return v


    raise RuntimeError(
        "spawn failed"
    )




def apply_control(
    vehicle,
    control
):

    cmd=carla.VehicleControl()


    cmd.throttle=float(
        control.throttle
    )

    cmd.brake=float(
        control.brake
    )

    cmd.steer=float(
        control.steer
    )


    vehicle.apply_control(
        cmd
    )





def main():

    client=carla.Client(
        "127.0.0.1",
        2000
    )

    client.set_timeout(30)


    world=client.get_world()


    vehicle=None


    try:

        print(
            "CARLA:",
            world.get_map().name
        )


        vehicle=spawn_vehicle(
            world
        )


        print(
            "ego:",
            vehicle.id
        )


        camera=CarlaRGBCamera(
            world,
            vehicle
        )


        camera.start()


        qwen=QwenMultimodalDriver()


        safety=SafetySupervisor()



        for i in range(20):


            frame=world.tick()


            time.sleep(
                0.2
            )


            scene=build_scene_state(
                vehicle,
                world,
                frame
            )


            image=camera.get_latest()



            command=qwen.infer(

                "前方车辆减速，请降低速度保持距离",

                scene,

                image

            )


            print(
                "COMMAND:",
                command
            )



            decision=safety.arbitrate(

                raw_control={

                    "throttle":0.2,

                    "brake":0.0,

                    "steer":0.0

                },


                vehicle_state={},

                command=command,


                risk={

                    "ttc_s":10,

                    "desired_gap_m":20,

                    "emergency_brake_requested":False

                },


                watchdog_alerts=[]

            )



            apply_control(
                vehicle,
                decision.final_control
            )



            print(
                {
                "frame":frame,
                "override":
                    decision.safety_override,
                "reason":
                    decision.reason
                }
            )


    finally:


        if vehicle:

            vehicle.destroy()



if __name__=="__main__":

    main()
