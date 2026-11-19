import json,math,numpy as np
from pathlib import Path
root=Path('/home/tiaozhansai/carla-driving-target-and-provement')
for c in ['40','60']:
 p=root/f'artifacts/runtime/command_frame_diagnostics_20261112/{c}/capture';m=json.load(open(p/'metadata.json'));ds=json.load(open(p/'center_crop_comparison.json'))['detections'];rgb=m['rgb'];camera=np.linalg.inv(np.array(rgb['world_matrix']));w,h=rgb['width'],rgb['height'];f=w/(2*math.tan(math.radians(rgb['fov'])/2));boxes=[]
 for a in m['evaluation_only_ground_truth_actors']:
  if a['role_name'].endswith(':ego'):continue
  pts=np.array(a['vertices_world']);q=np.column_stack([pts,np.ones(len(pts))])@camera.T
  if any(q[:,0]<=0):continue
  u=f*q[:,1]/q[:,0]+w/2;v=-f*q[:,2]/q[:,0]+h/2;boxes.append((a['role_name'],[min(u),min(v),max(u),max(v)]))
 def iou(a,b):
  z=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]));return z/max((a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-z,1e-9)
 print(c,'frame',m['frame'])
 for i,d in enumerate(ds):print('P-%04d'%(i+1),'confidence',round(d['confidence'],3),'IoU',[(n,round(iou(d['bbox_original_px'],b),3)) for n,b in boxes])
