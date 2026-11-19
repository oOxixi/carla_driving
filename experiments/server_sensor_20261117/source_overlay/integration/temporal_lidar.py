"""Experimental short-window RGB/LiDAR association; not safety calibrated."""
from __future__ import annotations
from collections import deque
from dataclasses import dataclass, replace
import math
from types import SimpleNamespace
import numpy as np
from .camera_lidar_association import _rigid_matrix, associate_rgb_lidar


@dataclass(frozen=True)
class _Observation:
    frame: int
    timestamp: float
    box: tuple
    class_name: str
    world_points: np.ndarray


def _iou(a, b):
    x1, y1, x2, y2 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    intersection = max(0., x2-x1) * max(0., y2-y1)
    union = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - intersection
    return intersection / union if union > 0 else 0.


def _overlap(a, b):
    return min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1])


class TemporalLidarAccumulator:
    """Use current points and recent same-track points, compensating ego motion."""
    def __init__(self, *, max_frames=4, max_age_s=.15, max_offset_m=.75,
                 min_box_iou=.4, max_points_per_object=128):
        if not 2 <= max_frames <= 8 or not 0 < max_age_s <= .5:
            raise ValueError('invalid temporal window')
        if not 0 < max_offset_m <= 1 or not 0 < min_box_iou <= 1 or max_points_per_object < 3:
            raise ValueError('invalid temporal association limits')
        self.max_frames, self.max_age_s = max_frames, max_age_s
        self.max_offset_m, self.min_box_iou = max_offset_m, min_box_iou
        self.max_points_per_object = max_points_per_object
        self.reset()

    def reset(self):
        self._tracks = {}
        self._last_frame = self._last_timestamp = None

    def associate(self, objects, lidar, rgb, ego_transform, camera_fov, world_map=None):
        try:
            single = associate_rgb_lidar(objects, lidar, rgb, ego_transform, camera_fov, world_map)
        except (AttributeError, TypeError, ValueError, RuntimeError):
            self.reset()
            raise
        frame = int(lidar.frame)
        lidar_time, rgb_time = getattr(lidar, 'timestamp', None), getattr(rgb, 'timestamp', None)
        if lidar_time is None or rgb_time is None:
            self.reset()
            return single
        timestamp = float(lidar_time)
        if (not math.isfinite(timestamp) or not math.isfinite(float(rgb_time))
            or (self._last_frame is not None and frame != self._last_frame + 1)
            or (self._last_timestamp is not None and
                (timestamp <= self._last_timestamp or timestamp-self._last_timestamp > self.max_age_s))):
            self.reset()
        self._last_frame, self._last_timestamp = frame, timestamp
        lidar_world = _rigid_matrix(lidar.transform, 'get_matrix')
        world_lidar = np.linalg.inv(lidar_world)
        world_camera = _rigid_matrix(rgb.transform, 'get_inverse_matrix')
        world_ego = _rigid_matrix(ego_transform, 'get_inverse_matrix')
        raw = np.frombuffer(lidar.raw_data, dtype=np.float32).reshape(-1, 4)
        if not len(raw):
            self._tracks.clear()
            return single
        world = np.concatenate((raw[:, :3], np.ones((len(raw), 1))), axis=1) @ lidar_world.T
        camera = world @ world_camera.T
        ego = world @ world_ego.T
        depth = camera[:, 0]
        focal = rgb.width / (2 * math.tan(math.radians(float(camera_fov)) / 2))
        safe = np.maximum(depth, .001)
        u = (focal * camera[:, 1] / safe + rgb.width / 2) / rgb.width
        v = (-focal * camera[:, 2] / safe + rgb.height / 2) / rgb.height
        valid = ((depth > 1) & (ego[:, 0] > 0) & (ego[:, 2] > -.25)
                 & np.isfinite(ego[:, :3]).all(axis=1) & np.isfinite(camera[:, :3]).all(axis=1))
        visual = [o for o in objects if o.class_name.lower() != 'obstacle']
        memberships = np.zeros(len(raw), dtype=np.int16)
        for obj in visual:
            x1, y1, x2, y2 = obj.bbox_xyxy_norm
            memberships += ((u >= x1) & (u <= x2) & (v >= y1) & (v <= y2)).astype(np.int16)
        ids = [o.track_id for o in visual if o.track_id]
        duplicate_ids = {track for track in ids if ids.count(track) > 1}
        output = list(single)
        next_tracks = {}
        for index, obj in enumerate(objects):
            track = obj.track_id
            if (obj.class_name.lower() == 'obstacle' or not track or track in duplicate_ids
                or any(other is not obj and _overlap(obj.bbox_xyxy_norm, other.bbox_xyxy_norm) for other in visual)):
                continue
            box = obj.bbox_xyxy_norm
            x1, y1, x2, y2 = box
            dx, dy = (x2-x1)*.05, (y2-y1)*.05
            mask = valid & (memberships == 1) & (u >= x1+dx) & (u <= x2-dx) & (v >= y1+dy) & (v <= y2-dy)
            current = world[mask, :3]
            if len(current) > self.max_points_per_object:
                current = current[np.linspace(0, len(current)-1, self.max_points_per_object, dtype=int)]
            previous = self._tracks.get(track, deque(maxlen=self.max_frames-1))
            if previous and (previous[-1].frame != frame-1 or previous[-1].class_name != obj.class_name.lower()
                             or _iou(previous[-1].box, box) < self.min_box_iou):
                previous = deque(maxlen=self.max_frames-1)
            previous = deque((p for p in previous if 0 < timestamp-p.timestamp <= self.max_age_s),
                             maxlen=self.max_frames-1)
            # No history alone may create a current target. Old points must be
            # spatially corroborated by at least one current-frame point.
            additions = []
            if len(current) and output[index].position_m is None:
                for observation in previous:
                    old = observation.world_points
                    if not len(old):
                        continue
                    dist = np.linalg.norm(old[:, None, :2] - current[None, :, :2], axis=2)
                    accepted = old[np.min(dist, axis=1) <= self.max_offset_m]
                    if len(accepted):
                        additions.append(accepted)
            # Current observation must be corroborated in two earlier frames.
            if len(additions) >= 2:
                old_world = np.concatenate(additions, axis=0)
                old_h = np.concatenate((old_world, np.ones((len(old_world), 1))), axis=1)
                old_lidar = (old_h @ world_lidar.T)[:, :3]
                padded = np.column_stack((old_lidar, np.zeros(len(old_lidar)))).astype(np.float32)
                merged = np.concatenate((raw, padded), axis=0)
                augmented = SimpleNamespace(frame=frame, timestamp=timestamp, transform=lidar.transform,
                                            raw_data=merged.tobytes())
                candidate = associate_rgb_lidar(objects, augmented, rgb, ego_transform, camera_fov, world_map)[index]
                if candidate.position_m is not None:
                    # Limit lag relative to actual current-frame points. This
                    # remains an unvalidated heuristic, not proof of identity.
                    x, y, z = candidate.position_m
                    estimate_world = np.linalg.inv(world_ego) @ np.array([x, -y, z, 1.])
                    nearest = np.min(np.linalg.norm(current[:, :2] - estimate_world[:2], axis=1))
                    # Repeated observations of one static reflector do not
                    # become a spatially supported object merely with time.
                    supporting = np.concatenate([current, *additions], axis=0)
                    supporting = supporting[np.linalg.norm(supporting[:, :2] - estimate_world[:2], axis=1) <= self.max_offset_m]
                    offsets = supporting[:, None, :2] - supporting[None, :, :2]
                    distinct = len(supporting) >= 2 and np.max(np.linalg.norm(offsets, axis=2)) >= .1
                    if nearest <= .35 and distinct:
                        output[index] = replace(candidate, geometry_source='RGB_LIDAR_TEMPORAL')
            previous.append(_Observation(frame, timestamp, box, obj.class_name.lower(), current.copy()))
            next_tracks[track] = previous
        self._tracks = next_tracks
        return tuple(output)
