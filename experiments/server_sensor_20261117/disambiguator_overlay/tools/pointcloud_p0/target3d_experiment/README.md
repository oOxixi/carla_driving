# 3D target disambiguation: isolated research

This directory is an offline experiment and is not imported by the production detection, tracking, localization, planning, or control paths. It is not a safety-qualified target tracker.

`Target3DDisambiguator` consumes same-sensor-frame LiDAR observations, frame-local raw point IDs, detection boxes, selected cluster IDs, and timestamps. It computes duplicate ID evidence, 3-D nearest distance, LiDAR-radial interval gaps, cluster spans and unselected-point geometry. Detection-box IoU is diagnostic only: overlapping boxes are not automatically combined. Lack of a calibrated research policy, missing actual continuous observations, absent clusters, inconsistent track/frame/timestamp, and duplicate ownership fail closed to `UNKNOWN`. Physical-object mixing cannot be excluded from the available sensor-only data. Even the optional multi-observation `SUPPORTED_UNVALIDATED` result has no driving-control authority.

`run_two_samples.py` loads the two saved frames and the pre-existing independent human review. The human review selects evaluation cases only. It reserves the formal channel, runs the existing scheme C on remaining points and tests only the requested radii. It writes `frozen_sensor_decisions.json` **before** opening semantic LiDAR or using actor ground truth for the audit. Semantic nearest-neighbor results and actor bounding boxes are only used after decisions to produce `offline_audit.json` and `point_ownership.csv`; none enter the sensor-only module. Actor association is the original automatic IoU matching, not an error-free identity label.

Run on the project server from the isolated worktree:

```bash
PYTHONPATH=$PWD /home/tiaozhansai/carla-driving-challenge/.venv/bin/python -m tools.pointcloud_p0.target3d_experiment.run_two_samples \
  --holdout-root /home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime/pointcloud_adaptive_development_20261117/new_scenes/holdout \
  --threshold-detections /home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime/yolo_threshold_sensitivity_20261117/detections.json \
  --manual-identities /home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime/yolo_dual_channel_isolation_20261117/identity_annotations.json \
  --output "$PWD/artifacts/runtime/target3d_disambiguator_20261117"
PYTHONPATH=$PWD /home/tiaozhansai/carla-driving-challenge/.venv/bin/python -m tools.pointcloud_p0.target3d_experiment.verify_two_samples \
  --output "$PWD/artifacts/runtime/target3d_disambiguator_20261117" \
  --holdout-root /home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime/pointcloud_adaptive_development_20261117/new_scenes/holdout
PYTHONPATH=$PWD /home/tiaozhansai/carla-driving-challenge/.venv/bin/python -m pytest -q \
  tools/pointcloud_p0/target3d_experiment/test_disambiguator.py \
  integration/tests/test_target_pointcloud_localization.py \
  integration/tests/test_duplicate_detection_grouper.py \
  integration/tests/test_pointcloud_p0_audit.py
```

`visualization.html` presents saved camera-box overlays and a top-down view; `interactive_3d.html` provides an optional rotatable view. Both read `visualization.json` from the output directory. Generate the camera images with `prepare_camera_views.py` using the same output, holdout root, and detections paths shown above; then copy both HTML files into the output directory. The second frame has no 0.35 formal detection: its neighboring group is also auxiliary, never a fabricated formal target.
