from __future__ import annotations


def build_scene_state(
    vehicle,
    world,
    frame
):

    transform=vehicle.get_transform()

    velocity=vehicle.get_velocity()


    speed=(velocity.x**2+
           velocity.y**2+
           velocity.z**2)**0.5


    objects=[]


    actors=world.get_actors().filter(
        "vehicle.*"
    )


    for actor in actors:


        if actor.id==vehicle.id:
            continue


        distance=(
            actor.get_location()
            .distance(
                vehicle.get_location()
            )
        )


        if distance < 50:


            objects.append(
                {
                    "object_id":
                        str(actor.id),

                    "category":
                        "vehicle",

                    "distance_m":
                        round(
                            distance,
                            2
                        ),

                    "direction":
                        "front",

                    "confidence":
                        1.0
                }
            )


    return {

        "frame_id":
            frame,


        "ego":
            {

            "speed_kmh":
                round(
                    speed*3.6,
                    2
                ),

            "lane_id":
                0

            },


        "weather":
            {
            "rain":
                world.get_weather()
                .precipitation,

            "night":
                False
            },


        "objects":
            objects

    }
