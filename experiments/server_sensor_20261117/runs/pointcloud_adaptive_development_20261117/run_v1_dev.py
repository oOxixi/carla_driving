import collections,json,pathlib,time
import numpy as np
from eval_helpers import ROOT,datasets,truth_labels,original,experimental,evaluate,assert_same_precluster,role_for_group
variants={'R0':{'alpha':1.0},'alpha_1.1':{'alpha':1.1},'alpha_1.2':{'alpha':1.2},'alpha_1.3':{'alpha':1.3},'alpha_1.4':{'alpha':1.4},'alpha_1.5':{'alpha':1.5},'fixed_1.20':{'fixed_radius':1.2}}
rows=[];exact=0;pre=0
for n,sample in enumerate(datasets('dev')):
 labels=truth_labels(sample);args=(sample['objects'],sample['lid'],sample['rgb'],sample['rad'],sample['ego']);base=original.localize_groups(*args);out={};order=np.random.default_rng(20261117+n).permutation(list(variants))
 for name in order:
  start=time.perf_counter_ns();loc=experimental.localize_groups(*args,**variants[name]);elapsed=(time.perf_counter_ns()-start)/1e6;assert_same_precluster(base,loc);pre+=1
  if name=='R0':
   assert len(base['groups'])==len(loc['groups'])
   for a,b in zip(base['groups'],loc['groups']):
    assert all(a[k]==b[k] for k in a),(sample['key'],a['group_id'])
   assert np.array_equal(base['point_state'],loc['point_state']) and np.array_equal(base['point_owner'],loc['point_owner']) and np.array_equal(base['point_reason'],loc['point_reason']);exact+=1
  rec=evaluate(sample,loc,labels,elapsed);rec['variant']=name;matches={z['id']:z['gt_match']['role'] for z in sample['d']['evaluation']['detections'] if z['gt_match']};actors=set(sample['role_ids'].values());multi=0;mix=0;unknown=0
  for group in loc['groups']:
   ng=np.asarray(group['nonground_point_indices'],dtype=int);pts=loc['lidar_ego'][ng];role,_=role_for_group(group,matches)
   if len(pts)<3 or len(pts)>2500:continue
   for component in experimental._depth_components(pts,group['experimental_epsilon_m'],None):
    vals=labels[ng[component]];vehicles={int(x) for x in vals if x in actors};multi+=int(len(vehicles)>1);unknown+=int(np.any(vals==-1));actor=sample['role_ids'].get(role)
    if actor is not None:mix+=int(np.any(vals==actor) and any(x not in actors and x!=-1 for x in vals))
  rec.update(candidate_multi_vehicle=multi,candidate_target_background=mix,candidate_unmatched_semantic=unknown);rows.append(rec)
 print('DONE',n+1,sample['dataset'],sample['key'],flush=True)
(ROOT/'v1_development_frames.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n');(ROOT/'v1_dev_verification.json').write_text(json.dumps({'inputs':exact,'R0_exact':exact,'unchanged_precluster':pre,'variants':variants},indent=2)+'\n');print('COMPLETE',len(rows),'inputs',exact,'precluster checks',pre)
