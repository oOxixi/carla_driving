import json,pathlib,sys,types,numpy as np
from integration.target_group_localization import localize_groups
R=pathlib.Path('/home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime');P=R/'pointcloud_adaptive_development_20261117';O=R/'yolo_threshold_sensitivity_20261117';sys.path.insert(0,str(P));from eval_helpers import sample_new
prior=[r for r in json.loads((O/'detections.json').read_text()) if r['threshold']==.2]; results=[]
files=sorted((P/'new_scenes/holdout').glob('*/result.json'));excluded={'holdout_257_36','holdout_257_43','holdout_257_50'}
for f in files:
 if f.parent.name in excluded:continue
 s=sample_new(f.parent);d=s['d'];rows=[r for r in prior if r['case']==d['case']];mixed=[types.SimpleNamespace(track_id=r['id'],class_name=r['class'],confidence=r['confidence'],bbox_xyxy_norm=[v/q for v,q in zip(r['bbox_px'],[800,450,800,450])]) for r in rows]
 base=localize_groups(s['objects'],s['lid'],s['rgb'],s['rad'],s['ego']);new=localize_groups(mixed,s['lid'],s['rgb'],s['rad'],s['ego']);old={m['id']:g for g in base['groups'] for m in g['members']};now={m['id']:g for g in new['groups'] for m in g['members']}
 for ident,g in old.items():
  h=now[ident];changed={}
  for k in ['box_point_indices','candidate_point_indices','nonground_point_indices','selected_point_indices']:
   before=set(g[k]);after=set(h[k]);
   if before!=after:changed[k]={'baseline':len(before),'mixed':len(after),'lost':len(before-after),'gained':len(after-before),'lost_indices':sorted(before-after),'gained_indices':sorted(after-before)}
  if changed:results.append({'case':d['case'],'id':ident,'changes':changed,'baseline_status':g['status'],'mixed_status':h['status'],'baseline_reason':g['reason'],'mixed_reason':h['reason']})
(O/'high_point_interference_020.json').write_text(json.dumps(results,indent=2)+'\n');print('AFFECTED HIGH GROUPS',len(results));
for r in results:print(r['case'],r['id'],{k:{j:v for j,v in vals.items() if not j.endswith('indices')} for k,vals in r['changes'].items()},r['baseline_status'],r['mixed_status'])
