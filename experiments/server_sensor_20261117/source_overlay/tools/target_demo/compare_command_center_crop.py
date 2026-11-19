"""Offline fixed center-crop comparison, never used for live control."""
import json
from pathlib import Path
import numpy as np
from PIL import Image
from integration.rgb_detector import OnnxYoloDetector

root=Path('artifacts/runtime/command_frame_diagnostics_20261112')
model=Path('/home/tiaozhansai/carla-driving-2B/deliveries/day7.19_group1/models/yolov8n.onnx')
detector=OnnxYoloDetector(model,confidence_threshold=.35)
for distance in (40,60):
    folder=root/str(distance)/'capture'
    image=np.asarray(Image.open(folder/'camera_rgb.png').convert('RGB'))
    bounds=(200,100,600,300)  # Fixed center crop; actor truth is not an input.
    x1,y1,x2,y2=bounds
    detections=detector.detect_rgb(image[y1:y2,x1:x2])
    output={'crop_xyxy_px':bounds,'confidence_threshold':.35,'detections':[{'class':obj.class_name,'confidence':obj.confidence,'bbox_original_px':[obj.bbox_xyxy_norm[i]*([x2-x1,y2-y1,x2-x1,y2-y1][i])+([x1,y1,x1,y1][i]) for i in range(4)]} for obj in detections]}
    (folder/'center_crop_comparison.json').write_text(json.dumps(output,indent=2,ensure_ascii=False))
    print(distance,json.dumps(output,ensure_ascii=False))
