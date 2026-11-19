'''Offline dual-channel replay. No production mutation, no vehicle-control output.'''
import csv,json,math,pathlib,sys,types
import numpy as np
from integration.target_group_localization import localize_groups
from integration.target_pointcloud_localization import _transform
from tools.pointcloud_p0.replay_io import Radar
ROOT=pathlib.Path('/home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime')
PREV=ROOT/'pointcloud_adaptive_development_20261117'; OLD=ROOT/'yolo_threshold_sensitivity_20261117'; OUT=ROOT/'yolo_dual_channel_isolation_20261117';sys.path.insert(0,str(PREV))
from eval_helpers import sample_new,truth_labels
prior=json.loads((OLD/'detections.json').read_text()); prior20=[r for r in prior if r['threshold']==.2]; src=PREV/'new_scenes/holdout'; excluded={'holdout_257_36','holdout_257_43','holdout_257_50'};files=[x for x in sorted(src.glob('*/result.json')) if x.parent.name not in excluded];assert len(files)==21
records=[];audits=[]
def sig(o):return (o.class_name,round(float(o.confidence),6),tuple(round(float(x),6) for x in o.bbox_xyxy_norm))
def snap(loc):return {'groups':loc['groups'],'state':loc['point_state'].tolist(),'owner':loc['point_owner'].tolist(),'reason':loc['point_reason'].tolist()}
def overlap(a,b):
 x1=max(a[0],b[0]);y1=max(a[1],b[1]);x2=min(a[2],b[2]);y2=min(a[3],b[3]);return max(0.,x2-x1)*max(0.,y2-y1)
for file in files:
 sample=sample_new(file.parent);d=sample['d'];case=d['case'];official=list(sample['objects']); rows=[r for r in prior20 if r['case']==case];high=[r for r in rows if not r['low_confidence_candidate']];lowrows=[r for r in rows if r['low_confidence_candidate']];assert {sig(o) for o in official}=={(r['class'],round(r['confidence'],6),tuple(round(v/s,6) for v,s in zip(r['bbox_px'],[800,450,800,450]))) for r in high}
 low=[types.SimpleNamespace(track_id=r['id'],class_name=r['class'],confidence=r['confidence'],bbox_xyxy_norm=[v/s for v,s in zip(r['bbox_px'],[800,450,800,450])]) for r in lowrows]
 base=localize_groups(official,sample['lid'],sample['rgb'],sample['rad'],sample['ego']);before=snap(base); raw=np.frombuffer(sample['lid'].raw_data,dtype=np.float32).reshape(-1,4);uv=base['uv'];world=base['lidar_world'];cam=_transform(world,np.asarray(sample['rgb'].transform.get_inverse_matrix()));ego=base['lidar_ego'];valid=(cam[:,0]>1)&(ego[:,0]>0)&np.isfinite(ego).all(axis=1)
 reserved=np.zeros(len(raw),dtype=bool)
 for o in official:
  x1,y1,x2,y2=o.bbox_xyxy_norm;reserved|=valid&(uv[:,0]>=x1)&(uv[:,0]<=x2)&(uv[:,1]>=y1)&(uv[:,1]<=y2)
 reserved|=(base['point_state']==1)
 keep=np.flatnonzero(~reserved);auxlid=types.SimpleNamespace(raw_data=raw[keep].tobytes(),transform=sample['lid'].transform,frame=sample['lid'].frame,timestamp=sample['lid'].timestamp)
 blank=Radar(b'',sample['rad'].transform,sample['rad'].frame);blank.timestamp=sample['rad'].timestamp
 aux=localize_groups(low,auxlid,sample['rgb'],blank,sample['ego']);assert snap(base)==before
 repeat=localize_groups(official,sample['lid'],sample['rgb'],sample['rad'],sample['ego']);assert snap(repeat)==before
 official_selected={i for g in base['groups'] for i in g['selected_point_indices']}; assert not (official_selected & set(keep)); labels=truth_labels(sample);info={m['id']:g for g in aux['groups'] for m in g['members']}
 rw=base['radar_world'];rc=_transform(rw,np.asarray(sample['rgb'].transform.get_inverse_matrix()));f=800/(2*math.tan(math.radians(50)));ru=(f*rc[:,1]/np.maximum(rc[:,0],1e-6)+400)/800;rv=(-f*rc[:,2]/np.maximum(rc[:,0],1e-6)+225)/450
 def rm(o):
  x1,y1,x2,y2=o.bbox_xyxy_norm;return (rc[:,0]>1)&(ru>=x1)&(ru<=x2)&(rv>=y1)&(rv<=y2)
 rformal=np.zeros(len(rw),dtype=bool)
 for o in official:rformal|=rm(o)
 rmasks=[rm(o) for o in low];rcount=np.sum(rmasks,axis=0) if rmasks else np.zeros(len(rw),dtype=int)
 gt_masks={}
 for role,box in d['gt_bbox_all'].items():
  xyz=_transform(rw,np.linalg.inv(np.asarray(box['matrix_world'])));gt_masks[role]=np.all(np.abs(xyz)<=np.asarray(box['extent'])+.2,axis=1)
 for o,old,r_mask in zip(low,lowrows,rmasks):
  group=info[o.track_id]; role=old['matched_role']; tid=d['evaluation']['gt_actor_ids'].get(role);sel=keep[np.asarray(group['selected_point_indices'],dtype=int)];ng=keep[np.asarray(group['nonground_point_indices'],dtype=int)];box=keep[np.asarray(group['box_point_indices'],dtype=int)];matches=[h for h in official if overlap(o.bbox_xyxy_norm,h.bbox_xyxy_norm)>0];cross=[h.track_id for h in matches if h.class_name!=o.class_name];same=[h.track_id for h in matches if h.class_name==o.class_name];lowover=[z.track_id for z in low if z.track_id!=o.track_id and overlap(o.bbox_xyxy_norm,z.bbox_xyxy_norm)>0];labs=labels[sel];target=int(np.count_nonzero(labs==tid)) if tid is not None else 0;unknown=int(np.count_nonzero(labs==-1));other=int(np.count_nonzero(np.isin(labs,[v for v in d['evaluation']['gt_actor_ids'].values() if v!=tid])));background=len(sel)-target-unknown-other
  pure=bool(role and len(group['members'])==1 and group['status']=='LOCATED_UNVALIDATED' and len(sel)>=3 and target==len(sel) and not matches and not lowover)
  radar_unique=r_mask&~rformal&(rcount==1);radar_truth=int(np.sum(radar_unique & gt_masks[role] & (sum(x.astype(int) for x in gt_masks.values())==1))) if role else None
  rec={'case':case,'frame':d['frame'],'candidate_id':o.track_id,'confidence':float(o.confidence),'predicted_class':o.class_name,'matched_role':role,'match_iou':old['match_iou'],'coverage_reconstructed':old['per_target_visible_pixel_coverage'],'two_target_coverage_flag':old['box_covers_two_targets_50pct'],'manual_verdict':'NOT_PERFORMED','cross_class_formal_overlaps':cross,'same_class_formal_overlaps':same,'other_low_box_overlaps':lowover,'raw_box_points_before_isolation':old['lidar_box_points'],'target_points_raw_before_isolation':old['lidar_box_target_semantic'],'withheld_formal_box_points':old['lidar_box_points']-len(box),'raw_box_points_after_isolation':len(box),'eligible_nonground_points':len(ng),'target_nonground_semantic':int(np.sum(labels[ng]==tid)) if tid is not None else None,'group_status':group['status'],'group_reason':group['reason'],'clusters':group['clusters'],'selected_total':len(sel),'selected_target':target,'selected_other_target':other,'selected_background':background,'selected_unknown':unknown,'selected_original_point_indices':sel.tolist(),'truth_pure_unambiguous_cluster':pure,'aux_output':'AMBIGUOUS' if (matches or lowover or group['reason']=='MULTIPLE_PLAUSIBLE_CLUSTERS') else 'VISUAL_ONLY','radar_candidate_unique_unreserved':int(np.sum(radar_unique)),'radar_target_bbox_offline_approx':radar_truth,'radar_used_for_aux_selection':False}
  assert not (set(sel)&official_selected);assert not np.any(reserved[sel]);records.append(rec)
 audits.append({'case':case,'formal_boxes':len(official),'auxiliary_boxes':len(low),'formal_selected_points':len(official_selected),'reserved_formal_box_points':int(reserved.sum()),'formal_replay_identical':True,'official_assigned_points_excluded':True,'all_formal_box_points_excluded':True,'formal_group_statuses':[g['status'] for g in base['groups']]})
 print('DONE',case,'official',len(official),'aux',len(low),flush=True)
assert len(audits)==21 and sum(a['formal_boxes'] for a in audits)==10 and len(records)==9 and all(r['matched_role'] for r in records)
assert all(a['formal_replay_identical'] and a['all_formal_box_points_excluded'] for a in audits)
(OUT/'candidates.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n');(OUT/'formal_audit.json').write_text(json.dumps(audits,ensure_ascii=False,indent=2)+'\n')
with (OUT/'candidates.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
summary={'frames':21,'targets':35,'formal_boxes':10,'auxiliary_boxes':9,'candidate_matched_automatically':9,'formal_replay_unchanged_frames':21,'truth_pure_unambiguous_cluster':sum(r['truth_pure_unambiguous_cluster'] for r in records),'aux_visual_only':sum(r['aux_output']=='VISUAL_ONLY' for r in records),'aux_ambiguous':sum(r['aux_output']=='AMBIGUOUS' for r in records),'cross_class_formal_overlap_flags':sum(bool(r['cross_class_formal_overlaps']) for r in records),'manual_reviews_completed':0,'background_false_positives_confirmed':None,'radar_not_used_for_aux':True,'production_unchanged':True,'formal_protection':'all LiDAR points projecting into any formal detection box withheld, regardless of state, plus all formally ASSIGNED points','ground_note':'auxiliary localizer refits ground on remaining points; may differ from formal ground model','mask_note':'CARLA reconstructed instance masks not original frame semantic annotation','radar_note':'sensor timestamps same for current samples but independent identity and real-time synchronisation not validated; diagnostic only'}
(OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print('SUMMARY',json.dumps(summary,ensure_ascii=False));print('CANDIDATES')
for r in records:print(r['case'],r['candidate_id'],round(r['confidence'],3),r['matched_role'],'points raw/target withheld available nonground/target selected',r['raw_box_points_before_isolation'],r['target_points_raw_before_isolation'],r['withheld_formal_box_points'],r['raw_box_points_after_isolation'],r['eligible_nonground_points'],r['target_nonground_semantic'],r['selected_total'],'reason',r['group_reason'],'out',r['aux_output'],'overlap',r['cross_class_formal_overlaps'],r['same_class_formal_overlaps'],r['other_low_box_overlaps'],'radar',r['radar_candidate_unique_unreserved'],r['radar_target_bbox_offline_approx'])
