"""Draw offline diagnostic overlays; semantic labels never feed localization."""
import json,math,pathlib
import numpy as np
from PIL import Image,ImageDraw
ROOT=pathlib.Path('/home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime/pointcloud_p0_rear_final_20261117')
OUT=pathlib.Path('/home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime/pointcloud_p0_diagnosis_20261117')
d=json.loads((OUT/'diagnosis.json').read_text());dest=OUT/'failure_overlays';dest.mkdir(exist_ok=True)
sem_dtype=np.dtype([('x','<f4'),('y','<f4'),('z','<f4'),('cos','<f4'),('id','<u4'),('tag','<u4')]);stats=[]
for r in d['failure_rows']:
 base=ROOT/r['case']/str(r['repeat']);raw=json.loads((base/'result.json').read_text());img=Image.open(base/'camera.png').convert('RGB');draw=ImageDraw.Draw(img)
 gt=raw['evaluation']['gt_projected_boxes_px'].get(r['role'])
 if gt:draw.rectangle(gt,outline=(255,230,0),width=2)
 if r['prediction_id']:
  obj=next(x for x in raw['predictions'] if x['id']==r['prediction_id']);bbox=[v*s for v,s in zip(obj['bbox'],[800,450,800,450])];draw.rectangle(bbox,outline=(90,200,255),width=2)
  lp=np.fromfile(base/'lidar.bin',dtype=np.float32).reshape(-1,4)[:,:3];sem=np.fromfile(base/'semantic_lidar.bin',dtype=sem_dtype);sp=np.column_stack((sem['x'],sem['y'],sem['z']));lc=np.asarray(raw['lidar_transform']);sc=np.asarray(raw['semantic_transform']);cm=np.asarray(raw['camera_transform']);liw=np.c_[lp,np.ones(len(lp))]@lc.T;sew=np.c_[sp,np.ones(len(sp))]@sc.T;cam=liw@np.linalg.inv(cm).T;f=800/(2*math.tan(math.radians(50)));safe=np.maximum(cam[:,0],1e-9);u=f*cam[:,1]/safe+400;v=-f*cam[:,2]/safe+225;target=raw['evaluation']['gt_actor_ids'][r['role']];other=set(raw['evaluation']['gt_actor_ids'].values())-{target};non=set(obj['nonground_point_indices']);labeled=0;found_target=0;found_other_vehicle=0;found_environment=0
  # Recompute same 0.08 m truth matching; only inspect the points in this box.
  for i in obj['box_point_indices']:
   delta=np.linalg.norm(sew[:,:3]-liw[i,:3],axis=1);j=int(np.argmin(delta));actor=int(sem['id'][j]) if delta[j]<=.08 else None
   if actor is not None:
    labeled+=1
    found_target+=int(actor==target);found_other_vehicle+=int(actor in other);found_environment+=int(actor!=target and actor not in other)
   col=(95,95,95) if actor is None else ((35,255,80) if actor==target else ((255,70,70) if actor in other else (255,130,0)))
   x,y=float(u[i]),float(v[i]);rad=3 if i in non else 2
   if cam[i,0]>1 and 0<=x<800 and 0<=y<450:draw.ellipse((x-rad,y-rad,x+rad,y+rad),fill=col,outline=(255,255,255) if i in non else None)
  assert [labeled,found_target,found_other_vehicle,found_environment]==[r['box']['matched_semantic'],r['box']['target'],r['box']['other_test_vehicle'],r['box']['other_or_environment']], (r['case'],r['repeat'],r['role'])
  stats.append({'case':r['case'],'repeat':r['repeat'],'role':r['role'],'box':len(obj['box_point_indices']),'semantic_matched':labeled})
 draw.rectangle((0,0,800,28),fill=(5,10,20));draw.text((7,7),f"{r['case']} / {r['repeat']+1} / {r['role']}  green=target  orange=background  red=other car  white border=after filters",fill=(255,255,255))
 img.save(dest/(r['case']+'_'+str(r['repeat'])+'_'+r['role']+'.png'))
(OUT/'failure_overlay_stats.json').write_text(json.dumps(stats,indent=2));print('overlays',len(d['failure_rows']),'matched',sum(x['semantic_matched'] for x in stats),'box points',sum(x['box'] for x in stats))
