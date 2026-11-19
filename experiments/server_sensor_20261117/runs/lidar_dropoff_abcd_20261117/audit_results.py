import ast,collections,itertools,json,math,pathlib,types
import numpy as np
from tools.pointcloud_p0.replay_io import TF
from tools.pointcloud_p0.run_matrix import semantic_correspondence,SEM_DTYPE
from integration.target_pointcloud_localization import _transform
P=pathlib.Path('/home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime/lidar_dropoff_abcd_20261117');rows=json.loads((P/'per_target.json').read_text());meta=json.loads((P/'run_metadata.json').read_text());r={(z['scene'],z['replicate'],z['role'],z['group']):z for z in rows};ns={'np':np};tree=next(z for z in ast.parse((P/'run_abcd.py').read_text()).body if isinstance(z,ast.ClassDef) and z.name=='cKDTree');exec(compile(ast.Module(body=[tree],type_ignores=[]),'grid_matcher','exec'),ns)
intensities=[];ranges=[];geoms=[];checks=0
for s in range(5):
 for rep in (0,4,9):
  folder=P/'samples'/str(s)/str(rep);block=json.loads((folder/'result.json').read_text());sem=types.SimpleNamespace(raw_data=(folder/'semantic_lidar.bin').read_bytes(),transform=TF(block['semantic_transform']));data=np.frombuffer(sem.raw_data,dtype=SEM_DTYPE);sw=_transform(np.column_stack([data['x'],data['y'],data['z']]),np.asarray(block['semantic_transform']));matcher=ns['cKDTree'](sw);ego=TF(meta['scene_settings'][str(s)]['ego_matrix']);lidtf=TF(block['lidar_transform'])
  for g in 'ABCD':
   raw=np.fromfile(folder/(g+'_lidar.bin'),dtype=np.float32).reshape(-1,4);lw=_transform(raw[:,:3],np.asarray(block['lidar_transform']));le=_transform(lw,np.linalg.inv(ego.m));dist,ix=matcher.query(lw);known=dist<=.08;labels=np.where(known,data['id'][ix].astype(np.int64),-1)
   target_ids={int(k) for k in block['gt_actor_ids']};idx=list(np.flatnonzero(np.isin(labels,list(target_ids))))+list(range(min(60,len(raw))));idx=sorted(set(idx));old=semantic_correspondence(le,idx,sem,ego)
   for j in idx:
    assert (j in old)==bool(known[j]);assert j not in old or old[j]['actor_id']==int(labels[j]);checks+=1
   if g=='D':
    mask=np.isin(labels,list(target_ids));intensities.extend(raw[mask,3].tolist());ranges.extend(np.linalg.norm(raw[mask,:3],axis=1).tolist())
 for role in 'ABC':
  block=json.loads((P/'samples'/str(s)/'0'/'result.json').read_text());record=r[s,0,role,'D'];g=next((x for x in block['results']['D']['groups'] if x['audit_role']==role),None)
  if g:
   raw=np.fromfile(P/'samples'/str(s)/'0'/'D_lidar.bin',dtype=np.float32).reshape(-1,4);w=_transform(raw[:,:3],np.asarray(block['lidar_transform']));ego=np.asarray(meta['scene_settings'][str(s)]['ego_matrix']);pts=_transform(w,np.linalg.inv(ego))[g['nonground_point_indices']];eps=min(1.,max(.38,.018*float(np.median(np.linalg.norm(pts[:,:2],axis=1))))) if len(pts) else None;dd=np.linalg.norm(pts[:,None,:]-pts[None,:,:],axis=2);need=min((sorted((dd[a,b],dd[a,c],dd[b,c]))[1] for a,b,c in itertools.combinations(range(len(pts)),3)),default=None)
  else:eps=need=None
  geoms.append({'scene':s,'role':role,'matched':bool(g),'baseline_target_avg':round(np.mean([r[s,n,role,'A']['target_raw_semantic'] for n in range(10)]),2),'no_drop_target':record['target_raw_semantic'],'largest_component':record.get('largest_component'),'epsilon_m':round(eps,3) if eps is not None else None,'min_epsilon_three_m':round(float(need),3) if need is not None else None})
assert len(rows)==600 and not meta['failures'] and all(r[s,n,role,'A']['target_raw_semantic']==r[s,n,role,'C']['target_raw_semantic'] and r[s,n,role,'B']['target_raw_semantic']==r[s,n,role,'D']['target_raw_semantic'] for s in range(5) for n in range(10) for role in 'ABC')
audit={'sampled_matcher_comparisons':checks,'target_intensity_min':min(intensities),'target_intensity_max':max(intensities),'target_range_from_lidar_min_m':min(ranges),'target_range_from_lidar_max_m':max(ranges),'intensity_limit_0_8_distance_m':-math.log(.8)/.004,'geometry_by_target':geoms}
(P/'audit_checks.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n');print(json.dumps(audit,ensure_ascii=False,indent=2))
