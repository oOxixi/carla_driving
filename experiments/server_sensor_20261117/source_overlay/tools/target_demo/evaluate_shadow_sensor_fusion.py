"""Side-by-side actual control and evaluation-only three-sensor fusion."""
import copy,dataclasses,json,os
from pathlib import Path
from integration import carla_runner
from integration.carla_perception import CarlaPerceptionBridge
from integration.second_group_runtime import CanonicalRuntimeBridge
from integration.experimental_sensor_fusion import ShadowSensorFusion
from qwen_service.client import QwenServiceClient
from tools.target_demo.capture_command_diagnostics import matrix,actor_truth

fusion=ShadowSensorFusion();records=[];commands=[];errors=[];shadow_by_frame={};augmented_requests=[];orig_acquire=CarlaPerceptionBridge.acquire;orig_submit=CanonicalRuntimeBridge.submit

def acquire(self,*args,**kwargs):
 sample=orig_acquire(self,*args,**kwargs)
 try:
  outputs=fusion.update(sample.frame.detected_objects,sample.lidar,sample.rgb,sample.radar,self._ego.get_transform(),float(self._sensors.actors['rgb_front'].attributes.get('fov',100)),self._map)
  shadow_by_frame[sample.frame.frame]=copy.deepcopy(outputs)
  # All actor truth is fetched only after the shadow calculation and recorded separately.
  truth=actor_truth(self); lanes={}
  for actor in self._world.get_actors().filter('vehicle.*'):
   role=actor.attributes.get('role_name','')
   if role.startswith('acceptance84:'):
    wp=self._map.get_waypoint(actor.get_location(),project_to_road=True)
    if wp:lanes[role]={'road_id':wp.road_id,'lane_id':wp.lane_id}
  records.append({'frame':sample.frame.frame,'world_frame':self._world.get_snapshot().frame,'scene':dataclasses.asdict(sample.frame),'shadow':outputs,'ego_world_matrix':matrix(self._ego.get_transform()),'camera_world_matrix':matrix(sample.rgb.transform),'camera_width':sample.rgb.width,'camera_height':sample.rgb.height,'camera_fov':float(self._sensors.actors['rgb_front'].attributes.get('fov',100)),'truth_for_evaluation_only':truth,'truth_lane_for_evaluation_only':lanes})
 except Exception as e: errors.append(f'{type(e).__name__}: {e}')
 return sample

def submit(self,envelope,scene,vehicle,**kwargs):
 commands.append({'frame':scene.frame,'text':envelope.get('source_text')})
 return orig_submit(self,envelope,scene,vehicle,**kwargs)

orig_infer=QwenServiceClient.infer
def infer_with_shadow(self,request):
 req=copy.deepcopy(request);frame=req.get('scene_summary',{}).get('frame_id');results=shadow_by_frame.get(frame,[])
 by_id={x['track_id']:x for x in results};changed=[]
 for target in req.get('targets',[]):
  item=by_id.get(target['target_id'])
  if not item or item.get('status')!='FUSED_UNVALIDATED':continue
  target['distance_m']=item['distance_m']
  lane={'SAME':'center_ahead','OTHER':'other_lane'}.get(item['lane_relation'],'unknown')
  target['relation']=f"{lane}; unvalidated radar radial velocity {item['radial_velocity_mps']:+.2f} m/s"
  target['relative_speed_mps']=None
  changed.append({'target_id':item['track_id'],'distance_m':item['distance_m'],'lane_relation':item['lane_relation'],'radial_velocity_mps':item['radial_velocity_mps'],'quality':'UNVALIDATED_SHADOW'})
 augmented_requests.append({'frame':frame,'changed':changed,'targets_sent':copy.deepcopy(req.get('targets',[]))})
 return orig_infer(self,req)

if __name__=='__main__':
 CarlaPerceptionBridge.acquire=acquire;CanonicalRuntimeBridge.submit=submit
 if os.environ.get('SHADOW_MODEL_INPUT')=='1':QwenServiceClient.infer=infer_with_shadow
 try:carla_runner.main()
 finally:
  out=Path(os.environ['SHADOW_EVAL_DIR']);out.mkdir(parents=True,exist_ok=True)
  with (out/'shadow_and_evaluation_truth.jsonl').open('w') as f:
   for x in records:f.write(json.dumps(x,ensure_ascii=False)+'\n')
  (out/'observer_status.json').write_text(json.dumps({'frames':len(records),'commands':commands,'errors':errors},ensure_ascii=False,indent=2))
  (out/'augmented_model_requests.json').write_text(json.dumps(augmented_requests,ensure_ascii=False,indent=2))
  print('SHADOW_OBSERVER',len(records),'frames',len(commands),'commands',len(errors),'errors',flush=True)
