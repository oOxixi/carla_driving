"""Predeclared spatial split. 32ch official-default profile; synchronized fresh sensors."""
import json,hashlib,pathlib,traceback,time,queue,os
import numpy as np,carla
from PIL import Image
from tools.pointcloud_p0.run_matrix import advance,get_sensor,read_frame,weather_for,evaluate,gt_positions
from integration.rgb_detector import OnnxYoloDetector,carla_rgb_array
from integration.object_tracker import SensorObjectTracker
from integration.target_pointcloud_localization import localize
BASE=pathlib.Path('/home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime/pointcloud_adaptive_development_20261117');OUT=BASE/'new_scenes';OUT.mkdir(exist_ok=True)
# Split by disjoint spawn origins, precommitted before running any variant.
plans=[];models=['vehicle.tesla.model3','vehicle.nissan.patrol','vehicle.carlamotors.carlacola'];weathers=['clear','night','rain','fog'];yaws=[0,15,-25,35]
for split,origins,distances in [('dev',[43,76,247],[17,22,27,32,37,42,48,53]),('holdout',[250,257],[18,24,30,36,43,50])]:
 for oi,origin in enumerate(origins):
  for j,dist in enumerate(distances):plans.append({'id':f'{split}_{origin}_{dist}','split':split,'spawn_index':origin,'distance_m':dist,'model':models[(j+oi)%3],'yaw_offset_deg':yaws[(j+2*oi)%4],'weather':weathers[(j+oi)%4],'scene_type':['open','adjacent','partial'][j%3]})
assert len(plans)==36 and len({(x['spawn_index'],x['distance_m']) for x in plans})==36
(BASE/'predeclared_plan.json').write_text(json.dumps(plans,ensure_ascii=False,indent=2)+'\n')
if os.environ.get('ADAPTIVE_EXTRA_HOLDOUT')=='1':
 plans=[{'id':f'holdout_extra_250_{dist}','split':'holdout','spawn_index':250,'distance_m':dist,'model':models[j%3],'yaw_offset_deg':yaws[j%4],'weather':'clear' if j%2==0 else weathers[(j//2)%4],'scene_type':['open','adjacent','partial'][j%3]} for j,dist in enumerate([19,21,25,29,33,39,41,45,47,49,51,55])]
 (BASE/'extra_holdout_plan.json').write_text(json.dumps(plans,ensure_ascii=False,indent=2)+'\n')
client=carla.Client('127.0.0.1',22170);client.set_timeout(30);world=client.get_world();assert world.get_map().name.endswith('Town05_Opt');mp=world.get_map();before=world.get_settings();oldweather=world.get_weather();detector=OnnxYoloDetector('/home/tiaozhansai/carla-driving-2B/deliveries/day7.19_group1/models/yolov8n.onnx');progress=[]
try:
 settings=world.get_settings();settings.synchronous_mode=True;settings.fixed_delta_seconds=.05;world.apply_settings(settings)
 for spec in plans[:int(os.environ.get("ADAPTIVE_PLAN_LIMIT",len(plans)))]:
  actors=[];sensors=[];root=OUT/spec['split']/spec['id'];root.mkdir(parents=True,exist_ok=True)
  try:
   world.set_weather(weather_for(world,spec['weather']));ew=mp.get_waypoint(mp.get_spawn_points()[spec['spawn_index']].location);lw=ew.get_left_lane();targetwp=advance(ew,spec['distance_m']);assert targetwp and lw
   def spawn(wp,model,role,offset=0.,yaw=0.):
    o=wp.transform;t=carla.Transform(carla.Location(x=o.location.x,y=o.location.y,z=o.location.z+.35),carla.Rotation(pitch=o.rotation.pitch,yaw=o.rotation.yaw+yaw,roll=o.rotation.roll));right=t.get_right_vector();t.location.x+=right.x*offset;t.location.y+=right.y*offset;bp=world.get_blueprint_library().find(model);bp.set_attribute('role_name','adaptive_test:'+role);a=world.try_spawn_actor(bp,t)
    if not a:raise RuntimeError('spawn failed '+role)
    actors.append(a);a.set_simulate_physics(False);return a
   ego=spawn(ew,'vehicle.tesla.model3','ego');vehicles={'T':spawn(targetwp,spec['model'],'T',yaw=spec['yaw_offset_deg'])}
   if spec['scene_type']=='adjacent':vehicles['N']=spawn(advance(lw,spec['distance_m']+1),'vehicle.ford.mustang','N')
   if spec['scene_type']=='partial':vehicles['N']=spawn(advance(ew,max(7,spec['distance_m']-8)),'vehicle.audi.a2','N',offset=.95)
   world.tick();qs={};actual={}
   specs=[('rgb','sensor.camera.rgb',carla.Transform(carla.Location(x=1.5,z=2.2),carla.Rotation(pitch=-8)),{'image_size_x':800,'image_size_y':450,'fov':100,'sensor_tick':.05}),('lidar','sensor.lidar.ray_cast',carla.Transform(carla.Location(z=2.35)),{'channels':32,'range':80,'rotation_frequency':20,'points_per_second':224000,'upper_fov':10,'lower_fov':-30,'sensor_tick':.05}),('semantic','sensor.lidar.ray_cast_semantic',carla.Transform(carla.Location(z=2.35)),{'channels':32,'range':80,'rotation_frequency':20,'points_per_second':224000,'upper_fov':10,'lower_fov':-30,'sensor_tick':.05}),('radar','sensor.other.radar',carla.Transform(carla.Location(x=1.5,z=1.0)),{'horizontal_fov':40,'vertical_fov':10,'range':80,'points_per_second':3000,'sensor_tick':.05})]
   for name,bp,tf,attrs in specs:
    sensor,q=get_sensor(world,ego,actors,name,bp,tf,attrs);sensors.append(sensor);qs[name]=q;actual[name]=dict(sensor.attributes)
   buffer={name:{} for name in qs};measurements=None
   for tick in range(40):
    world.tick();time.sleep(.03)
    for name,q in qs.items():
     while True:
      try:item=q.get_nowait();buffer[name][item.frame]=item
      except queue.Empty:break
    common=set.intersection(*(set(z) for z in buffer.values()))
    if tick>=5 and common:
     frame=max(common);measurements={name:items[frame] for name,items in buffer.items()};break
   if measurements is None:raise RuntimeError('NO_COMMON_SENSOR_FRAME '+str({k:list(v)[-10:] for k,v in buffer.items()}))
   assert all(x.frame==frame for x in measurements.values());assert max(x.timestamp for x in measurements.values())-min(x.timestamp for x in measurements.values())<=.001
   rgb,lid,sem,rad=(measurements[k] for k in ('rgb','lidar','semantic','radar'));tracker=SensorObjectTracker();objs=[o for o in tracker.update(frame,detector.detect_measurement(rgb)) if o.class_name.lower() in {'car','truck','bus'}];base=localize(objs,lid,rgb,rad,ego.get_transform());ev=evaluate(base['objects'],base,sem,vehicles,ego,rgb);gt={role:gt_positions(a,ego) for role,a in vehicles.items()};boxes={}
   for role,v in vehicles.items():
    b=v.bounding_box;mat=np.asarray(v.get_transform().get_matrix())@np.asarray(carla.Transform(b.location,b.rotation).get_matrix());boxes[role]={'matrix_world':mat.tolist(),'extent':[b.extent.x,b.extent.y,b.extent.z]}
   for name,v in [('lidar',lid),('semantic_lidar',sem),('radar',rad)]:(root/(name+'.bin')).write_bytes(v.raw_data)
   Image.fromarray(carla_rgb_array(rgb)).save(root/'camera.png');weather=world.get_weather()
   data={'case':spec['id'],'repeat':0,'frame':frame,'split':spec['split'],'plan':spec,'sensors':{'channels':32,'points_per_second':224000,'attributes':actual,'frames':{k:int(v.frame) for k,v in measurements.items()},'timestamps':{k:float(v.timestamp) for k,v in measurements.items()}},'weather_actual':{k:float(getattr(weather,k)) for k in ('cloudiness','precipitation','precipitation_deposits','wetness','fog_density','fog_distance','sun_altitude_angle')},'ego_transform':ego.get_transform().get_matrix(),'lidar_transform':lid.transform.get_matrix(),'camera_transform':rgb.transform.get_matrix(),'radar_transform':rad.transform.get_matrix(),'semantic_transform':sem.transform.get_matrix(),'predictions':base['objects'],'evaluation':ev,'gt_positions_all':gt,'gt_bbox_all':boxes,'status':'COMPLETED'}
   (root/'result.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');progress.append({'id':spec['id'],'status':'COMPLETED','expected':len(vehicles),'matches':len(ev['matched_roles']),'frame':frame});print('DONE',spec['id'],spec['model'],spec['scene_type'],'matches',len(ev['matched_roles']),'/',len(vehicles),flush=True)
  except Exception as ex:
   traceback.print_exc();progress.append({'id':spec['id'],'status':'ERROR','error':repr(ex)});print('ERROR',spec['id'],repr(ex),flush=True)
  finally:
   for sensor in sensors:
    try:sensor.stop()
    except Exception:pass
   for actor in reversed(actors):
    try:actor.destroy()
    except Exception:pass
  (BASE/'collection_progress.json').write_text(json.dumps(progress,ensure_ascii=False,indent=2)+'\n')
finally:world.set_weather(oldweather);world.apply_settings(before)
print('COLLECTION COMPLETE',len(progress),'success',sum(x['status']=='COMPLETED' for x in progress),flush=True)
