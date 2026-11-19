"""Capture one command-frame's inputs for offline debugging, never for control.

Run the CARLA runner's usual arguments after this script. The diagnostic bundle
is saved only after the runner exits. Simulator actor truth is explicitly stored
in a separate evaluation-only field and is never supplied to the runner.
"""
from __future__ import annotations
import dataclasses
import json
import os
from pathlib import Path
import sys
import numpy as np
from PIL import Image
from integration import carla_runner
from integration.carla_perception import CarlaPerceptionBridge
from integration.rgb_detector import OnnxYoloDetector
from integration.second_group_runtime import CanonicalRuntimeBridge

state = {'sample': None, 'bridge': None, 'raw': None, 'transform': None,
         'detector_frame': None, 'detection': None, 'capture': None, 'error': None}
orig_acquire = CarlaPerceptionBridge.acquire
orig_detect = OnnxYoloDetector.detect_measurement
orig_decode = OnnxYoloDetector._decode
orig_submit = CanonicalRuntimeBridge.submit


def decode(self, output, transform):
    state['raw'] = output
    state['transform'] = dataclasses.asdict(transform)
    return orig_decode(self, output, transform)


def detect(self, measurement):
    result = orig_detect(self, measurement)
    state['detector_frame'] = measurement.frame
    state['detection'] = [dataclasses.asdict(x) for x in result]
    return result


def acquire(self, *args, **kwargs):
    sample = orig_acquire(self, *args, **kwargs)
    state['sample'], state['bridge'] = sample, self
    return sample


def matrix(transform):
    return [[float(v) for v in row] for row in transform.get_matrix()]


def actor_truth(bridge):
    result = []
    for actor in bridge._world.get_actors().filter('vehicle.*'):
        role = actor.attributes.get('role_name', '')
        if not role.startswith('acceptance84:'):
            continue
        transform = actor.get_transform()
        vertices = actor.bounding_box.get_world_vertices(transform)
        result.append({'role_name': role, 'type_id': actor.type_id,
                       'world_matrix': matrix(transform),
                       'vertices_world': [[p.x, p.y, p.z] for p in vertices]})
    return result


def submit(self, envelope, scene, vehicle, **kwargs):
    try:
        sample, bridge = state['sample'], state['bridge']
        if (state['capture'] is None and sample is not None and sample.frame.frame == scene.frame
                and state['detector_frame'] == scene.frame and state['raw'] is not None):
            rgb, lidar, radar = sample.rgb, sample.lidar, sample.radar
            returns = [] if radar is None else [
                {'depth': float(x.depth), 'azimuth': float(x.azimuth),
                 'altitude': float(x.altitude), 'velocity': float(x.velocity)} for x in radar]
            metadata = {
                'frame': scene.frame, 'sim_time_s': scene.sim_time_s,
                'world_snapshot_frame': bridge._world.get_snapshot().frame,
                'command_text': envelope.get('source_text'),
                'rgb': {'width': rgb.width, 'height': rgb.height,
                        'timestamp': rgb.timestamp, 'world_matrix': matrix(rgb.transform),
                        'fov': float(bridge._sensors.actors['rgb_front'].attributes.get('fov',100))},
                'lidar': {'timestamp': lidar.timestamp, 'world_matrix': matrix(lidar.transform)},
                'radar': {'timestamp': None if radar is None else radar.timestamp,
                          'world_matrix': None if radar is None else matrix(radar.transform),
                          'returns': returns},
                'ego_world_matrix': matrix(bridge._ego.get_transform()),
                'detector_frame': state['detector_frame'], 'detector_output_shape': list(state['raw'].shape),
                'detector_letterbox': state['transform'], 'detector_postprocessed': state['detection'],
                'scene': dataclasses.asdict(scene), 'source_by_field': dict(sample.source_by_field),
                'evaluation_only_ground_truth_actors': actor_truth(bridge),
            }
            state['capture'] = {'metadata': metadata, 'rgb_bytes': bytes(rgb.raw_data),
                                'lidar_bytes': bytes(lidar.raw_data), 'yolo': np.array(state['raw'], copy=True)}
            print(f"diagnostic capture buffered for frame {scene.frame}", flush=True)
    except Exception as error:
        state['error'] = f'{type(error).__name__}: {error}'
        print('diagnostic capture failed:', state['error'], flush=True)
    return orig_submit(self, envelope, scene, vehicle, **kwargs)


def save():
    directory = Path(os.environ['COMMAND_DIAGNOSTIC_DIR'])
    directory.mkdir(parents=True, exist_ok=True)
    capture = state['capture']
    if capture is None:
        with (directory / 'capture_error.json').open('x', encoding='utf8') as f:
            json.dump({'error': state['error'] or 'no matching command frame captured'}, f)
        return
    m = capture['metadata']; width, height = m['rgb']['width'], m['rgb']['height']
    bgra = np.frombuffer(capture['rgb_bytes'], dtype=np.uint8).reshape(height, width, 4)
    with (directory / 'camera_rgb.png').open('xb') as f:
        Image.fromarray(bgra[:, :, [2, 1, 0]], mode='RGB').save(f, format='PNG')
    with (directory / 'lidar_xyzi.npy').open('xb') as f:
        np.save(f, np.frombuffer(capture['lidar_bytes'], dtype=np.float32).reshape(-1, 4))
    with (directory / 'yolo_raw.npy').open('xb') as f:
        np.save(f, capture['yolo'])
    with (directory / 'metadata.json').open('x', encoding='utf8') as f:
        json.dump(m, f, ensure_ascii=False, indent=2)
    print(f'diagnostic bundle saved to {directory}', flush=True)


if __name__ == '__main__':
    OnnxYoloDetector._decode = decode
    OnnxYoloDetector.detect_measurement = detect
    CarlaPerceptionBridge.acquire = acquire
    CanonicalRuntimeBridge.submit = submit
    try:
        carla_runner.main()
    finally:
        save()
