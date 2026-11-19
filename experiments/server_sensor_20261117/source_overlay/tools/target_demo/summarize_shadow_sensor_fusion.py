"""Compare shadow position estimates with actor boxes, exclusively offline."""
import json,glob,sys,math
from pathlib import Path
from collections import Counter
import numpy as np
for case in sys.argv[1:]:
 p=Path('artifacts/runtime/multisensor_follow_20261112')/case
 records=[json.loads(l) for l in (p/'evaluation/shadow_and_evaluation_truth.jsonl').open()];status=json.loads((p/'evaluation/observer_status.json').read_text())
 runtime_ids={x['frame'] for l in open(glob.glob(str(p/'*.jsonl'))[0]) if (x:=json.loads(l)).get('record_type')=='frame'}
 records=[x for x in records if x['frame'] in runtime_ids];status_count=Counter();fused_frames=0;associations=Counter();mismatch=0;inside=0;unknown=0;errs=[];geom_conflicts=0;ambig_img=0;visual_evaluated=0
 for row in records:
  outputs=row['shadow'];status_count.update(o['status'] for o in outputs);fused=[o for o in outputs if o['status']=='FUSED_UNVALIDATED'];fused_frames+=bool(fused)
  ego=np.asarray(row['ego_world_matrix']);actors=[a for a in row['truth_for_evaluation_only'] if not a['role_name'].endswith(':ego')]
  for o in fused:
   x,y,z=o['position_m'];world=ego@np.array([x,-y,z,1]);candidates=[]
   for a in actors:
    transform=np.asarray(a['world_matrix']);inv=np.linalg.inv(transform);verts=np.asarray(a['vertices_world']);v=np.column_stack((verts,np.ones(len(verts))))@inv.T;low=v[:,:3].min(axis=0);high=v[:,:3].max(axis=0);q=inv@world;delta=np.maximum(np.maximum(low-q[:3],q[:3]-high),0);dist=float(np.linalg.norm(delta));candidates.append((dist,a,low,high))
   candidates.sort(key=lambda x:x[0]);near=[x for x in candidates if x[0]<=.25]
   if len(near)!=1:
    unknown+=1;continue
   dist,a,low,high=near[0];role=a['role_name'].split(':')[-1];associations[role]+=1;inside+=dist<=.001
   transform=np.asarray(a['world_matrix']);inv=np.linalg.inv(transform);ego_local=inv@ego[:,3];nearest=ego_local.copy();nearest[:2]=np.clip(nearest[:2],low[:2],high[:2]);nearest[2]=0;near_world=transform@nearest;true_range=np.linalg.norm(near_world[:2]-ego[:2,3]);errs.append(abs(o['distance_m']-true_range))
   if 'camera_world_matrix' in row:
    visual_evaluated+=1
    cam=np.linalg.inv(np.asarray(row['camera_world_matrix']));w,h=row['camera_width'],row['camera_height'];f=w/(2*math.tan(math.radians(row['camera_fov'])/2));b=np.asarray(o['bbox'])*[w,h,w,h];overlaps=[]
    for aa in actors:
     v=np.asarray(aa['vertices_world']);q=np.column_stack((v,np.ones(len(v))))@cam.T
     if (q[:,0]<=0).any():continue
     u=f*q[:,1]/q[:,0]+w/2;v=-f*q[:,2]/q[:,0]+h/2;gt=[min(u),min(v),max(u),max(v)]
     inter=max(0,min(gt[2],b[2])-max(gt[0],b[0]))*max(0,min(gt[3],b[3])-max(gt[1],b[1]));union=(gt[2]-gt[0])*(gt[3]-gt[1])+(b[2]-b[0])*(b[3]-b[1])-inter
     overlaps.append((inter/max(union,1e-9),aa['role_name'].split(':')[-1]))
    overlaps.sort(reverse=True)
    if len(overlaps)>1 and overlaps[1][0]>=.3:ambig_img+=1
    elif overlaps and overlaps[0][0]>=.3 and overlaps[0][1]!=role:geom_conflicts+=1
 command=next((x for x in records if status['commands'] and x['frame']==status['commands'][0]['frame']),None)
 result={'case':case,'runtime_frames':len(records),'frames_with_fusion':fused_frames,'status_counts':dict(status_count),'fused_estimates':sum(status_count.get(k,0) for k in ('FUSED_UNVALIDATED',)),'truth_associations_within_025m':dict(associations),'inside_truth_box':int(inside),'unmatched_or_ambiguous':unknown,'visual_geometry_evaluated':visual_evaluated,'visual_geometry_conflicts':geom_conflicts if visual_evaluated else None,'ambiguous_2d_overlap':ambig_img if visual_evaluated else None,'absolute_range_error_to_nearest_bbox_surface_m':{'count':len(errs),'median':round(float(np.median(errs)),2) if errs else None,'p95':round(float(np.percentile(errs,95)),2) if errs else None,'max':round(max(errs),2) if errs else None},'command_shadow':None if command is None else command['shadow'],'observer_errors':status['errors']}
 (p/'evaluation/fusion_summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))
