"""Observe CARLA sensor callback cadence without failing on the first missed tick."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import time

import carla

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from car_control_A import CarlaSession
from integration.sensor_stability import (
    SensorFrameCounter,
    _configure_blueprint,
    _make_transform,
    _spawn_ego,
    selected_sensor_specs,
)


client = carla.Client("127.0.0.1", 2000)
client.set_timeout(10.0)
world = client.get_world()
specs = selected_sensor_specs("both", "low")
sensor_ids = tuple(spec.sensor_id for spec in specs)
counter = SensorFrameCounter(sensor_ids)
observations: list[dict[str, object]] = []

with CarlaSession(world, fixed_delta_seconds=0.05) as session:
    ego = _spawn_ego(session, world, 0)
    session.tick(10.0)
    for spec in specs:
        sensor = world.spawn_actor(
            _configure_blueprint(world, spec),
            _make_transform(carla, spec),
            attach_to=ego,
        )
        session.track_actor(sensor).listen(counter.callback(spec.sensor_id))

    for index in range(30):
        frame = session.tick(10.0)
        time.sleep(0.20)
        observations.append({
            "tick_index": index,
            "world_frame": frame,
            "exact_aligned": counter.wait_for_frame(sensor_ids, frame, timeout_s=0.0),
            "callback_counts": counter.counts(),
            "frame_bounds": counter.frame_bounds(),
        })

time.sleep(0.5)
print(json.dumps({
    "map": world.get_map().name,
    "observations": observations,
    "final_counts": counter.counts(),
    "final_bounds": counter.frame_bounds(),
    "invalid_callbacks": counter.invalid_callbacks(),
}, ensure_ascii=False, indent=2))
