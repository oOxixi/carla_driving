"""Isolated replay: only scheme-C final connected-component epsilon is overridden."""
import ast,collections,csv,hashlib,json,pathlib,types
import numpy as np
from tools.pointcloud_p0.replay_io import read,TF
from tools.pointcloud_p0.run_matrix import SEM_DTYPE
from integration.target_pointcloud_localization import _transform
import integration.target_group_localization as mod
P=pathlib.Path('/home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime');IN=P/'lidar_dropoff_abcd_20261117';SRC=P/'pointcloud_p0_rear_final_20261117/default_far';OUT=P/'radius_sweep_ad_20261117';WORK=pathlib.Path('/home/tiaozhansai/carla-lane-association-20261117');meta=json.loads((IN/'run_metadata.json').read_text());ns={'np':np};node=next(z for z in ast.parse((IN/'run_abcd.py').read_text()).body if isinstance(z,ast.ClassDef) and z.name=='cKDTree');exec(compile(ast.Module(body=[node],type_ignores=[]),'audit_matcher','exec'),ns)
real_clusters=mod._clusters;R={'R0':None,'R1':.75,'R2':.85,'R3':.95,'R4':1.05,'R5':1.20};rows=[];r0checked=0;unchanged=0
try:
 for source in ('D','A'):
  for scene in range(5):
   original,_,rgb,radar,_,objs=read(SRC/str(scene));ego=TF(meta['scene_settings'][str(scene)]['ego_matrix']);matches={z['id']:z['gt_match']['role'] for z in original['evaluation']['detections'] if z['gt_match']};truth=meta['scene_settings'][str(scene)]['gt']
   for rep in range(10):
    folder=IN/'samples'/str(scene)/str(rep);block=json.loads((folder/'result.json').read_text());frame=rgb.frame;lid=types.SimpleNamespace(raw_data=(folder/(source+'_lidar.bin')).read_bytes(),transform=TF(block['lidar_transform']),frame=frame,timestamp=0.);sem=np.fromfile(folder/'semantic_lidar.bin',dtype=SEM_DTYPE);sp=_transform(np.column_stack((sem['x'],sem['y'],sem['z'])),np.asarray(block['semantic_transform']));tree=ns['cKDTree'](sp);raw=np.frombuffer(lid.raw_data,dtype=np.float32).reshape(-1,4);world=_transform(raw[:,:3],np.asarray(block['lidar_transform']));dist,ix=tree.query(world);ids=np.where(dist<=.08,sem['id'][ix].astype(np.int64),-1);roleids={v:int(k) for k,v in block['gt_actor_ids'].items()};baseline=None
    for label,radius in R.items():
     if radius is None:mod._clusters=real_clusters
     else:mod._clusters=lambda points,eps,min_points=3,r=radius:real_clusters(points,r,min_points)
     loc=mod.localize_groups(objs,lid,rgb,radar,ego);groups=loc['groups'];rolemap={}
     for g in groups:
      roles={matches[m['id']] for m in g['members'] if m['id'] in matches}
      if len(roles)==1:
       role=next(iter(roles));assert role not in rolemap;rolemap[role]=g
     invariant=[{k:g[k] for k in ('group_id','members','representative','group_evidence','box_point_indices','candidate_point_indices','nonground_point_indices')} for g in groups]
     if radius is None:
      baseline=invariant;old=block['results'][source]['groups'];assert len(old)==len(groups)
      for oldg,newg in zip(old,groups):
       for k in ('group_id','members','representative','group_evidence','box_point_indices','candidate_point_indices','nonground_point_indices','selected_point_indices','status','reason','clusters'):
        assert oldg[k]==newg[k],(source,scene,rep,k,oldg[k],newg[k])
      r0checked+=1
     else:
      assert baseline==invariant,(source,scene,rep,label,'stage changed');unchanged+=1
     for role,actor in roleids.items():
      g=rolemap.get(role);row={'source':source,'scene':scene,'rep':rep,'radius':label,'epsilon_override_m':radius,'role':role,'actor_id':actor,'matched_detection':g is not None}
      if not g:row.update(status='NO_MATCHED_DETECTION',reason='NO_MATCHED_DETECTION',candidate_count=0,selected_target=0,selected_background=0,selected_other_vehicle=0,selected_unmatched=0,selected_total=0,components=[]);rows.append(row);continue
      ng=np.asarray(g['nonground_point_indices'],dtype=int);pts=loc['lidar_ego'][ng];eps=(min(1.,max(.38,.018*float(np.median(np.linalg.norm(pts[:,:2],axis=1))))) if len(pts) else None) if radius is None else radius
      components=[]
      if len(pts)>=3 and len(pts)<=2500:
       for component in real_clusters(pts,eps):
        pointidx=ng[component];a=ids[pointidx];target=int(np.count_nonzero(a==actor));other=int(np.count_nonzero(np.isin(a,[v for v in roleids.values() if v!=actor])));unknown=int(np.count_nonzero(a==-1));background=int(len(a)-target-other-unknown);vehicles=sorted({int(z) for z in a if z in roleids.values()});span=np.ptp(pts[component],axis=0);plausible=bool(span[0]<=6.5 and span[1]<=3.5 and span[2]<=3.)
        components.append({'count':len(a),'target':target,'background':background,'other_vehicle':other,'unknown':unknown,'vehicle_ids':vehicles,'multi_vehicle':len(vehicles)>1,'target_plus_background':target>0 and background>0,'plausible_span':plausible,'point_indices':pointidx.tolist()})
      select=np.asarray(g['selected_point_indices'],dtype=int);v=ids[select];target=int(np.count_nonzero(v==actor));other=int(np.count_nonzero(np.isin(v,[z for z in roleids.values() if z!=actor])));unknown=int(np.count_nonzero(v==-1));bg=int(len(v)-target-other-unknown);position=truth[role]['position'];error=None;center_error=None
      if g['status']=='LOCATED_UNVALIDATED':
       error=float(g['nearest_surface_distance_m']-position['nearest_box_distance_m']);center_error=float(np.linalg.norm(np.asarray(g['cluster_center_ego'])-np.asarray(position['center_ego'])))
      row.update(status=g['status'],reason=g['reason'],epsilon_m=eps,nonground_count=len(ng),candidate_count=len(components),valid_cluster_count=len(g['clusters']),candidate_mixed_background=sum(x['target_plus_background'] for x in components),candidate_multi_vehicle=sum(x['multi_vehicle'] for x in components),selected_total=len(v),selected_target=target,selected_background=bg,selected_other_vehicle=other,selected_unmatched=unknown,selected_pure=bool(len(v)>=3 and target==len(v)),selected_mixed_vehicle=bool(target and other),range_error_m=error,visible_center_vs_box_center_m=center_error,components=components)
      rows.append(row)
   print('DONE',source,scene,flush=True)
finally:mod._clusters=real_clusters
assert len(rows)==1800 and r0checked==100 and unchanged==500
(OUT/'per_target.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n');fields=[k for k in dict.fromkeys(k for r in rows for k in r) if k!='components']
with (OUT/'per_target.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
(OUT/'metadata.json').write_text(json.dumps({'source':str(IN),'target_records':len(rows),'R0_replay_frames':r0checked,'unchanged_preclustering_checks':unchanged,'radius_values':R,'fixed_detection_and_radar':str(SRC),'algorithm_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [WORK/'integration/target_group_localization.py',WORK/'integration/target_pointcloud_localization.py',WORK/'integration/duplicate_detection_grouper.py']},'note':'Only group final clustering function changed in memory; detection grouping and single-detection anchors remain original. No simulator or production code change.'},indent=2)+'\n')
print('DONE rows',len(rows),'R0',r0checked,'invariant',unchanged,flush=True)
