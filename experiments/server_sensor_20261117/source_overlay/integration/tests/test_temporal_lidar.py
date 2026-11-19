from types import SimpleNamespace
import numpy as np
import pytest
from integration.contracts import DetectedObject
from integration.temporal_lidar import TemporalLidarAccumulator


class Translation:
    def __init__(self, x=0): self.x = x
    def get_matrix(self):
        result = np.eye(4); result[0, 3] = self.x; return result.tolist()
    def get_inverse_matrix(self):
        result = np.eye(4); result[0, 3] = -self.x; return result.tolist()


def sample(frame, points, ego_x=0):
    transform = Translation(ego_x)
    raw = np.asarray(points, dtype=np.float32).reshape(-1, 4).tobytes()
    lidar = SimpleNamespace(frame=frame, timestamp=frame*.05, raw_data=raw, transform=transform)
    rgb = SimpleNamespace(frame=frame, timestamp=frame*.05, width=400, height=200, transform=transform)
    return lidar, rgb, transform


def box(track='A', bounds=(.4,.3,.6,.7)):
    return DetectedObject(2, 'car', .9, bounds, track_id=track)


def test_sparse_stationary_target_accumulates_with_ego_motion():
    a=TemporalLidarAccumulator(); results=[]
    for frame in range(1,5):
        ego_x=frame-1; lidar,rgb,ego=sample(frame, [[60-ego_x, .2*(frame%2), .3, 1]], ego_x)
        results.append(a.associate((box(),), lidar, rgb, ego, 90)[0])
    assert results[0].position_m is None and results[1].position_m is None
    assert results[2].geometry_source == 'RGB_LIDAR_TEMPORAL'
    assert results[2].position_m[0] == pytest.approx(58)
    assert results[3].position_m[0] == pytest.approx(57)


def test_history_alone_does_not_revive_missing_target():
    a=TemporalLidarAccumulator()
    for frame in (1,2):
        lidar,rgb,ego=sample(frame, [[40,0,.3,1]])
        a.associate((box(),), lidar, rgb, ego, 90)
    lidar,rgb,ego=sample(3, [[10,9,.3,1]])
    result,=a.associate((box(),), lidar, rgb, ego, 90)
    assert result.position_m is None


def test_overlap_and_track_change_do_not_merge_other_targets():
    a=TemporalLidarAccumulator()
    for frame in (1,2):
        lidar,rgb,ego=sample(frame, [[40,0,.3,1]])
        a.associate((box(),), lidar, rgb, ego, 90)
    lidar,rgb,ego=sample(3, [[40,0,.3,1]])
    first,second=a.associate((box(),box('B',(.45,.3,.65,.7))),lidar,rgb,ego,90)
    assert first.position_m is None and second.position_m is None
    lidar,rgb,ego=sample(4, [[40,0,.3,1]])
    result,=a.associate((box('B'),),lidar,rgb,ego,90)
    assert result.position_m is None


def test_jump_in_world_position_or_missing_frame_does_not_use_history():
    a=TemporalLidarAccumulator()
    for frame in (1,2):
        lidar,rgb,ego=sample(frame, [[40,0,.3,1]])
        a.associate((box(),),lidar,rgb,ego,90)
    lidar,rgb,ego=sample(3, [[42,0,.3,1]])
    result,=a.associate((box(),),lidar,rgb,ego,90)
    assert result.position_m is None
    lidar,rgb,ego=sample(5, [[42,0,.3,1]])
    result,=a.associate((box(),),lidar,rgb,ego,90)
    assert result.position_m is None


def test_missing_timestamps_disables_history():
    a=TemporalLidarAccumulator()
    for frame in (1,2,3):
        lidar,rgb,ego=sample(frame, [[40,0,.3,1]])
        del lidar.timestamp; del rgb.timestamp
        result,=a.associate((box(),),lidar,rgb,ego,90)
        assert result.position_m is None


def test_two_frames_do_not_count_as_three_independent_frames():
    a=TemporalLidarAccumulator()
    lidar,rgb,ego=sample(1, [[40,0,.3,1], [40.1,0,.3,1]])
    a.associate((box(),),lidar,rgb,ego,90)
    lidar,rgb,ego=sample(2, [[40,0,.3,1]])
    result,=a.associate((box(),),lidar,rgb,ego,90)
    assert result.position_m is None


def test_temporal_estimate_must_stay_near_current_points():
    a=TemporalLidarAccumulator()
    for frame in (1,2):
        lidar,rgb,ego=sample(frame, [[40,0,.3,1]])
        a.associate((box(),),lidar,rgb,ego,90)
    lidar,rgb,ego=sample(3, [[40.7,0,.3,1]])
    result,=a.associate((box(),),lidar,rgb,ego,90)
    assert result.position_m is None


def test_repeated_identical_reflection_does_not_become_object():
    a=TemporalLidarAccumulator()
    for frame in range(1,5):
        lidar,rgb,ego=sample(frame, [[40,0,.3,1]])
        result,=a.associate((box(),),lidar,rgb,ego,90)
        assert result.position_m is None
