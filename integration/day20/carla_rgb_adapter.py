from __future__ import annotations

import carla
import os


class CarlaRGBCamera:

    def __init__(
        self,
        world,
        vehicle,
        save_dir="artifacts/day20_rgb"
    ):

        self.world = world
        self.vehicle = vehicle
        self.save_dir = save_dir

        os.makedirs(
            save_dir,
            exist_ok=True
        )

        self.image_path=None
        self.sensor=None


    def start(self):

        blueprint = (
            self.world
            .get_blueprint_library()
            .find(
                "sensor.camera.rgb"
            )
        )


        blueprint.set_attribute(
            "image_size_x",
            "1280"
        )

        blueprint.set_attribute(
            "image_size_y",
            "720"
        )


        transform = carla.Transform(
            carla.Location(
                x=1.5,
                z=2.2
            )
        )


        self.sensor = (
            self.world
            .spawn_actor(
                blueprint,
                transform,
                attach_to=self.vehicle
            )
        )


        self.sensor.listen(
            self._callback
        )



    def _callback(self,image):

        path=os.path.join(
            self.save_dir,
            f"{image.frame}.png"
        )

        image.save_to_disk(
            path
        )

        self.image_path=path



    def get_latest(self):

        return self.image_path



    def stop(self):

        if self.sensor:

            self.sensor.stop()

            self.sensor.destroy()
