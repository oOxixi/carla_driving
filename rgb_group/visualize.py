from __future__ import annotations


def draw_observation(image_bgr, observation):
    import cv2

    canvas = image_bgr.copy()
    for obj in observation.objects:
        x1, y1, x2, y2 = obj.bbox_xyxy
        label = f"{obj.category} {obj.confidence:.2f} {obj.image_region}"
        cv2.rectangle(canvas, (x1, y1), (x2, y2), (255, 255, 255), 2)
        cv2.putText(canvas, label, (x1, max(18, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 255), 1, cv2.LINE_AA)
    text = f"frame={observation.frame} status={observation.perception_status} light={observation.traffic_light.state} latency={observation.latency_ms:.1f}ms"
    cv2.putText(canvas, text, (12, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (255, 255, 255), 2, cv2.LINE_AA)
    return canvas
