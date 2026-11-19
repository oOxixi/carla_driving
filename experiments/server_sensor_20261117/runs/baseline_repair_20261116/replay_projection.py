import json,numpy as np
from types import SimpleNamespace as NS
from integration.actor_projection_audit import projected_actor_aliases
for case in ('40m','60m','occlusion'):
 base='/home/tiaozhansai/carla-driving-target-and-provement/artifacts/runtime/live_demo_20261116/'+case+'/evaluation/'
 st=json.load(open(base+'observer_status.json')); frame=st['commands'][0]['frame'];row=next(json.loads(x) for x in open(base+'shadow_and_evaluation_truth.jsonl') if json.loads(x)['frame']==frame)
 rgb=NS(frame=frame,width=row['camera_width'],height=row['camera_height'],transform=NS(get_inverse_matrix=lambda:np.linalg.inv(np.asarray(row['camera_world_matrix'])).tolist()));scene=NS(frame=frame,detected_objects=[NS(**x) for x in row['scene']['detected_objects']]);actors=[]
 for a in row['truth_for_evaluation_only']:
  if a['role_name'].endswith(':ego'):continue
  vertices=[NS(x=v[0],y=v[1],z=v[2]) for v in a['vertices_world']];bbox=NS(get_world_vertices=lambda _,v=vertices:v);actor=NS(is_alive=True,bounding_box=bbox,get_transform=lambda:None);actors.append((actor,{'type':'vehicle','actor_id':a['role_name'].split(':')[-1]}))
 print(case,'command_frame',frame,'associations',projected_actor_aliases(scene,rgb,actors,row['camera_fov']))
