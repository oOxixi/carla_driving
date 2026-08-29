# C validation records

This folder records member C sensor/perception validation evidence.

Scope:
- deterministic C role validation
- RGB/LiDAR frame alignment
- front distance and TTC evidence
- sensor failure / fail-closed behavior
- CARLA sensors-mode scenario evidence

Do not treat world/scenario truth as final perception evidence.

## 2026-07-31 CARLA Sensor Validation

Validated C-side perception and safety-state evidence on branch `new`.

Completed evidence:
- `deterministic_C_role_validation`: PASS.
- `D03_front_vehicle_brake`: SUCCEEDED, LiDAR front-distance/TTC safety evidence.
- `D07_low_ttc_emergency_brake`: SUCCEEDED, low-TTC emergency brake evidence.
- `D02_pedestrian_crossing`: SUCCEEDED after enabling RGB ONNX detection and recording C fail-closed perception override reason.

D02 notes:
- Initial D02 sensor run failed because RGB detector was unavailable or C visual confidence threshold rejected weak detections.
- With YOLO ONNX enabled and `--c-visual-confidence-threshold 0.50`, the detector produced person evidence.
- C accepted `PERSON` and requested `FULL_BRAKE` with reason `visual_hazard_without_range`.
- Runner records this as `C_FRONT_PEDESTRIAN_VISUAL_HAZARD_WITHOUT_RANGE`, allowing the D02 expected reason contract to pass.
- Final D02 evidence: no collision, no route deviation, score 25.0, status SUCCEEDED.

Important boundary:
- D03/D07 mainly validate LiDAR/front-distance/TTC risk handling.
- D02 validates RGB pedestrian evidence plus C fail-closed behavior.
- World/scenario truth should not be treated as final sensor perception evidence.

## Named C Deliverables

The team handoff names five C-role deliverables. This repository keeps them
under `car_control_C/` as lightweight, auditable wrappers around the validated
runtime path:

- `sensor_adapter.py`: frame/timestamp/extrinsics audit records for RGB/LiDAR/Radar inputs.
- `rgb_pipeline.py`: ROI, Top-K detection, tracking-jump guard, and P95 latency summaries.
- `fusion_tracker.py`: stable C target IDs plus distance, speed, TTC, and risk-level export.
- `perception_state.json`: sample B/D-readable PerceptionState without raw sensor access.
- `fault_injection.sh`: repeatable fault-injection evidence commands for camera blackout, radar dropout, LiDAR missing frame, false positive, false negative, and latency noise.
