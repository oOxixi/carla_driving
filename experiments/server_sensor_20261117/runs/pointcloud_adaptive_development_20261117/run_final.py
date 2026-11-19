import collections,json,time,numpy as np
from eval_helpers import ROOT,datasets,truth_labels,experimental,original,evaluate,assert_same_precluster,role_for_group
D=json.loads((ROOT/'depth_profile.json').read_text());G=json.loads((ROOT/'geometry_profile.json').read_text());alpha=json.loads((ROOT/'v1_parameter_lock.json').read_text())['selected']['alpha'];variants={'Baseline':{},'V1':{'alpha':alpha},'V2':{'alpha':alpha,'depth_profile':D},'V3':{'alpha':alpha,'depth_profile':D,'geometry_profile':G},'fixed_1.20':{'fixed_radius':1.2}};rows=[];exact=0;checks=0
for split in ('dev','holdout'):
 for n,s in enumerate(datasets(split)):
  labels=truth_labels(s);args=(s['objects'],s['lid'],s['rgb'],s['rad'],s['ego']);base=original.localize_groups(*args);matches={z['id']:z['gt_match']['role'] for z in s['d']['evaluation']['detections'] if z['gt_match']};actors=set(s['role_ids'].values());order=np.random.default_rng(831+n+(0 if split=='dev' else 999)).permutation(list(variants))
  for name in order:
   kw=variants[name];start=time.perf_counter_ns();loc=experimental.localize_groups(*args,**kw);elapsed=(time.perf_counter_ns()-start)/1e6;assert_same_precluster(base,loc);checks+=1
   if name=='Baseline':
    assert len(base['groups'])==len(loc['groups'])
    for a,b in zip(base['groups'],loc['groups']):assert all(a[k]==b[k] for k in a)
    assert np.array_equal(base['point_state'],loc['point_state']) and np.array_equal(base['point_owner'],loc['point_owner']);exact+=1
   selected=[];multi=0;mix=0;unscored=0
   for i,g in enumerate(loc['groups']):
    sel=g['selected_point_indices'];selected.extend(sel);assert all(loc['point_state'][j]==experimental.ASSIGNED and loc['point_owner'][j]==i for j in sel)
    if g['reason']=='GEOMETRY_REJECTED_OR_AMBIGUOUS':assert not sel and g['status']=='UNKNOWN'
    ng=np.asarray(g['nonground_point_indices'],dtype=int);pts=loc['lidar_ego'][ng];role,_=role_for_group(g,matches)
    if len(pts)<3 or len(pts)>2500:continue
    med=float(np.median(np.linalg.norm(pts[:,:2],axis=1)));eps=g['experimental_epsilon_m'];tau=experimental._limit(kw.get('depth_profile'),med)
    for comp in experimental._depth_components(pts,eps,tau):
     v=labels[ng[comp]];found={int(z) for z in v if z in actors};multi+=int(len(found)>1);unscored+=int(np.any(v==-1));target=s['role_ids'].get(role)
     if target is not None:mix+=int(np.any(v==target) and any(z not in actors and z!=-1 for z in v))
   assert len(selected)==len(set(selected));assert np.all((loc['point_state']==experimental.ASSIGNED)|(loc['point_owner']==-1))
   rec=evaluate(s,loc,labels,elapsed);rec.update(variant=name,candidate_multi_vehicle=multi,candidate_target_background=mix,candidate_unmatched_semantic=unscored);rows.append(rec)
  print('DONE',s['dataset'],s['key'],flush=True)
(ROOT/'final_frames.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n');(ROOT/'final_verification.json').write_text(json.dumps({'input_samples':exact,'R0_exact':exact,'unchanged_precluster':checks,'unique_owner_checks':checks,'variants':list(variants),'excluded_for_spatial_separation':['holdout_257_36','holdout_257_43','holdout_257_50'],'alpha_locked_before_holdout':alpha},indent=2)+'\n');print('COMPLETE',len(rows),'inputs',exact,'invariants',checks)
