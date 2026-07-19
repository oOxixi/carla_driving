from __future__ import annotations

from typing import Iterable, List, Optional, Sequence, Tuple

import numpy as np


def build_camera_intrinsic(
    width: int,
    height: int,
    fov_deg: float,
) -> np.ndarray:
    """Build a pinhole-camera intrinsic matrix."""

    width = int(width)
    height = int(height)
    fov_deg = float(fov_deg)

    focal = width / (
        2.0 * np.tan(np.deg2rad(fov_deg) / 2.0)
    )

    intrinsic = np.identity(3, dtype=np.float64)
    intrinsic[0, 0] = focal
    intrinsic[1, 1] = focal
    intrinsic[0, 2] = width / 2.0
    intrinsic[1, 2] = height / 2.0

    return intrinsic


def world_to_camera_matrix(sensor_transform) -> np.ndarray:
    """Return CARLA world-to-camera homogeneous transform."""

    return np.asarray(
        sensor_transform.get_inverse_matrix(),
        dtype=np.float64,
    )


def project_world_point(
    location,
    world_to_camera: np.ndarray,
    intrinsic: np.ndarray,
    near_clip_m: float = 0.5,
) -> Optional[Tuple[float, float, float]]:
    """Project one CARLA world point into image coordinates.

    CARLA/Unreal coordinate system:
      x: forward
      y: right
      z: up

    Camera projection convention:
      x: image right
      y: image down
      z: forward depth
    """

    point_world = np.array(
        [location.x, location.y, location.z, 1.0],
        dtype=np.float64,
    )

    point_sensor = world_to_camera @ point_world

    point_camera = np.array(
        [
            point_sensor[1],
            -point_sensor[2],
            point_sensor[0],
        ],
        dtype=np.float64,
    )

    depth = float(point_camera[2])

    if not np.isfinite(depth) or depth <= float(near_clip_m):
        return None

    uvw = intrinsic @ point_camera

    if not np.all(np.isfinite(uvw)):
        return None

    if abs(float(uvw[2])) < 1e-8:
        return None

    u = float(uvw[0] / uvw[2])
    v = float(uvw[1] / uvw[2])

    if not np.isfinite(u) or not np.isfinite(v):
        return None

    return u, v, depth


def bbox_world_vertices(actor) -> Iterable:
    """Return the eight world-space vertices of an actor bounding box."""

    bounding_box = actor.bounding_box
    actor_transform = actor.get_transform()

    return bounding_box.get_world_vertices(actor_transform)


def project_actor_bbox(
    actor,
    world_to_camera: np.ndarray,
    intrinsic: np.ndarray,
    width: int,
    height: int,
    near_clip_m: float = 0.5,
) -> Optional[Tuple[int, int, int, int]]:
    """Project a CARLA actor 3D bounding box into the RGB image.

    Important:
    If even one vertex is behind or too close to the camera plane, the
    projection is rejected. Keeping only the visible vertices can create
    an invalid box spanning most of the image.
    """

    width = int(width)
    height = int(height)

    if width <= 0 or height <= 0:
        return None

    vertices = list(bbox_world_vertices(actor))

    if len(vertices) != 8:
        return None

    projected_points: List[Tuple[float, float, float]] = []

    for vertex in vertices:
        projected = project_world_point(
            vertex,
            world_to_camera,
            intrinsic,
            near_clip_m=near_clip_m,
        )

        if projected is None:
            return None

        projected_points.append(projected)

    xs = [point[0] for point in projected_points]
    ys = [point[1] for point in projected_points]

    raw_x1 = min(xs)
    raw_y1 = min(ys)
    raw_x2 = max(xs)
    raw_y2 = max(ys)

    # Bounding box is completely outside the visible image.
    if raw_x2 < 0.0:
        return None
    if raw_y2 < 0.0:
        return None
    if raw_x1 >= float(width):
        return None
    if raw_y1 >= float(height):
        return None

    x1 = int(max(0.0, min(float(width - 1), raw_x1)))
    y1 = int(max(0.0, min(float(height - 1), raw_y1)))
    x2 = int(max(0.0, min(float(width - 1), raw_x2)))
    y2 = int(max(0.0, min(float(height - 1), raw_y2)))

    box_width = x2 - x1
    box_height = y2 - y1

    if box_width < 3 or box_height < 3:
        return None

    # Reject unstable near-camera projections.
    if box_width >= int(width * 0.95):
        return None

    if box_height >= int(height * 0.95):
        return None

    return x1, y1, x2, y2


def image_region(
    bbox: Sequence[int],
    width: int,
) -> str:
    """Split the image horizontally into left/center/right regions."""

    x1, _, x2, _ = bbox
    center_x = (float(x1) + float(x2)) / 2.0

    if center_x < float(width) / 3.0:
        return "FRONT_LEFT"

    if center_x > 2.0 * float(width) / 3.0:
        return "FRONT_RIGHT"

    return "FRONT_CENTER"


def is_in_danger_zone(
    bbox: Sequence[int],
    width: int,
    height: int,
) -> bool:
    """Simple 2D image-space danger-zone heuristic.

    This is only a visual heuristic. It must not be used as a replacement
    for LiDAR distance, TTC or the safety supervisor.
    """

    x1, y1, x2, y2 = [float(value) for value in bbox]

    if x2 <= x1 or y2 <= y1:
        return False

    center_x = (x1 + x2) / 2.0
    bottom_y = y2
    width_ratio = (x2 - x1) / max(float(width), 1.0)

    return (
        float(width) * 0.28
        <= center_x
        <= float(width) * 0.72
        and bottom_y >= float(height) * 0.48
        and width_ratio >= 0.025
    )
