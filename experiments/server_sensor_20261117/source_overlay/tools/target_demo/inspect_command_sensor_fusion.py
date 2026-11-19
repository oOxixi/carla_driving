"""Inspect same-frame camera/LiDAR/radar association; truth is evaluation-only."""
import json,math
from pathlib import Path
import numpy as np
from PIL import Image
from integration.rgb_detector import OnnxYoloDetector
from integration.experimental_crop_detector import ExperimentalCropDetector
MODEL='/home/tiaozhansai/carla-driving-2B/deliveries/day7.19_group1/models/yolov8n.onnx'
def transform(p,m):return (np.column_stack((p,np.ones(len(p))))@np.asarray(m).T)[:,:3]
for d in (40,60):
 p=Path(f'artifacts/runtime/command_frame_diagnostics_20261112/{d}/capture');m=json.loads((p/'metadata.json').read_text());img=np.array(Image.open(p/'camera_rgb.png').convert('RGB'));camera=m['rgb']; h,w=img.shape[:2];f=w/(2*math.tan(math.radians(camera['fov'])/2));cam_inv=np.linalg.inv(camera['world_matrix']);ego_inv=np.linalg.inv(m['ego_world_matrix'])
 def project(x):
  c=transform(x,cam_inv);return np.column_stack((f*c[:,1]/c[:,0]+w/2,-f*c[:,2]/c[:,0]+h/2,c[:,0]))
 model=ExperimentalCropDetector(OnnxYoloDetector(MODEL));detections=model.detect_rgb(img); boxes=np.array([np.array(o.bbox_xyxy_norm)*[w,h,w,h] for o in detections if o.class_name=='car']); objects=[o for o in detections if o.class_name=='car']
 lp=np.load(p/'lidar_xyzi.npy')[:,:3]; lw=transform(lp,m['lidar']['world_matrix']);lpix=project(lw)
 rr=m['radar']['returns']; rp=np.array([[r['depth']*math.cos(r['altitude'])*math.cos(r['azimuth']),r['depth']*math.cos(r['altitude'])*math.sin(r['azimuth']),r['depth']*math.sin(r['altitude'])] for r in rr]);rw=transform(rp,m['radar']['world_matrix']);rpix=project(rw)
 actors=m['evaluation_only_ground_truth_actors']; summaries=[]
 for o,b in zip(objects,boxes):
  def inside(pix):return (pix[:,2]>0)&(pix[:,0]>=b[0])&(pix[:,0]<=b[2])&(pix[:,1]>=b[1])&(pix[:,1]<=b[3])
  lm=inside(lpix);rm=inside(rpix); details=[]
  for a in actors:
   if a['role_name'].endswith(':ego'):continue
   inv=np.linalg.inv(a['world_matrix']);av=transform(np.array(a['vertices_world']),inv);lo=av.min(axis=0)-.25;hi=av.max(axis=0)+.25
   def count(world,mask):
    if not mask.any(): return 0
    q=transform(world[mask],inv);return int(np.all((q>=lo)&(q<=hi),axis=1).sum())
   details.append((a['role_name'],count(lw,lm),count(rw,rm)))
  le=transform(lw[lm],ego_inv);re=transform(rw[rm],ego_inv)
  summaries.append({'score':round(o.confidence,3),'bbox_px':np.round(b,1).tolist(),'lidar_points':len(le),'lidar_ego_xyz':np.round(le,1).tolist(),'radar_points':len(re),'radar_ego_xyz':np.round(re,1).tolist(),'radar_velocity_mps':[round(rr[i]['velocity'],1) for i in np.where(rm)[0]],'eval_actor_overlap_counts':details})
 result={'scenario':d,'frame':m['frame'],'sync_rgb_lidar':m['rgb']['timestamp']-m['lidar']['timestamp'],'sync_rgb_radar':m['rgb']['timestamp']-m['radar']['timestamp'],'objects':summaries}
 (p/'sensor_fusion_diagnostic.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))
