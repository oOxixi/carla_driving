from rgb_group.schemas import Detection, TrafficLightObservation, VisionObservation


def test_observation_summary():
    obs = VisionObservation(
        frame=10,
        sim_time_s=0.5,
        sensor_id="front_rgb",
        image_width=1280,
        image_height=720,
        objects=[Detection("x", "PEDESTRIAN", 0.9, (500, 200, 600, 700), "FRONT_CENTER", True)],
        traffic_light=TrafficLightObservation("RED", 0.9, True, (600, 50, 640, 130), "TEST"),
    )
    assert obs.scene_summary["front_pedestrian"]
    assert obs.scene_summary["red_light"]
