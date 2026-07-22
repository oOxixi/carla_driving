from __future__ import annotations


import math



def calculate_distance(
    a,
    b
):
    """
    CARLA Location距离
    """

    return a.distance(b)





def is_front_vehicle(
    ego,
    actor
):
    """
    判断目标是否在ego前方
    """

    ego_tf = ego.get_transform()

    actor_loc = actor.get_location()

    ego_loc = ego_tf.location


    dx = actor_loc.x - ego_loc.x

    dy = actor_loc.y - ego_loc.y



    yaw = math.radians(
        ego_tf.rotation.yaw
    )


    forward_x = math.cos(
        yaw
    )

    forward_y = math.sin(
        yaw
    )


    dot = (
        dx * forward_x
        +
        dy * forward_y
    )


    return dot > 0






def build_scene_state(
    world,
    ego
):

    """
    CARLA真实SceneState

    不修改integration/contracts
    只生成Qwen输入
    """



    frame_id = (
        world.get_snapshot()
        .frame
    )



    ego_tf = ego.get_transform()


    velocity = ego.get_velocity()


    speed = math.sqrt(
        velocity.x**2
        +
        velocity.y**2
        +
        velocity.z**2
    )


    objects=[]



    actors = world.get_actors()


    for actor in actors:


        if actor.id == ego.id:

            continue



        if not actor.type_id.startswith(
            "vehicle."
        ):

            continue



        distance = calculate_distance(

            actor.get_location(),

            ego_tf.location

        )



        if distance < 50:


            if not is_front_vehicle(
                ego,
                actor
            ):

                continue



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





    weather = world.get_weather()



    scene = {


        "frame_id":

            frame_id,



        "ego":

        {

            "speed_kmh":

                round(
                    speed * 3.6,
                    2
                ),


            "lane_id":

                0

        },


        "weather":

        {

            "rain":

                float(
                    weather.precipitation
                ),


            "night":

                bool(
                    weather.sun_altitude_angle < 0
                )

        },


        "objects":

            objects

    }



    return scene

