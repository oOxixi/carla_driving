"""Summarize recorded outcomes; simulation truth remains evaluation-only."""
import json,glob,math,sys
from pathlib import Path
import numpy as np
root=Path('artifacts/runtime/crop_follow_20261112')
for case in sys.argv[1:]:
 p=root/case; s=json.loads((p/'evaluation/observer_status.json').read_text()); rows=[json.loads(l) for l in (p/'evaluation/truth_for_evaluation.jsonl').open()]; command=s['commands'][0]; r=next(x for x in rows if x['frame']==command['frame']);cam=np.linalg.inv(np.array(r['camera_world_matrix']));f=r['camera_width']/(2*math.tan(math.radians(r['fov'])/2))
 truth=[]
 for a in r['evaluation_only_actors']:
  if a['role_name'].endswith(':ego'):continue
  v=np.array(a['vertices_world']); loc=np.column_stack([v,np.ones(len(v))])@cam.T
  if np.any(loc[:,0]<=0):continue
  u=f*loc[:,1]/loc[:,0]+r['camera_width']/2;v=-f*loc[:,2]/loc[:,0]+r['camera_height']/2
  box=[float(min(u)),float(min(v)),float(max(u)),float(max(v))]
  truth.append({'role':a['role_name'].split(':')[-1],'forward_m':round(float(loc[:,0].mean()),2),'box_px':[round(z,1) for z in box]})
 def iou(a,b):
  intersection=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1])); aa=(a[2]-a[0])*(a[3]-a[1]);ab=(b[2]-b[0])*(b[3]-b[1]);return intersection/max(aa+ab-intersection,1e-9)
 objects=[]
 for o in r['scene']['detected_objects']:
  box=[o['bbox_xyxy_norm'][i]*([r['camera_width'],r['camera_height']]*2)[i] for i in range(4)]
  overlaps=sorted([(iou(box,t['box_px']),t['role']) for t in truth],reverse=True)
  objects.append({'id':o['track_id'],'class':o['class_name'],'score':round(o['confidence'],3),'distance':o['distance_m'],'lane':o['lane_relation'],'box_px':[round(z,1) for z in box],'truth_overlaps':[(role,round(score,3)) for score,role in overlaps]})
 results=[];frames=[]
 for line in open(glob.glob(str(p/'*.jsonl'))[0]):
  x=json.loads(line)
  if x['record_type']=='frame':frames.append(x)
  if x['record_type']=='canonical_routing':
   o=x['payload']['orchestration']; plan=o.get('decision_plan') or {}; results.append({'disposition':o.get('disposition'),'grounding':plan.get('model_grounding'),'reason':(o.get('feedback') or {}).get('terminal_reason'),'model_timing':o.get('model_timing')})
 timed=[]
 for x in frames:
  def search(v):
   if isinstance(v,dict):
    for k,w in v.items():
     if k=='sensor_to_control_ms' and isinstance(w,(int,float)):timed.append(w)
     else:search(w)
   elif isinstance(v,list):
    for w in v:search(w)
  search(x)
 result={'case':case,'command_frame':command['frame'],'evaluator_frames':len(rows),'runtime_frames':len(frames),'command_objects':objects,'truth_boxes':truth,'detector_stats':r['detector_stats'],'decisions':results,'timing_sensor_to_control_ms':{'count':len(timed),'median':round(float(np.median(timed)),2) if timed else None,'p95':round(float(np.percentile(timed,95)),2) if timed else None,'max':round(max(timed),2) if timed else None},'collisions':sum(bool(x['scene']['collision']) for x in rows),'observer_errors':s['errors']}
 (p/'evaluation/summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))
