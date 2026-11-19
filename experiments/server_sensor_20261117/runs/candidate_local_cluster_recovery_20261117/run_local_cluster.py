'''Offline single-frame, candidate-level clustering; semantic labels never enter cluster selection.'''
import csv,hashlib,html,json,math,pathlib,sys,types,time
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from integration.target_group_localization import localize_groups
from integration.target_pointcloud_localization import _transform
from tools.pointcloud_p0.replay_io import Radar
from tools.pointcloud_p0.run_matrix import SEM_DTYPE
ROOT=pathlib.Path('/home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime');P=ROOT/'pointcloud_adaptive_development_20261117';OLD=ROOT/'yolo_threshold_sensitivity_20261117';DUAL=ROOT/'yolo_dual_channel_isolation_20261117';OUT=ROOT/'candidate_local_cluster_recovery_20261117';(OUT/'images').mkdir(exist_ok=True);sys.path.insert(0,str(P));from eval_helpers import sample_new,ns
prior=[r for r in json.loads((OLD/'detections.json').read_text()) if r['threshold']==.2];original=json.loads((DUAL/'candidates.json').read_text());human=json.loads((DUAL/'identity_annotations.json').read_text())['answers'];cases=[('holdout_extra_250_25','C-0002'),('holdout_250_30','C-0002'),('holdout_extra_250_21','C-0002'),('holdout_extra_250_39','C-0002'),('holdout_250_30','C-0001'),('holdout_extra_250_41','C-0001'),('holdout_extra_250_49','C-0001'),('holdout_extra_250_47','C-0001')];assert all(human[case+' / '+ident]['classification']=='REAL_NEW_TARGET' for case,ident in cases)
all_points=[];all_edges=[];all_clusters=[];all_cases=[];formal_audit=[];html_rows=[]
def snapshot(l):return {'groups':l['groups'],'state':l['point_state'].tolist(),'owner':l['point_owner'].tolist(),'reason':l['point_reason'].tolist(),'plane':l['ground_plane']}
def comps(points,eps):
 if not len(points):return []
 adj=np.linalg.norm(points[:,None,:]-points[None,:,:],axis=2)<=eps;seen=set();out=[]
 for i in range(len(points)):
  if i in seen:continue
  todo=[i];seen.add(i);component=[]
  while todo:
   j=todo.pop();component.append(j)
   for n in np.flatnonzero(adj[j]):
    n=int(n)
    if n not in seen:seen.add(n);todo.append(n)
  out.append(np.asarray(component,dtype=int))
 return sorted(out,key=lambda x:(-len(x),min(x)))
def asfloat(x):return float(x) if x is not None else None
for case,ident in cases:
 s=sample_new(P/'new_scenes/holdout'/case);d=s['d'];manual=human[case+' / '+ident];source=next(r for r in original if r['case']==case and r['candidate_id']==ident);raw=np.frombuffer(s['lid'].raw_data,dtype=np.float32).reshape(-1,4)
 formal=localize_groups(s['objects'],s['lid'],s['rgb'],s['rad'],s['ego']);before=snapshot(formal);uv=formal['uv'];cam=_transform(formal['lidar_world'],np.asarray(s['rgb'].transform.get_inverse_matrix()));valid=(cam[:,0]>1)&(formal['lidar_ego'][:,0]>0)&np.isfinite(formal['lidar_ego']).all(axis=1);reserved=np.zeros(len(raw),bool)
 for o in s['objects']:
  x1,y1,x2,y2=o.bbox_xyxy_norm;reserved|=valid&(uv[:,0]>=x1)&(uv[:,0]<=x2)&(uv[:,1]>=y1)&(uv[:,1]<=y2)
 reserved|=formal['point_state']==1;keep=np.flatnonzero(~reserved);auxlid=types.SimpleNamespace(raw_data=raw[keep].tobytes(),transform=s['lid'].transform,frame=s['lid'].frame,timestamp=s['lid'].timestamp);rad=Radar(b'',s['rad'].transform,s['rad'].frame);rad.timestamp=s['rad'].timestamp
 lows=[r for r in prior if r['case']==case and r['low_confidence_candidate']];objects=[types.SimpleNamespace(track_id=r['id'],class_name=r['class'],confidence=r['confidence'],bbox_xyxy_norm=[v/q for v,q in zip(r['bbox_px'],[800,450,800,450])]) for r in lows];loc=localize_groups(objects,auxlid,s['rgb'],rad,s['ego']);g=next(g for g in loc['groups'] if ident in [m['id'] for m in g['members']]);assert len(g['members'])==1,'Do not combine candidate hypotheses'
 indices=np.asarray(g['nonground_point_indices'],int);orig=keep[indices];xyz=loc['lidar_ego'][indices];assert len(xyz)==source['eligible_nonground_points'];assert not np.any(reserved[orig]);after=localize_groups(s['objects'],s['lid'],s['rgb'],s['rad'],s['ego']);assert before==snapshot(after) and before==snapshot(formal)
 formal_audit.append({'case':case,'candidate':ident,'formal_count':len(s['objects']),'all_groups_ownership_states_reasons_and_plane_identical':True,'formal_reserved_points_excluded_from_candidate':True,'points_reserved':int(np.sum(reserved))})
 # Record all graph edges using geometry alone, no semantic IDs or hand tuning.
 range3=np.linalg.norm(raw[orig,:3],axis=1);range2=np.linalg.norm(xyz[:,:2],axis=1);edge_geom=[]
 for i in range(len(xyz)):
  for j in range(i+1,len(xyz)):
   edge_geom.append({'i':i+1,'j':j+1,'distance_m':float(np.linalg.norm(xyz[i]-xyz[j])),'radial_depth_difference_m':float(abs(range3[i]-range3[j])),'pixel_distance_px':float(np.linalg.norm((uv[orig[i]]-uv[orig[j]])*np.array([800,450])))})
 edge_geom.sort(key=lambda x:(x['distance_m'],x['radial_depth_difference_m'],x['i'],x['j']))
 # Experimental rank score for human review only: equally weight per-candidate spatial and depth ranks.
 # It makes no admission/rejection decision and is computed before any semantic truth.
 m=len(edge_geom);depth_order=sorted(range(m),key=lambda i:(edge_geom[i]['radial_depth_difference_m'],edge_geom[i]['distance_m'],edge_geom[i]['i'],edge_geom[i]['j']));depth_ranks={ix:rank for rank,ix in enumerate(depth_order)}
 for rank,e in enumerate(edge_geom):e['review_priority_uncalibrated']=float(1.-(rank+depth_ranks[rank])/(2.*max(1,m-1)))
 all_edges.extend({'case':case,'candidate':ident,**e} for e in edge_geom)
 n=len(xyz);eps0=min(1.,max(.38,.018*float(np.median(range2)))) if n>=3 else None;radii=[('R0',eps0),('R1',.45),('R2',.48),('R3',.52),('R4',.55)] if case=='holdout_extra_250_25' else [('R0',eps0)];algorithm=[]
 for label,eps in radii:
  cs=comps(xyz,eps) if eps is not None else [];eligible=[]
  for cc in cs:
   span=np.ptp(xyz[cc],axis=0)
   if len(cc)>=3 and span[0]<=6.5 and span[1]<=3.5 and span[2]<=3.:eligible.append(cc)
  ambiguous=len(eligible)>1 and len(eligible[1])>=.67*len(eligible[0]);selected=eligible[0] if eligible and not ambiguous else np.array([],dtype=int)
  algorithm.append({'radius_name':label,'radius_m':asfloat(eps),'components':cs,'eligible':eligible,'ambiguous':ambiguous,'selected':selected})
 # Only after all cluster memberships and choices are fixed, bring in semantic and actor truth.
 sem=np.fromfile(s['semantic'],dtype=SEM_DTYPE);sw=_transform(np.column_stack((sem['x'],sem['y'],sem['z'])),np.asarray(s['sem_transform']));dist,nearest=ns['cKDTree'](sw).query(formal['lidar_world'][orig]);semid=np.where(dist<=.08,sem['id'][nearest].astype(np.int64),-1);semtag=np.where(dist<=.08,sem['tag'][nearest].astype(np.int64),-1);tid=s['role_ids'][source['matched_role']];role_ids=set(s['role_ids'].values());classes=[]
 for aid,tag in zip(semid,semtag):
  if aid==tid:k='TARGET_APPROX'
  elif aid==-1:k='UNKNOWN'
  elif aid in role_ids or tag in (14,15,16,17,18,19):k='OTHER_VEHICLE_APPROX'
  else:k='ENVIRONMENT_OR_OTHER_APPROX'
  classes.append(k)
 classes=np.asarray(classes);target_count=int(np.sum(classes=='TARGET_APPROX'));assert target_count==source['target_nonground_semantic'];gt_nearest=float(d['gt_positions_all'][source['matched_role']]['nearest_box_distance_m'])
 for i in range(n):
  all_points.append({'case':case,'candidate':ident,'point_no':i+1,'original_lidar_index':int(orig[i]),'ego_forward_m':float(xyz[i,0]),'ego_left_m':float(xyz[i,1]),'ego_up_m':float(xyz[i,2]),'radial_3d_m':float(range3[i]),'horizontal_range_m':float(range2[i]),'image_x_px':float(uv[orig[i],0]*800),'image_y_px':float(uv[orig[i],1]*450),'offline_label':str(classes[i]),'semantic_actor_id':int(semid[i]) if semid[i]>=0 else None,'semantic_tag':int(semtag[i]) if semtag[i]>=0 else None,'semantic_match_distance_m':float(dist[i]) if dist[i]<=.08 else None})
 case_result={'case':case,'candidate':ident,'manual_classification':manual['classification'],'group_input_points':n,'offline_target_points':target_count,'offline_other_vehicle_points':int(np.sum(classes=='OTHER_VEHICLE_APPROX')),'offline_environment_or_other_points':int(np.sum(classes=='ENVIRONMENT_OR_OTHER_APPROX')),'offline_unknown_points':int(np.sum(classes=='UNKNOWN')),'baseline_radius_m':asfloat(eps0),'ground_plane_available':loc['ground_plane'] is not None,'manual_two_vehicle_review':manual['multiple'],'formal_overlap':bool(source['cross_class_formal_overlaps'] or source['same_class_formal_overlaps']),'genuine_multiframe_evidence':False,'radar_used_in_auxiliary':False,'candidate_3d_center_supported':False,'range_only_promoted':False,'gt_nearest_bbox_surface_m':gt_nearest}
 all_cases.append(case_result)
 for entry in algorithm:
  accepted=entry['selected'];total=len(accepted);chosen=classes[accepted];tp=int(np.sum(chosen=='TARGET_APPROX'));other=int(np.sum(chosen=='OTHER_VEHICLE_APPROX'));environment=int(np.sum(chosen=='ENVIRONMENT_OR_OTHER_APPROX'));unknown=int(np.sum(chosen=='UNKNOWN'));rr=range2[accepted];xyzsel=xyz[accepted];near=float(np.min(rr)) if total else None;p10=float(np.percentile(rr,10)) if total else None;center=np.median(xyzsel,axis=0) if total else None
  component_details=[]
  for cc in entry['eligible']:
   vals=classes[cc];component_details.append({'point_nos':(cc+1).tolist(),'size':len(cc),'target_approx':int(np.sum(vals=='TARGET_APPROX')),'other_vehicle_approx':int(np.sum(vals=='OTHER_VEHICLE_APPROX')),'environment_or_other_approx':int(np.sum(vals=='ENVIRONMENT_OR_OTHER_APPROX')),'unknown':int(np.sum(vals=='UNKNOWN')),'xyz_span_m':np.ptp(xyz[cc],axis=0).tolist(),'radial_depth_span_m':float(np.ptp(range3[cc])),'min_horizontal_range_m':float(np.min(range2[cc]))})
  identity_ambiguous=source['aux_output']=='AMBIGUOUS'
  status='UNKNOWN' if (entry['ambiguous'] or identity_ambiguous) else 'CANDIDATE_3D_UNVALIDATED' if total else 'VISUAL_ONLY'
  result={'case':case,'candidate':ident,'strategy':entry['radius_name'],'radius_m':entry['radius_m'],'components_ge3_count':len(entry['eligible']),'components_ge3':component_details,'multiple_components_ambiguous':entry['ambiguous'],'chosen_point_count':total,'chosen_point_nos':(accepted+1).tolist(),'chosen_target_approx':tp,'chosen_other_vehicle_approx':other,'chosen_environment_or_other_approx':environment,'chosen_unknown':unknown,'offline_precision':(tp/total if total else None),'offline_recall':(tp/target_count if target_count else None),'nearest_surface_range_m':near,'surface_range_p10_m':p10,'gt_bbox_surface_m':gt_nearest,'nearest_range_signed_error_m':(near-gt_nearest if total else None),'p10_range_signed_error_m':(p10-gt_nearest if total else None),'radial_depth_span_m':float(np.ptp(range3[accepted])) if total else None,'horizontal_range_span_m':float(np.ptp(rr)) if total else None,'horizontal_range_iqr_m':float(np.percentile(rr,75)-np.percentile(rr,25)) if total else None,'position_surface_median_ego_xyz':center.tolist() if total else None,'position_surface_xyz_span_m':np.ptp(xyzsel,axis=0).tolist() if total else None,'status':status,'geometric_candidate_exists':bool(total),'identity_or_ownership_ambiguous':identity_ambiguous,'position_uncertainty':'UNCALIBRATED_SINGLE_FRAME_SPREAD_ONLY','surface_is_not_vehicle_center':True,'promoted_to_follow':False}
  all_clusters.append(result)
 if (case,ident) in [('holdout_250_30','C-0002'),('holdout_extra_250_21','C-0002')]:
  source_image=Image.open(P/'new_scenes/holdout'/case/'camera.png').convert('RGB');row=next(r for r in lows if r['id']==ident);box=row['bbox_px'];dx=max(25,(box[2]-box[0])*1.3);dy=max(25,(box[3]-box[1])*1.3);rect=(max(0,int(box[0]-dx)),max(0,int(box[1]-dy)),min(800,math.ceil(box[2]+dx)),min(450,math.ceil(box[3]+dy)));base=source_image.crop(rect).resize(((rect[2]-rect[0])*4,(rect[3]-rect[1])*4),Image.Resampling.NEAREST);draw=ImageDraw.Draw(base);b=[(box[0]-rect[0])*4,(box[1]-rect[1])*4,(box[2]-rect[0])*4,(box[3]-rect[1])*4];draw.rectangle(b,outline='yellow',width=5)
  name=case+'__'+ident;base.save(OUT/'images'/(name+'_base.png'));colors={'TARGET_APPROX':'#00d7ff','OTHER_VEHICLE_APPROX':'#ff41c8','ENVIRONMENT_OR_OTHER_APPROX':'#ff9600','UNKNOWN':'#ffffff'}
  for i in range(n):
   image=base.copy();dr=ImageDraw.Draw(image);x=(uv[orig[i],0]*800-rect[0])*4;y=(uv[orig[i],1]*450-rect[1])*4;dr.ellipse((x-18,y-18,x+18,y+18),fill='black');dr.ellipse((x-13,y-13,x+13,y+13),fill=colors[str(classes[i])],outline='white',width=3);image.save(OUT/'images'/(name+'_point_'+str(i+1)+'.png'))
  html_rows.append({'case':case,'candidate':ident,'name':name,'points':[x for x in all_points if x['case']==case and x['candidate']==ident],'edges':edge_geom})
 print('DONE',case,ident,'points',n,'target approx',target_count,'radii',len(radii),flush=True)
assert len(all_cases)==8 and all(x['all_groups_ownership_states_reasons_and_plane_identical'] for x in formal_audit)
(OUT/'cases.json').write_text(json.dumps(all_cases,ensure_ascii=False,indent=2)+'\n');(OUT/'clusters.json').write_text(json.dumps(all_clusters,ensure_ascii=False,indent=2)+'\n');(OUT/'points.json').write_text(json.dumps(all_points,ensure_ascii=False,indent=2)+'\n');(OUT/'edges.json').write_text(json.dumps(all_edges,ensure_ascii=False,indent=2)+'\n');(OUT/'formal_audit.json').write_text(json.dumps(formal_audit,ensure_ascii=False,indent=2)+'\n');(OUT/'mixed_page_data.json').write_text(json.dumps(html_rows,ensure_ascii=False,indent=2)+'\n')
for name,rows in [('points',all_points),('edges',all_edges),('clusters',all_clusters)]:
 if rows:
  with (OUT/(name+'.csv')).open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
metadata={'frames':len(set(c for c,i in cases)),'target_hypotheses':len(cases),'scope':'offline no train no production integration','baseline':'0.35 formal + 0.20-0.35 auxiliary unique group points after formal reservation and ground','comparison_25':['R0 actual adaptive','0.45','0.48','0.52','0.55'],'other_cases':'R0 only; no calibrated depth cutoff; uncalibrated per-candidate equal-rank score is review-only','truth_usage':'post hoc only; sem lidar nearest <=0.08m and automatic bbox IoU role association, not accepted as algorithm input','min_points':3,'range_only':'not automatically promoted; single frame quality limits','output_status':'no follow control, no certified identity','formal_integrity_checks':len(formal_audit),'mixed_review':'point labels are offline approximate semantic classifications, not human annotations','radial_depth':'LiDAR-frame 3D range; surface metric is ego-frame horizontal distance','motion':'single frame, cannot quantify temporal stability'};(OUT/'metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
print('COMPLETE',len(all_cases),'cases',len(all_clusters),'rows',len(all_points),'points',len(all_edges),'edges')
for r in all_clusters:print(r['case'],r['candidate'],r['strategy'],'eps',r['radius_m'],'components',r['components_ge3_count'],'ambiguous',r['multiple_components_ambiguous'],'chosen',r['chosen_point_count'],'truth target/other/env/unknown',r['chosen_target_approx'],r['chosen_other_vehicle_approx'],r['chosen_environment_or_other_approx'],r['chosen_unknown'],'P/R',r['offline_precision'],r['offline_recall'],'distance err',r['nearest_range_signed_error_m'],'status',r['status'])
