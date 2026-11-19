"""Read saved sensor payloads without changing the recordings."""
import json,pathlib,types
import numpy as np
class TF:
 def __init__(self,m):self.m=np.asarray(m,dtype=float)
 def get_matrix(self):return self.m
 def get_inverse_matrix(self):return np.linalg.inv(self.m)
class Radar:
 def __init__(self,d,tf,frame):
  self.transform=tf;self.frame=frame;self.timestamp=0.;a=np.frombuffer(d,dtype=np.float32).reshape(-1,4)
  self.points=[types.SimpleNamespace(velocity=float(v),azimuth=float(z),altitude=float(t),depth=float(r)) for v,z,t,r in a]
 def __iter__(self):return iter(self.points)
def read(p):
 p=pathlib.Path(p);d=json.loads((p/'result.json').read_text());frame=d['frame'];lid=types.SimpleNamespace(raw_data=(p/'lidar.bin').read_bytes(),transform=TF(d['lidar_transform']),frame=frame,timestamp=0.);rgb=types.SimpleNamespace(transform=TF(d['camera_transform']),width=800,height=450,frame=frame,timestamp=0.);rad=Radar((p/'radar.bin').read_bytes(),TF(d['radar_transform']),frame);ego=TF(d['ego_transform']);objs=[types.SimpleNamespace(track_id=o['id'],class_name=o['class'],confidence=o['confidence'],bbox_xyxy_norm=o['bbox']) for o in d['predictions']];return d,lid,rgb,rad,ego,objs
