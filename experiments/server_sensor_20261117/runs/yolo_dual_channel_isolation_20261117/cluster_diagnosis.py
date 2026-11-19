'''Recreate isolated candidate clusters and record component sizes, using truth only afterwards.'''
import json,pathlib,types,sys,csv
import numpy as np
from integration.target_group_localization import localize_groups
from integration.target_pointcloud_localization import _transform
from tools.pointcloud_p0.replay_io import Radar
ROOT=pathlib.Path('/home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime');P=ROOT/'yolo_dual_channel_isolation_20261117';PREV=ROOT/'pointcloud_adaptive_development_20261117';OLD=ROOT/'yolo_threshold_sensitivity_20261117';sys.path.insert(0,str(PREV));from eval_helpers import sample_new,truth_labels
prior=[r for r in json.loads((OLD/'detections.json').read_text()) if r['threshold']==.2]; records=json.loads((P/'candidates.json').read_text());annotations=json.loads((P/'manual_annotations.json').read_text())['answers']; output=[]
for case in sorted({r['case'] for r in records}):
 sample=sample_new(PREV/'new_scenes/holdout'/case);formal=localize_groups(sample['objects'],sample['lid'],sample['rgb'],sample['rad'],sample['ego']);raw=np.frombuffer(sample['lid'].raw_data,dtype=np.float32).reshape(-1,4);uv=formal['uv'];cam=_transform(formal['lidar_world'],np.asarray(sample['rgb'].transform.get_inverse_matrix()));valid=(cam[:,0]>1)&(formal['lidar_ego'][:,0]>0)&np.isfinite(formal['lidar_ego']).all(axis=1);reserved=np.zeros(len(raw),bool)
 for obj in sample['objects']:
  x1,y1,x2,y2=obj.bbox_xyxy_norm;reserved|=valid&(uv[:,0]>=x1)&(uv[:,0]<=x2)&(uv[:,1]>=y1)&(uv[:,1]<=y2)
 reserved|=(formal['point_state']==1);keep=np.flatnonzero(~reserved);lid=types.SimpleNamespace(raw_data=raw[keep].tobytes(),transform=sample['lid'].transform,frame=sample['lid'].frame,timestamp=sample['lid'].timestamp);rad=Radar(b'',sample['rad'].transform,sample['rad'].frame);rad.timestamp=sample['rad'].timestamp
 lowrows=[r for r in prior if r['case']==case and r['low_confidence_candidate']];low=[types.SimpleNamespace(track_id=r['id'],class_name=r['class'],confidence=r['confidence'],bbox_xyxy_norm=[v/s for v,s in zip(r['bbox_px'],[800,450,800,450])]) for r in lowrows];loc=localize_groups(low,lid,sample['rgb'],rad,sample['ego']); groups={m['id']:g for g in loc['groups'] for m in g['members']};labels=truth_labels(sample)
 for r in (x for x in records if x['case']==case):
  g=groups[r['candidate_id']];ix=np.asarray(g['nonground_point_indices'],int);original_ix=keep[ix];p=loc['lidar_ego'][ix];n=len(p);assert n==r['eligible_nonground_points'] and g['reason']==r['group_reason'];tid=sample['role_ids'][r['matched_role']];labs=labels[original_ix];eps=min(1.,max(.38,.018*float(np.median(np.linalg.norm(p[:,:2],axis=1))))) if n>=3 else None;components=[]
  if eps is not None:
   adj=np.linalg.norm(p[:,None,:]-p[None,:,:],axis=2)<=eps;seen=set()
   for i in range(n):
    if i in seen:continue
    todo=[i];seen.add(i);comp=[]
    while todo:
     j=todo.pop();comp.append(j)
     for k in np.flatnonzero(adj[j]):
      k=int(k)
      if k not in seen:seen.add(k);todo.append(k)
    comp=np.asarray(comp,int);components.append({'size':len(comp),'target':int(np.count_nonzero(labs[comp]==tid)),'other_test_actor':int(np.count_nonzero(np.isin(labs[comp],[v for v in sample['role_ids'].values() if v!=tid]))),'unmatched_semantic':int(np.count_nonzero(labs[comp]==-1))})
   components.sort(key=lambda z:z['size'],reverse=True)
  target_points=p[labs==tid];min3=None
  if len(target_points)>=3:
   distances=np.linalg.norm(target_points[:,None,:]-target_points[None,:,:],axis=2);np.fill_diagonal(distances,np.inf);min3=float(np.min(np.partition(distances,1,axis=1)[:,1]))
  selected=set(g['selected_point_indices']);assert not selected
  output.append({'case':case,'id':r['candidate_id'],'role':r['matched_role'],'raw_total':r['raw_box_points_before_isolation'],'raw_target':r['target_points_raw_before_isolation'],'reserved_by_formal':r['withheld_formal_box_points'],'nonground_total':n,'nonground_target':int(np.sum(labs==tid)),'nonground_other_test_actor':int(np.count_nonzero(np.isin(labs,[v for v in sample['role_ids'].values() if v!=tid]))),'nonground_unmatched_semantic':int(np.sum(labs==-1)),'epsilon_m':eps,'components_including_singles':components,'largest_component':max((v['size'] for v in components),default=0),'target_three_point_min_radius_m':min3,'reason':g['reason'],'human_multiple_vehicles':annotations[case+' / '+r['candidate_id']]['covers_two_vehicles'],'radar_unique':r['radar_candidate_unique_unreserved'],'radar_target_box_approx':r['radar_target_bbox_offline_approx']})
(P/'cluster_diagnosis.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n');print('RESULTS',len(output))
for x in output:print(x['case'],x['id'],'eps',round(x['epsilon_m'],3) if x['epsilon_m'] else None,'components',x['components_including_singles'],'min3_target',round(x['target_three_point_min_radius_m'],3) if x['target_three_point_min_radius_m'] is not None else None,'reason',x['reason'])
