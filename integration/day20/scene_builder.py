from __future__ import annotations


import math

from integration.carla_perception import (
    actor_speed_limit_mps,
    lane_metrics,
    traffic_light_and_stop_distance,
)



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



    snapshot = world.get_snapshot()
    frame_id = snapshot.frame



    ego_tf = ego.get_transform()


    velocity = ego.get_velocity()


    speed = math.hypot(velocity.x, velocity.y)

    world_map = world.get_map()
    waypoint = world_map.get_waypoint(ego_tf.location, project_to_road=True)
    lane_id = int(waypoint.lane_id) if waypoint is not None else 0
    lane_offset, route_deviation = lane_metrics(world_map, ego, None)
    traffic_light, stop_distance, _ = traffic_light_and_stop_distance(ego)
    speed_limit = actor_speed_limit_mps(ego)


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

        "sim_time_s":

            float(snapshot.timestamp.elapsed_seconds),



        "ego":

        {

            "speed_kmh":

                round(
                    speed * 3.6,
                    2
                ),


            "lane_id":

                lane_id

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

            objects,

        "traffic_light":

            traffic_light,

        "distance_to_stop_line_m":

            stop_distance,

        "speed_limit_mps":

            speed_limit,

        "lane_offset_m":

            lane_offset,

        "route_deviation_m":

            route_deviation,

    }



    return scene

