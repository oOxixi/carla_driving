import math
from types import SimpleNamespace

import pytest

from integration.route_manager import (
    LaneCorridorRequirement,
    RouteManager,
    RoutePlanningError,
    RouteRecoveryPolicy,
    RouteRecoveryTracker,
    SpeedWindowRequirement,
)
from integration.route_planner import build_destination_route_reference


class Waypoint:
    def __init__(
        self, x, y, yaw, *, road_id, lane_id=1, section_id=0, s=0.0,
        lane_type="Driving", is_junction=False,
    ):
        self.transform = SimpleNamespace(
            location=SimpleNamespace(x=float(x), y=float(y), z=0.0),
            rotation=SimpleNamespace(yaw=float(yaw)),
        )
        self.road_id = road_id
        self.section_id = section_id
        self.lane_id = lane_id
        self.s = float(s)
        self.lane_type = lane_type
        self.is_junction = is_junction
        self.children = []
        self.left = None
        self.right = None
        self.lane_change = "NONE"
        self.left_lane_marking = SimpleNamespace(lane_change="NONE")
        self.right_lane_marking = SimpleNamespace(lane_change="NONE")

    def next(self, _distance):
        return list(self.children)

    def get_left_lane(self):
        return self.left

    def get_right_lane(self):
        return self.right


class TopologyMap:
    def __init__(self, topology, projections):
        self.topology = tuple(topology)
        self.projections = projections
        self.topology_calls = 0

    def get_topology(self):
        self.topology_calls += 1
        return list(self.topology)

    def get_waypoint(self, location, project_to_road=True):
        assert project_to_road
        return min(
            self.projections,
            key=lambda waypoint: math.hypot(
                waypoint.transform.location.x - location.x,
                waypoint.transform.location.y - location.y,
            ),
        )


def location(x, y):
    return SimpleNamespace(x=float(x), y=float(y), z=0.0)


def _fork_map():
    start = Waypoint(0, 0, 0, road_id=1, s=0)
    junction_exit = Waypoint(2, 0, 0, road_id=1, s=2, is_junction=True)
    left_entry = Waypoint(2, 0, -45, road_id=2, s=0, is_junction=True)
    left_exit = Waypoint(4, -2, -45, road_id=2, s=3)
    right_entry = Waypoint(2, 0, 45, road_id=3, s=0, is_junction=True)
    right_exit = Waypoint(4, 2, 45, road_id=3, s=3)
    junction_exit.children = [left_entry, right_entry]
    return TopologyMap(
        [(start, junction_exit), (left_entry, left_exit), (right_entry, right_exit)],
        [start, junction_exit, left_entry, left_exit, right_entry, right_exit],
    ), start, left_exit, right_exit


def test_destination_selects_correct_junction_branch() -> None:
    world_map, start, _left, right = _fork_map()
    manager = RouteManager(world_map, sample_step_m=2.0)

    route = manager.plan(start.transform, right.transform, 10.0)

    assert route.reference.metadata["planner"] == "CARLA_TOPOLOGY_ASTAR"
    assert route.reference.points_xy_m[-1] == pytest.approx((4.0, 2.0))
    assert all(y >= 0.0 for _x, y in route.reference.points_xy_m)
    assert route.validation.destination_error_m == pytest.approx(0.0)
    assert route.validation.repeated_sample_count == 0
    assert world_map.topology_calls == 1


def test_legacy_destination_entrypoint_delegates_to_route_manager() -> None:
    world_map, start, _left, right = _fork_map()

    reference = build_destination_route_reference(
        world_map,
        start.transform,
        (right.transform.location.x, right.transform.location.y),
        10.0,
        step_m=2.0,
    )

    assert reference.metadata["planner"] == "CARLA_TOPOLOGY_ASTAR"
    assert reference.points_xy_m[-1] == pytest.approx((4.0, 2.0))


def test_topology_graph_is_cached_across_routes() -> None:
    world_map, start, left, right = _fork_map()
    manager = RouteManager(world_map, sample_step_m=2.0)

    manager.plan(start.transform, left.transform, 5.0)
    manager.plan(start.transform, right.transform, 5.0)

    assert world_map.topology_calls == 1


def test_distance_contract_route_is_owned_by_route_manager() -> None:
    manager, nodes = _linear_route_manager(20)

    route = manager.plan_distance(nodes[0].transform, 10.0, 5.0)

    assert route.total_length_m == pytest.approx(10.0)
    assert route.reference.metadata["planner"] == "CARLA_TOPOLOGY_COVERAGE"
    assert route.reference.metadata["planning_mode"] == "TOPOLOGY_DISTANCE_COVERAGE"
    assert route.reference.metadata["requested_distance_m"] == pytest.approx(10.0)
    assert route.reference.points_xy_m[-1] == pytest.approx((10.0, 0.0))


def test_distance_contract_explicitly_allows_revisiting_topology() -> None:
    first = Waypoint(0, 0, 0, road_id=12, s=0)
    second = Waypoint(1, 0, 0, road_id=12, s=1)
    third = Waypoint(2, 0, 0, road_id=12, s=2)
    first.children = [second]
    second.children = [third]
    third.children = [first]
    world_map = TopologyMap([(first, third)], [first, second, third])

    route = RouteManager(world_map, sample_step_m=1.0).plan_distance(
        first.transform, 6.0, 4.0,
    )

    assert route.total_length_m >= 6.0
    assert route.validation.repeated_sample_count > 0


def test_distance_route_selects_first_candidate_that_satisfies_scene_topology() -> None:
    _blocked_manager, blocked = _linear_route_manager(30)
    compatible = [
        Waypoint(index, 100.0, 0, road_id=26, lane_id=1, s=index)
        for index in range(31)
    ]
    for first, second in zip(compatible, compatible[1:]):
        first.children = [second]
    for source in compatible:
        adjacent = Waypoint(
            source.transform.location.x, 96.5, 0.0,
            road_id=26, lane_id=2, s=source.s,
        )
        source.left = adjacent
    world_map = TopologyMap(
        [
            (blocked[0], blocked[-1]),
            (compatible[0], compatible[-1]),
        ],
        [*blocked, *compatible],
    )
    manager = RouteManager(world_map, sample_step_m=1.0)

    selected, route = manager.plan_distance_compatible(
        (blocked[0].transform, compatible[0].transform),
        20.0,
        5.0,
        lane_corridors=(
            LaneCorridorRequirement("overtake", "LEFT", 5.0, 15.0, True),
        ),
    )

    assert selected == 1
    assert route.start_xy_m == pytest.approx((0.0, 100.0))
    assert route.reference.metadata["compatibility_candidate_index"] == 1


def test_distance_route_rejects_speed_window_that_curvature_cannot_support() -> None:
    start = Waypoint(0, 0, 0, road_id=27, s=0)
    corner = Waypoint(1, 0, 90, road_id=27, s=1)
    end = Waypoint(1, 1, 90, road_id=27, s=2)
    start.children = [corner]
    corner.children = [end]
    world_map = TopologyMap([(start, end)], [start, corner, end])
    manager = RouteManager(world_map, sample_step_m=1.0)

    with pytest.raises(RoutePlanningError) as error:
        manager.plan_distance_compatible(
            (start.transform,),
            2.0,
            10.0,
            speed_windows=(
                SpeedWindowRequirement("approach", 0.0, 2.0, 40.0),
            ),
        )

    assert error.value.code == "ROUTE_NO_COMPATIBLE_ANCHOR"


def test_unreachable_destination_returns_explicit_reason() -> None:
    start = Waypoint(0, 0, 0, road_id=1, s=0)
    start_exit = Waypoint(2, 0, 0, road_id=1, s=2)
    destination_entry = Waypoint(20, 20, 0, road_id=9, s=0)
    destination = Waypoint(22, 20, 0, road_id=9, s=2)
    world_map = TopologyMap(
        [(start, start_exit), (destination_entry, destination)],
        [start, start_exit, destination_entry, destination],
    )

    with pytest.raises(RoutePlanningError) as error:
        RouteManager(world_map, sample_step_m=2.0).plan(
            start.transform, destination.transform, 5.0,
        )

    assert error.value.code == "ROUTE_UNREACHABLE"


def test_non_driving_destination_fails_before_search() -> None:
    world_map, start, _left, right = _fork_map()
    right.lane_type = "Sidewalk"

    with pytest.raises(RoutePlanningError) as error:
        RouteManager(world_map, sample_step_m=2.0).plan(
            start.transform, right.transform, 5.0,
        )

    assert error.value.code == "ROUTE_DESTINATION_UNMAPPABLE"


def test_parallel_lane_is_selected_by_lane_identity_not_xy_proximity() -> None:
    start = Waypoint(0, 0, 0, road_id=10, lane_id=1, s=0)
    end = Waypoint(4, 0, 0, road_id=10, lane_id=1, s=4)
    parallel_start = Waypoint(0, 0.4, 0, road_id=10, lane_id=2, s=0)
    parallel_end = Waypoint(4, 0.4, 0, road_id=10, lane_id=2, s=4)
    world_map = TopologyMap(
        [(start, end), (parallel_start, parallel_end)],
        [start, end, parallel_start, parallel_end],
    )

    route = RouteManager(world_map, sample_step_m=2.0).plan(
        parallel_start.transform, parallel_end.transform, 5.0,
    )

    assert {sample.lane_id for sample in route.samples} == {2}
    assert all(y == pytest.approx(0.4) for _x, y in route.reference.points_xy_m)


def _parallel_lane_change_map(*, permitted: bool = True):
    source = [
        Waypoint(index, 0.0, 0.0, road_id=11, lane_id=1, s=index)
        for index in range(41)
    ]
    target = [
        Waypoint(index, -3.5, 0.0, road_id=11, lane_id=2, s=index)
        for index in range(41)
    ]
    for lane in (source, target):
        for first, second in zip(lane, lane[1:]):
            first.children = [second]
    for current, adjacent in zip(source, target):
        current.left = adjacent
        adjacent.right = current
        if permitted:
            current.left_lane_marking.lane_change = "Left"
            adjacent.right_lane_marking.lane_change = "Right"
    return (
        TopologyMap(
            [(source[0], source[-1]), (target[0], target[-1])],
            [*source, *target],
        ),
        source,
        target,
    )


def test_global_route_uses_smooth_legal_lane_change_to_reach_destination() -> None:
    world_map, source, target = _parallel_lane_change_map()

    route = RouteManager(world_map, sample_step_m=1.0).plan(
        source[0].transform, target[-1].transform, 8.0,
    )

    assert route.destination_xy_m == pytest.approx((40.0, -3.5))
    assert route.reference.metadata["lane_change_count"] == 1
    assert route.validation.maximum_gap_m < 1.5
    assert {sample.lane_id for sample in route.samples} == {1, 2}
    lateral = [point[1] for point in route.reference.points_xy_m]
    assert lateral == sorted(lateral, reverse=True)


def test_global_route_does_not_cross_solid_lane_marking() -> None:
    world_map, source, target = _parallel_lane_change_map(permitted=False)

    with pytest.raises(RoutePlanningError) as error:
        RouteManager(world_map, sample_step_m=1.0).plan(
            source[0].transform, target[-1].transform, 8.0,
        )

    assert error.value.code == "ROUTE_UNREACHABLE"


def test_route_state_exposes_shared_route_coordinates_and_lane_relations() -> None:
    start = Waypoint(0, 0, 0, road_id=20, lane_id=1, s=0)
    middle = Waypoint(4, 0, 0, road_id=20, lane_id=1, s=4)
    end = Waypoint(8, 4, 45, road_id=20, lane_id=1, s=10)
    left = Waypoint(4, -3.5, 0, road_id=20, lane_id=2, s=4)
    right = Waypoint(4, 3.5, 0, road_id=20, lane_id=-1, s=4)
    start.children = [middle]
    middle.children = [end]
    for waypoint in (start, middle, end):
        waypoint.left = left
        waypoint.right = right
    world_map = TopologyMap([(start, end)], [start, middle, end])
    manager = RouteManager(world_map, sample_step_m=2.0, maximum_gap_m=6.0)
    route = manager.plan(start.transform, end.transform, 5.0)

    state = manager.state(route, 4.0, 0.2)

    assert state.route_s == pytest.approx(4.0, abs=0.3)
    assert 0.0 < state.route_progress < 1.0
    assert state.route_remaining_m > 0.0
    assert state.lane_id == 1
    assert state.lane_relation == "CURRENT"
    assert state.left_lane_id == 2
    assert state.right_lane_id == -1
    assert state.road_curvature > 0.0
    assert state.reached_destination is False
    assert state.status == "ON_ROUTE"
    assert state.requires_replan is False

    left_placement = manager.placement(route, 4.0, "LEFT")
    assert left_placement.route_s == pytest.approx(4.0)
    assert left_placement.lane_relation == "LEFT"
    assert left_placement.lane_id == 2

    off_route = manager.state(route, 4.0, 20.0, previous_s_m=state.route_s)
    assert off_route.status == "OFF_ROUTE"
    assert off_route.reason == "ROUTE_DEVIATION_REPLAN_REQUIRED"
    assert off_route.requires_replan is True

    replanned = manager.replan(start.transform, end.transform, 5.0)
    assert replanned.reference.metadata["planning_reason"] == "OFF_ROUTE_REPLAN"


def test_missing_adjacent_lane_returns_explicit_reason() -> None:
    start = Waypoint(0, 0, 0, road_id=21, lane_id=1, s=0)
    end = Waypoint(4, 0, 0, road_id=21, lane_id=1, s=4)
    world_map = TopologyMap([(start, end)], [start, end])
    manager = RouteManager(world_map, sample_step_m=2.0)
    route = manager.plan(start.transform, end.transform, 5.0)

    with pytest.raises(RoutePlanningError) as error:
        manager.placement(route, 2.0, "RIGHT")

    assert error.value.code == "ROUTE_LANE_UNAVAILABLE"


def test_recovery_tracker_confirms_cools_down_and_exhausts_attempts() -> None:
    start = Waypoint(0, 0, 0, road_id=22, lane_id=1, s=0)
    end = Waypoint(4, 0, 0, road_id=22, lane_id=1, s=4)
    world_map = TopologyMap([(start, end)], [start, end])
    manager = RouteManager(world_map, sample_step_m=2.0)
    route = manager.plan(start.transform, end.transform, 5.0)
    off_route = manager.state(route, 4.0, 20.0)
    tracker = RouteRecoveryTracker(RouteRecoveryPolicy(
        confirmation_s=0.5,
        cooldown_s=2.0,
        maximum_attempts=2,
    ))

    assert tracker.observe(off_route, 0.0).status == "OFF_ROUTE_CONFIRMING"
    assert tracker.observe(off_route, 0.4).should_replan is False
    first = tracker.observe(off_route, 0.5)
    assert first.should_replan is True
    assert first.attempt == 1

    tracker.note_replan_succeeded()
    assert tracker.observe(off_route, 0.6).status == "OFF_ROUTE_CONFIRMING"
    assert tracker.observe(off_route, 1.1).status == "REPLAN_COOLDOWN"
    second = tracker.observe(off_route, 2.6)
    assert second.should_replan is True
    assert second.attempt == 2

    assert tracker.observe(off_route, 2.7).status == "OFF_ROUTE_CONFIRMING"
    exhausted = tracker.observe(off_route, 3.2)
    assert exhausted.status == "RECOVERY_EXHAUSTED"
    assert exhausted.reason == "ROUTE_REPLAN_ATTEMPTS_EXHAUSTED"


def test_recovery_is_suppressed_during_intentional_manoeuvre() -> None:
    start = Waypoint(0, 0, 0, road_id=23, lane_id=1, s=0)
    end = Waypoint(4, 0, 0, road_id=23, lane_id=1, s=4)
    world_map = TopologyMap([(start, end)], [start, end])
    manager = RouteManager(world_map, sample_step_m=2.0)
    route = manager.plan(start.transform, end.transform, 5.0)
    off_route = manager.state(route, 4.0, 20.0)
    tracker = RouteRecoveryTracker(RouteRecoveryPolicy(confirmation_s=0.0))

    suppressed = tracker.observe(
        off_route, 1.0, recovery_suppressed=True,
    )

    assert suppressed.status == "RECOVERY_SUPPRESSED"
    assert suppressed.reason == "INTENTIONAL_MANEUVER_ACTIVE"
    assert tracker.attempts == 0


def test_replan_connects_current_pose_before_returning_to_lane() -> None:
    start = Waypoint(0, 0, 0, road_id=24, lane_id=1, s=0)
    middle = Waypoint(2, 0, 0, road_id=24, lane_id=1, s=2)
    end = Waypoint(4, 0, 0, road_id=24, lane_id=1, s=4)
    start.children = [middle]
    middle.children = [end]
    world_map = TopologyMap([(start, end)], [start, middle, end])
    manager = RouteManager(
        world_map, sample_step_m=2.0, off_route_threshold_m=1.0,
    )
    current = SimpleNamespace(
        location=location(0, 2),
        rotation=SimpleNamespace(yaw=0.0),
    )

    route = manager.replan(current, end.transform, 5.0)
    state = manager.state(route, 0.0, 2.0)

    assert route.reference.points_xy_m[0] == pytest.approx((0.0, 2.0))
    assert route.reference.metadata["recovery_connector_m"] == pytest.approx(2.0)
    assert route.reference.route_id.startswith("replan-")
    assert state.cross_track_error_m == pytest.approx(0.0)
    assert state.status == "ON_ROUTE"


def test_rejoin_preserves_forward_mission_suffix_instead_of_regenerating_coverage() -> None:
    manager, nodes = _linear_route_manager(100)
    mission = manager.plan_distance(nodes[0].transform, 100.0, 5.0)
    current = SimpleNamespace(
        location=location(10, 2),
        rotation=SimpleNamespace(yaw=0.0),
    )

    recovered = manager.rejoin_route(
        current,
        mission,
        route_s=10.0,
        target_speed_mps=5.0,
        lookahead_m=20.0,
    )

    assert recovered.reference.points_xy_m[0] == pytest.approx((10.0, 2.0))
    assert recovered.destination_xy_m == pytest.approx(mission.destination_xy_m)
    assert recovered.reference.points_xy_m[-1] == pytest.approx((100.0, 0.0))
    assert recovered.reference.metadata["planning_reason"] == "OFF_ROUTE_REJOIN"
    assert recovered.reference.metadata["source_route_id"] == mission.reference.route_id
    assert recovered.reference.metadata["rejoin_route_s_m"] >= 30.0
    assert min(point[0] for point in recovered.reference.points_xy_m) >= 10.0


def _linear_route_manager(length_m: int = 200) -> tuple[RouteManager, list[Waypoint]]:
    nodes = [
        Waypoint(index, 0, 0, road_id=25, lane_id=1, s=index)
        for index in range(length_m + 1)
    ]
    for first, second in zip(nodes, nodes[1:]):
        first.children = [second]
    world_map = TopologyMap([(nodes[0], nodes[-1])], nodes)
    return RouteManager(world_map, sample_step_m=1.0), nodes


def test_local_reference_is_bounded_and_preserves_global_coordinates() -> None:
    manager, nodes = _linear_route_manager()
    route = manager.plan(nodes[0].transform, nodes[-1].transform, 9.0)

    local = manager.local_reference(
        route, 100.0, 7.0, lookbehind_m=10.0, lookahead_m=30.0,
    )

    assert local.points_xy_m[0] == pytest.approx((90.0, 0.0))
    assert local.points_xy_m[-1] == pytest.approx((130.0, 0.0))
    assert len(local.points_xy_m) < len(route.reference.points_xy_m)
    assert local.target_speed_mps == 7.0
    assert local.metadata["global_route_id"] == route.reference.route_id
    assert local.metadata["global_route_s_m"] == pytest.approx(100.0)


def test_local_reference_near_destination_retains_a_segment() -> None:
    manager, nodes = _linear_route_manager(10)
    route = manager.plan(nodes[0].transform, nodes[-1].transform, 4.0)

    local = manager.local_reference(route, route.total_length_m, 0.0)

    assert len(local.points_xy_m) >= 2
    assert local.points_xy_m[-1] == pytest.approx(route.destination_xy_m)
    assert local.metadata["global_s_end_m"] == pytest.approx(route.total_length_m)


def test_mission_placement_translates_progress_after_replan() -> None:
    manager, nodes = _linear_route_manager(20)
    route = manager.plan(nodes[0].transform, nodes[-1].transform, 4.0)

    placement = manager.mission_placement(route, 17.0, 10.0)

    assert placement.route_s == pytest.approx(17.0)
    assert placement.x_m == pytest.approx(7.0)
    with pytest.raises(RoutePlanningError, match="ROUTE_EVENT_ALREADY_PASSED"):
        manager.mission_placement(route, 9.0, 10.0)
    with pytest.raises(RoutePlanningError, match="ROUTE_EVENT_BEYOND_ACTIVE_ROUTE"):
        manager.mission_placement(route, 31.0, 10.0)


def test_discontinuous_topology_edge_is_rejected() -> None:
    start = Waypoint(0, 0, 0, road_id=30, s=0)
    end = Waypoint(50, 0, 0, road_id=30, s=50)
    world_map = TopologyMap([(start, end)], [start, end])

    with pytest.raises(RoutePlanningError) as error:
        RouteManager(world_map, sample_step_m=2.0).plan(
            start.transform, end.transform, 5.0,
        )

    assert error.value.code == "ROUTE_DISCONTINUOUS"


def test_repeated_waypoint_in_topology_edge_is_rejected_as_loop() -> None:
    start = Waypoint(0, 0, 0, road_id=40, s=0)
    middle = Waypoint(2, 0, 0, road_id=40, s=2)
    end = Waypoint(10, 0, 0, road_id=40, s=10)
    start.children = [middle]
    middle.children = [start]
    world_map = TopologyMap([(start, end)], [start, middle, end])

    with pytest.raises(RoutePlanningError) as error:
        RouteManager(world_map, sample_step_m=2.0).plan(
            start.transform, end.transform, 5.0,
        )

    assert error.value.code == "ROUTE_LOOP_DETECTED"
