from __future__ import annotations

from typing import List, Tuple

from .geometry import (
    build_camera_intrinsic,
    image_region,
    is_in_danger_zone,
    project_actor_bbox,
    world_to_camera_matrix,
)
from .schemas import Detection, TrafficLightObservation


OBSTACLE_CATEGORIES = {
    "VEHICLE",
    "PEDESTRIAN",
    "BICYCLE",
    "MOTORCYCLE",
    "TRAFFIC_CONE",
    "ROADBLOCK",
}


def _category(type_id: str) -> str:
    """Map CARLA actor type IDs to the shared perception categories."""

    actor_type = str(type_id).lower()

    if actor_type.startswith("vehicle."):
        if "bicycle" in actor_type or "bike" in actor_type:
            return "BICYCLE"

        if "motorcycle" in actor_type:
            return "MOTORCYCLE"

        return "VEHICLE"

    if actor_type.startswith("walker.pedestrian"):
        return "PEDESTRIAN"

    if (
        "trafficcone" in actor_type
        or "traffic_cone" in actor_type
        or "cone" in actor_type
    ):
        return "TRAFFIC_CONE"

    if (
        "barrier" in actor_type
        or "roadblock" in actor_type
    ):
        return "ROADBLOCK"

    if actor_type.startswith("traffic.traffic_light"):
        return "TRAFFIC_LIGHT"

    return "UNKNOWN"


def _light_state(actor) -> str:
    """Read a CARLA traffic light state safely."""

    try:
        raw_value = str(actor.get_state())
        state = raw_value.split(".")[-1].upper()
    except Exception:
        return "UNKNOWN"

    if state in {"RED", "YELLOW", "GREEN", "OFF"}:
        return state

    return "UNKNOWN"


def _bbox_area_ratio(
    bbox,
    width: int,
    height: int,
) -> float:
    box_width = max(0, int(bbox[2]) - int(bbox[0]))
    box_height = max(0, int(bbox[3]) - int(bbox[1]))

    image_area = max(1, int(width) * int(height))

    return float(box_width * box_height) / float(image_area)


def _valid_traffic_light_bbox(
    bbox,
    width: int,
    height: int,
) -> bool:
    """Reject obviously invalid CARLA traffic-light projections.

    CARLA traffic-light actors can include pole/trigger geometry. When such
    geometry is close to the camera, its projected actor bounding box can
    cover most of the image. These boxes are unsuitable as visual GT.
    """

    box_width = int(bbox[2]) - int(bbox[0])
    box_height = int(bbox[3]) - int(bbox[1])
    area_ratio = _bbox_area_ratio(bbox, width, height)

    if box_width < 3 or box_height < 3:
        return False

    if area_ratio > 0.12:
        return False

    if box_width > int(width * 0.45):
        return False

    if box_height > int(height * 0.55):
        return False

    return True


class CarlaGroundTruthBackend:
    """Simulation-only perception backend.

    This backend projects CARLA actor bounding boxes into the front RGB
    camera image. It exists to freeze interfaces and support controlled
    simulation tests before a real ONNX detector is available.

    Its output must never be reported as real RGB model accuracy.
    """

    name = "CARLA_GT"

    def __init__(
        self,
        world,
        ego_vehicle,
        width: int,
        height: int,
        fov_deg: float,
        max_distance_m: float = 80.0,
    ) -> None:
        self.world = world
        self.ego_vehicle = ego_vehicle
        self.width = int(width)
        self.height = int(height)
        self.max_distance_m = float(max_distance_m)

        self.k = build_camera_intrinsic(
            width=self.width,
            height=self.height,
            fov_deg=float(fov_deg),
        )

    def infer(
        self,
        image_bgr,
        sensor_transform,
    ) -> Tuple[
        List[Detection],
        TrafficLightObservation,
        List[str],
    ]:
        """Generate structured perception from CARLA simulator actors."""

        world_to_camera = world_to_camera_matrix(
            sensor_transform
        )

        ego_location = self.ego_vehicle.get_location()

        detections: List[Detection] = []

        # Each item:
        # (
        #   is_center_candidate,
        #   bbox_area,
        #   confidence,
        #   detection,
        #   traffic_light_state,
        # )
        light_candidates = []

        actors = self.world.get_actors()

        for actor in actors:
            if actor.id == self.ego_vehicle.id:
                continue

            category = _category(actor.type_id)

            if category == "UNKNOWN":
                continue

            try:
                actor_location = actor.get_location()
                distance_m = ego_location.distance(actor_location)
            except Exception:
                continue

            if distance_m > self.max_distance_m:
                continue

            bbox = project_actor_bbox(
                actor=actor,
                world_to_camera=world_to_camera,
                intrinsic=self.k,
                width=self.width,
                height=self.height,
                near_clip_m=0.5,
            )

            if bbox is None:
                continue

            if (
                category == "TRAFFIC_LIGHT"
                and not _valid_traffic_light_bbox(
                    bbox=bbox,
                    width=self.width,
                    height=self.height,
                )
            ):
                continue

            region = image_region(
                bbox=bbox,
                width=self.width,
            )

            if category == "PEDESTRIAN":
                x1, y1, x2, y2 = bbox
                center_x = (x1 + x2) / 2.0
                bottom_y = y2
                box_height = y2 - y1

                in_danger_zone = (
                    self.width * 0.30
                    <= center_x
                    <= self.width * 0.70
                    and bottom_y >= self.height * 0.58
                    and box_height >= self.height * 0.08
                )

            elif category in {
                "VEHICLE",
                "BICYCLE",
                "MOTORCYCLE",
                "TRAFFIC_CONE",
                "ROADBLOCK",
            }:
                in_danger_zone = is_in_danger_zone(
                    bbox=bbox,
                    width=self.width,
                    height=self.height,
                )

            else:
                in_danger_zone = False

            confidence = max(
                0.55,
                1.0
                - distance_m
                / (self.max_distance_m * 1.3),
            )
            confidence = min(float(confidence), 0.99)

            detection = Detection(
                track_id=f"carla_{actor.id}",
                category=category,
                confidence=confidence,
                bbox_xyxy=bbox,
                image_region=region,
                in_danger_zone=in_danger_zone,
                source=self.name,
                metadata={
                    "actor_id": int(actor.id),
                    # Debug-only field. It is not a LiDAR distance output.
                    "distance_m_debug": round(
                        float(distance_m),
                        2,
                    ),
                },
            )

            detections.append(detection)

            if category == "TRAFFIC_LIGHT":
                box_area = (
                    (bbox[2] - bbox[0])
                    * (bbox[3] - bbox[1])
                )

                is_center_candidate = (
                    region == "FRONT_CENTER"
                )

                light_candidates.append(
                    (
                        is_center_candidate,
                        int(box_area),
                        confidence,
                        detection,
                        _light_state(actor),
                    )
                )

        detections.sort(
            key=lambda detection: (
                not detection.in_danger_zone,
                -float(detection.confidence),
            )
        )

        if light_candidates:
            # Prefer a center traffic light, then a larger and more
            # confident visible traffic light.
            selected = sorted(
                light_candidates,
                key=lambda item: (
                    not item[0],
                    -item[1],
                    -item[2],
                ),
            )[0]

            _, _, _, selected_detection, state = selected

            traffic_light = TrafficLightObservation(
                state=state,
                confidence=selected_detection.confidence,
                visible=True,
                bbox_xyxy=selected_detection.bbox_xyxy,
                source=self.name,
            )
        else:
            traffic_light = TrafficLightObservation()

        warnings = [
            "SIMULATION_GT_BACKEND_NOT_FOR_REAL_MODEL_ACCURACY"
        ]

        return detections, traffic_light, warnings
