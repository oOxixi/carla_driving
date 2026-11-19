import csv,json,math,hashlib,itertools,pathlib
import numpy as np, carla
from tools.pointcloud_p0.replay_io import read,TF
from tools.pointcloud_p0.run_matrix import setup_waypoints,CASES,semantic_correspondence,SEM_DTYPE
from integration.target_pointcloud_localization import localize,_transform
BASE=pathlib.Path('/home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime')
SRC=BASE/'pointcloud_p0_rear_final_20261117'; GRP=BASE/'pointcloud_group_regression55_20261117';OUT=BASE/'pointcloud_far15_diagnosis_20261117'
client=carla.Client('127.0.0.1',22170);client.set_timeout(10);mp=client.get_world().get_map();assert 'Town05' in mp.name
case=next(c for c in CASES if c[0]=='default_far');offsets=[]
for i in range(5):
 d=json.loads((SRC/'far'/str(i)/'result.json').read_text());e,w=setup_waypoints(mp,case,i)
 for z in d['evaluation']['detections']:
  if 'gt' in z:
   wp=w[z['gt_match']['role']].transform.location;offsets.append(np.array(z['gt']['center_world'][:2])-np.array([wp.x,wp.y]))
offset=np.mean(offsets,axis=0);offseterr=max(float(np.linalg.norm(v-offset)) for v in offsets)
rows=[];checks=[]
for i in range(5):
 p=SRC/'default_far'/str(i);d,l,r,rad,ego,objs=read(p);loc=localize(objs,l,r,rad,ego);ev=d['evaluation'];saved={x['id']:x for x in d['predictions']};replayed={x['id']:x for x in loc['objects']};grp=json.loads((GRP/'default_far'/str(i)/'result.json').read_text())
 for ident,o in saved.items():
  q=replayed[ident];checks.append(all(o[k]==q[k] for k in ['status','reason','box_point_indices','exclusive_point_indices','nonground_point_indices','clusters','radar_box_exclusive_count']))
 egom=np.asarray(d['ego_transform']);e,w=setup_waypoints(mp,case,i);assert np.linalg.norm(np.array([e.transform.location.x,e.transform.location.y])-egom[:2,3])<.01
 sem=np.fromfile(p/'semantic_lidar.bin',dtype=SEM_DTYPE);semxyz=np.column_stack((sem['x'],sem['y'],sem['z']));semworld=_transform(semxyz,np.asarray(d['semantic_transform']));semcam=_transform(semworld,np.linalg.inv(np.asarray(d['camera_transform'])));f=800/(2*math.tan(math.radians(100)/2));su=(f*semcam[:,1]/np.maximum(semcam[:,0],1e-6)+400)/800;sv=(-f*semcam[:,2]/np.maximum(semcam[:,0],1e-6)+225)/450
 rw=loc['_radar_world'];rc=_transform(rw,np.linalg.inv(np.asarray(d['camera_transform'])));ru=(f*rc[:,1]/np.maximum(rc[:,0],1e-6)+400)/800;rv=(-f*rc[:,2]/np.maximum(rc[:,0],1e-6)+225)/450
 pred_by_role={z['gt_match']['role']:(saved[z['id']],z) for z in ev['detections'] if z['gt_match']};sem_obj=type('Sem',(),{'raw_data':(p/'semantic_lidar.bin').read_bytes(),'transform':TF(d['semantic_transform'])})()
 for role in ev['expected_roles']:
  actor=ev['gt_actor_ids'][role];sm=(sem['id']==actor);visible=sm&(semcam[:,0]>1)&(su>=0)&(su<=1)&(sv>=0)&(sv<=1);sp=semworld[sm];wp=w[role].transform.location;center=np.array([wp.x,wp.y])+offset;distance=float(np.linalg.norm(center-egom[:2,3]));match=pred_by_role.get(role)
  row={'repeat':i,'frame':d['frame'],'role':role,'actor_id':actor,'center_distance_m_reconstructed':round(distance,3),'semantic_target_all':int(sm.sum()),'semantic_target_visible':int(visible.sum())}
  if match:
   o,z=match;box=o['bbox'];bb=np.array(box)*[800,450,800,450];idx=np.array(o['box_point_indices'],dtype=int);ex=np.array(o['exclusive_point_indices'],dtype=int);ng=np.array(o['nonground_point_indices'],dtype=int);plane=loc['plane'];xyz=loc['_lidar_ego'];ht=xyz[idx,2]-(plane['a']*xyz[idx,0]+plane['b']*xyz[idx,1]+plane['c']);groundfirst=int(((ht>.22)&(ht<3.5)).sum());pts=xyz[ng];eps=min(1.,max(.38,.018*float(np.median(np.linalg.norm(pts[:,:2],axis=1))))) if len(pts)>=3 else None
   sizes=[];threshold=None
   if eps is not None:
    dist=np.linalg.norm(pts[:,None,:]-pts[None,:,:],axis=2);seen=set()
    for k in range(len(pts)):
     if k in seen:continue
     stack=[k];seen.add(k);n=0
     while stack:
      j=stack.pop();n+=1
      for t in np.flatnonzero(dist[j]<=eps):
       t=int(t)
       if t not in seen:seen.add(t);stack.append(t)
     sizes.append(n)
    threshold=min(sorted([dist[a,b],dist[a,c],dist[b,c]])[1] for a,b,c in itertools.combinations(range(len(pts)),3))
   labels=semantic_correspondence(xyz,list(map(int,idx)),sem_obj,ego);target_in_box=sum(q['actor_id']==actor for q in labels.values());unknown=len(idx)-len(labels)
   radar_mask=(rc[:,0]>1)&(ru>=box[0])&(ru<=box[2])&(rv>=box[1])&(rv<=box[3]);rpts=rw[radar_mask];near=int((np.min(np.linalg.norm(rpts[:,None,:]-sp[None,:,:],axis=2),axis=1)<=1.25).sum()) if len(sp) and len(rpts) else 0
   sr=visible&(su>=box[0])&(su<=box[2])&(sv>=box[1])&(sv<=box[3]);g=next(x for x in grp['groups'] if x['role_audit']==role)
   row.update(detection=o['id'],bbox_width_px=round(bb[2]-bb[0],2),bbox_height_px=round(bb[3]-bb[1],2),confidence=round(o['confidence'],4),match_iou=z['gt_match']['iou'],box_raw=len(idx),box_target_semantic=target_in_box,box_semantic_unmatched=unknown,semantic_target_in_detection=int(sr.sum()),groundfirst_count=groundfirst,exclusive_after_overlap=len(ex),nonground_after_overlap=len(ng),component_sizes=sorted(sizes,reverse=True),epsilon_m=round(eps,3) if eps is not None else None,epsilon_for_3_m=round(float(threshold),3) if threshold is not None else None,radar_in_box=int(radar_mask.sum()),radar_box_exclusive=o['radar_box_exclusive_count'],radar_within_1_25m_semantic=near,status=o['status'],reason=o['reason'],group_reason=g['reason'],category='A_框内稀疏')
  else:
   b=ev['gt_projected_boxes_px'][role];box=[b[0]/800,b[1]/450,b[2]/800,b[3]/450];rm=(rc[:,0]>1)&(ru>=box[0])&(ru<=box[2])&(rv>=box[1])&(rv<=box[3]);rp=rw[rm];near=int((np.min(np.linalg.norm(rp[:,None,:]-sp[None,:,:],axis=2),axis=1)<=1.25).sum()) if len(sp) and len(rp) else 0
   row.update(detection=None,radar_in_gt_box=int(rm.sum()),radar_gtbox_within_1_25m_semantic=near,status='NO_MATCHED_DETECTION',reason='DETECTION_MISS_OR_IOU_BELOW_0.3',category='未匹配检测_无法归入ABC')
  rows.append(row)
assert len(rows)==15 and len(checks)==14 and all(checks)
summary={'source':str(SRC/'default_far'),'group_replay':str(GRP/'default_far'),'frozen_original_replay_all_14_match':all(checks),'ground_truth_center_reconstruction':'Town05 map test waypoints plus mean box-center offset from 11 located 64-line same-scene counterparts; horizontal ego-origin to box-center. Not original saved truth for failed cases.','offset_reference_count':len(offsets),'offset_max_error_m':offseterr,'rows':rows,'source_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [pathlib.Path('integration/target_pointcloud_localization.py'),pathlib.Path('integration/target_group_localization.py'),pathlib.Path('tools/pointcloud_p0/run_matrix.py')]}}
lib=client.get_world().get_blueprint_library(); b=lib.find('sensor.lidar.ray_cast'); sb=lib.find('sensor.lidar.ray_cast_semantic')
summary['current_carla_blueprint_defaults']={'sensor.lidar.ray_cast':{a.id:float(a) for a in b if a.id in ('dropoff_general_rate','dropoff_zero_intensity','dropoff_intensity_limit','noise_stddev')},'semantic_lidar_dropoff_attributes':[a.id for a in sb if 'dropoff' in a.id],'caveat':'Current blueprint defaults, not saved historical actor attributes; collection script does not override these settings.'}
(OUT/'diagnosis.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
keys=list(dict.fromkeys(k for row in rows for k in row))
with (OUT/'diagnosis.csv').open('w',encoding='utf-8-sig',newline='') as f:
 writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader();writer.writerows(rows)
print(json.dumps(summary,ensure_ascii=False,indent=2))
