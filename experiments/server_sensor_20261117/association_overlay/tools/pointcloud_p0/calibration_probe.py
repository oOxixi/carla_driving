"""New independent semantic-camera probe, no detector/localizer invocation."""
import json,math,pathlib
import numpy as np,carla
from PIL import Image,ImageDraw
from tools.pointcloud_p0.run_matrix import setup_waypoints,CASES,get_sensor,read_frame,SEM_DTYPE
OUT=pathlib.Path('/home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime/pointcloud_p0_diagnosis_20261117/calibration_probe');OUT.mkdir(parents=True,exist_ok=True)
client=carla.Client('127.0.0.1',22170);client.set_timeout(30);world=client.get_world();mp=world.get_map();prior=world.get_settings();setting=world.get_settings();setting.synchronous_mode=True;setting.fixed_delta_seconds=.05;world.apply_settings(setting)
results=[]
try:
 for kind in ('near','middle','far'):
  case=next(c for c in CASES if c[0]==kind);ew,targets=setup_waypoints(mp,case,0);actors=[];sensors=[];vehicles={}
  try:
   bp=world.get_blueprint_library().find('vehicle.tesla.model3')
   def spawn(w):
    t=w.transform;t.location.z+=.35;a=world.try_spawn_actor(bp,t)
    if not a:raise RuntimeError('cannot spawn probe vehicle')
    actors.append(a);a.set_simulate_physics(False);return a
   ego=spawn(ew)
   for role,w in targets.items():vehicles[role]=spawn(w)
   cam=carla.Transform(carla.Location(x=1.5,z=2.2),carla.Rotation(pitch=-8));lid=carla.Transform(carla.Location(z=2.35));rad=carla.Transform(carla.Location(x=1.5,z=1.0));cattr={'image_size_x':800,'image_size_y':450,'fov':100,'sensor_tick':0};lattr={'channels':64,'range':80,'rotation_frequency':20,'points_per_second':640000,'upper_fov':10,'lower_fov':-30,'sensor_tick':0}
   qs={}
   for name,bpname,tf,attrs in [('rgb','sensor.camera.rgb',cam,cattr),('seg','sensor.camera.semantic_segmentation',cam,cattr),('sem','sensor.lidar.ray_cast_semantic',lid,lattr),('lidar','sensor.lidar.ray_cast',lid,lattr),('radar','sensor.other.radar',rad,{'horizontal_fov':40,'vertical_fov':10,'range':80,'points_per_second':12000,'sensor_tick':0})]:
    a,q=get_sensor(world,ego,actors,name,bpname,tf,attrs);sensors.append(a);qs[name]=q
   for _ in range(5):
    frame=world.tick();data={name:read_frame(q,frame) for name,q in qs.items()}
   assert all(x.frame==frame for x in data.values())
   ts={name:float(x.timestamp) for name,x in data.items()}
   rgb,seg,sem,radar=data['rgb'],data['seg'],data['sem'],data['radar']
   mask=np.frombuffer(seg.raw_data,dtype=np.uint8).reshape(450,800,4)[:,:,2]==14
   image=np.frombuffer(rgb.raw_data,dtype=np.uint8).reshape(450,800,4)[:,:,[2,1,0]]
   pic=Image.fromarray(image.copy());draw=ImageDraw.Draw(pic)
   cm=np.array(rgb.transform.get_matrix());ego_m=np.array(ego.get_transform().get_matrix());sm=np.array(sem.transform.get_matrix());rm=np.array(radar.transform.get_matrix());invcm=np.linalg.inv(cm);f=800/(2*math.tan(math.radians(50)))
   def project(xyz,tf):
    p=np.c_[xyz,np.ones(len(xyz))]@tf.T@invcm.T;return np.column_stack((f*p[:,1]/np.maximum(p[:,0],1e-9)+400,-f*p[:,2]/np.maximum(p[:,0],1e-9)+225)),p[:,0]
   def matches(uv,depth,radius):
    out=[]
    for (u,v),z in zip(uv,depth):
     x=int(round(u));y=int(round(v))
     if z<=1 or not (0<=x<800 and 0<=y<450):continue
     out.append(bool(mask[max(0,y-radius):min(450,y+radius+1),max(0,x-radius):min(800,x+radius+1)].any()))
    return out
   raw=np.frombuffer(sem.raw_data,dtype=SEM_DTYPE);xyz=np.column_stack((raw['x'],raw['y'],raw['z']));iscar=np.isin(raw['id'],[v.id for v in vehicles.values()]);uv,z=project(xyz[iscar],sm);exact=matches(uv,z,0);near=matches(uv,z,2)
   for (u,v),depth in zip(uv,z):
    if depth>1 and 0<=u<800 and 0<=v<450:draw.ellipse((u-1,v-1,u+1,v+1),fill=(0,255,0))
   rd=np.frombuffer(radar.raw_data,dtype=np.float32).reshape(-1,4);azi=rd[:,1];alt=rd[:,2];dep=rd[:,3];xyzr=np.column_stack((dep*np.cos(alt)*np.cos(azi),dep*np.cos(alt)*np.sin(azi),dep*np.sin(alt)));wr=np.c_[xyzr,np.ones(len(xyzr))]@rm.T
   hits=np.zeros(len(rd),dtype=bool)
   for vehicle in vehicles.values():
    b=vehicle.bounding_box;bt=carla.Transform(b.location,b.rotation);bm=np.asarray(vehicle.get_transform().get_matrix())@np.asarray(bt.get_matrix());local=wr@np.linalg.inv(bm).T;hits|=np.all(np.abs(local[:,:3])<=np.array([b.extent.x,b.extent.y,b.extent.z])+.2,axis=1)
   ur,zr=project(xyzr[hits],rm);r_exact=matches(ur,zr,0);r_near=matches(ur,zr,2)
   for (u,v),depth in zip(ur,zr):
    if depth>1 and 0<=u<800 and 0<=v<450:draw.ellipse((u-1,v-1,u+1,v+1),fill=(255,0,0))
   pic.save(OUT/(kind+'_overlay.png'));Image.fromarray(np.uint8(mask)*255).save(OUT/(kind+'_semantic_car_mask.png'))
   def stat(a):return {'n':len(a),'matches':sum(a),'ratio':sum(a)/len(a) if a else None}
   results.append({'case':kind,'frame':frame,'timestamps':ts,'max_timestamp_difference_s':max(ts.values())-min(ts.values()),'camera_intrinsics_runtime':{'width':rgb.width,'height':rgb.height,'fov':rgb.fov},'lidar_actor_points_to_semantic_camera':{'exact_pixel':stat(exact),'within_2px':stat(near)},'radar_points_in_expanded_actor_bbox_to_semantic_camera':{'exact_pixel':stat(r_exact),'within_2px':stat(r_near)},'warning':'Sensors have different mounting positions; visibility, occlusion, lidar ray sampling and rasterization can yield mismatches even with correct calibration. Bounding-box radar labels are approximate; this is a geometric sanity check, not an independent calibration certificate.'})
  finally:
   for s in sensors:
    try:s.stop()
    except Exception:pass
   for a in reversed(actors):
    try:a.destroy()
    except Exception:pass
finally:world.apply_settings(prior)
(OUT/'result.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n');print(json.dumps(results,ensure_ascii=False,indent=2))
