"""Risk checks on existing overlap recordings; single-detection anchors stay original."""
import ast,collections,csv,json,pathlib
import numpy as np
from tools.pointcloud_p0.replay_io import read
from tools.pointcloud_p0.run_matrix import SEM_DTYPE
from integration.target_pointcloud_localization import _transform
import integration.target_group_localization as mod
P=pathlib.Path('/home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime');OUT=P/'radius_sweep_ad_20261117';IN=P/'lidar_dropoff_abcd_20261117';ns={'np':np};node=next(z for z in ast.parse((IN/'run_abcd.py').read_text()).body if isinstance(z,ast.ClassDef) and z.name=='cKDTree');exec(compile(ast.Module(body=[node],type_ignores=[]),'matcher','exec'),ns)
sets={'overlap20':'pointcloud_overlap20_raw_20261117','sweep':'pointcloud_overlap_sweep_raw_20261117','focus':'pointcloud_overlap_focus_raw_20261117','holdout':'pointcloud_overlap_holdout_raw_20261117'};R={'R0':None,'R1':.75,'R2':.85,'R3':.95,'R4':1.05,'R5':1.20};real=mod._clusters;rows=[];frames=[];checks=0
try:
 for setname,folder in sets.items():
  for file in sorted((P/folder).glob('*/*/result.json')):
   d,l,r,rad,ego,objs=read(file.parent);ev=d['evaluation'];ids_by_role=ev['gt_actor_ids'];known_actors=set(ids_by_role.values());matches={z['id']:z['gt_match']['role'] for z in ev['detections'] if z['gt_match']};sem=np.fromfile(file.parent/'semantic_lidar.bin',dtype=SEM_DTYPE);sp=_transform(np.column_stack((sem['x'],sem['y'],sem['z'])),np.asarray(d['semantic_transform']));raw=np.frombuffer(l.raw_data,dtype=np.float32).reshape(-1,4);wp=_transform(raw[:,:3],np.asarray(d['lidar_transform']));dist,ix=ns['cKDTree'](sp).query(wp);ids=np.where(dist<=.08,sem['id'][ix].astype(np.int64),-1);baseline=None
   for name,eps in R.items():
    captured=[]
    def components(points,original_eps,min_points=3):
     v=real(points,original_eps if eps is None else eps,min_points);captured.append(v);return v
    mod._clusters=components;loc=mod.localize_groups(objs,l,r,rad,ego);invariant=[{k:g[k] for k in ('group_id','members','representative','group_evidence','box_point_indices','candidate_point_indices','nonground_point_indices')} for g in loc['groups']]
    if name=='R0':baseline=invariant
    else:assert invariant==baseline;checks+=1
    expected_call_groups=[g for g in loc['groups'] if loc['ground_plane'] is not None and 3<=len(g['nonground_point_indices'])<=2500];assert len(captured)==len(expected_call_groups);compmap={g['group_id']:c for g,c in zip(expected_call_groups,captured)}
    found=set()
    for g in loc['groups']:
     roles={matches[m['id']] for m in g['members'] if m['id'] in matches};role=next(iter(roles)) if len(roles)==1 else None
     if role and g['status']=='LOCATED_UNVALIDATED':found.add(role)
     target=ids_by_role.get(role);idx=np.asarray(g['selected_point_indices'],dtype=int);labels=ids[idx];unknown=int(np.count_nonzero(labels==-1));wrong_vehicle=int(np.count_nonzero(np.isin(labels,[v for v in known_actors if v!=target]))) if role else 0;correct=int(np.count_nonzero(labels==target)) if role else 0;bg=int(len(labels)-unknown-wrong_vehicle-correct) if role else 0;unscored=len(labels) if not role else 0
     ng=np.asarray(g['nonground_point_indices'],dtype=int);multi=0;mix=0
     for component in compmap.get(g['group_id'],[]):
      lab=ids[ng[component]];actors={int(x) for x in lab if x in known_actors};multi+=int(len(actors)>1)
      if role:mix+=int(np.any(lab==target) and any(x not in known_actors and x!=-1 for x in lab))
     error=None
     if role and g['status']=='LOCATED_UNVALIDATED' and role in d.get('gt_positions_all',{}):error=float(g['nearest_surface_distance_m']-d['gt_positions_all'][role]['nearest_box_distance_m'])
     rows.append({'set':setname,'case':d['case'],'repeat':d['repeat'],'frame':d['frame'],'radius':name,'role':role,'status':g['status'],'reason':g['reason'],'selected_total':len(idx),'target':correct,'background':bg,'other_vehicle':wrong_vehicle,'unmatched_semantic':unknown if role else 0,'unmatched_detection':unscored,'selected_pure':bool(role and len(idx)>=3 and correct==len(idx)),'candidate_multi_vehicle':multi,'candidate_target_plus_background':mix,'range_error_m':error})
    frames.append({'set':setname,'case':d['case'],'repeat':d['repeat'],'frame':d['frame'],'radius':name,'expected':len(ev['expected_roles']),'located':len(found),'matched_roles':len(set(matches.values())),'injected':bool(d.get('injected_duplicate'))})
   print('DONE',setname,d['case'],d['repeat'],flush=True)
finally:mod._clusters=real
assert len(frames)==54*6 and checks==54*5
(OUT/'overlap_control_rows.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n');(OUT/'overlap_control_frames.json').write_text(json.dumps(frames,ensure_ascii=False,indent=2)+'\n')
with (OUT/'overlap_control_rows.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
print('COMPLETE',len(frames),'frames, group rows',len(rows),'preserved precluster checks',checks,flush=True)
