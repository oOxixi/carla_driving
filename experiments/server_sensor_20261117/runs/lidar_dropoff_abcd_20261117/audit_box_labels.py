import ast,collections,json,pathlib
import numpy as np
from tools.pointcloud_p0.run_matrix import SEM_DTYPE
from integration.target_pointcloud_localization import _transform
P=pathlib.Path('/home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime/lidar_dropoff_abcd_20261117');ns={'np':np};node=next(x for x in ast.parse((P/'run_abcd.py').read_text()).body if isinstance(x,ast.ClassDef) and x.name=='cKDTree');exec(compile(ast.Module(body=[node],type_ignores=[]),'matcher','exec'),ns);totals={g:collections.Counter() for g in 'ABCD'};data=[]
for scene in range(5):
 for rep in range(10):
  folder=P/'samples'/str(scene)/str(rep);d=json.loads((folder/'result.json').read_text());sem=np.fromfile(folder/'semantic_lidar.bin',dtype=SEM_DTYPE);sp=_transform(np.column_stack([sem['x'],sem['y'],sem['z']]),np.asarray(d['semantic_transform']));tree=ns['cKDTree'](sp);roleids={v:int(k) for k,v in d['gt_actor_ids'].items()}
  for name in 'ABCD':
   raw=np.fromfile(folder/(name+'_lidar.bin'),dtype=np.float32).reshape(-1,4);xyz=_transform(raw[:,:3],np.asarray(d['lidar_transform']));dist,ix=tree.query(xyz);ids=np.where(dist<=.08,sem['id'][ix].astype(np.int64),-1)
   for group in d['results'][name]['groups']:
    role=group['audit_role']
    if role is None:continue
    indices=group['box_point_indices'];a=ids[indices];target=int(np.sum(a==roleids[role]));unknown=int(np.sum(a==-1));other=int(np.sum(np.isin(a,[v for k,v in roleids.items() if k!=role])));background=int(len(a)-target-unknown-other);counts={'target':target,'other_vehicle':other,'background':background,'unmatched':unknown};totals[name].update(counts);data.append(dict(scene=scene,rep=rep,group=name,role=role,**counts))
print({k:dict(v) for k,v in totals.items()});(P/'box_label_audit.json').write_text(json.dumps({'totals':{k:dict(v) for k,v in totals.items()},'rows':data},ensure_ascii=False,indent=2)+'\n')
