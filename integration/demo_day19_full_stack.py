from __future__ import annotations

import time
import carla


from car_control_D.safety_supervisor import SafetySupervisor

from .carla_state_adapter import get_vehicle_state



def spawn_vehicle(world):

    blueprint_library = world.get_blueprint_library()

    vehicles = blueprint_library.filter(
        "vehicle.tesla.model3"
    )

    if not vehicles:
        vehicles = blueprint_library.filter(
            "vehicle.*"
        )

    if not vehicles:
        raise RuntimeError(
            "No vehicle blueprint found"
        )

    bp = vehicles[0]

    spawn_points = (
        world
        .get_map()
        .get_spawn_points()
    )

    for point in spawn_points:

        vehicle = world.try_spawn_actor(
            bp,
            point
        )

        if vehicle is not None:
            return vehicle


    raise RuntimeError(
        "vehicle spawn failed"
    )



def apply_control(vehicle, control):

    cmd = carla.VehicleControl()

    cmd.throttle = float(
        control.throttle
    )

    cmd.brake = float(
        control.brake
    )

    cmd.steer = float(
        control.steer
    )

    vehicle.apply_control(cmd)



def main():

    client = carla.Client(
        "127.0.0.1",
        2000
    )

    client.set_timeout(30)


    world = client.get_world()


    print(
        "CARLA:",
        world.get_map().name
    )


    vehicle = None


    try:

        vehicle = spawn_vehicle(
            world
        )


        print(
            "ego vehicle:",
            vehicle.id
        )


        supervisor = SafetySupervisor()


        # 模拟合法语音控制结果
        # 对应上游ASR/NLU输出
        command = {
            "schema_version": "1.0",

            "command_id": "demo_cmd_001",

            "source_text": "进入隧道了，减速",

            # 必须是系统支持的 intent
            "intent": "SLOW_DOWN",

            "parameters": {
                "mode": "RELATIVE",
                "action": "DECELERATE"
            },

            "asr_confidence": None,

            "intent_confidence": 0.95,

            "confidence": 0.95,

            "status": "valid",

            "ambiguity_type": "NONE",

            "confirm_required": False,

            "errors": [],

            "warnings": [],

            "t_audio_start_ns": None,

            "t_asr_end_ns": None,

            "t_intent_end_ns": None,

            "valid_duration_s": 5.0,
        }


        for i in range(10):

            frame = world.tick()


            state = get_vehicle_state(
                vehicle,
                world,
                frame
            )


            decision = supervisor.arbitrate(

                raw_control={

                    "throttle":
                        0.25,

                    "brake":
                        0.0,

                    "steer":
                        0.0,
                },


                vehicle_state=state,


                command=command,


                risk={

                    "ttc_s":
                        10.0,

                    "desired_gap_m":
                        20.0,

                    "emergency_brake_requested":
                        False,
                },


                watchdog_alerts=[]
            )


            apply_control(
                vehicle,
                decision.final_control
            )


            print(

                {

                    "frame":
                        frame,


                    "speed":
                        round(
                            state["speed_mps"],
                            3
                        ),


                    "override":
                        decision.safety_override,


                    "reason":
                        decision.reason,


                    "control":
                        decision
                        .final_control
                        .to_dict()
                }

            )


            time.sleep(0.1)



    finally:

        if vehicle is not None:

            vehicle.destroy()

            print(
                "vehicle destroyed"
            )



if __name__ == "__main__":
    main()
