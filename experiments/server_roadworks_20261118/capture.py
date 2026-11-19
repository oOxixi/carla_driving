import argparse
import json
import math
import queue
from pathlib import Path

import carla


WIDTH, HEIGHT, FOV = 1920, 1200, 54
CANDIDATES = {
    'south': (4, 2, 16),
    'north': (7, -2, 12),
    'park': (8, -2, 8),
    'avenue': (5, 2, 92),
    'downtown': (20, -2, 4),
    'boulevard': (20, 5, 63),
}

def xyz(obj):
    return [obj.x, obj.y, obj.z]

def world_point(wp, right=0, up=0, forward=0):
    tf = wp.transform
    loc = tf.location
    side = tf.get_right_vector()
    front = tf.get_forward_vector()
    return carla.Location(
        loc.x + side.x * right + front.x * forward,
        loc.y + side.y * right + front.y * forward,
        loc.z + up,
    )

def pose(wp, right=0, z=0, yaw=0, forward=0):
    loc = world_point(wp, right, z, forward)
    return carla.Transform(loc, carla.Rotation(yaw=wp.transform.rotation.yaw+yaw))

def waypoint_at(origin, meters):
    if meters == 0:
        return origin
    choices = origin.next(meters) if meters > 0 else origin.previous(-meters)
    if len(choices) != 1:
        raise RuntimeError(f'No unique route at {meters} m')
    return choices[0]

def left_of(wp):
    left = wp.get_left_lane()
    if (not left or left.lane_type != carla.LaneType.Driving
            or left.lane_id * wp.lane_id <= 0):
        raise RuntimeError(f'No same-direction left lane near {wp}')
    return left

def project(point, inverse_matrix):
    v = [sum(a*b for a, b in zip(row, [*xyz(point),1])) for row in inverse_matrix]
    f = WIDTH / (2*math.tan(math.radians(FOV/2)))
    return [WIDTH/2 + f*v[1]/v[0], HEIGHT/2 - f*v[2]/v[0]]

def smooth(value):
    t = min(1, max(0, value))
    return t*t*t*(t*(6*t-15)+10)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('candidate', choices=CANDIDATES)
    parser.add_argument('--port', type=int, default=24560)
    parser.add_argument('--camera-height', type=float, default=6.25)
    parser.add_argument('--camera-back', type=float, default=10.35)
    parser.add_argument('--camera-pitch', type=float, default=-14.5)
    parser.add_argument('--sun-relative', type=float, default=-115)
    parser.add_argument('--bike', default='vehicle.diamondback.century')
    args = parser.parse_args()

    out = Path(__file__).resolve().parent
    client = carla.Client('127.0.0.1', args.port)
    client.set_timeout(35)
    world = client.get_world()
    road_map = world.get_map()
    origin = road_map.get_waypoint_xodr(*CANDIDATES[args.candidate])
    if origin is None:
        raise RuntimeError('Could not locate selected road waypoint')
    for meter in range(0, 46, 2):
        left_of(waypoint_at(origin,meter))
    print('road', args.candidate, origin, 'width', origin.lane_width, flush=True)

    initial_weather = world.get_weather()
    initial_settings = world.get_settings()
    settings = world.get_settings()
    settings.synchronous_mode = True
    settings.fixed_delta_seconds = 0.05
    settings.no_rendering_mode = False
    lib = world.get_blueprint_library()
    actors = {}
    camera = None

    def spawn(name, blue_id, tf, color=None):
        bp = lib.find(blue_id)
        if color and bp.has_attribute('color'):
            bp.set_attribute('color', color)
        if bp.has_attribute('role_name'):
            bp.set_attribute('role_name', name)
        actor = world.try_spawn_actor(bp, tf)
        if actor is None:
            raise RuntimeError(f'Could not spawn {name} at {tf}')
        actors[name] = actor
        return actor

    try:
        world.apply_settings(settings)
        weather = carla.WeatherParameters.ClearNoon
        weather.sun_altitude_angle = 46
        weather.sun_azimuth_angle = (origin.transform.rotation.yaw+args.sun_relative)%360
        weather.cloudiness = 10
        world.set_weather(weather)

        ego = spawn('ego','vehicle.lincoln.mkz_2020',pose(origin, -0.15, 0.20),
                    '22,43,85')
        ego.apply_control(carla.VehicleControl(brake=1, hand_brake=True))
        bike = spawn('bike', args.bike, pose(waypoint_at(origin,16.2),-0.64,0.14))
        side = origin.lane_width/2
        inner = 0.22
        outer = side-0.10
        for index,meter in enumerate([10.5, 13.9, 17.1, 20.6, 24.0, 27.2]):
            wp = waypoint_at(origin,meter)
            spawn(f'cone_inner_{index}','static.prop.trafficcone01',pose(wp,inner,0.02))
            spawn(f'cone_outer_{index}','static.prop.trafficcone01',pose(wp,outer,0.02))
        for index,meter in enumerate([17.85, 22.5, 26.05]):
            spawn(f'barrier_{index}','static.prop.streetbarrier',
                  pose(waypoint_at(origin,meter), (inner+outer)/2,0.015,yaw=12-5*index))
        spawn('warning','static.prop.warningconstruction',
              pose(waypoint_at(origin,12.45), (inner+outer)/2,0.03,yaw=175))
        spawn('debris','static.prop.dirtdebris02',
              pose(waypoint_at(origin,21.0), (inner+outer)/2,0.015,yaw=17))

        cam_bp = lib.find('sensor.camera.rgb')
        for k,v in {'image_size_x':WIDTH,'image_size_y':HEIGHT,'fov':FOV,
                    'motion_blur_intensity':0,'lens_flare_intensity':0}.items():
            if cam_bp.has_attribute(k):
                cam_bp.set_attribute(k, str(v))
        cam_tf = carla.Transform(
            world_point(origin, 0.65, args.camera_height, -args.camera_back),
            carla.Rotation(pitch=args.camera_pitch, yaw=origin.transform.rotation.yaw+0.7),
        )
        camera = world.spawn_actor(cam_bp,cam_tf)
        frames = queue.Queue()
        camera.listen(frames.put)
        world.get_spectator().set_transform(cam_tf)

        front = world_point(waypoint_at(origin,16.2),0) - world_point(origin,0)
        bike_yaw = math.atan2(front.y,front.x)
        speed = 2.6
        for step in range(25):
            if step >= 8:
                bike.set_target_velocity(carla.Vector3D(speed*math.cos(bike_yaw),speed*math.sin(bike_yaw),0))
            frame = world.tick(20)
        image = frames.get(timeout=20)
        while image.frame < frame-2:
            image = frames.get(timeout=20)
        raw_path = out / f'{args.candidate}_rgb.png'
        raw_path.unlink(missing_ok=True)
        image.save_to_disk(str(raw_path))
        measured = bike.get_velocity()
        bike_speed_kph = 3.6*math.hypot(measured.x, measured.y)
        print('camera frame',image.frame, 'bike km/h', round(bike_speed_kph,2),
              'bike transform', bike.get_transform(), flush=True)

        def flat(d,r):
            return project(world_point(waypoint_at(origin,d),r,0.035),image.transform.get_inverse_matrix())

        def marker(actor,z):
            v = actor.get_location()
            return project(carla.Location(v.x,v.y,v.z+z),image.transform.get_inverse_matrix())

        path = []
        for i in range(153):
            d = 2.6 + i*0.252
            wp = waypoint_at(origin,d)
            left = left_of(wp)
            left_distance = (wp.lane_width+left.lane_width)/2
            fraction = smooth((d-3.6)/10) * (1-smooth((d-28.5)/12))
            path.append(flat(d, -0.15 - (left_distance-0.15)*fraction))

        state = {
            'source': {'server_version':client.get_server_version(),'map':road_map.name,
                       'frame':image.frame,'image_size':[image.width,image.height],
                       'road_id':origin.road_id,'lane_id':origin.lane_id,'s':origin.s,
                       'camera_location':xyz(image.transform.location),
                       'camera_rotation':[image.transform.rotation.pitch,image.transform.rotation.yaw,image.transform.rotation.roll],
                       'bike_speed_kph':bike_speed_kph,
                       'actors':{name:{'type':actor.type_id,'id':actor.id,'location':xyz(actor.get_location())} for name,actor in actors.items()}},
            'path':path,
            'work_polygon':[flat(9.8,inner-0.15),flat(9.8,outer+0.20),
                            flat(27.75,outer+0.20),flat(27.75,inner-0.15)],
            'bike':marker(bike,0.95),
            'warning':marker(actors['warning'],0.48),
            'ego':marker(ego,1.05),
            'left':flat(10,-4.35),
        }
        (out/f'{args.candidate}_capture.json').write_text(json.dumps(state,indent=2))
        print('saved',raw_path,flush=True)
    finally:
        if camera:
            camera.stop()
            camera.destroy()
        client.apply_batch([carla.command.DestroyActor(actor.id) for actor in actors.values()])
        world.set_weather(initial_weather)
        world.apply_settings(initial_settings)


if __name__=='__main__':
    main()
