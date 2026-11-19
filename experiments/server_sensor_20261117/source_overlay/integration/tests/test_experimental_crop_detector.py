import numpy as np
import pytest
from integration.contracts import DetectedObject
from integration.experimental_crop_detector import ExperimentalCropDetector

def obj(score, box, cls=2, name='car'):
    return DetectedObject(cls,name,score,box)

class FakeDetector:
    confidence_threshold=.35
    iou_threshold=.45
    def __init__(self, outputs): self.outputs=list(outputs); self.calls=[]
    def detect_rgb(self, image):
        self.calls.append((image.shape,self.confidence_threshold))
        result=self.outputs.pop(0)
        if isinstance(result,Exception): raise result
        return result

def test_forward_crop_maps_and_confirms_low_candidate_without_duplicate():
    low=obj(.08,(.49,.39,.51,.41)); hit=obj(.8,(.48,.38,.52,.42))
    d=FakeDetector([(low,),(hit,)])
    result=ExperimentalCropDetector(d).detect_rgb(np.zeros((100,200,3),dtype=np.uint8))
    assert len(d.calls)==2 and d.calls[0][1]==.05 and d.calls[1][1]==.35
    assert len(result)==1 and result[0].confidence==.8
    assert result[0].bbox_xyxy_norm==pytest.approx((.49,.391,.51,.409))

def test_unverified_low_candidate_never_becomes_final_and_gets_own_crop():
    d=FakeDetector([(obj(.08,(.02,.30,.04,.32)),),(),()])
    result=ExperimentalCropDetector(d).detect_rgb(np.zeros((450,800,3),dtype=np.uint8))
    assert len(d.calls)==3 and not result

def test_threshold_restored_on_detector_failure():
    d=FakeDetector([RuntimeError('failed')])
    with pytest.raises(RuntimeError): ExperimentalCropDetector(d).detect_rgb(np.zeros((100,200,3),dtype=np.uint8))
    assert d.confidence_threshold==.35
