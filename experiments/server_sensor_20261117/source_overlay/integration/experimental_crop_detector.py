"""Experimental coarse-to-fine RGB detection; never weakens control gates."""
from __future__ import annotations
from dataclasses import replace
import numpy as np
from .rgb_detector import carla_rgb_array, _class_aware_nms

class ExperimentalCropDetector:
    def __init__(self, detector, low_threshold=0.05, max_candidate_crops=2):
        if not 0 < low_threshold < detector.confidence_threshold:
            raise ValueError('low threshold must be below detector threshold')
        self.detector = detector
        self.low_threshold = low_threshold
        self.max_candidate_crops = max_candidate_crops
        self.last_stats = {}

    def detect_measurement(self, measurement):
        return self.detect_rgb(carla_rgb_array(measurement))

    def detect_rgb(self, image):
        image=np.asarray(image); height,width=image.shape[:2]
        threshold=self.detector.confidence_threshold
        try:
            self.detector.confidence_threshold=self.low_threshold
            coarse=self.detector.detect_rgb(image)
        finally:
            self.detector.confidence_threshold=threshold
        final=[x for x in coarse if x.confidence >= threshold]
        low=[x for x in coarse if x.confidence < threshold and x.class_name in ('car','truck','bus')]
        regions=[]
        crop_counts=[]
        def run_crop(region):
            xa,ya,xb,yb=region
            detections=self.detector.detect_rgb(image[ya:yb,xa:xb])
            regions.append(region); crop_counts.append(len(detections))
            for obj in detections:
                bx1,by1,bx2,by2=obj.bbox_xyxy_norm
                norm=((xa+bx1*(xb-xa))/width,(ya+by1*(yb-ya))/height,
                      (xa+bx2*(xb-xa))/width,(ya+by2*(yb-ya))/height)
                final.append(replace(obj,bbox_xyxy_norm=norm))
        run_crop((int(width*.25),int(height*.22),int(width*.75),int(height*.67)))
        for obj in sorted(low,key=lambda item:item.confidence,reverse=True)[:self.max_candidate_crops]:
            x1,y1,x2,y2=obj.bbox_xyxy_norm
            # Already verified by the forward crop or the full image.
            matched=False
            for hit in final:
                if hit.class_id != obj.class_id: continue
                a,b,c,d=hit.bbox_xyxy_norm
                inter=max(0,min(x2,c)-max(x1,a))*max(0,min(y2,d)-max(y1,b))
                union=(x2-x1)*(y2-y1)+(c-a)*(d-b)-inter
                if union > 0 and inter/union >= .3:
                    matched=True; break
            if matched: continue
            cx=(x1+x2)*width/2; cy=(y1+y2)*height/2
            crop_w=max(width*.25,(x2-x1)*width*8); crop_h=max(height*.27,(y2-y1)*height*8)
            xa=max(0,int(cx-crop_w/2)); ya=max(0,int(cy-crop_h/2))
            xb=min(width,int(cx+crop_w/2)); yb=min(height,int(cy+crop_h/2))
            if xb-xa >= 32 and yb-ya >= 32: run_crop((xa,ya,xb,yb))
        if final:
            boxes=np.asarray([x.bbox_xyxy_norm for x in final]); scores=np.asarray([x.confidence for x in final]); ids=np.asarray([x.class_id for x in final])
            keep=_class_aware_nms(boxes,scores,ids,self.detector.iou_threshold)
            final=[final[i] for i in keep]
        self.last_stats={'coarse':len(coarse),'low_vehicle_candidates':len(low),'regions':regions,'crop_detection_counts':crop_counts,'final':len(final)}
        return tuple(final)
