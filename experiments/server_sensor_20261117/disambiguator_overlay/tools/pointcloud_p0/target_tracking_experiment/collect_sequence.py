"""Capture a synchronized static reconstruction on a dedicated CARLA server."""
import json, pathlib, time, queue, hashlib, argparse
from dataclasses import asdict
import carla
from PIL import Image
from integration.rgb_detector import carla_rgb_array
from tools.pointcloud_p0.run_matrix import advance,get_sensor,weather_for,gt_positions
from tools.pointcloud_p0.target_tracking_experiment.tracker import Config

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=pathlib.Path,required=True);ap.add_argument('--frames',type=int,default=30);ap.add_argument('--port',type=int,default=22170);a=ap.parse_args()
 out=a.out;out.mkdir(parents=True,exist_ok=True)
 model=pathlib.Path('/home/tiaozhansai/carla-driving-2B/deliveries/day7.19_group1/models/yolov8n.onnx')
 plan={'case':'extra_250_25 reconstructed static','frames_requested':a.frames,'port':a.port,'radius_m_for_auxiliary_case_only':0.52,'tracker_config':asdict(Config()),'frame_interval_s':.05,'seed_formal_box':[.5026447177,.4004538655,.5558878183,.4826931357],'seed_aux_box':[.4752073586,.343940556,.545599222,.426766634],'seed_iou_min':.3,'detector_model_sha256':hashlib.sha256(model.read_bytes()).hexdigest(),'notes':'All gates are provisional; seed boxes are previous reviewed visual hints, not simulator truth. Semantic and actor data are for frozen-decision audit only. No control.'}
 (out/'predeclared_plan.json').write_text(json.dumps(plan,indent=2)+'\n')
 client=carla.Client('127.0.0.1',a.port);client.set_timeout(90);world=client.get_world()
 if not world.get_map().name.endswith('Town05_Opt'):world=client.load_world('Town05_Opt')
 mp=world.get_map();before=world.get_settings();oldweather=world.get_weather();actors=[];sensors=[]
 try:
  settings=world.get_settings();settings.synchronous_mode=True;settings.fixed_delta_seconds=.05;world.apply_settings(settings);world.set_weather(weather_for(world,'clear'))
  ew=mp.get_waypoint(mp.get_spawn_points()[250].location);targetwp=advance(ew,25)
  def spawn(wp,model,role,offset=0.,yaw=0.):
   o=wp.transform;t=carla.Transform(carla.Location(x=o.location.x,y=o.location.y,z=o.location.z+.35),carla.Rotation(pitch=o.rotation.pitch,yaw=o.rotation.yaw+yaw,roll=o.rotation.roll));right=t.get_right_vector();t.location.x+=right.x*offset;t.location.y+=right.y*offset;bp=world.get_blueprint_library().find(model);bp.set_attribute('role_name','tracking_experiment:'+role);v=world.try_spawn_actor(bp,t)
   if not v:raise RuntimeError('spawn failed '+role)
   actors.append(v);v.set_simulate_physics(False);return v
  ego=spawn(ew,'vehicle.tesla.model3','ego');vehicles={'T':spawn(targetwp,'vehicle.carlamotors.carlacola','T',yaw=-25),'N':spawn(advance(ew,17),'vehicle.audi.a2','N',offset=.95)};world.tick()
  specs=[('rgb','sensor.camera.rgb',carla.Transform(carla.Location(x=1.5,z=2.2),carla.Rotation(pitch=-8)),{'image_size_x':800,'image_size_y':450,'fov':100,'sensor_tick':.05}),('lidar','sensor.lidar.ray_cast',carla.Transform(carla.Location(z=2.35)),{'channels':32,'range':80,'rotation_frequency':20,'points_per_second':224000,'upper_fov':10,'lower_fov':-30,'sensor_tick':.05}),('semantic','sensor.lidar.ray_cast_semantic',carla.Transform(carla.Location(z=2.35)),{'channels':32,'range':80,'rotation_frequency':20,'points_per_second':224000,'upper_fov':10,'lower_fov':-30,'sensor_tick':.05}),('radar','sensor.other.radar',carla.Transform(carla.Location(x=1.5,z=1)),{'horizontal_fov':40,'vertical_fov':10,'range':80,'points_per_second':3000,'sensor_tick':.05})]
  qs={};actual={}
  for name,bp,tf,attrs in specs:
   sensor,q=get_sensor(world,ego,actors,name,bp,tf,attrs);sensors.append(sensor);qs[name]=q;actual[name]=dict(sensor.attributes)
  buffers={k:{} for k in qs};saved=[]
  for tick in range(a.frames+35):
   world.tick();time.sleep(.04)
   for name,q in qs.items():
    while True:
     try:item=q.get_nowait();buffers[name][item.frame]=item
     except queue.Empty:break
   common=sorted(set.intersection(*(set(z) for z in buffers.values())))
   for frame in common:
    m={name:items.pop(frame) for name,items in buffers.items()}
    if tick<5:continue
    if saved and frame!=saved[-1]+1:raise RuntimeError('nonconsecutive synchronized frames')
    if max(x.timestamp for x in m.values())-min(x.timestamp for x in m.values())>.001:raise RuntimeError('sensor timestamp mismatch')
    rgb,lid,sem,rad=(m[k] for k in ('rgb','lidar','semantic','radar'));root=out/'frames'/str(frame);root.mkdir(parents=True,exist_ok=True);oracle=out/'oracle'/str(frame);oracle.mkdir(parents=True,exist_ok=True)
    for name,v in [('lidar',lid),('radar',rad)]:(root/(name+'.bin')).write_bytes(v.raw_data)
    (oracle/'semantic_lidar.bin').write_bytes(sem.raw_data);Image.fromarray(carla_rgb_array(rgb)).save(root/'camera.png')
    data={'frame':frame,'sensors':{'attributes':actual,'frames':{k:int(v.frame) for k,v in m.items()},'timestamps':{k:float(v.timestamp) for k,v in m.items()}},'ego_transform':ego.get_transform().get_matrix(),'lidar_transform':lid.transform.get_matrix(),'camera_transform':rgb.transform.get_matrix(),'radar_transform':rad.transform.get_matrix(),'predictions':[]}
    (root/'result.json').write_text(json.dumps(data)+'\n')
    truth={'semantic_transform':sem.transform.get_matrix(),'actor_ids':{k:v.id for k,v in vehicles.items()},'gt_positions_all':{k:gt_positions(v,ego) for k,v in vehicles.items()}}
    (oracle/'truth.json').write_text(json.dumps(truth)+'\n');saved.append(frame)
    print('SAVED',frame,flush=True)
    if len(saved)>=a.frames:break
   if len(saved)>=a.frames:break
  if len(saved)!=a.frames:raise RuntimeError('insufficient common frames '+str(len(saved)))
  (out/'capture_manifest.json').write_text(json.dumps({'frames':saved,'count':len(saved),'map':mp.name,'sensor_attributes':actual},indent=2)+'\n')
 finally:
  for s in sensors:
   try:s.stop()
   except Exception:pass
  for v in reversed(actors):
   try:v.destroy()
   except Exception:pass
  world.set_weather(oldweather);world.apply_settings(before)
if __name__=='__main__':main()
