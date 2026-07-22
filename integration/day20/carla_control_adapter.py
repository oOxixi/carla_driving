from __future__ import annotations

import math
import carla



class CarlaControlAdapter:

    """
    Day20 high-level intent
    ->
    CARLA VehicleControl

    Qwen only outputs:
        SET_SPEED
        STOP
        EMERGENCY_BRAKE

    Never output:
        throttle
        brake
        steer
    """



    def get_speed_kmh(
        self,
        vehicle
    ):

        velocity = vehicle.get_velocity()

        speed = math.sqrt(
            velocity.x ** 2 +
            velocity.y ** 2 +
            velocity.z ** 2
        )

        return speed * 3.6



    def apply(
        self,
        vehicle,
        control_target
    ):


        control = carla.VehicleControl()


        current_speed = self.get_speed_kmh(
            vehicle
        )


        target_speed = (
            control_target.target_speed_kmh
        )



        # emergency
        if control_target.emergency_stop:

            control.throttle = 0.0

            control.brake = 1.0

            reason = "emergency_stop"



        # stop
        elif control_target.stop:

            control.throttle = 0.0

            control.brake = 0.8

            reason = "stop"



        # speed control
        elif target_speed is not None:


            if current_speed < target_speed - 1:


                control.throttle = 0.35

                control.brake = 0.0


            elif current_speed > target_speed + 2:


                control.throttle = 0.0

                control.brake = 0.35


            else:

                control.throttle = 0.15

                control.brake = 0.0


            reason = (
                f"target_speed={target_speed}"
            )


        else:


            control.throttle = 0.0

            control.brake = 0.0

            reason="no_action"



        vehicle.apply_control(
            control
        )



        return {

            "current_speed_kmh":
                round(
                    current_speed,
                    2
                ),

            "target_speed_kmh":
                target_speed,


            "control":
                {

                    "throttle":
                        control.throttle,

                    "brake":
                        control.brake,

                    "steer":
                        control.steer
                },


            "reason":
                reason
        }
