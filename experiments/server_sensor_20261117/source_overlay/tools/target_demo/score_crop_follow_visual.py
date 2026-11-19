"""Evaluation-only projected-box statistics, not target-binding ground truth."""
import glob,json,math
from collections import Counter
from pathlib import Path
import numpy as np
root=Path('artifacts/runtime/crop_follow_20261112')
for case in ('40_combined','60_combined','occlusion_retry'):
 p=root/case;frames=[json.loads(l) for l in open(glob.glob(str(p/'*.jsonl'))[0]) if json.loads(l).get('record_type')=='frame']; ids={x['frame'] for x in frames};rows=[json.loads(l) for l in (p/'evaluation/truth_for_evaluation.jsonl').open() if json.loads(l)['frame'] in ids]
 matched=Counter();car_frames=0;unknown=0;total=0;both_near_lead=0
 for row in rows:
  cam=np.linalg.inv(np.asarray(row['camera_world_matrix']));width,height=row['camera_width'],row['camera_height'];f=width/(2*math.tan(math.radians(row['fov'])/2)); truths={}
  for a in row['evaluation_only_actors']:
   if a['role_name'].endswith(':ego'):continue
   xyz=np.array(a['vertices_world']);v=np.column_stack([xyz,np.ones(len(xyz))])@cam.T
   if np.any(v[:,0]<=0): continue
   u=f*v[:,1]/v[:,0]+width/2;w=-f*v[:,2]/v[:,0]+height/2
   truths[a['role_name'].split(':')[-1]]=[min(u),min(w),max(u),max(w)]
  found=set();cars=[o for o in row['scene']['detected_objects'] if o['class_name']=='car'];car_frames+=bool(cars)
  for o in cars:
   total+=1;unknown+=o['distance_m'] is None or o['lane_relation']=='UNKNOWN'; b=[o['bbox_xyxy_norm'][i]*([width,height]*2)[i] for i in range(4)]
   overlaps=[]
   for name,a in truths.items():
    it=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1])); union=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-it;overlaps.append((it/max(union,1e-9),name))
   if overlaps:
    score,name=max(overlaps)
    if score>=.3:found.add(name)
    near=dict((name,score) for score,name in overlaps)
    if near.get('occluder_near',0)>=.3 and near.get('lead_target',0)>=.3:both_near_lead+=1
  matched.update(found)
 out={'case':case,'frames':len(rows),'car_detected_frames':car_frames,'highest_iou_at_least_03_frames':dict(matched),'car_detections':total,'distance_or_lane_unknown_detections':unknown,'detections_overlap_both_occluder_and_lead':both_near_lead,'collision_frames':sum(x['scene']['collision'] for x in rows),'mean_speed_mps':round(sum(x['speed_mps'] for x in frames)/len(frames),3),'max_speed_mps':round(max(x['speed_mps'] for x in frames),3)}
 (p/'evaluation/visual_summary.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False))
