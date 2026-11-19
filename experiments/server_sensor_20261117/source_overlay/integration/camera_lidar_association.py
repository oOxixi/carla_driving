# Project same-frame LiDAR points into the camera; no CARLA actor truth.
from dataclasses import replace
import math
import numpy as np


def _separated_clusters(points, gap_m=0.75):
    """Group by continuous depth and lateral gaps, not fixed depth bins."""
    if not len(points):
        return []
    ordered = points[np.argsort(points[:, 0])]
    depth_groups = np.split(ordered, np.flatnonzero(np.diff(ordered[:, 0]) > gap_m) + 1)
    clusters = []
    for group in depth_groups:
        ordered_y = group[np.argsort(group[:, 1])]
        clusters.extend(np.split(ordered_y, np.flatnonzero(np.diff(ordered_y[:, 1]) > gap_m) + 1))
    return [group for group in clusters if len(group) >= 3]


def _unknown_geometry(obj):
    """Do not attach a front-corridor range to an unassociated RGB target."""
    return replace(obj, distance_m=None, position_m=None, geometry_source=None,
                   lane_relation='UNKNOWN')


def _rigid_matrix(transform, method):
    matrix = np.asarray(getattr(transform, method)(), dtype=float)
    if matrix.shape != (4, 4) or not np.isfinite(matrix).all():
        raise ValueError('invalid transform matrix')
    rotation = matrix[:3, :3]
    if (not np.allclose(matrix[3], [0, 0, 0, 1], atol=1e-5)
            or not np.allclose(rotation.T @ rotation, np.eye(3), atol=1e-3)
            or not np.isclose(np.linalg.det(rotation), 1, atol=1e-3)):
        raise ValueError('transform matrix must be rigid')
    return matrix


def associate_rgb_lidar(objects, lidar, rgb, ego_transform, camera_fov, world_map=None):
    frame=getattr(lidar, 'frame', None)
    if frame is None or frame != getattr(rgb, 'frame', None):
        raise ValueError('RGB/LiDAR frames differ')
    lidar_time, rgb_time = getattr(lidar, 'timestamp', None), getattr(rgb, 'timestamp', None)
    if lidar_time is not None and rgb_time is not None:
        if (not math.isfinite(float(lidar_time)) or not math.isfinite(float(rgb_time))
                or abs(float(lidar_time) - float(rgb_time)) > 0.001):
            raise ValueError('RGB/LiDAR timestamps differ')
    fov=float(camera_fov)
    if (type(rgb.width) is not int or type(rgb.height) is not int
            or rgb.width <= 0 or rgb.height <= 0 or not math.isfinite(fov) or not 0 < fov < 180):
        raise ValueError('invalid camera dimensions or FOV')
    lidar_matrix=_rigid_matrix(lidar.transform, 'get_matrix')
    camera_inverse=_rigid_matrix(rgb.transform, 'get_inverse_matrix')
    ego_inverse=_rigid_matrix(ego_transform, 'get_inverse_matrix')
    points=np.frombuffer(lidar.raw_data,dtype=np.float32).reshape(-1,4)[:,:3]
    if not len(points):
        return tuple(o if o.class_name.lower()=='obstacle' else _unknown_geometry(o) for o in objects)
    homogeneous=np.concatenate((points,np.ones((len(points),1))),axis=1)
    world=homogeneous @ lidar_matrix.T
    camera=world @ camera_inverse.T
    ego=world @ ego_inverse.T
    depth=camera[:,0]
    valid=(depth>1)&(ego[:,0]>0)&(ego[:,2]>-0.25)&np.isfinite(ego[:,:3]).all(axis=1)
    focal=rgb.width/(2*math.tan(math.radians(float(camera_fov))/2))
    safe=np.maximum(depth,0.001)
    u=(focal*camera[:,1]/safe+rgb.width/2)/rgb.width
    v=(-focal*camera[:,2]/safe+rgb.height/2)/rgb.height
    candidates=[]
    memberships=np.zeros(len(points),dtype=np.int16)
    for obj in objects:
        if obj.class_name.lower()=='obstacle': continue
        ax,ay,bx,by=obj.bbox_xyxy_norm
        memberships += ((u>=ax)&(u<=bx)&(v>=ay)&(v<=by)).astype(np.int16)
    for obj in objects:
        if obj.class_name.lower()=='obstacle':
            candidates.append(obj);continue
        x1,y1,x2,y2=obj.bbox_xyxy_norm
        # Exclude 5% of each box edge to reduce background leakage.
        dx=(x2-x1)*.05;dy=(y2-y1)*.05
        mask=valid&(memberships==1)&(u>=x1+dx)&(u<=x2-dx)&(v>=y1+dy)&(v<=y2-dy)
        selected=ego[mask,:3]
        groups=_separated_clusters(selected)
        # Accept a clearly dominant nearest cluster only; otherwise it may be
        # a second actor or a foreground/background overlap. These support
        # thresholds are conservative heuristics, not calibrated confidence.
        if not groups:
            candidates.append(_unknown_geometry(obj));continue
        groups.sort(key=lambda g:float(np.median(g[:,0])))
        cluster=groups[0]
        if len(groups)>1 and (len(cluster)<8 or any(len(cluster)<4*len(g) for g in groups[1:])):
            candidates.append(_unknown_geometry(obj));continue
        xyz=np.median(cluster,axis=0)
        if np.ptp(cluster[:,1])>4 or np.ptp(cluster[:,0])>2.1:
            candidates.append(_unknown_geometry(obj));continue
        # CARLA y points right; canonical ego coordinates use y-left.
        pos=(float(xyz[0]),float(-xyz[1]),float(xyz[2]))
        lane='UNKNOWN'
        if world_map is not None:
            try:
                import carla
                ego_wp=world_map.get_waypoint(ego_transform.location,project_to_road=True)
                location=ego_transform.transform(carla.Location(x=float(xyz[0]),y=float(xyz[1]),z=0))
                wp=world_map.get_waypoint(location,project_to_road=True)
                if ego_wp and wp and location.distance(wp.transform.location) < max(0.5,float(wp.lane_width)/2-0.3):
                    if wp.road_id == ego_wp.road_id:
                        lane='SAME' if wp.lane_id == ego_wp.lane_id else 'OTHER'
                    elif hasattr(ego_wp, 'next'):
                        # Road IDs can change along a continuous lane.
                        continuations=ego_wp.next(max(0.5,float(xyz[0])))
                        near=[w for w in continuations if location.distance(w.transform.location) < max(0.5,float(w.lane_width)/2-0.3)]
                        if len(near)==1: lane='SAME'
            except (AttributeError,RuntimeError,TypeError):pass
        candidates.append(replace(obj,position_m=pos,geometry_source='RGB_LIDAR_PROJECTED',lane_relation=lane,distance_m=float(np.linalg.norm(xyz[:2]))))
    return tuple(candidates)
