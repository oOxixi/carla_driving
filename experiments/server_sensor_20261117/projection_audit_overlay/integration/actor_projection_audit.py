"""Conservative, evaluation-only matching of image tracks to scenario actors.

Actor positions are simulator truth. This module is only for acceptance labels;
its results must never be supplied to perception, planning, or control.
"""
from __future__ import annotations

from collections import Counter
import math


def _family(name):
    name = str(name).lower()
    if name in {'car', 'truck', 'bus', 'vehicle'}:
        return 'vehicle'
    if name in {'person', 'pedestrian'} or name.startswith('walker'):
        return 'pedestrian'
    return None


def _coverage(box, other):
    x1, y1, x2, y2 = box
    a, b, c, d = other
    intersection = max(0., min(x2, c) - max(x1, a)) * max(0., min(y2, d) - max(y1, b))
    return intersection / max((x2 - x1) * (y2 - y1), 1e-12)


def projected_actor_aliases(scene, rgb, actors, fov, world_frame):
    """Map unambiguous same-frame tracks to actors for evaluation only.

    A match requires >= 50% box coverage, no other same-class actor covering
    >= 10%, and unique assignment. This projection is not proof of identity
    or a control-quality target estimate.
    """
    if rgb is None or getattr(rgb, 'frame', None) != scene.frame or world_frame != scene.frame:
        return {}
    try:
        width, height = int(rgb.width), int(rgb.height)
        fov = float(fov)
        if width <= 0 or height <= 0 or not math.isfinite(fov) or not 0 < fov < 180:
            return {}
        matrix = rgb.transform.get_inverse_matrix()
        if len(matrix) != 4 or any(len(row) != 4 for row in matrix):
            return {}
        focal = width / (2 * math.tan(math.radians(fov) / 2))
    except (ValueError, TypeError, AttributeError, OverflowError):
        return {}

    candidates = []
    for actor, spec in actors:
        if not getattr(actor, 'is_alive', False):
            continue
        family = _family(spec.get('type', ''))
        actor_id = str(spec.get('actor_id', ''))
        if not family or not actor_id:
            continue
        try:
            vertices = actor.bounding_box.get_world_vertices(actor.get_transform())
            projected = []
            for vertex in vertices:
                xyz = (float(vertex.x), float(vertex.y), float(vertex.z), 1.)
                camera_xyz = [sum(float(matrix[i][j]) * xyz[j] for j in range(4)) for i in range(3)]
                if not all(math.isfinite(value) for value in camera_xyz) or camera_xyz[0] <= 1.:
                    raise ValueError('invalid projection')
                x, y, z = camera_xyz
                projected.append(((focal * y / x + width / 2) / width, (-focal * z / x + height / 2) / height))
            if len(projected) != 8:
                raise ValueError('incomplete actor bounding box')
            box = (min(p[0] for p in projected), min(p[1] for p in projected),
                   max(p[0] for p in projected), max(p[1] for p in projected))
            if box[2] <= 0 or box[0] >= 1 or box[3] <= 0 or box[1] >= 1:
                continue
            candidates.append((actor_id, family, box))
        except (AttributeError, RuntimeError, ValueError, TypeError, OverflowError):
            # Unknown projection means association to this family is unproven.
            candidates.append((actor_id, family, None))

    proposals = []
    for detection in scene.detected_objects:
        family = _family(detection.class_name)
        track = detection.track_id
        if not family or not track:
            continue
        relevant = [candidate for candidate in candidates if candidate[1] == family]
        if any(candidate[2] is None for candidate in relevant):
            continue
        box = detection.bbox_xyxy_norm
        if (len(box) != 4 or not all(math.isfinite(float(value)) for value in box)
                or box[2] <= box[0] or box[3] <= box[1]):
            continue
        scored = sorted(((_coverage(box, candidate[2]), candidate[0]) for candidate in relevant), reverse=True)
        if not scored or scored[0][0] < .5 or (len(scored) > 1 and scored[1][0] >= .1):
            continue
        proposals.append((str(track), scored[0][1]))
    track_counts = Counter(track for track, _ in proposals)
    actor_counts = Counter(actor_id for _, actor_id in proposals)
    return {track: actor_id for track, actor_id in proposals
            if track_counts[track] == 1 and actor_counts[actor_id] == 1}
