import ast,collections,importlib.util,json,pathlib,time,types
import numpy as np
from tools.pointcloud_p0.replay_io import read,TF
from tools.pointcloud_p0.run_matrix import SEM_DTYPE
from integration.target_pointcloud_localization import _transform
import integration.target_group_localization as original
P=pathlib.Path('/home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime');ROOT=P/'pointcloud_adaptive_development_20261117';OLD=P/'lidar_dropoff_abcd_20261117';OLDDET=P/'pointcloud_p0_rear_final_20261117/default_far'
ns={'np':np};node=next(z for z in ast.parse((OLD/'run_abcd.py').read_text()).body if isinstance(z,ast.ClassDef) and z.name=='cKDTree');exec(compile(ast.Module(body=[node],type_ignores=[]),'matcher','exec'),ns)
spec=importlib.util.spec_from_file_location('experimental_group_localization',ROOT/'experimental_group_localization.py');experimental=importlib.util.module_from_spec(spec);spec.loader.exec_module(experimental)
oldmeta=json.loads((OLD/'run_metadata.json').read_text())
def sample_new(path):
 d,l,r,rad,ego,objs=read(path);ts=d['sensors']['timestamps'];l.timestamp=float(ts['lidar']);r.timestamp=float(ts['rgb']);rad.timestamp=float(ts['radar']);assert l.frame==r.frame==rad.frame and max(l.timestamp,r.timestamp,rad.timestamp)-min(l.timestamp,r.timestamp,rad.timestamp)<=.001
 return {'key':d['case'],'dataset':d['split'],'d':d,'lid':l,'rgb':r,'rad':rad,'ego':ego,'objects':objs,'semantic':path/'semantic_lidar.bin','sem_transform':d['semantic_transform'],'role_ids':d['evaluation']['gt_actor_ids'],'gt':d['gt_positions_all'],'radar_sync':True}
def sample_old(scene,rep):
 d,_,rgb,radar,_,objs=read(OLDDET/str(scene));folder=OLD/'samples'/str(scene)/str(rep);block=json.loads((folder/'result.json').read_text());lid=types.SimpleNamespace(raw_data=(folder/'A_lidar.bin').read_bytes(),transform=TF(block['lidar_transform']),frame=rgb.frame,timestamp=0.);ego=TF(oldmeta['scene_settings'][str(scene)]['ego_matrix']);gt={k:v['position'] for k,v in oldmeta['scene_settings'][str(scene)]['gt'].items()}
 return {'key':f'oldA_{scene}_{rep}','dataset':'oldA','d':d,'lid':lid,'rgb':rgb,'rad':radar,'ego':ego,'objects':objs,'semantic':folder/'semantic_lidar.bin','sem_transform':block['semantic_transform'],'role_ids':{v:int(k) for k,v in block['gt_actor_ids'].items()},'gt':gt,'radar_sync':False}
def datasets(split):
 if split=='dev':
  for s in range(5):
   for n in range(10):yield sample_old(s,n)
 for file in sorted((ROOT/'new_scenes'/split).glob('*/result.json')):
  if split=='holdout' and file.parent.name in {'holdout_257_36','holdout_257_43','holdout_257_50'}:continue
  yield sample_new(file.parent)
def truth_labels(sample):
 sem=np.fromfile(sample['semantic'],dtype=SEM_DTYPE);xyz=np.column_stack([sem['x'],sem['y'],sem['z']]);world=_transform(xyz,np.asarray(sample['sem_transform']));raw=np.frombuffer(sample['lid'].raw_data,dtype=np.float32).reshape(-1,4);lw=_transform(raw[:,:3],np.asarray(sample['lid'].transform.get_matrix()));dist,ix=ns['cKDTree'](world).query(lw);return np.where(dist<=.08,sem['id'][ix].astype(np.int64),-1)
def role_for_group(g,matches):
 roles={matches[m['id']] for m in g['members'] if m['id'] in matches}
 return next(iter(roles)) if len(roles)==1 else None,roles
def evaluate(sample,loc,labels,elapsed):
 d=sample['d'];roles=sample['role_ids'];matches={z['id']:z['gt_match']['role'] for z in d['evaluation']['detections'] if z['gt_match']};groups=loc['groups'];base={k:set() for k in roles};chosen={k:set() for k in roles};details=[];located=set();scored=collections.Counter();merged_groups=0;errors=[]
 for g in groups:
  role,roleset=role_for_group(g,matches);merged_groups+=int(len(roleset)>1);actor=roles.get(role);box=np.asarray(g['box_point_indices'],dtype=int);sel=np.asarray(g['selected_point_indices'],dtype=int)
  if role:
   base[role].update(int(i) for i in box if labels[i]==actor);chosen[role].update(int(i) for i in sel if labels[i]==actor)
   a=labels[sel];good=int(np.count_nonzero(a==actor));unknown=int(np.count_nonzero(a==-1));other=int(np.count_nonzero(np.isin(a,[v for v in roles.values() if v!=actor])));background=len(a)-good-unknown-other;scored.update({'target':good,'other_vehicle':other,'background':background,'unmatched_semantic':unknown})
   if g['status']=='LOCATED_UNVALIDATED':
    located.add(role);gt=sample['gt'][role];errors.append({'role':role,'error':float(g['nearest_surface_distance_m']-gt['nearest_box_distance_m'])})
  else:good=unknown=other=background=0;scored['unmatched_detection']+=len(sel)
  details.append({'group_id':g['group_id'],'role':role,'matched_roles':sorted(roleset),'status':g['status'],'reason':g['reason'],'diagnostic_outcome':g.get('diagnostic_outcome'),'box_count':len(box),'nonground_count':len(g['nonground_point_indices']),'selected_count':len(sel),'selected_target':good,'selected_background':background,'selected_other_vehicle':other,'selected_unmatched_semantic':unknown,'clusters':g['clusters'],'epsilon_m':g.get('experimental_epsilon_m'),'depth_limit_m':g.get('experimental_depth_limit_m'),'geometry_rejected':g.get('geometry_rejected',[])})
 denom=sum(len(v) for v in base.values());num=sum(len(chosen[k]&v) for k,v in base.items())
 return {'dataset':sample['dataset'],'case':sample['key'],'frame':d['frame'],'radar_sync':sample['radar_sync'],'expected':len(roles),'matched':len(set(matches.values())),'located':len(located),'located_roles':sorted(located),'point_counts':dict(scored),'recall_numerator':num,'recall_denominator':denom,'merged_detection_groups':merged_groups,'range_errors':errors,'elapsed_ms':elapsed,'groups':details}
def assert_same_precluster(a,b):
 fields=('group_id','members','representative','group_evidence','box_point_indices','candidate_point_indices','nonground_point_indices');assert [{k:x[k] for k in fields} for x in a['groups']]==[{k:x[k] for k in fields} for x in b['groups']]
def no_radar(sample):
 radar=sample['rad'];return types.SimpleNamespace(transform=radar.transform,frame=radar.frame,timestamp=radar.timestamp,points=[],__iter__=lambda self:iter([]))
