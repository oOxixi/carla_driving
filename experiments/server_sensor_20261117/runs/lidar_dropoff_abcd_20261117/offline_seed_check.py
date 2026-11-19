"""Supplementary independent Python RNG masks on native group-D returns; not native CARLA seeds."""
import ast,collections,csv,json,pathlib,time,types
import numpy as np
from tools.pointcloud_p0.replay_io import read,TF
from tools.pointcloud_p0.run_matrix import SEM_DTYPE
from integration.target_pointcloud_localization import _transform
from integration.target_group_localization import localize_groups
P=pathlib.Path('/home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime/lidar_dropoff_abcd_20261117');SRC=P.parent/'pointcloud_p0_rear_final_20261117/default_far';meta=json.loads((P/'run_metadata.json').read_text());ns={'np':np};node=next(z for z in ast.parse((P/'run_abcd.py').read_text()).body if isinstance(z,ast.ClassDef) and z.name=='cKDTree');exec(compile(ast.Module(body=[node],type_ignores=[]),'grid_matcher','exec'),ns);rows=[]
for scene in range(5):
 original,_,rgb,radar,_,objs=read(SRC/str(scene));folder=P/'samples'/str(scene)/'0';block=json.loads((folder/'result.json').read_text());raw=np.fromfile(folder/'D_lidar.bin',dtype=np.float32).reshape(-1,4);data=np.fromfile(folder/'semantic_lidar.bin',dtype=SEM_DTYPE);sw=_transform(np.column_stack([data['x'],data['y'],data['z']]),np.asarray(block['semantic_transform']));lw=_transform(raw[:,:3],np.asarray(block['lidar_transform']));dist,ix=ns['cKDTree'](sw).query(lw);labels=np.where(dist<=.08,data['id'][ix].astype(np.int64),-1);actor_by_role={v:int(k) for k,v in block['gt_actor_ids'].items()};match={z['id']:z['gt_match']['role'] for z in original['evaluation']['detections'] if z['gt_match']};ego=TF(meta['scene_settings'][str(scene)]['ego_matrix'])
 for seed in range(10):
  rng=np.random.default_rng(np.random.SeedSequence([20261117,scene,seed]));u_general=rng.random(len(raw));u_intensity=rng.random(len(raw));intensity=raw[:,3]
  for name,rate,zero in [('A',.45,.4),('B',0.,.4),('C',.45,0.),('D',0.,0.)]:
   p_drop=np.where(intensity>=.8,0.,zero*(1.-intensity/.8));mask=(u_general>=rate)&(u_intensity>=p_drop);masked=raw[mask];labs=labels[mask];lid=types.SimpleNamespace(raw_data=masked.tobytes(),transform=TF(block['lidar_transform']),frame=rgb.frame,timestamp=rgb.timestamp)
   t0=time.perf_counter_ns();loc=localize_groups(objs,lid,rgb,radar,ego);elapsed=(time.perf_counter_ns()-t0)/1e6;byrole={}
   for g in loc['groups']:
    roles={match[m['id']] for m in g['members'] if m['id'] in match}
    if len(roles)==1:byrole[next(iter(roles))]=g
   for role,actor_id in actor_by_role.items():
    row={'scene':scene,'seed':seed,'group':name,'role':role,'lidar_total':len(masked),'target_raw':int(np.count_nonzero(labs==actor_id)),'elapsed_ms':round(elapsed,3)};g=byrole.get(role)
    if g:
     selected=np.asarray(g['selected_point_indices'],dtype=int);assigned=labs[selected];good=int(np.sum(assigned==actor_id));unknown=int(np.sum(assigned==-1));wrong=int(len(selected)-good-unknown);row.update(status=g['status'],reason=g['reason'],box_total=len(g['box_point_indices']),nonground_count=len(g['nonground_point_indices']),valid_clusters=len(g['clusters']),selected_total=len(selected),selected_target=good,selected_wrong=wrong,selected_unmatched=unknown)
    else:row.update(status='NO_MATCHED_DETECTION',reason='NO_MATCHED_DETECTION',selected_total=0,selected_target=0,selected_wrong=0,selected_unmatched=0)
    rows.append(row)
 print('scene',scene,'complete',flush=True)
assert len(rows)==600
(P/'offline_seed_per_target.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n');keys=list(dict.fromkeys(k for row in rows for k in row))
with (P/'offline_seed_per_target.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
for name in 'ABCD':
 a=[x for x in rows if x['group']==name];print(name,'avg_target',np.mean([x['target_raw'] for x in a]),'status',dict(collections.Counter(x['status'] for x in a)),'true_wrong_unknown',*[sum(x[k] for x in a) for k in ('selected_target','selected_wrong','selected_unmatched')])
