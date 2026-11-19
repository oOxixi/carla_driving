import carla,hashlib,json,pathlib
from tools.pointcloud_p0.run_matrix import CASES,setup_waypoints,get_sensor,read_frame,weather_for
P=pathlib.Path('/home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime/lidar_dropoff_abcd_20261117')
c=carla.Client('127.0.0.1',22170);c.set_timeout(30);w=c.get_world();assert w.get_map().name.endswith('Town05_Opt');old=w.get_settings();weather=w.get_weather();actors=[];sensors=[];rows=[]
try:
 settings=w.get_settings();settings.synchronous_mode=True;settings.fixed_delta_seconds=.05;w.apply_settings(settings);w.set_weather(weather_for(w,'clear'));e,targets=setup_waypoints(w.get_map(),next(x for x in CASES if x[0]=='default_far'),0);bp=w.get_blueprint_library().find('vehicle.tesla.model3')
 def spawn(wp,role):
  t=wp.transform;t.location.z+=.35;bp.set_attribute('role_name','dropoff_seed_probe:'+role);a=w.try_spawn_actor(bp,t)
  if not a:raise RuntimeError('spawn failed '+role)
  actors.append(a);a.set_simulate_physics(False);return a
 ego=spawn(e,'ego');cars={r:spawn(p,r) for r,p in targets.items()};queues={}
 for seed in (1,2,3):
  attr={'channels':32,'range':80,'rotation_frequency':20,'points_per_second':224000,'upper_fov':10,'lower_fov':-30,'sensor_tick':0,'noise_seed':seed,'dropoff_general_rate':.45,'dropoff_zero_intensity':.4,'dropoff_intensity_limit':.8}
  sensor,q=get_sensor(w,ego,actors,'lidar','sensor.lidar.ray_cast',carla.Transform(carla.Location(z=2.35)),attr);sensors.append(sensor);queues[seed]=q
 for k in range(8):
  frame=w.tick();samples={seed:read_frame(q,frame) for seed,q in queues.items()};hashes={str(seed):hashlib.sha256(v.raw_data).hexdigest() for seed,v in samples.items()};rows.append({'step':k,'frame':frame,'counts':{str(seed):len(v) for seed,v in samples.items()},'hashes':hashes,'all_equal':len(set(hashes.values()))==1,'horizontal_angle':{str(seed):float(v.horizontal_angle) for seed,v in samples.items()}})
finally:
 for s in sensors:
  try:s.stop()
  except Exception:pass
 for a in reversed(actors):
  try:a.destroy()
  except Exception:pass
 w.set_weather(weather);w.apply_settings(old)
(P/'seed_probe.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2))
