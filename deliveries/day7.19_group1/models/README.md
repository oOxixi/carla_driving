# Models

Place a COCO-style YOLOv8/YOLO11 detection ONNX model here as:

`models/yolov8n.onnx`

The generic ONNX backend detects person, bicycle, car, motorcycle, bus, truck and traffic-light objects.
A COCO detector does not determine the traffic-light color; until a dedicated color classifier is added,
its structured state is `UNKNOWN`. For immediate CARLA interface tests, use `--backend carla_gt`.
