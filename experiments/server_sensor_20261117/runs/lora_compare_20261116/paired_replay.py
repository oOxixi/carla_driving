"""Exact captured requests, two real model services, independent GT audit only."""
import copy,glob,json,time,math
from pathlib import Path
import numpy as np
from qwen_service.client import QwenServiceClient
ROOT=Path('/home/tiaozhansai/carla-driving-target-and-provement');OUT=ROOT/'artifacts/runtime/lora_compare_20261116';results=[]
clients={'base':QwenServiceClient('http://127.0.0.1:18161',timeout_s=30),'v14':QwenServiceClient('http://127.0.0.1:28761',timeout_s=30)}
for case in ('40m','60m','occlusion'):
 p=ROOT/'artifacts/runtime/live_demo_20261116'/case
 rows=[json.loads(x) for x in open(glob.glob(str(p/'EXPERIMENT*.jsonl'))[0])]; route=next(x for x in rows if x.get('record_type')=='canonical_routing' and x.get('phase')=='SUBMIT');request=route['payload']['orchestration']['model_request'];frame=request['scene_summary']['frame_id'];obs=next(json.loads(l) for l in open(p/'evaluation/shadow_and_evaluation_truth.jsonl') if json.loads(l)['frame']==frame)
 camera=np.linalg.inv(np.asarray(obs['camera_world_matrix']));w,h=obs['camera_width'],obs['camera_height'];f=w/(2*math.tan(math.radians(obs['camera_fov'])/2));truth=[]
 for a in obs['truth_for_evaluation_only']:
  if a['role_name'].endswith(':ego'):continue
  v=np.asarray(a['vertices_world']);q=np.column_stack((v,np.ones(len(v))))@camera.T
  if (q[:,0]<=0).any():continue
  u=f*q[:,1]/q[:,0]+w/2;z=-f*q[:,2]/q[:,0]+h/2;truth.append((a['role_name'].split(':')[-1],[min(u),min(z),max(u),max(z)]))
 def iou(a,b):
  inter=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]));return inter/max((a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-inter,1e-9)
 associations={}
 for item in request.get('target_grounding',{}).get('visual_candidates',[]):
  box=[v*([w,h,w,h][i]) for i,v in enumerate(item['bbox_xyxy_norm'])];associations[item['target_id']]={role:round(float(iou(box,b)),3) for role,b in truth}
 for model in ('base','v14'):
  q=copy.deepcopy(request);q['request_id']=f'paired-{case}-{model}';q['created_at_ns']=time.monotonic_ns();q['deadline_ns']=q['created_at_ns']+25_000_000_000
  begin=time.monotonic()
  try:
   result=clients[model].infer(q);ground=result.get('model_grounding') or {};choice=ground.get('target_id');entry={'case':case,'frame':frame,'model':model,'model_id':result.get('model_id'),'choice':ground,'target_overlaps':associations.get(choice,{}),'all_candidate_overlaps':associations,'elapsed_ms':round((time.monotonic()-begin)*1000),'reason_code':result.get('reason_code')}
  except Exception as e:entry={'case':case,'frame':frame,'model':model,'error':f'{type(e).__name__}: {e}'}
  results.append(entry);print(json.dumps(entry,ensure_ascii=False),flush=True)
(OUT/'paired_replay.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
