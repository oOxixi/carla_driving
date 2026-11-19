"""Offline CARLA replay plus truth-only audit. Never feed truth to inference."""
import json,math,pathlib,types,os,collections,itertools
import numpy as np
from tools.pointcloud_p0.replay_io import read,TF
from tools.pointcloud_p0.run_matrix import semantic_correspondence,iou
from integration.target_group_localization import localize_groups,ASSIGNED,ENVIRONMENT,AMBIGUOUS
BASE=pathlib.Path('/home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime')
ROOT=pathlib.Path(os.environ.get('GROUP_TEST_INPUT',str(BASE/'pointcloud_p0_rear_final_20261117')));OUT=pathlib.Path(os.environ.get('GROUP_TEST_OUTPUT',str(BASE/'pointcloud_group_regression55_20261117')));OUT.mkdir(parents=True,exist_ok=True)
rows=[]
def qs(v):return {'n':len(v),'p50':float(np.percentile(v,50)),'p95':float(np.percentile(v,95))} if v else {'n':0,'p50':None,'p95':None}
def status_of_bbox(gtboxes,obj):
 b=[v*s for v,s in zip(obj['bbox'],[800,450,800,450])];best=sorted(((iou(b,q),role) for role,q in gtboxes.items() if q),reverse=True)
 # Independent matching lets duplicate boxes both map to one reference. Ambiguous ties remain unscored.
 if not best or best[0][0]<.3 or (len(best)>1 and best[0][0]-best[1][0]<.05):return None
 return best[0][1]
for fi,f in enumerate(sorted(ROOT.glob('*/*/result.json'))):
 try:
  d,l,r,rad,ego,objects=read(f.parent);loc=localize_groups(objects,l,r,rad,ego);ev=d['evaluation'];pred={x['id']:x for x in d['predictions']};matches={e['id']:e['gt_match']['role'] for e in ev['detections'] if e['gt_match']};actor_ids=ev['gt_actor_ids'];det_role={p['id']:status_of_bbox(ev['gt_projected_boxes_px'],p) for p in d['predictions']}
  raw_idx=sorted(set(i for g in loc['groups'] for i in g['box_point_indices']));sem=types.SimpleNamespace(raw_data=(f.parent/'semantic_lidar.bin').read_bytes(),transform=TF(d['semantic_transform']));labels=semantic_correspondence(loc['lidar_ego'],raw_idx,sem,ego)
  true_pairs={'same_total':0,'same_grouped':0,'different_total':0,'different_grouped':0,'unknown_pairs':0,'overlap_same_total':0,'overlap_same_grouped':0,'overlap_different_total':0,'overlap_different_grouped':0}
  group_by_id={m['id']:g['group_id'] for g in loc['groups'] for m in g['members']}
  for a,b in itertools.combinations(pred,2):
   ra,rb=det_role[a],det_role[b]
   if not ra or not rb:true_pairs['unknown_pairs']+=1;continue
   k='same' if ra==rb else 'different';true_pairs[k+'_total']+=1;true_pairs[k+'_grouped']+=int(group_by_id[a]==group_by_id[b]);ba=pred[a]['bbox'];bb=pred[b]['bbox'];has_overlap=min(ba[2],bb[2])>max(ba[0],bb[0]) and min(ba[3],bb[3])>max(ba[1],bb[1]);true_pairs['overlap_'+k+'_total']+=int(has_overlap);true_pairs['overlap_'+k+'_grouped']+=int(has_overlap and group_by_id[a]==group_by_id[b])
  groups=[];located_roles=set();denom_by_role=collections.defaultdict(set);assigned_by_role=collections.defaultdict(set);totals=collections.Counter();errors=[]
  gt_positions={e['gt_match']['role']:e['gt'] for e in ev['detections'] if e.get('gt_match') and 'gt' in e}
  gt_positions.update(d.get('gt_positions_all',{}))
  for g in loc['groups']:
   role_candidates=set(matches[m['id']] for m in g['members'] if m['id'] in matches)
   if not role_candidates:
    role_candidates=set(det_role[m['id']] for m in g['members'] if det_role[m['id']])
   role=next(iter(role_candidates)) if len(role_candidates)==1 else None
   actor=actor_ids.get(role);selected=g['selected_point_indices']
   for i in g['box_point_indices']:
    lb=labels.get(i)
    if actor is not None and lb and lb['actor_id']==actor:denom_by_role[role].add(i)
   truth={'target':0,'other_vehicle':0,'environment':0,'unmatched_semantic':0,'unmatched_detection':0}
   for i in selected:
    z=labels.get(i)
    if actor is None:k='unmatched_detection'
    elif not z:k='unmatched_semantic'
    elif z['actor_id']==actor:k='target';assigned_by_role[role].add(i)
    elif z['actor_id'] in actor_ids.values():k='other_vehicle'
    else:k='environment'
    truth[k]+=1;totals[k]+=1
   if g['status']=='LOCATED_UNVALIDATED' and role:
    located_roles.add(role)
    if role in gt_positions:
     error=float(g['nearest_surface_distance_m']-gt_positions[role]['nearest_box_distance_m']);errors.append(abs(error))
     g['range_error_m']=error
   out={k:v for k,v in g.items() if k not in ('box_point_indices','candidate_point_indices','nonground_point_indices','selected_point_indices','radar_point_indices')}
   out['role_audit']=role;out['selected_truth_audit']=truth;out['selected_point_indices']=selected;out['candidate_count']=len(g['candidate_point_indices']);out['nonground_count']=len(g['nonground_point_indices']);groups.append(out)
  denominator=sum(len(v) for v in denom_by_role.values());numerator=sum(len(assigned_by_role[k]&v) for k,v in denom_by_role.items())
  states=collections.Counter(int(x) for x in loc['point_state']);sub=OUT/d['case']/str(d['repeat']);sub.mkdir(parents=True,exist_ok=True)
  (sub/'point_status.u8').write_bytes(loc['point_state'].tobytes());(sub/'point_owner.i32').write_bytes(loc['point_owner'].astype('<i4').tobytes());(sub/'point_reason.u8').write_bytes(loc['point_reason'].tobytes())
  result={'case':d['case'],'repeat':d['repeat'],'frame':d['frame'],'groups':groups,'pair_evidence':loc['pair_evidence'],'point_states':dict(states),'target_labeled_environment':sum(1 for j,z in labels.items() if loc['point_state'][j]==ENVIRONMENT and z['actor_id'] in actor_ids.values()),'labeled_points':len(labels),'examined_box_points':len(raw_idx),'truth_precision_counts':dict(totals),'recall_denominator':denominator,'recall_numerator':numerator,'expected_roles':ev['expected_roles'],'located_roles':sorted(located_roles),'baseline_located_roles':sorted(e['gt_match']['role'] for e in ev['detections'] if e.get('gt_match') and 'errors' in e),'absolute_range_errors':errors,'baseline_range_errors':[abs(e['errors']['nearest_surface_range_error_m']) for e in ev['detections'] if e.get('gt_match') and 'errors' in e],'pair_metrics':true_pairs,'point_data_source':str(f.parent),'point_files':str(sub),'status':'COMPLETED'}
  (sub/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');rows.append(result);print('DONE',fi+1,d['case'],d['repeat'],'located',len(located_roles),flush=True)
 except Exception as e:
  import traceback;traceback.print_exc();rows.append({'case':f.parent.parent.name,'repeat':f.parent.name,'status':'ERROR','error':repr(e)});print('ERROR',str(f),repr(e),flush=True)
 (OUT/'progress.json').write_text(json.dumps([{'case':r['case'],'repeat':r['repeat'],'status':r['status']} for r in rows],ensure_ascii=False,indent=2))
ok=[r for r in rows if r['status']=='COMPLETED'];counts=collections.Counter();pairs=collections.Counter()
for r in ok:counts.update(r['truth_precision_counts']);pairs.update(r['pair_metrics'])
expected=sum(len(r['expected_roles']) for r in ok);located=sum(len(r['located_roles']) for r in ok);base=sum(len(set(r['baseline_located_roles'])) for r in ok);denom=sum(r['recall_denominator'] for r in ok);num=sum(r['recall_numerator'] for r in ok);scored=counts['target']+counts['other_vehicle']+counts['environment'];errors=[x for r in ok for x in r['absolute_range_errors']];old_errors=[x for r in ok for x in r['baseline_range_errors']]
summary={'recordings':len(rows),'completed':len(ok),'errors':[r for r in rows if r['status']!='COMPLETED'],'expected_vehicles':expected,'baseline_located':base,'new_located':located,'baseline_coverage':base/expected if expected else None,'new_coverage':located/expected if expected else None,'assigned_point_truth':dict(counts),'scored_precision':counts['target']/scored if scored else None,'unscored_assigned':counts['unmatched_semantic']+counts['unmatched_detection'],'point_recall_within_matched_boxes':num/denom if denom else None,'point_recall_numerator':num,'point_recall_denominator':denom,'target_labeled_environment':sum(r['target_labeled_environment'] for r in ok),'pair_metrics':dict(pairs),'range_errors_absolute':qs(errors),'baseline_range_errors_absolute':qs(old_errors),'cases':{case:{'runs':sum(r['case']==case for r in ok),'expected':sum(len(r['expected_roles']) for r in ok if r['case']==case),'baseline_located':sum(len(set(r['baseline_located_roles'])) for r in ok if r['case']==case),'new_located':sum(len(r['located_roles']) for r in ok if r['case']==case)} for case in sorted({r['case'] for r in ok})},'definitions':{'precision':'assigned points with auditable ground truth only; unmatched semantic/detection reported separately','recall':'labeled target points within matched detection boxes; missed detections excluded from this conditional denominator','pair':'independent projected-box IoU>=0.3 with 0.05 margin; unscored ambiguous pairs reported','range':'only samples where actor nearest bounding-box surface truth was saved; failed original samples may lack it','timestamps':'historical raw timestamps unavailable, replay uses same recorded frame IDs and equal placeholders'}}
(OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');print('SUMMARY',json.dumps(summary,ensure_ascii=False),flush=True)
