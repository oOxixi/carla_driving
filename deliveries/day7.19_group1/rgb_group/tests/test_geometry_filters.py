from rgb_group.geometry import (
    image_region,
    is_in_danger_zone,
)
from rgb_group.carla_gt_backend import (
    _valid_traffic_light_bbox,
)


def test_image_region_left():
    assert (
        image_region(
            bbox=(10, 100, 100, 200),
            width=640,
        )
        == "FRONT_LEFT"
    )


def test_image_region_center():
    assert (
        image_region(
            bbox=(270, 100, 370, 200),
            width=640,
        )
        == "FRONT_CENTER"
    )


def test_image_region_right():
    assert (
        image_region(
            bbox=(540, 100, 630, 200),
            width=640,
        )
        == "FRONT_RIGHT"
    )


def test_center_vehicle_can_be_dangerous():
    bbox = (270, 190, 370, 350)

    assert is_in_danger_zone(
        bbox=bbox,
        width=640,
        height=360,
    )


def test_small_far_object_not_dangerous():
    bbox = (310, 140, 325, 155)

    assert not is_in_danger_zone(
        bbox=bbox,
        width=640,
        height=360,
    )


def test_side_object_not_dangerous():
    bbox = (20, 190, 120, 350)

    assert not is_in_danger_zone(
        bbox=bbox,
        width=640,
        height=360,
    )


def test_reject_huge_traffic_light_bbox():
    # Similar to the invalid box observed in the previous GT output.
    bbox = (109, 228, 639, 359)

    assert not _valid_traffic_light_bbox(
        bbox=bbox,
        width=640,
        height=360,
    )


def test_accept_normal_traffic_light_bbox():
    bbox = (233, 156, 274, 169)

    assert _valid_traffic_light_bbox(
        bbox=bbox,
        width=640,
        height=360,
    )


def test_controlled_pedestrian_geometry():
    bbox = (314, 185, 325, 242)
    x1, y1, x2, y2 = bbox
    center_x = (x1 + x2) / 2.0
    bottom_y = y2
    box_height = y2 - y1

    danger = (
        640 * 0.30 <= center_x <= 640 * 0.70
        and bottom_y >= 360 * 0.58
        and box_height >= 360 * 0.08
    )

    assert danger
