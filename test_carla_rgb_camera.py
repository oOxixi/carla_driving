import traceback

import carla

from rgb_group.camera_sensor import FrontRGBCamera


HOST = "127.0.0.1"
PORT = 2000
TM_PORT = 8000


def main():
    client = carla.Client(HOST, PORT)
    client.set_timeout(60.0)

    print("server:", client.get_server_version())

    world = client.get_world()
    original_settings = world.get_settings()
    traffic_manager = client.get_trafficmanager(TM_PORT)

    vehicle = None
    camera = None

    try:
        settings = world.get_settings()
        settings.synchronous_mode = True
        settings.fixed_delta_seconds = 0.05
        settings.no_rendering_mode = False
        world.apply_settings(settings)

        traffic_manager.set_synchronous_mode(True)

        blueprints = world.get_blueprint_library()
        vehicle_bp = blueprints.filter("vehicle.*")[0]

        for transform in world.get_map().get_spawn_points():
            vehicle = world.try_spawn_actor(vehicle_bp, transform)
            if vehicle is not None:
                break

        if vehicle is None:
            raise RuntimeError("Could not spawn test vehicle")

        print("vehicle:", vehicle.id)

        world.tick()

        camera = FrontRGBCamera(
            world,
            vehicle,
            width=640,
            height=360,
            fov_deg=90.0,
        )

        print("camera:", camera.actor.id)

        received = 0

        for i in range(20):
            expected = world.tick()

            try:
                frame = camera.get_for_frame(
                    expected_frame=expected,
                    timeout_s=10.0,
                    max_frame_lag=2,
                )
            except Exception as exc:
                print(
                    f"tick={i}, world_frame={expected}, "
                    f"camera error={exc}"
                )
                continue

            print(
                f"tick={i}, "
                f"world_frame={expected}, "
                f"camera_frame={frame.frame}, "
                f"time={frame.sim_time_s:.3f}, "
                f"shape={frame.image_bgr.shape}, "
                f"mean={frame.image_bgr.mean():.2f}"
            )
            received += 1

        print(f"received={received}/20")

        if received == 0:
            raise RuntimeError("Camera produced zero images")

    except Exception:
        traceback.print_exc()
        raise

    finally:
        if camera is not None:
            camera.stop()

        try:
            world.tick()
        except Exception:
            pass

        if camera is not None and camera.actor is not None:
            try:
                client.apply_batch_sync(
                    [carla.command.DestroyActor(camera.actor.id)],
                    False,
                )
            except Exception:
                pass

        if vehicle is not None:
            try:
                client.apply_batch_sync(
                    [carla.command.DestroyActor(vehicle.id)],
                    False,
                )
            except Exception:
                pass

        try:
            traffic_manager.set_synchronous_mode(False)
        except Exception:
            pass

        try:
            world.apply_settings(original_settings)
        except Exception:
            pass


if __name__ == "__main__":
    main()
