"""Capture C1 on a dedicated CARLA port, with per-frame truth isolated."""
import argparse,hashlib,json,pathlib,queue,time
from dataclasses import asdict
import carla,numpy as np
from PIL import Image
from integration.rgb_detector import carla_rgb_array
from tools.pointcloud_p0.run_matrix import advance,get_sensor,weather_for
from tools.pointcloud_p0.unified_tracking_experiment.tracker import Config

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=pathlib.Path,required=True);ap.add_argument('--port',type=int,default=22170);a=ap.parse_args();out=a.root;out.mkdir(parents=True,exist_ok=True)
 model=pathlib.Path('/home/tiaozhansai/carla-driving-2B/deliveries/day7.19_group1/models/yolov8n.onnx')
 plan={'experiment':'C1','map':'Town05_Opt','spawn_index':18,'frames':60,'dt_s':.05,'target_speeds_mps':{'ego':7.,'front':5.,'adjacent':6.},'initial_distances_m':{'front':22.,'adjacent':27.},'motion':'scripted constant-velocity kinematic transforms on straight lane; not physics-driving','formal_threshold':.35,'aux_threshold':.20,'nms_iou':.45,'tracker':asdict(Config()),'seed_boxes':'none','pointcloud':'original scheme C R0; no sample-specific .52','overlap_rule':'cross-channel overlapping boxes unresolved unless two independent selected point clusters separated by >=1m 3D and >=.5m radial gap; provisional','gates_and_confirmation':'uncalibrated offline research values','C1_gate':'do not claim pass or advance C2 unless truth-audited identity errors absent and natural channel migration is observable; quality and coverage also need review','model_sha256':hashlib.sha256(model.read_bytes()).hexdigest()}
 (out/'predeclared_plan.json').write_text(json.dumps(plan,indent=2)+'\n')
 c=carla.Client('127.0.0.1',a.port);c.set_timeout(90);w=c.get_world()
 if not w.get_map().name.endswith('Town05_Opt'):raise RuntimeError('only use isolated Town05_Opt instance')
 mp=w.get_map();before=w.get_settings();oldweather=w.get_weather();actors=[];sensors=[]
 try:
  settings=w.get_settings();settings.synchronous_mode=True;settings.fixed_delta_seconds=.05;w.apply_settings(settings);w.set_weather(weather_for(w,'clear'));ew=mp.get_waypoint(mp.get_spawn_points()[18].location);lw=ew.get_left_lane();assert lw and str(lw.lane_type)=='Driving';wp={'ego':ew,'front':advance(ew,22),'adjacent':advance(lw,27)};assert all(wp.values())
  def spawn(key,model):
   t=wp[key].transform;t.location.z+=.35;bp=w.get_blueprint_library().find(model);bp.set_attribute('role_name','unified_c1:'+key);v=w.try_spawn_actor(bp,t)
   if not v:raise RuntimeError('spawn failed '+key)
   actors.append(v);v.set_simulate_physics(False);return v
  ego=spawn('ego','vehicle.tesla.model3');vehicles={'front':spawn('front','vehicle.audi.a2'),'adjacent':spawn('adjacent','vehicle.tesla.model3')};allv={'ego':ego,**vehicles};w.tick();base={k:v.get_transform() for k,v in allv.items()}
  specs=[('rgb','sensor.camera.rgb',carla.Transform(carla.Location(x=1.5,z=2.2),carla.Rotation(pitch=-8)),{'image_size_x':800,'image_size_y':450,'fov':100,'sensor_tick':.05}),('lidar','sensor.lidar.ray_cast',carla.Transform(carla.Location(z=2.35)),{'channels':32,'range':80,'rotation_frequency':20,'points_per_second':224000,'upper_fov':10,'lower_fov':-30,'sensor_tick':.05}),('semantic','sensor.lidar.ray_cast_semantic',carla.Transform(carla.Location(z=2.35)),{'channels':32,'range':80,'rotation_frequency':20,'points_per_second':224000,'upper_fov':10,'lower_fov':-30,'sensor_tick':.05}),('radar','sensor.other.radar',carla.Transform(carla.Location(x=1.5,z=1)),{'horizontal_fov':40,'vertical_fov':10,'range':80,'points_per_second':3000,'sensor_tick':.05})]
  qs={};actual={}
  for name,bp,tf,attrs in specs:
   s,q=get_sensor(w,ego,actors,name,bp,tf,attrs);sensors.append(s);qs[name]=q;actual[name]=dict(s.attributes)
  bufs={k:{} for k in qs};snapshots={};saved=[]
  for tick in range(100):
   # Warm up static for ten ticks; thereafter advance all actors before each synchronized tick.
   step=max(0,tick-9)
   for role,v in allv.items():
    origin=base[role];f=origin.get_forward_vector();distance=plan['target_speeds_mps'][role]*step*.05;t=carla.Transform(carla.Location(x=origin.location.x+f.x*distance,y=origin.location.y+f.y*distance,z=origin.location.z),origin.rotation);v.set_transform(t)
   frame=w.tick();snapshot=w.get_snapshot();assert snapshot.frame==frame
   truth={}
   for role,v in vehicles.items():
    tr=snapshot.find(v.id).get_transform();corners=v.bounding_box.get_world_vertices(tr);verts=[[p.x,p.y,p.z] for p in corners];truth[role]={'actor_id':v.id,'vertices_world':verts,'center_world':np.mean(verts,axis=0).tolist()}
   snapshots[frame]={'ego_transform':snapshot.find(ego.id).get_transform().get_matrix(),'actors':truth,'motion_step':step}
   time.sleep(.04)
   for name,q in qs.items():
    while True:
     try:x=q.get_nowait();bufs[name][x.frame]=x
     except queue.Empty:break
   for fid in sorted(set.intersection(*(set(b) for b in bufs.values()))):
    m={k:b.pop(fid) for k,b in bufs.items()};st=snapshots.pop(fid,None)
    if not st or st['motion_step']<1:continue
    if saved and fid!=saved[-1]+1:raise RuntimeError('nonconsecutive frames')
    if max(x.timestamp for x in m.values())-min(x.timestamp for x in m.values())>.001:raise RuntimeError('sensor timestamp mismatch')
    rgb,lid,sem,rad=(m[k] for k in ('rgb','lidar','semantic','radar'));fp=out/'frames'/str(fid);op=out/'oracle'/str(fid);fp.mkdir(parents=True,exist_ok=True);op.mkdir(parents=True,exist_ok=True)
    Image.fromarray(carla_rgb_array(rgb)).save(fp/'camera.png')
    for name,v in [('lidar',lid),('radar',rad)]:(fp/(name+'.bin')).write_bytes(v.raw_data)
    (op/'semantic_lidar.bin').write_bytes(sem.raw_data)
    data={'frame':fid,'sensors':{'attributes':actual,'frames':{k:int(v.frame) for k,v in m.items()},'timestamps':{k:float(v.timestamp) for k,v in m.items()}},'ego_transform':st['ego_transform'],'lidar_transform':lid.transform.get_matrix(),'camera_transform':rgb.transform.get_matrix(),'radar_transform':rad.transform.get_matrix(),'predictions':[]}
    truth={'actors':st['actors'],'semantic_transform':sem.transform.get_matrix(),'motion_step':st['motion_step']}
    (fp/'result.json').write_text(json.dumps(data)+'\n');(op/'truth.json').write_text(json.dumps(truth)+'\n');saved.append(fid);print('SAVED',fid,flush=True)
    if len(saved)>=plan['frames']:break
   if len(saved)>=plan['frames']:break
  if len(saved)!=plan['frames']:raise RuntimeError('insufficient frames '+str(len(saved)))
  (out/'capture_manifest.json').write_text(json.dumps({'frames':saved,'count':len(saved),'sensor_attributes':actual},indent=2)+'\n')
 finally:
  for s in sensors:
   try:s.stop()
   except Exception:pass
  for v in reversed(actors):
   try:v.destroy()
   except Exception:pass
  w.set_weather(oldweather);w.apply_settings(before)
if __name__=='__main__':main()
