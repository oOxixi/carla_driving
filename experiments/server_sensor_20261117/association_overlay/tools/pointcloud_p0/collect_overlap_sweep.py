"""20 new stationary CARLA cases; five explicitly injected duplicate detections."""
import copy,json,math,pathlib,traceback
from dataclasses import replace
import carla,numpy as np
from PIL import Image,ImageDraw
from integration.rgb_detector import OnnxYoloDetector,carla_rgb_array
from integration.object_tracker import SensorObjectTracker
from integration.target_pointcloud_localization import localize
from tools.pointcloud_p0.run_matrix import setup_waypoints,advance,CASES,weather_for,get_sensor,read_frame,evaluate,gt_positions
BASE=pathlib.Path('/home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime');OUT=BASE/'pointcloud_overlap_sweep_raw_20261117';OUT.mkdir(parents=True,exist_ok=True)
client=carla.Client('127.0.0.1',22170);client.set_timeout(30);world=client.get_world();mp=world.get_map();assert mp.name.endswith('Town05_Opt');before=world.get_settings();old_weather=world.get_weather();detector=OnnxYoloDetector('/home/tiaozhansai/carla-driving-2B/deliveries/day7.19_group1/models/yolov8n.onnx');summary=[]
try:
 s=world.get_settings();s.synchronous_mode=True;s.fixed_delta_seconds=.05;world.apply_settings(s)
 for case in ['occlusion_new']:
  for n in range(10):
   directory=OUT/case/str(n);directory.mkdir(parents=True,exist_ok=True);actors=[];sensors=[]
   try:
    weather='night' if case=='night_new' else 'clear';world.set_weather(weather_for(world,weather))
    ew,_=setup_waypoints(mp,CASES[1],0);lw=ew.get_left_lane()
    def spawn(w,kind='vehicle.tesla.model3',lateral=0,yaw=0,role=''):
     if w is None:raise RuntimeError('waypoint unavailable')
     old=w.transform;t=carla.Transform(carla.Location(x=old.location.x,y=old.location.y,z=old.location.z+.35),carla.Rotation(pitch=old.rotation.pitch,yaw=old.rotation.yaw,roll=old.rotation.roll));right=t.get_right_vector();t.location.x+=right.x*lateral;t.location.y+=right.y*lateral;t.rotation.yaw+=yaw
     bp=world.get_blueprint_library().find(kind);bp.set_attribute('role_name','overlap20:'+role);a=world.try_spawn_actor(bp,t)
     if not a:raise RuntimeError('spawn failed '+role)
     actors.append(a);a.set_simulate_physics(False);return a
    ego=spawn(ew,yaw=(-3,-1.5,0,1.5,3)[n%5],role='ego')
    if case=='duplicate':
     dist=12+n*3;spec=[('A',advance(ew,dist),'vehicle.tesla.model3',0),('B',advance(lw,dist+2),'vehicle.audi.a2',.35)]
    elif case=='occlusion_new':
     dist=16+(n%3)*2;spec=[('A',advance(ew,dist),'vehicle.tesla.model3',(1.0,1.2,1.4,1.6,1.8,2.0,2.2,2.4,2.6,2.8)[n]),('B',advance(ew,dist+8),'vehicle.audi.a2',0)]
    elif case=='adjacent':
     dist=14+n*3;spec=[('A',advance(ew,dist),'vehicle.tesla.model3',.15),('B',advance(lw,dist+1),'vehicle.ford.mustang',.45)]
    else:
     dist=12+n*6;spec=[('A',advance(ew,dist),'vehicle.tesla.model3',0),('B',advance(lw,dist+2),'vehicle.audi.a2',.4)]
    vehicles={name:spawn(w,kind,lateral=offset,role=name) for name,w,kind,offset in spec}
    tcam=carla.Transform(carla.Location(x=1.5,z=2.2),carla.Rotation(pitch=-8));tlid=carla.Transform(carla.Location(z=2.35));trad=carla.Transform(carla.Location(x=1.5,z=1.0));channels=64 if n%2==0 else 32;pps=640000 if channels==64 else 224000
    attrs={'channels':channels,'range':80,'rotation_frequency':20,'points_per_second':pps,'upper_fov':10,'lower_fov':-30,'sensor_tick':0};qs={}
    for name,bp,tf,kw in [('rgb','sensor.camera.rgb',tcam,{'image_size_x':800,'image_size_y':450,'fov':100,'sensor_tick':0}),('lidar','sensor.lidar.ray_cast',tlid,attrs),('semantic','sensor.lidar.ray_cast_semantic',tlid,attrs),('radar','sensor.other.radar',trad,{'horizontal_fov':40,'vertical_fov':10,'range':80,'points_per_second':12000,'sensor_tick':0})]:
     sensor,q=get_sensor(world,ego,actors,name,bp,tf,kw);sensors.append(sensor);qs[name]=q
    for _ in range(4):
     frame=world.tick();data={k:read_frame(q,frame) for k,q in qs.items()}
    rgb,lid,sem,rad=(data[k] for k in ('rgb','lidar','semantic','radar'));assert all(z.frame==frame for z in data.values());assert max(z.timestamp for z in data.values())-min(z.timestamp for z in data.values())<=.001
    tracker=SensorObjectTracker();objs=list(tracker.update(frame,detector.detect_measurement(rgb)));objs=[o for o in objs if o.class_name.lower() in {'car','truck','bus'}];original=[{'id':o.track_id,'class':o.class_name,'confidence':o.confidence,'bbox':list(o.bbox_xyxy_norm)} for o in objs];injected=None
    if case=='duplicate' and objs:
     ref=max(objs,key=lambda o:o.confidence);x1,y1,x2,y2=ref.bbox_xyxy_norm;shift=.0003;dup=replace(ref,track_id='INJECTED-1',class_name='truck' if ref.class_name.lower()!='truck' else 'car',confidence=ref.confidence*.8,bbox_xyxy_norm=(x1+shift,y1,x2+shift,y2));objs.append(dup);injected={'derived_from_detection':ref.track_id,'id':dup.track_id,'label':'synthetic duplicate of real YOLO box; not a second YOLO prediction','shift_fraction':shift}
    loc=localize(objs,lid,rgb,rad,ego.get_transform());evaluation=evaluate(loc['objects'],loc,sem,vehicles,ego,rgb);gt={role:gt_positions(a,ego) for role,a in vehicles.items()}
    for name,measurement in [('lidar',lid),('semantic_lidar',sem),('radar',rad)]:(directory/(name+'.bin')).write_bytes(measurement.raw_data)
    img=Image.fromarray(carla_rgb_array(rgb));img.save(directory/'camera.png');draw=ImageDraw.Draw(img)
    for o in objs:
     b=[x*s for x,s in zip(o.bbox_xyxy_norm,[800,450,800,450])];draw.rectangle(b,outline='cyan' if o.track_id!='INJECTED-1' else 'magenta',width=2);draw.text((b[0],max(0,b[1]-12)),o.track_id,fill='white')
    img.save(directory/'detections.png')
    result={'case':case,'repeat':n,'frame':frame,'sensors':{'channels':channels,'points_per_second':pps,'rgb_frame':rgb.frame,'lidar_frame':lid.frame,'semantic_frame':sem.frame,'radar_frame':rad.frame,'timestamps':{name:float(v.timestamp) for name,v in data.items()}},'weather':weather,'yaw_offset_degrees':(-3,-1.5,0,1.5,3)[n%5],'source_distance_m':dist,'ego_transform':ego.get_transform().get_matrix(),'lidar_transform':lid.transform.get_matrix(),'camera_transform':rgb.transform.get_matrix(),'radar_transform':rad.transform.get_matrix(),'semantic_transform':sem.transform.get_matrix(),'predictions':loc['objects'],'original_yolo_predictions':original,'injected_duplicate':injected,'evaluation':evaluation,'gt_positions_all':gt,'status':'COMPLETED'}
    (directory/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');summary.append({'case':case,'repeat':n,'status':'COMPLETED','frame':frame,'detections':len(original),'injected':bool(injected)});print('DONE',case,n,'detections',len(original),'injected',bool(injected),flush=True)
   except Exception as e:
    traceback.print_exc();summary.append({'case':case,'repeat':n,'status':'ERROR','error':repr(e)});print('ERROR',case,n,repr(e),flush=True)
   finally:
    for sensor in sensors:
     try:sensor.stop()
     except Exception:pass
    for actor in reversed(actors):
     try:actor.destroy()
     except Exception:pass
   (OUT/'progress.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
finally:world.set_weather(old_weather);world.apply_settings(before)
print('COMPLETE',len(summary),flush=True)
