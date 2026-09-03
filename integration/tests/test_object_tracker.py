from integration.contracts import DetectedObject
from integration.object_tracker import SensorObjectTracker


def _object(distance: float, center_x: float = 0.5, class_name: str = "car") -> DetectedObject:
    return DetectedObject(
        2,
        class_name,
        0.9,
        (center_x - 0.1, 0.3, center_x + 0.1, 0.8),
        distance,
    )


def test_sensor_tracks_remain_stable_under_small_motion() -> None:
    tracker = SensorObjectTracker()
    first = tracker.update(1, (_object(20.0),))[0]
    second = tracker.update(2, (_object(18.5, 0.52),))[0]
    assert first.track_id == second.track_id
    assert first.track_id.startswith("C-")


def test_distinct_objects_do_not_reuse_one_track_in_same_frame() -> None:
    tracker = SensorObjectTracker()
    tracked = tracker.update(1, (_object(20.0, 0.3), _object(20.0, 0.7)))
    assert tracked[0].track_id != tracked[1].track_id


def test_track_expires_after_sensor_gap() -> None:
    tracker = SensorObjectTracker(maximum_frame_gap=2)
    first = tracker.update(1, (_object(10.0),))[0]
    later = tracker.update(4, (_object(10.0),))[0]
    assert first.track_id != later.track_id


def test_class_change_never_uses_scenario_truth_to_preserve_identity() -> None:
    tracker = SensorObjectTracker()
    car = tracker.update(1, (_object(10.0, class_name="car"),))[0]
    bicycle = tracker.update(2, (_object(9.5, class_name="bicycle"),))[0]
    assert car.track_id != bicycle.track_id

