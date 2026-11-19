import json,math,numpy as np
for path in ['artifacts/runtime/live_demo_20261116/40m','artifacts/runtime/baseline_repair_20261116/40_dense']:
 stat=json.load(open(path+'/evaluation/observer_status.json')); n=stat['commands'][0]['frame'];rows=[json.loads(l) for l in open(path+'/evaluation/shadow_and_evaluation_truth.jsonl')];r=next(x for x in rows if x['frame']==n);cam=np.linalg.inv(np.array(r['camera_world_matrix']));w,h=r['camera_width'],r['camera_height'];f=w/(2*math.tan(math.radians(r['camera_fov'])/2));truth=[]
 for a in r['truth_for_evaluation_only']:
  if a['role_name'].endswith(':ego'):continue
  v=np.array(a['vertices_world']);q=np.column_stack((v,np.ones(len(v))))@cam.T
  if (q[:,0]<=0).any():continue
  u=f*q[:,1]/q[:,0]+w/2;v=-f*q[:,2]/q[:,0]+h/2;truth.append((a['role_name'],[min(u),min(v),max(u),max(v)]))
 def iou(a,b):
  z=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]));return z/max((a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-z,1e-9)
 print(path)
 for x in r['scene']['detected_objects']:
  box=[x['bbox_xyxy_norm'][i]*[w,h,w,h][i] for i in range(4)];print(x['track_id'],round(x['confidence'],2),[(role,round(iou(box,t),2)) for role,t in truth])
