from types import SimpleNamespace

from tools.validate_route_generalization import (
    _route_profiles,
    _select_diverse_routes,
)


def _route(points, *, length_m, junction_count, road_ids):
    return SimpleNamespace(
        reference=SimpleNamespace(points_xy_m=tuple(points)),
        total_length_m=float(length_m),
        validation=SimpleNamespace(junction_count=junction_count),
        samples=tuple(SimpleNamespace(road_id=value) for value in road_ids),
    )


def test_route_profiles_distinguish_length_curvature_and_topology() -> None:
    straight, metrics = _route_profiles(_route(
        [(0.0, 0.0), (100.0, 0.0), (200.0, 0.0)],
        length_m=200.0,
        junction_count=0,
        road_ids=[1],
    ))
    curved, _ = _route_profiles(_route(
        [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0)],
        length_m=1_200.0,
        junction_count=4,
        road_ids=[1, 2, 3],
    ))

    assert set(straight) == {"junction_free", "short_route", "straight"}
    assert metrics["maximum_curvature_per_m"] == 0.0
    assert {
        "curved", "junction", "multi_junction", "long_route", "multi_road",
    }.issubset(curved)


def test_diverse_selection_prefers_new_profiles_and_spawn_points() -> None:
    candidates = [
        {
            "profiles": ["straight", "short_route"],
            "start_spawn_index": 0,
            "destination_spawn_index": 1,
            "total_length_m": 100.0,
        },
        {
            "profiles": ["curved", "long_route", "multi_junction"],
            "start_spawn_index": 2,
            "destination_spawn_index": 3,
            "total_length_m": 1_500.0,
        },
        {
            "profiles": ["straight", "short_route"],
            "start_spawn_index": 0,
            "destination_spawn_index": 4,
            "total_length_m": 120.0,
        },
    ]

    selected = _select_diverse_routes(candidates, 2)

    assert selected[0]["start_spawn_index"] == 2
    assert selected[1]["start_spawn_index"] == 0
