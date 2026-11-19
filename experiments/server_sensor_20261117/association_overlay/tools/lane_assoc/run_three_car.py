"""Three-vehicle, sensor-only experiment. Ground truth only after prediction."""
import json,math,queue,time,traceback,sys
from pathlib import Path
import carla,numpy as np
from PIL import Image,ImageDraw
from integration.rgb_detector import OnnxYoloDetector,carla_rgb_array
from integration.object_tracker import SensorObjectTracker
from integration.experimental_sensor_fusion import ShadowSensorFusion
from integration.target_lane_association import associate,build_follow_candidates
ROOT=Path('/home/tiaozhansai/carla-driving-target-and-provement')
OUT=ROOT/'artifacts/runtime/lane_assoc_20261117'
OUT.mkdir(parents=True,exist_ok=True)
client=carla.Client('127.0.0.1',22170);client.set_timeout(20)
world=client.get_world();m=world.get_map();original=world.get_settings();actors=[];sensors=[]
def advance(w,d):
 for _ in range(d):
  n=w.next(1.0)
  if len(n)!=1 or n[0].is_junction:return None
  w=n[0]
 return w
def find_start():
 for spawn in m.get_spawn_points():
  e=m.get_waypoint(spawn.location)
  if not e or e.is_junction:continue
  left,right=e.get_left_lane(),e.get_right_lane()
  if not left or not right or str(left.lane_type)!='Driving' or str(right.lane_type)!='Driving':continue
  f=e.transform.get_forward_vector()
  def same(w):
   x=w.transform.get_forward_vector();return x.x*f.x+x.y*f.y>.8
  if not same(left) or not same(right):continue
  a,b,c=advance(e,24),advance(left,20),advance(right,20)
  if a and b and c and all(advance(q,35) for q in (e,left,right)):
   return spawn,e,a,b,c
 raise RuntimeError('no safe three-lane test location')
def spawn_vehicle(bp,waypoint,role):
 t=waypoint.transform
 t.location.z+=0.35
 bp.set_attribute('role_name','lane_assoc_test:'+role)
 actor=world.try_spawn_actor(bp,t)
 if not actor:raise RuntimeError('could not spawn '+role)
 actors.append(actor);return actor
def sensor(ego,name,bpname,tf,attrs):
 bp=world.get_blueprint_library().find(bpname)
 for k,v in attrs.items():bp.set_attribute(k,str(v))
 actor=world.spawn_actor(bp,tf,attach_to=ego);actors.append(actor);sensors.append(actor)
 q=queue.Queue(maxsize=150);actor.listen(q.put)
 return q
def read_frame(q,frame):
 deadline=time.monotonic()+8
 while time.monotonic()<deadline:
  item=q.get(timeout=max(.1,deadline-time.monotonic()))
  if item.frame==frame:return item
  if item.frame>frame:raise RuntimeError('sensor skipped frame')
 raise RuntimeError('sensor timeout')
def bbox_projection(actor,camera):
 vertices=actor.bounding_box.get_world_vertices(actor.get_transform())
 inv=np.asarray(camera.transform.get_inverse_matrix())
 f=camera.width/(2*math.tan(math.radians(100)/2));out=[]
 for v in vertices:
  q=inv@np.array([v.x,v.y,v.z,1])
  if q[0]<=0:return None
  out.append((f*q[1]/q[0]+camera.width/2,-f*q[2]/q[0]+camera.height/2))
 return [min(x for x,y in out),min(y for x,y in out),max(x for x,y in out),max(y for x,y in out)]
def iou(a,b):
 if not b:return 0.
 inter=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
 union=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-inter
 return inter/max(1,union)
def assess(records,truth,camera):
 truth_boxes={k:bbox_projection(v,camera) for k,v in truth.items()}
 evidence={};assigned={}
 for rec in records:
  box=[n*s for n,s in zip(rec['bbox'],[camera.width,camera.height,camera.width,camera.height])]
  vals={k:round(iou(box,b),3) for k,b in truth_boxes.items()}
  hits=[k for k,v in vals.items() if v>=.3]
  evidence[rec['id']]=vals
  if len(hits)==1:assigned.setdefault(hits[0],[]).append(rec['id'])
 expected={'A':'CURRENT','B':'LEFT','C':'RIGHT'}
 checks=[]
 for role,lane in expected.items():
  ids=assigned.get(role,[])
  if len(ids)!=1:
   checks.append({'step':role,'pass':False,'reason':'unique detection assignment unavailable','ids':ids});continue
  rec=next(r for r in records if r['id']==ids[0])
  checks.append({'step':role,'pass':rec['lane_relation']==lane and rec['longitudinal_relation']=='AHEAD',
                 'reason':'expected '+lane+' AHEAD; got '+rec['lane_relation']+' '+rec['longitudinal_relation'],'id':ids[0]})
 eligible=build_follow_candidates(records)
 aid=assigned.get('A',[])
 checks.append({'step':'candidate','pass':len(aid)==1 and eligible==aid,
                'reason':'follow list must contain only the uniquely matched A','actual':eligible,'expected_ids':aid})
 return {'checks':checks,'passed':all(x['pass'] for x in checks),'iou':evidence,'assigned':assigned,'candidates':eligible}
def project_lidar(rgb,lidar):
 pts=np.frombuffer(lidar.raw_data,dtype=np.float32).reshape(-1,4)[:,:3]
 homo=np.column_stack((pts,np.ones(len(pts))));lw=np.asarray(lidar.transform.get_matrix())
 ci=np.asarray(rgb.transform.get_inverse_matrix());xyz=homo@lw.T@ci.T
 front=xyz[:,0]>1.;xyz=xyz[front];f=rgb.width/(2*math.tan(math.radians(100)/2))
 uv=np.column_stack((f*xyz[:,1]/xyz[:,0]+rgb.width/2,-f*xyz[:,2]/xyz[:,0]+rgb.height/2))
 return uv
def save_artifacts(rgb,lidar,radar,records,evaluation):
 image=Image.fromarray(carla_rgb_array(rgb));image.save(OUT/'camera.png')
 ann=image.copy();draw=ImageDraw.Draw(ann)
 colors={'CURRENT':'#39ea84','LEFT':'#ffbe46','RIGHT':'#45baff','UNKNOWN':'#ff6878'}
 for r in records:
  box=tuple(n*s for n,s in zip(r['bbox'],[rgb.width,rgb.height,rgb.width,rgb.height]))
  col=colors[r['lane_relation']];draw.rectangle(box,outline=col,width=3)
  draw.text((box[0],max(0,box[1]-18)),r['id']+' '+r['lane_relation']+' '+str(r['distance_m']),fill=col)
 ann.save(OUT/'detections.png')
 overlay=image.copy();draw=ImageDraw.Draw(overlay);uv=project_lidar(rgb,lidar)
 for r in records:
  x1,y1,x2,y2=[n*s for n,s in zip(r['bbox'],[rgb.width,rgb.height,rgb.width,rgb.height])]
  p=uv[(uv[:,0]>=x1)&(uv[:,0]<=x2)&(uv[:,1]>=y1)&(uv[:,1]<=y2)]
  for x,y in p[::max(1,len(p)//450)]:draw.ellipse((x-1,y-1,x+1,y+1),fill='#38f0a0')
 overlay.save(OUT/'lidar_projection.png')
 (OUT/'lidar.bin').write_bytes(lidar.raw_data)
 (OUT/'radar.bin').write_bytes(radar.raw_data)
 payload={'scenario':'three_cars_same_frame','map':m.name,'frame':rgb.frame,'camera_size':[rgb.width,rgb.height],
          'ego_lane':records[0].get('ego_lane') if records else None,'targets':records,'evaluation':evaluation,
          'sensor_frames':{'camera':rgb.frame,'lidar':lidar.frame,'radar':radar.frame},'sim_time_s':float(rgb.timestamp),'status':'PASS' if evaluation['passed'] else 'FAIL',
          'notes':['truth used only in evaluation','fusion requires three preceding matching frames','no model or control input','experimental fusion not formally validated']}
 (OUT/'result.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2))
 return payload
try:
 settings=world.get_settings();settings.synchronous_mode=True;settings.fixed_delta_seconds=.05
 world.apply_settings(settings)
 spawn,ego_wp,front_wp,left_wp,right_wp=find_start()
 lib=world.get_blueprint_library()
 bp=lib.find('vehicle.tesla.model3')
 ego=spawn_vehicle(bp,ego_wp,'ego')
 truth={'A':spawn_vehicle(bp,front_wp,'front_same_lane'),
        'B':spawn_vehicle(bp,left_wp,'front_left_lane'),
        'C':spawn_vehicle(bp,right_wp,'front_right_lane')}
 for a in [ego,*truth.values()]:a.set_simulate_physics(False)
 qrgb=sensor(ego,'rgb','sensor.camera.rgb',carla.Transform(carla.Location(x=1.5,z=2.2),carla.Rotation(pitch=-8)),{'image_size_x':800,'image_size_y':450,'fov':100,'sensor_tick':0.0})
 qlid=sensor(ego,'lidar','sensor.lidar.ray_cast',carla.Transform(carla.Location(z=2.35)),{'channels':64,'range':80,'rotation_frequency':20,'points_per_second':640000,'upper_fov':10,'lower_fov':-30,'sensor_tick':0.0})
 qrad=sensor(ego,'radar','sensor.other.radar',carla.Transform(carla.Location(x=1.5,z=1.0)),{'horizontal_fov':40,'vertical_fov':10,'range':80,'points_per_second':12000,'sensor_tick':0.0})
 detector=OnnxYoloDetector('/home/tiaozhansai/carla-driving-2B/deliveries/day7.19_group1/models/yolov8n.onnx')
 tracker=SensorObjectTracker();fusion=ShadowSensorFusion()
 history=[];best=-1
 print('READY map',m.name,'ego road/lane',ego_wp.road_id,ego_wp.lane_id,flush=True)
 for n in range(45):
  frame=world.tick();rgb=read_frame(qrgb,frame);lidar=read_frame(qlid,frame);radar=read_frame(qrad,frame)
  objects=tracker.update(frame,detector.detect_measurement(rgb))
  fused=fusion.update(objects,lidar,rgb,radar,ego.get_transform(),100,m)
  byid={x['track_id']:x for x in fused}
  records=[]
  for obj in objects:
   if obj.class_name.lower() not in {'car','truck','bus'}:continue
   f=byid.get(obj.track_id,{})
   good=f.get('status')=='FUSED_UNVALIDATED' and f.get('lidar_unique',0)>=3 and f.get('radar_unique',0)>=1
   if good:
    p=f['position_m'];loc=ego.get_transform().transform(carla.Location(x=p[0],y=-p[1],z=p[2]))
    lane=associate(m,ego.get_location(),loc)
    position=[round(loc.x,3),round(loc.y,3),round(loc.z,3)]
   else:
    lane={'lane_relation':'UNKNOWN','longitudinal_relation':'UNKNOWN','same_lane':None,'delta_s_m':None,'reason':'INSUFFICIENT_SENSOR_ASSOCIATION'}
    position=None
   records.append({'id':obj.track_id,'class':obj.class_name,'confidence':round(obj.confidence,3),
      'bbox':list(obj.bbox_xyxy_norm),'distance_m':round(f['distance_m'],2) if good else None,
      'sensor_status':f.get('status','NO_SENSOR_ASSOCIATION'),'lidar_points':f.get('lidar_unique',0),
      'radar_points':f.get('radar_unique',0),'world_position':position,'ego_lane':ego_wp.lane_id,**lane})
  ev=assess(records,truth,rgb);score=sum(int(x['pass']) for x in ev['checks'])
  history.append({'frame':frame,'detections':len(records),'fused':sum(x['distance_m'] is not None for x in records),'checks_passed':score,'passed':ev['passed']})
  print('FRAME',frame,'detected',len(records),'located',history[-1]['fused'],'checks',score,flush=True)
  if score>best:
   best=score;save_artifacts(rgb,lidar,radar,records,ev)
  if ev['passed']:break
 (OUT/'history.json').write_text(json.dumps(history,ensure_ascii=False,indent=2))
 print('RESULT', 'PASS' if ev['passed'] else 'FAIL','best',best,flush=True)
finally:
 for s in sensors:
  try:s.stop()
  except Exception:pass
 for a in reversed(actors):
  try:a.destroy()
  except Exception:pass
 try:world.apply_settings(original)
 except Exception:pass
