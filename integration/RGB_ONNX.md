# RGB ONNX vehicle and pedestrian detection

The sensor bridge can run an Ultralytics-style COCO detection model on every
frame-aligned CARLA RGB image.  The retained classes are person, bicycle, car,
motorcycle, bus and truck.  A central-corridor detection and the same-frame
front LiDAR range produce `lead_distance_m`; the first implementation treats
the object as stationary and never uses CARLA actor truth for its speed.

Install one ONNX Runtime package (CPU shown here):

```powershell
python -m pip install -r requirements.txt
```

Place a compatible model outside Git, for example:

```text
artifacts/models/yolo11n.onnx
```

Run on the already-loaded CARLA map:

```powershell
python -m integration.carla_runner `
  --host 127.0.0.1 --port 2000 `
  --perception-mode sensors --scenario-facts-mode perception `
  --rgb-detector-model artifacts/models/yolo11n.onnx `
  --rgb-detector-confidence 0.25 `
  --scenario follow --frames 120
```

Auditable frame fields include `scene.detected_objects` and source labels:

- `RGB_ONNX_OBJECT_DETECTOR`
- `RGB_ONNX_LIDAR_FRONT_CORRIDOR`
- `RGB_LIDAR_STATIC_OBSTACLE_ASSUMPTION`
- `LIDAR_UNCLASSIFIED_FRONT_CORRIDOR` when LiDAR sees an obstacle that RGB misses

If the configured model cannot load or inference fails, perception raises a
fail-closed error and normal propulsion is suppressed.  Model weights are not
committed by default.  Confirm the model license and competition distribution
rules before packaging third-party weights.
