from types import SimpleNamespace
import numpy as np
import pytest
from integration.contracts import DetectedObject
from integration.camera_lidar_association import associate_rgb_lidar

class Transform:
    def get_matrix(self):return np.eye(4).tolist()
    def get_inverse_matrix(self):return np.eye(4).tolist()

def test_projection_separates_two_tracks_and_rejects_wrong_frames():
    pts=np.array([[10,-2,.2,1],[10.1,-2.1,.3,1],[10.2,-1.9,.4,1],
                  [20,4,.2,1],[20.1,4.1,.3,1],[20.2,3.9,.4,1]],dtype=np.float32)
    lidar=SimpleNamespace(frame=1,raw_data=pts.tobytes(),transform=Transform())
    rgb=SimpleNamespace(frame=1,width=400,height=200,transform=Transform())
    a=DetectedObject(2,'car',.9,(.35,.38,.45,.55),track_id='A')
    b=DetectedObject(2,'car',.9,(.55,.38,.65,.55),track_id='B')
    first,second=associate_rgb_lidar((a,b),lidar,rgb,Transform(),90)
    assert first.track_id=='A' and first.geometry_source=='RGB_LIDAR_PROJECTED'
    assert second.track_id=='B' and second.geometry_source=='RGB_LIDAR_PROJECTED'
    assert first.position_m[0]==pytest.approx(10.1,abs=.2) and first.position_m[1]>0
    assert second.position_m[0]==pytest.approx(20.1,abs=.2) and second.position_m[1]<0
    rgb.frame=2
    with pytest.raises(ValueError,match='frames differ'):associate_rgb_lidar((a,),lidar,rgb,Transform(),90)


def _inputs(points, *, lidar_transform=None, camera_transform=None, timestamp=2.0):
    pts = np.asarray(points, dtype=np.float32).reshape(-1, 4)
    lidar = SimpleNamespace(frame=1, timestamp=timestamp, raw_data=pts.tobytes(),
                            transform=lidar_transform or Transform())
    rgb = SimpleNamespace(frame=1, timestamp=timestamp, width=400, height=200,
                          transform=camera_transform or Transform())
    obj = DetectedObject(2, 'car', .9, (.3, .2, .7, .8), distance_m=7.0, track_id='A')
    return obj, lidar, rgb


def test_depth_bin_boundary_does_not_split_one_object():
    obj, lidar, rgb = _inputs([[9.8, 0, .2, 1], [9.9, 0, .3, 1],
                               [10.1, 0, .2, 1], [10.2, 0, .3, 1]])
    result, = associate_rgb_lidar((obj,), lidar, rgb, Transform(), 90)
    assert result.geometry_source == 'RGB_LIDAR_PROJECTED'
    assert result.distance_m == pytest.approx(10, abs=.15)


def test_ambiguous_or_missing_cluster_does_not_reuse_unrelated_range():
    obj, lidar, rgb = _inputs([[10, 0, .2, 1], [10.1, .1, .3, 1], [10.2, -.1, .3, 1],
                               [20, 0, .2, 1], [20.1, .1, .3, 1], [20.2, -.1, .3, 1]])
    result, = associate_rgb_lidar((obj,), lidar, rgb, Transform(), 90)
    assert result.distance_m is None and result.position_m is None
    assert result.geometry_source is None and result.lane_relation == 'UNKNOWN'
    lidar.raw_data = b''
    result, = associate_rgb_lidar((obj,), lidar, rgb, Transform(), 90)
    assert result.distance_m is None and result.position_m is None


def test_overlapping_boxes_do_not_share_lidar_points():
    obj, lidar, rgb = _inputs([[10, 0, .2, 1], [10.1, .1, .3, 1], [10.2, -.1, .3, 1]])
    other = DetectedObject(2, 'car', .9, (.35, .25, .65, .75), distance_m=8.0, track_id='B')
    first, second = associate_rgb_lidar((obj, other), lidar, rgb, Transform(), 90)
    assert first.distance_m is None and second.distance_m is None


def test_transforms_affect_projected_ego_position():
    class Translation(Transform):
        def get_matrix(self):
            matrix = np.eye(4); matrix[:3, 3] = [2, 1, 0]; return matrix.tolist()
    obj, lidar, rgb = _inputs([[8, 0, .2, 1], [8.1, .1, .3, 1], [8.2, -.1, .3, 1]],
                              lidar_transform=Translation())
    result, = associate_rgb_lidar((obj,), lidar, rgb, Transform(), 90)
    assert result.position_m[0] == pytest.approx(10.1, abs=.01)
    assert result.position_m[1] == pytest.approx(-1, abs=.01)
    assert result.distance_m == pytest.approx(np.hypot(10.1, 1), abs=.01)


def test_projection_rejects_invalid_calibration_and_timestamp():
    obj, lidar, rgb = _inputs([[10, 0, .2, 1], [10.1, .1, .3, 1], [10.2, -.1, .3, 1]])
    with pytest.raises(ValueError, match='FOV'):
        associate_rgb_lidar((obj,), lidar, rgb, Transform(), 180)
    rgb.timestamp += .01
    with pytest.raises(ValueError, match='timestamps'):
        associate_rgb_lidar((obj,), lidar, rgb, Transform(), 90)
    rgb.timestamp = lidar.timestamp
    class BadTransform(Transform):
        def get_matrix(self):
            matrix = np.eye(4); matrix[0, 0] = 2; return matrix.tolist()
    lidar.transform = BadTransform()
    with pytest.raises(ValueError, match='rigid'):
        associate_rgb_lidar((obj,), lidar, rgb, Transform(), 90)


def test_dominant_nearest_cluster_can_ignore_a_small_separate_fragment():
    foreground = [[10 + i * .01, (i % 3 - 1) * .04, .3, 1] for i in range(16)]
    fragment = [[12, 0, .2, 1], [12.1, .1, .3, 1], [12.2, -.1, .3, 1]]
    obj, lidar, rgb = _inputs(foreground + fragment)
    result, = associate_rgb_lidar((obj,), lidar, rgb, Transform(), 90)
    assert result.distance_m == pytest.approx(10.075, abs=.1)


def test_dominant_background_does_not_override_smaller_foreground():
    foreground = [[10, 0, .2, 1], [10.1, .1, .3, 1], [10.2, -.1, .3, 1]]
    background = [[20 + i * .01, (i % 3 - 1) * .04, .3, 1] for i in range(16)]
    obj, lidar, rgb = _inputs(foreground + background)
    result, = associate_rgb_lidar((obj,), lidar, rgb, Transform(), 90)
    assert result.distance_m is None


def test_rotated_lidar_transform_projects_to_expected_ego_axes():
    class RotatedLidar(Transform):
        def get_matrix(self):
            return [[0, -1, 0, 0], [1, 0, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
    points = [[0, -10, .2, 1], [.1, -10.1, .3, 1], [-.1, -10.2, .3, 1]]
    obj, lidar, rgb = _inputs(points, lidar_transform=RotatedLidar())
    result, = associate_rgb_lidar((obj,), lidar, rgb, Transform(), 90)
    assert result.position_m == pytest.approx((10.1, 0.0, .3), abs=.01)
