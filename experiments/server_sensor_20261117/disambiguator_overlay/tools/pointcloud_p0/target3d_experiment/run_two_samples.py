"""Reproduce two isolated cases; semantic/actor values appear only in audit phase."""
from __future__ import annotations
import argparse,csv,hashlib,json,math,pathlib,types
import numpy as np
from integration.target_group_localization import localize_groups
from integration.target_pointcloud_localization import _transform,_clusters
from tools.pointcloud_p0.replay_io import read,Radar
from tools.pointcloud_p0.target3d_experiment.disambiguator import TargetObservation,PairObservation,Target3DDisambiguator
SEM_DTYPE=np.dtype([('x','<f4'),('y','<f4'),('z','<f4'),('cos','<f4'),('id','<u4'),('tag','<u4')])
CASES=(('holdout_extra_250_25','C-0002'),('holdout_250_30','C-0002'))
def normalized(x):
 if isinstance(x,np.ndarray):return {'shape':list(x.shape),'dtype':str(x.dtype),'sha256':hashlib.sha256(np.ascontiguousarray(x).tobytes()).hexdigest()}
 if isinstance(x,(np.integer,np.floating)):return x.item()
 if isinstance(x,dict):return {str(k):normalized(v) for k,v in x.items()}
 if isinstance(x,(list,tuple)):return [normalized(v) for v in x]
 return x

def choose(points,eps):
 if len(points)<3:return [],False,[]
 options=[]
 for cluster in _clusters(points,eps):
  span=np.ptp(points[cluster],axis=0)
  if span[0]<=6.5 and span[1]<=3.5 and span[2]<=3.0:options.append(cluster)
 options.sort(key=lambda x:(-len(x),int(np.min(x))))
 ambiguous=len(options)>1 and len(options[1])>=.67*len(options[0])
 chosen=[] if not options or ambiguous else options[0].tolist()
 return [x.tolist() for x in options],ambiguous,chosen

def audit_semantic(case_path,d,world,indices):
 sem=np.fromfile(case_path/'semantic_lidar.bin',dtype=SEM_DTYPE)
 sw=_transform(np.column_stack((sem['x'],sem['y'],sem['z'])),np.asarray(d['semantic_transform']))
 result={}
 for original_index in indices:
  ds=np.sum((sw-world[original_index])**2,axis=1);j=int(np.argmin(ds));distance=float(np.sqrt(ds[j]))
  result[int(original_index)]={'id':int(sem['id'][j]) if distance<=.08 else None,'tag':int(sem['tag'][j]) if distance<=.08 else None,'match_distance_m':distance if distance<=.08 else None}
 return result

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--holdout-root',type=pathlib.Path,required=True);ap.add_argument('--threshold-detections',type=pathlib.Path,required=True);ap.add_argument('--manual-identities',type=pathlib.Path,required=True);ap.add_argument('--output',type=pathlib.Path,required=True);args=ap.parse_args();args.output.mkdir(parents=True,exist_ok=True)
 prior=[r for r in json.loads(args.threshold_detections.read_text()) if r['threshold']==.2];manual=json.loads(args.manual_identities.read_text())['answers'];frozen=[];case_data={};formal_checks=[];disambiguator=Target3DDisambiguator()
 for case,ident in CASES:
  assert manual[case+' / '+ident]['classification']=='REAL_NEW_TARGET','manual review is used only for selecting the offline case'
  path=args.holdout_root/case;d,lidar,rgb,radar,ego,formal_objects=read(path);ts=d['sensors']['timestamps'];lidar.timestamp=float(ts['lidar']);rgb.timestamp=float(ts['rgb']);radar.timestamp=float(ts['radar'])
  formal=localize_groups(formal_objects,lidar,rgb,radar,ego);before=normalized(formal);raw=np.frombuffer(lidar.raw_data,dtype=np.float32).reshape(-1,4);uv=formal['uv'];cam=_transform(formal['lidar_world'],np.asarray(rgb.transform.get_inverse_matrix()));valid=(cam[:,0]>1)&(formal['lidar_ego'][:,0]>0)&np.isfinite(formal['lidar_ego']).all(axis=1);reserved=np.zeros(len(raw),dtype=bool)
  for o in formal_objects:
   x1,y1,x2,y2=o.bbox_xyxy_norm;reserved|=valid&(uv[:,0]>=x1)&(uv[:,0]<=x2)&(uv[:,1]>=y1)&(uv[:,1]<=y2)
  reserved|=formal['point_state']==1;keep=np.flatnonzero(~reserved);aux_lidar=types.SimpleNamespace(raw_data=raw[keep].tobytes(),transform=lidar.transform,frame=lidar.frame,timestamp=lidar.timestamp);empty_radar=Radar(b'',radar.transform,radar.frame);empty_radar.timestamp=radar.timestamp
  lows=[r for r in prior if r['case']==case and r['low_confidence_candidate']];low_objects=[types.SimpleNamespace(track_id=r['id'],class_name=r['class'],confidence=r['confidence'],bbox_xyxy_norm=[v/z for v,z in zip(r['bbox_px'],[800,450,800,450])]) for r in lows];aux=localize_groups(low_objects,aux_lidar,rgb,empty_radar,ego);group=next(g for g in aux['groups'] if ident in [m['id'] for m in g['members']]);assert len(group['members'])==1
  aux_ids=keep[np.asarray(group['nonground_point_indices'],dtype=int)];aux_xyz=raw[aux_ids,:3].astype(float);aux_ego=formal['lidar_ego'][aux_ids];assert not np.any(reserved[aux_ids]);others=[g for g in aux['groups'] if ident not in [m['id'] for m in g['members']]]
  other_aux_ids=set(int(i) for g in others for i in keep[np.asarray(g['nonground_point_indices'],dtype=int)]);assert not set(aux_ids.tolist()) & other_aux_ids
  official_groups=[g for g in formal['groups'] if g['selected_point_indices']];assert len(official_groups)<=1,'This two-case experiment does not choose among several formal targets'
  official_group=official_groups[0] if official_groups else None;official_ids=np.asarray(official_group['selected_point_indices'],dtype=int) if official_group else np.asarray([],dtype=int);assert not set(official_ids.tolist())&set(aux_ids.tolist());assert normalized(formal)==before
  exact_r0=min(1.0,max(.38,.018*float(np.median(np.linalg.norm(aux_ego[:,:2],axis=1))))) if len(aux_ids)>=3 else None
  radii=[('R0_exact',exact_r0),('TEST',.52)] if case=='holdout_extra_250_25' else [('R0_exact',exact_r0),('R0_rounded',.5098),('R1',.53),('R2',.55),('R3',.58),('R4',.60)]
  lowrow=next(x for x in lows if x['id']==ident);b=tuple(v/z for v,z in zip(lowrow['bbox_px'],[800,450,800,450]))
  for name,eps in radii:
   clusters,amb,chosen=choose(aux_ego,eps);chosen_ids=aux_ids[np.asarray(chosen,dtype=int)];auxobs=TargetObservation(ident,int(d['frame']),float(ts['lidar']),'lidar',b,aux_ids.astype(np.int64),aux_xyz,chosen_ids.astype(np.int64));officialobs=None
   if official_group:
    fid=official_group['representative'];obj=next(o for o in formal_objects if o.track_id==fid);officialobs=TargetObservation(fid,int(d['frame']),float(ts['lidar']),'lidar',tuple(obj.bbox_xyxy_norm),official_ids.astype(np.int64),raw[official_ids,:3].astype(float),official_ids.astype(np.int64))
   decision=disambiguator.evaluate(PairObservation(officialobs,auxobs));assert decision['status']=='UNKNOWN' and not decision['formal_control_authority'];frozen.append({'case':case,'candidate_id':ident,'frame':d['frame'],'timestamp_lidar':float(ts['lidar']),'timestamp_rgb':float(ts['rgb']),'radius_name':name,'radius_m':float(eps),'candidate_point_ids':aux_ids.tolist(),'candidate_cluster_ids':chosen_ids.tolist(),'candidate_component_ids':[aux_ids[np.asarray(c,dtype=int)].tolist() for c in clusters],'component_ambiguous':amb,'formal_target_id':officialobs.target_id if officialobs else None,'formal_bbox_xyxy_norm':list(officialobs.detection_box_xyxy) if officialobs else None,'aux_bbox_xyxy_norm':list(auxobs.detection_box_xyxy),'formal_selected_ids':official_ids.tolist(),'other_auxiliary_candidate_ids':sorted(other_aux_ids),'formal_reserved_ids':np.flatnonzero(reserved).tolist(),'decision':decision})
  after=localize_groups(formal_objects,lidar,rgb,radar,ego);assert normalized(after)==before and normalized(formal)==before;formal_checks.append({'case':case,'unchanged_all_localizer_return_fields':True,'official_selected_count':len(official_ids),'auxiliary_candidate_count':len(aux_ids),'other_auxiliary_candidate_count':len(other_aux_ids),'unique_sensor_point_ownership':True,'geometry_algorithm_truth_free':True});case_data[case]=(path,d,lidar,formal,aux_ids,aux_ego,official_ids,other_aux_ids,uv,raw,reserved)
 (args.output/'frozen_sensor_decisions.json').write_text(json.dumps(frozen,ensure_ascii=False,indent=2)+'\n');(args.output/'formal_audit.json').write_text(json.dumps(formal_checks,ensure_ascii=False,indent=2)+'\n')
 # Decisions were written before truth is loaded or used. Everything below is offline evaluation only.
 frozen=json.loads((args.output/'frozen_sensor_decisions.json').read_text());audited=[];ownership=[];visual=[]
 for entry in frozen:
  case=entry['case'];path,d,lidar,formal,aux_ids,aux_ego,official_ids,other_aux_ids,uv,raw,reserved=case_data[case];chosen=set(entry['candidate_cluster_ids']);eligible=set(entry['candidate_point_ids']);official=set(entry['formal_selected_ids']);neighbors=set(entry['other_auxiliary_candidate_ids']);assert not (chosen&official or eligible&official or eligible&neighbors)
  cand_row=next(r for r in prior if r['case']==case and r['id']==entry['candidate_id']);x1,y1,x2,y2=[v/z for v,z in zip(cand_row['bbox_px'],[800,450,800,450])];cam=_transform(formal['lidar_world'],np.linalg.inv(np.asarray(d['camera_transform'])));valid=(cam[:,0]>1)&(formal['lidar_ego'][:,0]>0)&np.isfinite(formal['lidar_ego']).all(axis=1);box_ids=set(np.flatnonzero(valid&(uv[:,0]>=x1)&(uv[:,0]<=x2)&(uv[:,1]>=y1)&(uv[:,1]<=y2)).tolist());ids=sorted(eligible|official|neighbors|box_ids);truth=audit_semantic(path,d,formal['lidar_world'],ids);target_id=int(d['evaluation']['gt_actor_ids'][cand_row['matched_role']]);role_ids=set(map(int,d['evaluation']['gt_actor_ids'].values()))
  def kind(i):
   a=truth[i]['id'];tag=truth[i]['tag']
   if a is None:return 'UNKNOWN_SEMANTIC'
   if a==target_id:return 'TARGET_APPROX'
   if a in role_ids or tag in (14,15,16,17,18,19):return 'OTHER_VEHICLE_APPROX'
   return 'ENVIRONMENT_OR_OTHER_APPROX'
  labels={i:kind(i) for i in ids};selected=list(chosen);denom=sum(labels[i]=='TARGET_APPROX' for i in eligible);tp=sum(labels[i]=='TARGET_APPROX' for i in selected);other=sum(labels[i]=='OTHER_VEHICLE_APPROX' for i in selected);env=sum(labels[i]=='ENVIRONMENT_OR_OTHER_APPROX' for i in selected);unknown=sum(labels[i]=='UNKNOWN_SEMANTIC' for i in selected)
  gt=float(d['gt_positions_all'][next(r['matched_role'] for r in prior if r['case']==case and r['id']==entry['candidate_id'])]['nearest_box_distance_m']);surface=float(np.min(np.linalg.norm(formal['lidar_ego'][selected,:2],axis=1))) if selected else None
  audited.append({'case':case,'radius_name':entry['radius_name'],'radius_m':entry['radius_m'],'cluster_point_count':len(selected),'component_count':len(entry['candidate_component_ids']),'target_approx':tp,'other_vehicle_approx':other,'environment_or_other_approx':env,'unknown_semantic':unknown,'point_precision':tp/len(selected) if selected else None,'point_recall_conditional':tp/denom if denom else None,'recall_denominator_eligible_target_approx':denom,'different_vehicle_merge':'OBSERVED' if other else 'NOT_OBSERVED_IN_ONE_CLUSTER' if selected else 'NOT_EVALUATED_NO_CLUSTER','surface_distance_m':surface,'gt_nearest_bbox_distance_m':gt,'surface_signed_error_m':surface-gt if surface is not None else None,'status':entry['decision']['status'],'reasons':entry['decision']['reasons']})
  for i in ids:
   owner='FORMAL_SELECTED' if i in official else 'AUX_CLUSTER_UNVALIDATED' if i in chosen else 'AUX_CANDIDATE_UNASSIGNED' if i in eligible else 'OTHER_AUX_CANDIDATE_UNASSIGNED' if i in neighbors else 'FORMAL_PROTECTED_NOT_SELECTED' if reserved[i] else 'FILTERED_OR_AMBIGUOUS_UNASSIGNED'
   ownership.append({'case':case,'radius_name':entry['radius_name'],'point_id':i,'owner':owner,'lidar_x_m':float(raw[i,0]),'lidar_y_m':float(raw[i,1]),'lidar_z_m':float(raw[i,2]),'image_u_px':float(uv[i,0]*800),'image_v_px':float(uv[i,1]*450),'semantic_audit_only':labels[i]})
  if (case=='holdout_extra_250_25' and entry['radius_name']=='TEST') or (case=='holdout_250_30' and entry['radius_name']=='R4'):
   positions=[]
   for i in sorted(eligible|official|neighbors):
    group='formal' if i in official else 'aux_cluster' if i in chosen else 'aux_unselected' if i in eligible else 'neighbor_aux_unselected'
    positions.append({'id':i,'group':group,'xyz':[float(v) for v in raw[i,:3]],'semantic_audit_only':labels[i]})
   visual.append({'case':case,'radius_m':entry['radius_m'],'formal_exists':bool(entry['formal_target_id']),'points':positions,'decision':entry['decision'],'note':'formal blue and unvalidated auxiliary yellow are separate observations; gray/purple points remain unassigned; no actor truth used to choose points'})
 (args.output/'offline_audit.json').write_text(json.dumps(audited,ensure_ascii=False,indent=2)+'\n');(args.output/'ownership.json').write_text(json.dumps(ownership,ensure_ascii=False,indent=2)+'\n');(args.output/'visualization.json').write_text(json.dumps(visual,ensure_ascii=False,indent=2)+'\n')
 with (args.output/'point_ownership.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(ownership[0]));w.writeheader();w.writerows(ownership)
 print(json.dumps({'formal_checks':formal_checks,'offline_audit':audited},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
