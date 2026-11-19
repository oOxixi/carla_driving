"""Synchronized sensor localization matrix. Simulator truth used only offline."""
import copy,json,math,queue,time,traceback,os
from pathlib import Path
import carla,numpy as np
from PIL import Image,ImageDraw
from integration.rgb_detector import OnnxYoloDetector,carla_rgb_array
from integration.object_tracker import SensorObjectTracker
from integration.target_pointcloud_localization import localize,_transform
from integration.camera_lidar_association import _rigid_matrix

OUT=Path(os.environ.get('POINTCLOUD_P0_OUTPUT','/home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime/pointcloud_p0_20261117'))
OUT.mkdir(parents=True,exist_ok=True)
CASES=[
 ('near','近距离',10,10,10,None,'clear',64,640000),
 ('middle','中距离',24,20,20,None,'clear',64,640000),
 ('far','远距离',44,40,40,None,'clear',64,640000),
 ('occlusion','部分遮挡',28,20,20,20,'clear',64,640000),
 ('sparse','点云稀疏',35,30,30,None,'clear',16,56000),
 ('close','多车紧邻',22,22,22,None,'clear',64,640000),
 ('rain','雨天',24,20,20,None,'rain',64,640000),
 ('night','夜间',24,20,20,None,'night',64,640000),
 ('fog','雾天',24,20,20,None,'fog',64,640000),
 ('default_mid','默认32线中距离',24,20,20,None,'clear',32,224000),
 ('default_far','默认32线远距离',44,40,40,None,'clear',32,224000)]
SEM_DTYPE=np.dtype([('x','<f4'),('y','<f4'),('z','<f4'),('cos','<f4'),('id','<u4'),('tag','<u4')])
def advance(w,d):
 for _ in range(d):
  n=w.next(1)
  if len(n)!=1 or n[0].is_junction:return None
  w=n[0]
 return w
def setup_waypoints(m,case,repeat):
 _,_,a,b,c,occ,_,_,_=case
 for spawn in m.get_spawn_points():
  e=m.get_waypoint(spawn.location)
  if not e or e.is_junction:continue
  l,r=e.get_left_lane(),e.get_right_lane()
  if not l or not r or str(l.lane_type)!='Driving' or str(r.lane_type)!='Driving':continue
  f=e.transform.get_forward_vector()
  if any(q.transform.get_forward_vector().x*f.x+q.transform.get_forward_vector().y*f.y<.8 for q in (l,r)):continue
  offset=(-2,-1,0,1,2)[repeat]
  targets={'A':advance(e,a+offset),'B':advance(l,b+offset),'C':advance(r,c+offset)}
  if occ is not None:targets['O']=advance(e,occ+offset)
  if all(targets.values()) and advance(e,58) and advance(l,58) and advance(r,58):return e,targets
 raise RuntimeError('NO_VALID_TEST_ROAD')
def bbox_projection(actor,camera):
 inv=np.asarray(camera.transform.get_inverse_matrix());f=camera.width/(2*math.tan(math.radians(100)/2));points=[]
 for v in actor.bounding_box.get_world_vertices(actor.get_transform()):
  q=inv@np.array([v.x,v.y,v.z,1.])
  if q[0]<=0:return None
  points.append((f*q[1]/q[0]+camera.width/2,-f*q[2]/q[0]+camera.height/2))
 return [min(x for x,y in points),min(y for x,y in points),max(x for x,y in points),max(y for x,y in points)]
def iou(a,b):
 if b is None:return 0.
 ix=max(0,min(a[2],b[2])-max(a[0],b[0]));iy=max(0,min(a[3],b[3])-max(a[1],b[1]))
 inter=ix*iy;return inter/max(1,(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-inter)
def get_sensor(world,ego,actors,name,bpname,tf,attrs):
 bp=world.get_blueprint_library().find(bpname)
 for k,v in attrs.items():bp.set_attribute(k,str(v))
 s=world.spawn_actor(bp,tf,attach_to=ego);actors.append(s);q=queue.Queue(maxsize=120);s.listen(q.put)
 return s,q
def read_frame(q,frame):
 deadline=time.monotonic()+10
 while time.monotonic()<deadline:
  p=q.get(timeout=max(.1,deadline-time.monotonic()))
  if p.frame==frame:return p
  if p.frame>frame:raise RuntimeError('frame skipped')
 raise RuntimeError('sensor timeout')
def weather_for(world,name):
 w=world.get_weather()
 w.cloudiness=0;w.precipitation=0;w.precipitation_deposits=0;w.wetness=0;w.wind_intensity=0
 w.fog_density=0;w.fog_distance=0;w.fog_falloff=1;w.sun_altitude_angle=50;w.sun_azimuth_angle=0
 if name=='rain':w.cloudiness=80;w.precipitation=70;w.precipitation_deposits=70;w.wetness=80
 elif name=='fog':w.fog_density=65;w.fog_distance=8;w.fog_falloff=1
 elif name=='night':w.sun_altitude_angle=-65;w.cloudiness=10
 else:w.cloudiness=5;w.precipitation=0;w.fog_density=0;w.sun_altitude_angle=50
 return w
def semantic_correspondence(lidar_ego,indices,semantic,ego_transform):
 """Audit-only spatial matching to co-located semantic LiDAR, never model input."""
 if not indices:return {}
 sem=np.frombuffer(semantic.raw_data,dtype=SEM_DTYPE)
 xyz=np.column_stack((sem['x'],sem['y'],sem['z'])).astype(float)
 sem_world=_transform(xyz,_rigid_matrix(semantic.transform,'get_matrix'))
 sem_ego=_transform(sem_world,_rigid_matrix(ego_transform,'get_inverse_matrix'))
 cell=.12
 vox=np.floor(sem_ego/cell).astype(np.int64);grid={}
 for i,key in enumerate(vox):grid.setdefault(tuple(key),[]).append(i)
 output={}
 for index in indices:
  point=lidar_ego[index];key=np.floor(point/cell).astype(np.int64);candidates=[]
  for dx in (-1,0,1):
   for dy in (-1,0,1):
    for dz in (-1,0,1):candidates.extend(grid.get((key[0]+dx,key[1]+dy,key[2]+dz),()))
  if not candidates:continue
  ds=np.linalg.norm(sem_ego[candidates]-point,axis=1);best=int(np.argmin(ds))
  if ds[best]>.08:continue
  j=candidates[best];output[index]={'actor_id':int(sem['id'][j]),'semantic_tag':int(sem['tag'][j]),'match_error_m':float(ds[best])}
 return output
def gt_positions(actor,ego):
 b=actor.bounding_box;v=b.get_world_vertices(actor.get_transform())
 center=np.mean([[p.x,p.y,p.z] for p in v],axis=0)
 ei=np.asarray(ego.get_transform().get_inverse_matrix())
 center_ego=(ei@np.r_[center,1.])[:3]
 vertices_ego=np.asarray([[p.x,p.y,p.z,1.] for p in v])@ei.T
 min_forward=float(np.min(vertices_ego[:,0]))
 local_box=carla.Transform(b.location,b.rotation)
 box_world=np.asarray(actor.get_transform().get_matrix())@np.asarray(local_box.get_matrix())
 ego_world=ego.get_location()
 ego_box=np.linalg.inv(box_world)@np.array([ego_world.x,ego_world.y,ego_world.z,1.])
 dx=max(0,abs(ego_box[0])-b.extent.x);dy=max(0,abs(ego_box[1])-b.extent.y)
 # Assuming approximately horizontal vehicle; return nearest 2D bounding-box surface.
 return {'center_world':center.tolist(),'center_ego':[float(center_ego[0]),float(-center_ego[1]),float(center_ego[2])],
         'nearest_box_distance_m':float(math.hypot(dx,dy)),'box_rear_longitudinal_m':min_forward}
def radar_gt_membership(points,actors,matched_role,margin_m=.2):
 # Audit-only check against expanded actor boxes; unmatched is not automatically an error.
 boxes={}
 for role,actor in actors.items():
  b=actor.bounding_box;local=carla.Transform(b.location,b.rotation)
  box_world=np.asarray(actor.get_transform().get_matrix())@np.asarray(local.get_matrix())
  boxes[role]=(np.linalg.inv(box_world),np.array([b.extent.x,b.extent.y,b.extent.z]))
 result={'total':len(points),'target':0,'other_vehicle':0,'ambiguous':0,'outside_actor_boxes':0,'box_margin_m':margin_m}
 for point in points:
  hits=[]
  for role,(inv,ext) in boxes.items():
   local=(inv@np.r_[point,1.])[:3]
   if np.all(np.abs(local)<=ext+margin_m):hits.append(role)
  if len(hits)>1:result['ambiguous']+=1
  elif not hits:result['outside_actor_boxes']+=1
  elif hits[0]==matched_role:result['target']+=1
  else:result['other_vehicle']+=1
 return result

def evaluate(predictions,loc,semantic,actors,ego,rgb):
 # Full simulator truth appears here, only after localization is complete.
 boxes={role:bbox_projection(a,rgb) for role,a in actors.items()}
 candidate=[]
 for o in predictions:
  box=[v*s for v,s in zip(o['bbox'],[rgb.width,rgb.height,rgb.width,rgb.height])]
  for role,b in boxes.items():
   score=iou(box,b)
   if score>=.3:candidate.append((score,o['id'],role))
 candidate.sort(reverse=True);used_ids=set();used_roles=set();matches={}
 for score,det,role in candidate:
  if det not in used_ids and role not in used_roles:
   matches[det]={'role':role,'iou':round(score,4)};used_ids.add(det);used_roles.add(role)
 indices=sorted({i for o in predictions for field in ('box_point_indices','nonground_point_indices','selected_point_indices') for i in o[field]})
 semlabels=semantic_correspondence(loc['_lidar_ego'],indices,semantic,ego.get_transform())
 vehicleids={int(a.id):role for role,a in actors.items()};out=[]
 for o in predictions:
  match=matches.get(o['id']);entry={'id':o['id'],'gt_match':match}
  target_id=int(actors[match['role']].id) if match else None
  for stage,key in [('box','box_point_indices'),('nonground','nonground_point_indices'),('selected','selected_point_indices')]:
   ids=o[key];labeled=[semlabels[i] for i in ids if i in semlabels]
   true=sum(x['actor_id']==target_id for x in labeled) if target_id is not None else None
   other=sum(x['actor_id'] in vehicleids and x['actor_id']!=target_id for x in labeled) if target_id is not None else None
   otherstatic=sum(x['actor_id'] not in vehicleids for x in labeled)
   entry[stage]={'total':len(ids),'matched_semantic':len(labeled),'unknown':len(ids)-len(labeled),
                 'target':true,'other_test_vehicle':other,'other_or_environment':otherstatic,
                 'tag_counts':{str(t):sum(z['semantic_tag']==t for z in labeled) for t in sorted({z['semantic_tag'] for z in labeled})}}
  if match and o['status']=='LOCATED_UNVALIDATED':
   points=loc['_radar_world'][o.get('radar_point_indices',[])]
   entry['radar_box_audit']=radar_gt_membership(points,actors,match['role'])
   gt=gt_positions(actors[match['role']],ego);actual=np.asarray(o['cluster_center_ego']);ref=np.asarray(gt['center_ego']);error=actual-ref
   entry['errors']={'cluster_center_vs_vehicle_center_3d_m':float(np.linalg.norm(error)),
      'longitudinal_center_difference_m':float(error[0]),'lateral_center_difference_m':float(error[1]),
      'rear_longitudinal_error_m':float(o['longitudinal_surface_min_m']-gt['box_rear_longitudinal_m']),
      'nearest_surface_range_error_m':float(o['nearest_surface_distance_m']-gt['nearest_box_distance_m']),
      'p10_surface_range_error_m':float(o['surface_distance_p10_m']-gt['nearest_box_distance_m'])}
   entry['gt']=gt
  out.append(entry)
 return {'detections':out,'gt_projected_boxes_px':boxes,'gt_actor_ids':{role:int(a.id) for role,a in actors.items()},'expected_roles':list(actors),'matched_roles':sorted(used_roles),
         'unmatched_roles':sorted(set(actors)-used_roles),'semantic_match_threshold_m':.08,
         'gt_detection_matching':'greedy one-to-one projected actor box IoU >= 0.3'}
def save_images(root,rgb,loc,evaluation,semlabels,actor_ids):
 rgb_array=carla_rgb_array(rgb);img=Image.fromarray(rgb_array);img.save(root/'camera.png')
 det=img.copy();draw=ImageDraw.Draw(det)
 for o in loc['objects']:
  box=[v*s for v,s in zip(o['bbox'],[rgb.width,rgb.height,rgb.width,rgb.height])]
  draw.rectangle(box,outline='#4ad7ff',width=2);draw.text((box[0],max(0,box[1]-15)),o['id'],fill='#4ad7ff')
 det.save(root/'detections.png')
 audit=img.copy();draw=ImageDraw.Draw(audit);uv=loc['_uv']
 eval_by_id={x['id']:x for x in evaluation['detections']}
 for o in loc['objects']:
  match=eval_by_id[o['id']]['gt_match'];target=actor_ids.get(match['role']) if match else None
  for i in o['selected_point_indices']:
   v=semlabels.get(i)
   col='#b4bac2' if not v or target is None else ('#36f28d' if v['actor_id']==target else '#ff6868')
   u,w=uv[i];x=u*rgb.width;y=w*rgb.height
   draw.ellipse((x-2,y-2,x+2,y+2),fill=col)
  box=[v*s for v,s in zip(o['bbox'],[rgb.width,rgb.height,rgb.width,rgb.height])]
  draw.rectangle(box,outline='#55baff',width=2);draw.text((box[0],max(0,box[1]-15)),o['id'],fill='#55baff')
 audit.save(root/'audit_points.png')

def run_one(client,world,m,detector,case,repeat):
 name,cn,a,b,c,occ,weather,channels,pps=case
 root=OUT/name/str(repeat);root.mkdir(parents=True,exist_ok=True)
 actors=[];sensor_actors=[];vehicles={}
 e,wps=setup_waypoints(m,case,repeat)
 try:
  world.set_weather(weather_for(world,weather))
  bp=world.get_blueprint_library().find('vehicle.tesla.model3')
  def spawn(w,role):
   t=w.transform;t.location.z+=.35
   if role=='O':
    right=t.get_right_vector();t.location.x+=right.x*.9;t.location.y+=right.y*.9
   bp.set_attribute('role_name','pointcloud_p0:'+role)
   v=world.try_spawn_actor(bp,t)
   if not v:raise RuntimeError('spawn failed: '+role)
   actors.append(v);v.set_simulate_physics(False);return v
  ego=spawn(e,'ego')
  for role,wp in wps.items():vehicles[role]=spawn(wp,role)
  tcam=carla.Transform(carla.Location(x=1.5,z=2.2),carla.Rotation(pitch=-8))
  tlid=carla.Transform(carla.Location(z=2.35))
  trad=carla.Transform(carla.Location(x=1.5,z=1.0))
  attrs={'channels':channels,'range':80,'rotation_frequency':20,'points_per_second':pps,'upper_fov':10,'lower_fov':-30,'sensor_tick':0}
  for name_,kind,tf,kw in [
   ('rgb','sensor.camera.rgb',tcam,{'image_size_x':800,'image_size_y':450,'fov':100,'sensor_tick':0}),
   ('lidar','sensor.lidar.ray_cast',tlid,attrs),('semantic','sensor.lidar.ray_cast_semantic',tlid,attrs),
   ('radar','sensor.other.radar',trad,{'horizontal_fov':40,'vertical_fov':10,'range':80,'points_per_second':12000,'sensor_tick':0})]:
   actor,q=get_sensor(world,ego,actors,name_,kind,tf,kw);sensor_actors.append(actor)
   if name_=='rgb':qrgb=q
   if name_=='lidar':qlid=q
   if name_=='semantic':qsem=q
   if name_=='radar':qrad=q
  for _ in range(4):
   frame=world.tick();rgb=read_frame(qrgb,frame);lidar=read_frame(qlid,frame);semantic=read_frame(qsem,frame);radar=read_frame(qrad,frame)
  if not (rgb.frame==lidar.frame==radar.frame==semantic.frame):raise RuntimeError('sensors not synchronized')
  tracker=SensorObjectTracker()
  objs=[o for o in tracker.update(frame,detector.detect_measurement(rgb)) if o.class_name.lower() in {'car','truck','bus'}]
  loc=localize(objs,lidar,rgb,radar,ego.get_transform())
  baseline=None
  if '--compare-radar' in __import__('sys').argv:
   from integration.target_pointcloud_localization_baseline import localize as baseline_localize
   baseline=baseline_localize(objs,lidar,rgb,radar,ego.get_transform())
  # Semantic sensor and simulator actor state are introduced only after loc completes.
  evaluation=evaluate(loc['objects'],loc,semantic,vehicles,ego,rgb)
  baseline_evaluation=evaluate(baseline['objects'],baseline,semantic,vehicles,ego,rgb) if baseline else None
  ids=sorted({i for o in loc['objects'] for i in o['selected_point_indices']})
  semlabels=semantic_correspondence(loc['_lidar_ego'],ids,semantic,ego.get_transform())
  save_images(root,rgb,loc,evaluation,semlabels,{role:int(v.id) for role,v in vehicles.items()})
  (root/'lidar.bin').write_bytes(lidar.raw_data);(root/'semantic_lidar.bin').write_bytes(semantic.raw_data);(root/'radar.bin').write_bytes(radar.raw_data)
  result={'case':name,'label':cn,'repeat':repeat,'frame':frame,'weather':weather,
          'sensors':{'channels':channels,'points_per_second':pps,'rgb_frame':rgb.frame,'lidar_frame':lidar.frame,'semantic_frame':semantic.frame,'radar_frame':radar.frame},
          'weather_actual':{k:float(getattr(world.get_weather(),k)) for k in ('cloudiness','precipitation','precipitation_deposits','wetness','fog_density','fog_distance','sun_altitude_angle')},
          'ego_transform':ego.get_transform().get_matrix(),'lidar_transform':lidar.transform.get_matrix(),'camera_transform':rgb.transform.get_matrix(),'radar_transform':radar.transform.get_matrix(),'semantic_transform':semantic.transform.get_matrix(),
          'ground_plane':loc['plane'],'predictions':loc['objects'],'evaluation':evaluation,'status':'COMPLETED'}
  if baseline is not None:result['baseline']={'predictions':baseline['objects'],'evaluation':baseline_evaluation}
  (root/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
  return result
 finally:
  for s in sensor_actors:
   try:s.stop()
   except Exception:pass
  for a in reversed(actors):
   try:a.destroy()
   except Exception:pass
def main():
 client=carla.Client('127.0.0.1',22170);client.set_timeout(30);world=client.get_world();m=world.get_map()
 if not m.name.endswith('Town05_Opt'):raise RuntimeError('isolated simulator map changed: '+m.name)
 previous=world.get_settings();oldweather=world.get_weather()
 detector=OnnxYoloDetector('/home/tiaozhansai/carla-driving-2B/deliveries/day7.19_group1/models/yolov8n.onnx')
 rows=[]
 try:
  settings=world.get_settings();settings.synchronous_mode=True;settings.fixed_delta_seconds=.05;world.apply_settings(settings)
  cases=([c for c in CASES if c[0] in {'default_mid','default_far'}] if '--default-only' in __import__('sys').argv else ([c for c in CASES if c[0]=='near'] if '--near-only' in __import__('sys').argv else ([c for c in CASES if c[0]=='occlusion'] if '--compare-radar' in __import__('sys').argv else (CASES[:2] if '--pilot' in __import__('sys').argv else CASES))))
  repetitions=1 if '--pilot' in __import__('sys').argv else 5
  for case in cases:
   for rep in range(repetitions):
    print('START',case[0],rep,flush=True)
    try:
     r=run_one(client,world,m,detector,case,rep)
     matched=sum(x['selected']['matched_semantic'] for x in r['evaluation']['detections'])
     n=sum(x['selected']['total'] for x in r['evaluation']['detections'])
     print('DONE',case[0],rep,'detections',len(r['predictions']),'localized',sum(x['status']=='LOCATED_UNVALIDATED' for x in r['predictions']),'semantic_matched',matched,'selected',n,flush=True)
     rows.append({'case':case[0],'repeat':rep,'status':'COMPLETED','frame':r['frame']})
    except Exception as e:
     traceback.print_exc();rows.append({'case':case[0],'repeat':rep,'status':'ERROR','error':type(e).__name__+': '+str(e)})
    (OUT/'progress.json').write_text(json.dumps({'mode':'pilot' if repetitions==1 else 'matrix','runs':rows},ensure_ascii=False,indent=2))
 finally:
  world.set_weather(oldweather);world.apply_settings(previous)
 print('ALL_DONE',len(rows),flush=True)
if __name__=='__main__':main()
