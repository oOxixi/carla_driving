"""Reconstruct static scenes for supplemental instance-visibility evidence; not original frame."""
import collections,json,math,os,pathlib,queue,time,traceback
import carla,numpy as np
from PIL import Image
from tools.pointcloud_p0.run_matrix import advance,get_sensor,weather_for,bbox_projection
P=pathlib.Path('/home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime');SRC=P/'pointcloud_adaptive_development_20261117/new_scenes/holdout';OUT=P/'yolo_unmatched25_diagnosis_20261117';(OUT/'reconstructed').mkdir(exist_ok=True);excluded={'holdout_257_36','holdout_257_43','holdout_257_50'};files=[x for x in sorted(SRC.glob('*/result.json')) if x.parent.name not in excluded];case_filter=os.environ.get('VIS_CASE');files=[f for f in files if not case_filter or f.parent.name==case_filter];limit=int(os.environ.get('VIS_PILOT_LIMIT',len(files)));client=carla.Client('127.0.0.1',int(os.environ.get('VIS_CARLA_PORT','22190')));client.set_timeout(30);world=client.get_world();assert world.get_map().name.endswith('Town05_Opt');assert not [a for a in world.get_actors() if a.type_id.startswith('vehicle.')];old=world.get_settings();weather=world.get_weather();results=[]
try:
 s=world.get_settings();s.synchronous_mode=True;s.fixed_delta_seconds=.05;world.apply_settings(s)
 for f in files[:limit]:
  d=json.loads(f.read_text());plan=d['plan'];actors=[];sensors=[]
  try:
   world.set_weather(weather_for(world,plan['weather']));mp=world.get_map();ew=mp.get_waypoint(mp.get_spawn_points()[plan['spawn_index']].location);lw=ew.get_left_lane()
   def spawn(wp,model,role,offset=0.,yaw=0.):
    o=wp.transform;t=carla.Transform(carla.Location(x=o.location.x,y=o.location.y,z=o.location.z+.35),carla.Rotation(pitch=o.rotation.pitch,yaw=o.rotation.yaw+yaw,roll=o.rotation.roll));right=t.get_right_vector();t.location.x+=right.x*offset;t.location.y+=right.y*offset;bp=world.get_blueprint_library().find(model);bp.set_attribute('role_name','visibility_audit:'+role);a=world.try_spawn_actor(bp,t)
    if not a:raise RuntimeError('spawn failed '+role)
    actors.append(a);a.set_simulate_physics(False);return a
   def create(role):
    if role=='T':return spawn(advance(ew,plan['distance_m']),plan['model'],'T',yaw=plan['yaw_offset_deg'])
    if plan['scene_type']=='adjacent':return spawn(advance(lw,plan['distance_m']+1),'vehicle.ford.mustang','N')
    return spawn(advance(ew,max(7,plan['distance_m']-8)),'vehicle.audi.a2','N',offset=.95)
   ego=spawn(ew,'vehicle.tesla.model3','ego');cars={role:create(role) for role in d['evaluation']['expected_roles']};world.tick();qs={};camera=carla.Transform(carla.Location(x=1.5,z=2.2),carla.Rotation(pitch=-8));attrs={'image_size_x':800,'image_size_y':450,'fov':100,'sensor_tick':.05}
   for name,bp in [('rgb','sensor.camera.rgb'),('instance','sensor.camera.instance_segmentation')]:
    sensor,q=get_sensor(world,ego,actors,name,bp,camera,attrs);sensors.append(sensor);qs[name]=q
   def get_pair():
    after=world.get_snapshot().frame;buf={k:{} for k in qs}
    for tick in range(40):
     world.tick();time.sleep(.03)
     for name,q in qs.items():
      while True:
       try:m=q.get_nowait();buf[name][m.frame]=m
       except queue.Empty:break
     common=[x for x in set.intersection(*(set(v) for v in buf.values())) if x>after+2]
     if tick>=5 and common:
      frame=max(common);pair={k:v[frame] for k,v in buf.items()};assert max(x.timestamp for x in pair.values())-min(x.timestamp for x in pair.values())<=.001;return pair
    raise RuntimeError('NO_SYNC_CAMERA_FRAME')
   def pixels(instance,actor):
    arr=np.frombuffer(instance.raw_data,dtype=np.uint8).reshape(450,800,4);ids=arr[:,:,0].astype(np.uint32)*256+arr[:,:,1].astype(np.uint32);mask=(ids==(actor.id%65536))&np.isin(arr[:,:,2],[14,15,16]);yy,xx=np.where(mask);return {'visible_pixels':int(len(xx)),'visible_bbox_px':[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)] if len(xx) else None,'actor_id':actor.id,'semantic_tags':{int(z):int(np.count_nonzero(arr[:,:,2][mask]==z)) for z in np.unique(arr[:,:,2][mask])}}
   full=get_pair();first={role:pixels(full['instance'],a) for role,a in cars.items()};original=np.asarray(Image.open(f.parent/'camera.png').convert('RGB')).astype(np.int16);now=np.frombuffer(full['rgb'].raw_data,dtype=np.uint8).reshape(450,800,4)[:,:,[2,1,0]].astype(np.int16);mae=float(np.mean(np.abs(original-now)));errs={role:float(np.max(np.abs(np.asarray(bbox_projection(a,full['rgb']))-np.asarray(d['evaluation']['gt_projected_boxes_px'][role])))) for role,a in cars.items()};assert max(errs.values())<.08,(d['case'],errs)
   Image.fromarray(now.astype(np.uint8)).save(OUT/'reconstructed'/f"{d['case']}_rgb.png");(OUT/'reconstructed'/f"{d['case']}_full_instance.bgra").write_bytes(full['instance'].raw_data)
   for a in cars.values():a.destroy()
   world.tick();solo={}
   for role in d['evaluation']['expected_roles']:
    a=create(role);world.tick();pair=get_pair();solo[role]=pixels(pair['instance'],a);solo[role]['frame']=pair['instance'].frame;a.destroy();world.tick()
   row={'case':d['case'],'reconstructed_frame':full['rgb'].frame,'rgb_original_vs_reconstruction_mae_0_255':mae,'box_projection_max_delta_px':errs,'full_visible':first,'solo_visible':solo,'visibility_ratio':{role:(first[role]['visible_pixels']/solo[role]['visible_pixels'] if solo[role]['visible_pixels'] else None) for role in first},'source_note':'newly reconstructed static scene with instance camera; not original-image instance segmentation'};results.append(row);(OUT/'visibility_cases').mkdir(exist_ok=True);(OUT/'visibility_cases'/f"{d['case']}.json").write_text(json.dumps(row,ensure_ascii=False,indent=2)+'\n');print('DONE',d['case'],'pixels',[(role,first[role]['visible_pixels'],solo[role]['visible_pixels']) for role in first],'mae',round(mae,2),flush=True)
  except Exception as e:traceback.print_exc();results.append({'case':d['case'],'error':repr(e)});print('ERROR',d['case'],repr(e),flush=True)
  finally:
   for a in sensors:
    try:a.stop()
    except Exception:pass
   for a in reversed(actors):
    try:
     if a.is_alive:a.destroy()
    except Exception:pass
finally:world.set_weather(weather);world.apply_settings(old)
name='visibility_pilot.json' if limit<len(files) else 'visibility_reconstruction.json';(OUT/name).write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n');print('COMPLETE',len(results),'errors',sum('error' in x for x in results),flush=True)
