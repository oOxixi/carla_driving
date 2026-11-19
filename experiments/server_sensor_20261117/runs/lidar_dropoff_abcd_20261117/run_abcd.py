"""Controlled four-LiDAR, single-frame scheme C experiment on isolated CARLA 22170."""
import collections,csv,hashlib,json,math,pathlib,time,traceback,types
import numpy as np,carla
class cKDTree:
 def __init__(self,points):
  self.points=points;self.cell=.08;self.base=100000
  grid=np.floor(points/self.cell).astype(np.int64)+10000
  assert grid.min()>=0 and grid.max()<self.base
  keys=(grid[:,0]*self.base+grid[:,1])*self.base+grid[:,2]
  self.order=np.argsort(keys);self.keys=keys[self.order]
 def query(self,points,k=1):
  grid=np.floor(points/self.cell).astype(np.int64)+10000;best=np.full(len(points),np.inf);which=np.zeros(len(points),dtype=int)
  for dx in (-1,0,1):
   for dy in (-1,0,1):
    for dz in (-1,0,1):
     keys=((grid[:,0]+dx)*self.base+grid[:,1]+dy)*self.base+grid[:,2]+dz
     begin=np.searchsorted(self.keys,keys,'left');end=np.searchsorted(self.keys,keys,'right');at=begin.copy()
     while np.any(at<end):
      active=np.flatnonzero(at<end);indices=self.order[at[active]];dist=np.sum((points[active]-self.points[indices])**2,axis=1);better=dist<best[active];best[active[better]]=dist[better];which[active[better]]=indices[better];at[active]+=1
  return np.sqrt(best),which
from tools.pointcloud_p0.replay_io import read,TF
from tools.pointcloud_p0.run_matrix import CASES,setup_waypoints,get_sensor,read_frame,weather_for,gt_positions,bbox_projection,SEM_DTYPE
from integration.target_group_localization import localize_groups
from integration.target_pointcloud_localization import _transform
BASE=pathlib.Path('/home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime');OUT=BASE/'lidar_dropoff_abcd_20261117';SRC=BASE/'pointcloud_p0_rear_final_20261117/default_far';GROUPS={'A':(.45,.4),'B':(0.,.4),'C':(.45,0.),'D':(0.,0.)};SAMPLES=10
WORK=pathlib.Path('/home/tiaozhansai/carla-lane-association-20261117')
def comp_sizes(points,eps):
 if not len(points):return []
 if len(points)>2500:return None
 ds=np.sum((points[:,None,:]-points[None,:,:])**2,axis=2);seen=set();sizes=[]
 for i in range(len(points)):
  if i in seen:continue
  todo=[i];seen.add(i);count=0
  while todo:
   j=todo.pop();count+=1
   for k in np.flatnonzero(ds[j]<=eps**2):
    k=int(k)
    if k not in seen:seen.add(k);todo.append(k)
  sizes.append(count)
 return sorted(sizes,reverse=True)
def sensor_transform_relative(m,ego):return np.linalg.inv(np.asarray(ego))@np.asarray(m)
def dump(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
client=carla.Client('127.0.0.1',22170);client.set_timeout(30);world=client.get_world();assert world.get_map().name.endswith('Town05_Opt');old=world.get_settings();oldweather=world.get_weather();rows=[];failures=[];settings_info={};start=time.time()
try:
 settings=world.get_settings();settings.synchronous_mode=True;settings.fixed_delta_seconds=.05;world.apply_settings(settings);world.set_weather(weather_for(world,'clear'))
 for scene in range(5):
  actors=[];sensors=[]
  try:
   original,l0,rgb,radar,ego0,objs=read(SRC/str(scene));e,wps=setup_waypoints(world.get_map(),next(x for x in CASES if x[0]=='default_far'),scene);bp=world.get_blueprint_library().find('vehicle.tesla.model3')
   def spawn(wp,role):
    t=wp.transform;t.location.z+=.35;bp.set_attribute('role_name','dropoff_abcd:'+role);a=world.try_spawn_actor(bp,t)
    if a is None:raise RuntimeError('spawn failed '+role)
    actors.append(a);a.set_simulate_physics(False);return a
   ego=spawn(e,'ego');vehicles={role:spawn(wp,role) for role,wp in wps.items()};world.tick();ego_tf=ego.get_transform();em=np.asarray(ego_tf.get_matrix());assert np.max(np.abs(em-np.asarray(original['ego_transform'])))<1e-4
   camera_rel=sensor_transform_relative(original['camera_transform'],original['ego_transform']);radar_rel=sensor_transform_relative(original['radar_transform'],original['ego_transform']);assert np.allclose(camera_rel[:3,3],[1.5,0,2.2],atol=1e-4);assert np.allclose(radar_rel[:3,3],[1.5,0,1.0],atol=1e-4)
   errs=[]
   for role,actor in vehicles.items():
    box=bbox_projection(actor,rgb);prev=original['evaluation']['gt_projected_boxes_px'][role];errs.append(float(np.max(np.abs(np.array(box)-prev))))
   assert max(errs)<.05,('truth box mismatch',errs)
   queues={};actual={};base={'channels':32,'range':80,'rotation_frequency':20,'points_per_second':224000,'upper_fov':10,'lower_fov':-30,'sensor_tick':0}
   for key,(general,zero) in GROUPS.items():
    attrs=dict(base,dropoff_general_rate=general,dropoff_zero_intensity=zero,dropoff_intensity_limit=.8,noise_seed=20261117)
    sensor,q=get_sensor(world,ego,actors,key,'sensor.lidar.ray_cast',carla.Transform(carla.Location(z=2.35)),attrs);sensors.append(sensor);queues[key]=q;actual[key]=dict(sensor.attributes)
   sensor,q=get_sensor(world,ego,actors,'sem','sensor.lidar.ray_cast_semantic',carla.Transform(carla.Location(z=2.35)),base);sensors.append(sensor);queues['semantic']=q;semattrs=dict(sensor.attributes)
   idrole={a.id:role for role,a in vehicles.items()};matches={z['id']:z['gt_match']['role'] for z in original['evaluation']['detections'] if z['gt_match']};truth={role:gt_positions(v,ego) for role,v in vehicles.items()}
   bboxtruth={}
   for role,v in vehicles.items():
    b=v.bounding_box;bw=np.asarray(v.get_transform().get_matrix())@np.asarray(carla.Transform(b.location,b.rotation).get_matrix());bboxtruth[role]={'matrix_world':bw.tolist(),'extent':[b.extent.x,b.extent.y,b.extent.z],'position':truth[role]}
   settings_info[str(scene)]={'max_gt_box_delta_px':max(errs),'ego_matrix':em.tolist(),'sensor_attrs':actual,'semantic_attrs':semattrs,'gt':bboxtruth,'detection_source':str(SRC/str(scene)/'result.json')}
   for tick in range(4+SAMPLES):
    frame=world.tick();samples={name:read_frame(q,frame) for name,q in queues.items()}
    if tick<4:continue
    rep=tick-4;sem=samples['semantic'];assert all(x.frame==frame and abs(x.timestamp-sem.timestamp)<.001 for x in samples.values());assert all(abs(float(x.horizontal_angle)-float(sem.horizontal_angle))<1e-5 for x in samples.values())
    rgb.frame=frame;rgb.timestamp=sem.timestamp;radar.frame=frame;radar.timestamp=sem.timestamp
    sema=np.frombuffer(sem.raw_data,dtype=SEM_DTYPE);sxyz=np.column_stack([sema['x'],sema['y'],sema['z']]);sworld=_transform(sxyz,np.asarray(sem.transform.get_matrix()));tree=cKDTree(sworld)
    folder=OUT/'samples'/str(scene)/str(rep);folder.mkdir(parents=True,exist_ok=True);(folder/'semantic_lidar.bin').write_bytes(sem.raw_data)
    result={'scene':scene,'replicate':rep,'frame':frame,'timestamp':float(sem.timestamp),'sensor_frames':{n:int(x.frame) for n,x in samples.items()},'sensor_timestamps':{n:float(x.timestamp) for n,x in samples.items()},'lidar_transform':samples['A'].transform.get_matrix(),'semantic_transform':sem.transform.get_matrix(),'radar_source':str(SRC/str(scene)/'radar.bin'),'camera_source':str(SRC/str(scene)/'result.json'),'gt_actor_ids':idrole,'results':{}}
    for name in GROUPS:
     lid=samples[name];(folder/(name+'_lidar.bin')).write_bytes(lid.raw_data);t0=time.perf_counter_ns();loc=localize_groups(objs,lid,rgb,radar,ego_tf);latency=(time.perf_counter_ns()-t0)/1e6
     xyz=loc['lidar_ego'];worldpts=loc['lidar_world'];ds,ix=tree.query(worldpts,k=1);known=ds<=.08;ids=np.where(known,sema['id'][ix].astype(np.int64),-1);tags=np.where(known,sema['tag'][ix].astype(np.int64),-1)
     groups=loc['groups'];group_data=[];role_map={}
     for g in groups:
      gr={k:v for k,v in g.items()};roles={matches[m['id']] for m in g['members'] if m['id'] in matches};role=next(iter(roles)) if len(roles)==1 else None
      if role:
       if role in role_map:raise RuntimeError('duplicate groups for matched role '+role)
       role_map[role]=g
      gr['audit_role']=role;group_data.append(gr)
     result['results'][name]={'elapsed_ms':latency,'lidar_points':len(xyz),'ground_plane':loc['ground_plane'],'groups':group_data,'sensor_frame':int(lid.frame),'horizontal_angle':float(lid.horizontal_angle),'sensor_timestamp':float(lid.timestamp),'lidar_hash':hashlib.sha256(lid.raw_data).hexdigest()}
     for role,vehicle in vehicles.items():
      actor_id=vehicle.id;raw_target=int(np.count_nonzero(ids==actor_id));near_unmatched=int(np.count_nonzero(~known));g=role_map.get(role);row={'scene':scene,'replicate':rep,'frame':frame,'group':name,'role':role,'actor_id':actor_id,'raw_lidar_total':len(xyz),'target_raw_semantic':raw_target,'raw_unmatched_semantic_all':near_unmatched,'matched_detection':bool(g),'elapsed_ms_per_frame':round(latency,3)}
      b=bboxtruth[role];local=_transform(worldpts,np.linalg.inv(np.asarray(b['matrix_world'])));ext=np.asarray(b['extent']);row['target_raw_bbox_0_08m']=int(np.count_nonzero(np.all(np.abs(local)<=ext+.08,axis=1)))
      if g:
       indices=np.asarray(g['box_point_indices'],dtype=int);ng=np.asarray(g['nonground_point_indices'],dtype=int);selected=np.asarray(g['selected_point_indices'],dtype=int);pts=xyz[ng]
       eps=min(1.,max(.38,.018*float(np.median(np.linalg.norm(pts[:,:2],axis=1))))) if len(pts) else None;sizes=comp_sizes(pts,eps) if eps is not None else []
       assigned_ids=ids[selected];true=int(np.count_nonzero(assigned_ids==actor_id));unmatched=int(np.count_nonzero(assigned_ids==-1));other=int(np.count_nonzero((assigned_ids!=-1)&(assigned_ids!=actor_id)));other_cars=int(np.count_nonzero(np.isin(assigned_ids,[v.id for v in vehicles.values() if v.id!=actor_id])));background=other-other_cars
       row.update(detection_ids=';'.join(m['id'] for m in g['members']),box_total=len(indices),box_target=int(np.count_nonzero(ids[indices]==actor_id)),candidate_count=len(g['candidate_point_indices']),nonground_count=len(ng),nonground_target=int(np.count_nonzero(ids[ng]==actor_id)),component_count=len(sizes) if sizes is not None else None,largest_component=max(sizes,default=0) if sizes is not None else None,valid_clusters=len(g['clusters']),status=g['status'],reason=g['reason'],selected_total=len(selected),selected_target=true,selected_other_vehicle=other_cars,selected_background=background,selected_unmatched=unmatched,point_precision=true/(true+other) if true+other else None,nearest_surface_error_m=round(float(g['nearest_surface_distance_m']-truth[role]['nearest_box_distance_m']),5) if g['status']=='LOCATED_UNVALIDATED' else None)
      else:row.update(status='NO_MATCHED_DETECTION',reason='NO_MATCHED_DETECTION',selected_total=0,selected_target=0,selected_other_vehicle=0,selected_background=0,selected_unmatched=0)
      rows.append(row)
    dump(folder/'result.json',result);print('DONE scene',scene,'replicate',rep,'frame',frame,flush=True)
   dump(OUT/'progress.json',{'complete_scenes':scene+1,'samples_per_scene':SAMPLES,'rows':len(rows),'failures':failures})
  except Exception as ex:
   traceback.print_exc();failures.append({'scene':scene,'error':repr(ex)});raise
  finally:
   for sensor in sensors:
    try:sensor.stop()
    except Exception:pass
   for actor in reversed(actors):
    try:actor.destroy()
    except Exception:pass
finally:
 world.set_weather(oldweather);world.apply_settings(old)
 dump(OUT/'run_metadata.json',{'scene_settings':settings_info,'failures':failures,'rows':len(rows),'wall_seconds':time.time()-start,'fixed_detection_and_radar_source':str(SRC),'temporal_note':'Saved original radar replayed with fixed pose and values for all groups; replay timestamp is aligned for API only, not a live same-frame radar measurement.','seed_note':'Same configured seed for each group. Seed probe shows 0.9.16 ignores noise_seed; ten consecutive draws are not ten independently seeded trials.','ground_truth_note':'Semantic LiDAR nearest neighbour <=0.08m and actor bounding boxes are used only after inference.','algorithm_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [WORK/'integration/target_group_localization.py',WORK/'integration/target_pointcloud_localization.py',WORK/'integration/duplicate_detection_grouper.py']}})
 if rows:
  keys=list(dict.fromkeys(k for row in rows for k in row));
  with (OUT/'per_target.csv').open('w',encoding='utf-8-sig',newline='') as f:
   writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader();writer.writerows(rows)
  dump(OUT/'per_target.json',rows)
print('FINISHED',len(rows),'errors',len(failures),'seconds',round(time.time()-start,1),flush=True)
